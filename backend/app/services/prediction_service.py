from __future__ import annotations

import json
import logging
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import requests
from fastapi import UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import FASTAPI_ROOT, REPO_ROOT, settings
from app.services.data_collector import DataCollector
from app.services.legacy_runtime import load_legacy_runtime
from app.services.oss_service import oss_service
from app.services.persistence import (
    create_camera_record,
    create_data_collection_record,
    create_img_record,
    create_video_record,
)
from app.services.socket_manager import socket_manager
from app.utils.common import JSONDict, cleanup_temp_dir, download_url_to_path, success


logger = logging.getLogger(__name__)


@dataclass
class VideoSession:
    session_id: str
    cap: any = None
    video_writer: any = None
    tracker: any = None
    data: JSONDict = field(default_factory=dict)
    stop_flag: bool = False
    is_processing: bool = False
    data_collector: DataCollector | None = None
    temp_dir: Path = field(init=False)
    download_path: Path = field(init=False)
    output_path: Path = field(init=False)
    video_output_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"video_{self.session_id}_"))
        self.download_path = self.temp_dir / "input.mp4"
        self.output_path = self.temp_dir / "output.mp4"
        self.video_output_path = self.temp_dir / "output.avi"


class PredictionService:
    def __init__(self) -> None:
        self.runtime = load_legacy_runtime()
        self.video_sessions: dict[str, VideoSession] = {}
        self.sessions_lock = threading.Lock()
        self.camera_lock = threading.Lock()
        self.camera_session: dict | None = None
        self.recording = False
        self.cap = None
        self.tracker = None
        self.current_kind = ""
        self.current_conf = 0.5
        self.esp32_socket = None
        self.is_recording_video = False
        self.recorded_frames: list[np.ndarray] = []
        self.recorded_original_frames: list[np.ndarray] = []
        self.camera_data_collector: DataCollector | None = None
        self.camera_meta: JSONDict = {}
        self._started = False
        self._heartbeat_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _heartbeat_loop(self) -> None:
        while True:
            time.sleep(settings.socketio_heartbeat_interval)
            socket_manager.emit_nowait("ping", {"timestamp": time.time()})
            socket_manager.emit_nowait("heartbeat", {"keepalive": True})

    def _json_error(self, message: str, status_code: int = 400, code: int = 400) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={"status": status_code, "message": message, "code": code},
        )

    def _resolve_kind(self, model_key: str) -> tuple[str, str]:
        legacy_config = self.runtime.config
        kind = model_key if model_key in legacy_config.MODELS_CONFIG else legacy_config.get_kind_by_model_name(model_key)
        if not kind:
            kind = model_key
        model_name = legacy_config.get_model_name_by_kind(kind) or model_key
        return kind, model_name

    def _resolve_local_path(self, value: str) -> Path:
        raw_value = value[1:] if value.startswith("/") else value
        candidates = [
            REPO_ROOT / raw_value,
            FASTAPI_ROOT / raw_value,
            Path(raw_value),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"Local file not found: {value}")

    def _download_file(self, url: str, save_path: Path, max_retries: int = 3, timeout: int = 30) -> None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(max_retries):
            try:
                with requests.get(url, stream=True, timeout=timeout) as response:
                    response.raise_for_status()
                    with save_path.open("wb") as file_handle:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                file_handle.write(chunk)
                if save_path.exists() and save_path.stat().st_size > 0:
                    return
                raise RuntimeError("Downloaded file is empty")
            except Exception:
                if save_path.exists():
                    save_path.unlink(missing_ok=True)
                if attempt == max_retries - 1:
                    raise
                time.sleep(2**attempt)

    def _cleanup_video_session(self, session: VideoSession) -> None:
        if session.cap and session.cap.isOpened():
            session.cap.release()
        if session.video_writer:
            session.video_writer.release()
        session.is_processing = False

    def _cleanup_video_files(self, session: VideoSession) -> None:
        cleanup_temp_dir(str(session.temp_dir))

    def get_models(self) -> JSONDict:
        model_items = []
        for kind, cfg in self.runtime.config.MODELS_CONFIG.items():
            model_items.append(
                {
                    "modelKey": kind,
                    "modelName": cfg.get("name", kind),
                    "classes": cfg.get("classes", []),
                }
            )
        return success({"models": model_items})

    def file_names(self, model_key: str | None) -> JSONDict:
        if not model_key:
            return {"weight_items": []}

        legacy_config = self.runtime.config
        config_obj = legacy_config.get_model_config(model_key) or legacy_config.get_config_by_model_name(model_key)
        if not config_obj:
            return {"weight_items": []}
        model_name = config_obj.get("name", model_key)
        return {"weight_items": [{"modelKey": model_key, "modelName": model_name}]}

    async def upload_file(self, file: UploadFile, category: str = "img_predict") -> JSONDict:
        if not file.filename:
            return {"error": "No file provided"}
        file_bytes = await file.read()
        file_url = oss_service.upload_bytes_for_category(file_bytes, file.filename, category)
        if file_url:
            return {"url": file_url, "data": file_url}
        return {"error": "OSS upload failed"}

    def serve_upload(self, category: str, filename: str) -> JSONResponse:
        del category, filename
        return JSONResponse({"error": "Local file serving is disabled, all files live in OSS"}, status_code=404)

    def predict_image(self, payload: JSONDict) -> JSONDict:
        model_key = payload.get("modelKey", "") or payload.get("kind", "")
        if not model_key:
            return {"status": 400, "message": "No model key provided", "code": 400}

        img_url = payload.get("inputImg", "")
        if not img_url:
            return {"status": 400, "message": "No image URL provided", "code": 400}

        kind, _model_name = self._resolve_kind(model_key)
        temp_dir = Path(tempfile.mkdtemp(prefix="predict_img_"))
        local_img_path: Path | None = None
        result_path = temp_dir / "result.jpg"
        result_data: JSONDict = {
            "username": payload.get("username", ""),
            "conf": payload.get("conf", "0.5"),
            "startTime": payload.get("startTime", ""),
            "inputImg": img_url,
            "modelKey": model_key,
            "cropType": payload.get("cropType", ""),
            "boxes": [],
        }

        try:
            if img_url.startswith("http://") or img_url.startswith("https://"):
                local_img_path = temp_dir / f"{uuid.uuid4().hex}.jpg"
                download_url_to_path(img_url, local_img_path)
            else:
                local_img_path = self._resolve_local_path(img_url)

            predictor = self.runtime.ONNXPredictor(
                kind=kind,
                img_path=str(local_img_path),
                save_path=str(result_path),
                conf=float(result_data.get("conf", 0.5)),
            )
            results = predictor.predict()
            uploaded_url = oss_service.upload_file(result_path, "img_predict")

            result_data["status"] = 200
            result_data["outImg"] = uploaded_url
            result_data["allTime"] = results.get("allTime", "")
            result_data["boxes"] = results.get("boxes", [])

            if len(results.get("boxes", [])) == 0:
                result_data["confidence"] = json.dumps([], ensure_ascii=False)
                result_data["label"] = json.dumps([], ensure_ascii=False)
                result_data["message"] = "No target detected"
            else:
                result_data["confidence"] = json.dumps(results.get("confidences", []), ensure_ascii=False)
                result_data["label"] = json.dumps(results.get("labels", []), ensure_ascii=False)
                result_data["message"] = "Prediction completed"

            create_img_record(
                {
                    "username": result_data["username"],
                    "modelKey": result_data["modelKey"],
                    "cropType": result_data["cropType"],
                    "label": result_data["label"],
                    "conf": result_data["conf"],
                    "confidence": result_data["confidence"],
                    "allTime": result_data["allTime"],
                    "startTime": result_data["startTime"],
                    "inputImg": result_data["inputImg"],
                    "outImg": result_data["outImg"],
                }
            )
        except Exception as exc:
            logger.exception("predict_image failed")
            result_data["status"] = 500
            result_data["message"] = f"Prediction failed: {exc}"
        finally:
            cleanup_temp_dir(str(temp_dir))

        return result_data

    def predict_video(
        self,
        *,
        session_id: str | None,
        model_key: str,
        input_video: str,
        username: str,
        start_time: str,
        conf: str,
        fps: str | None,
    ):
        if not input_video:
            return self._json_error("Input video URL is empty")

        session_id = session_id or uuid.uuid4().hex[:8]
        with self.sessions_lock:
            existing = self.video_sessions.get(session_id)
            if existing and existing.is_processing:
                existing.stop_flag = True
                time.sleep(0.3)
            session = VideoSession(session_id)
            self.video_sessions[session_id] = session

        kind, model_name = self._resolve_kind(model_key)
        session.data.update(
            {
                "username": username,
                "weight": model_name,
                "conf": conf,
                "startTime": start_time,
                "inputVideo": input_video,
                "kind": kind,
                "modelKey": model_key,
                "fps": fps,
                "sessionId": session_id,
            }
        )

        try:
            if input_video.startswith("/"):
                local_source_path = self._resolve_local_path(input_video)
                shutil.copy2(local_source_path, session.download_path)
            else:
                self._download_file(input_video, session.download_path)
        except Exception as exc:
            self._cleanup_video_files(session)
            with self.sessions_lock:
                self.video_sessions.pop(session_id, None)
            return self._json_error(f"Video download failed: {exc}")

        if not session.download_path.exists() or session.download_path.stat().st_size == 0:
            self._cleanup_video_files(session)
            with self.sessions_lock:
                self.video_sessions.pop(session_id, None)
            return self._json_error("Downloaded video file is empty or missing")

        cap = cv2.VideoCapture(str(session.download_path))
        if not cap.isOpened():
            self._cleanup_video_files(session)
            with self.sessions_lock:
                self.video_sessions.pop(session_id, None)
            return self._json_error("Unable to open the downloaded video file")

        session.cap = cap
        model_config = self.runtime.config.get_model_config(kind)
        conf_threshold = model_config.get("conf_threshold", float(conf or 0.5))
        tracker_type = self.runtime.tracker_config.DEFAULT_TRACKER
        original_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        output_fps = int(fps) if fps and fps.isdigit() else original_fps
        output_fps = max(output_fps, 1)

        session.video_writer = cv2.VideoWriter(
            str(session.video_output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            output_fps,
            (width, height),
        )
        session.tracker = self.runtime.TrackerPredictor(
            kind=kind,
            conf=conf_threshold,
            tracker_type=tracker_type,
            reset_id=True,
        )
        session.is_processing = True
        session.data_collector = DataCollector(oss_service, session_id, "video")

        def generate():
            frame_count = 0
            last_fps_time = time.time()
            fps_frame_count = 0
            processing_fps = 0.0
            try:
                while cap.isOpened() and not session.stop_flag:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame_count += 1
                    fps_frame_count += 1
                    now = time.time()
                    if now - last_fps_time >= 1.0:
                        processing_fps = fps_frame_count / (now - last_fps_time)
                        fps_frame_count = 0
                        last_fps_time = now

                    original_frame = frame.copy()
                    results = session.tracker.track_frame(frame)
                    processed_frame = session.tracker.draw_detections(original_frame, results, show_stats=False)

                    detections = results.get("detections", [])
                    if session.data_collector:
                        for det in detections:
                            track_id = det.get("track_id")
                            if track_id is not None:
                                session.data_collector.collect_detection(
                                    original_frame,
                                    track_id,
                                    det.get("class_name", "unknown"),
                                    det.get("bbox", [0, 0, 0, 0]),
                                    det.get("confidence", 0),
                                )

                    stats = results.get("stats", {})
                    current_frame = stats.get("current_frame", {})
                    bayesian_stats = stats.get("bayesian_stats", {})
                    track_stats = {
                        "sessionId": session_id,
                        "total_counts": stats.get("total_counts", {}),
                        "current_frame": current_frame,
                        "total_tracks": stats.get("total_tracks", 0),
                        "class_count": sum(1 for count in current_frame.values() if count > 0),
                        "interval": results.get("interval", 1),
                        "video_fps": original_fps,
                        "processing_fps": round(processing_fps, 1),
                        "frame_count": frame_count,
                        "total_frames": total_frames,
                        "bayesian_stats": {
                            "rematch_count": bayesian_stats.get("rematch_count", 0),
                            "stable_library_size": bayesian_stats.get("stable_library_size", 0),
                            "sigma_sq": bayesian_stats.get("sigma_sq", 0),
                            "rematched_ids": bayesian_stats.get("rematched_ids", []),
                        },
                    }
                    socket_manager.emit_nowait("track_stats", track_stats)

                    session.video_writer.write(processed_frame)
                    ok, jpeg = cv2.imencode(".jpg", processed_frame)
                    if ok:
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n"
                            + jpeg.tobytes()
                            + b"\r\n"
                        )
            finally:
                self._cleanup_video_session(session)
                try:
                    if not session.stop_flag:
                        socket_manager.emit_nowait(
                            "video_complete",
                            {"sessionId": session_id, "message": "Processing complete"},
                        )
                        for progress in self.convert_avi_to_mp4(session.video_output_path, session.output_path):
                            socket_manager.emit_nowait("progress", {"sessionId": session_id, "data": progress})
                        uploaded_url = oss_service.upload_file(session.output_path, "video_predict")
                        session.data["outVideo"] = uploaded_url
                        final_stats = session.tracker.get_stats() if session.tracker else {}
                        session.data["trackStats"] = json.dumps(final_stats, ensure_ascii=False)
                        create_video_record(
                            {
                                "username": session.data.get("username", ""),
                                "modelKey": session.data.get("modelKey", ""),
                                "startTime": session.data.get("startTime", ""),
                                "inputVideo": session.data.get("inputVideo", ""),
                                "outVideo": session.data.get("outVideo", ""),
                                "trackStats": session.data.get("trackStats", ""),
                            }
                        )
                        if session.data_collector:
                            summary = session.data_collector.save_summary(session.data.get("username", ""))
                            if summary:
                                create_data_collection_record(summary)
                                socket_manager.emit_nowait(
                                    "data_collection_complete",
                                    {"sessionId": session_id, "summary": summary},
                                )
                    else:
                        socket_manager.emit_nowait(
                            "video_stopped",
                            {"sessionId": session_id, "message": "Processing stopped"},
                        )
                finally:
                    self._cleanup_video_files(session)
                    with self.sessions_lock:
                        self.video_sessions.pop(session.session_id, None)

        return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

    def create_video_session(
        self,
        input_video: str,
        model_key: str,
        username: str,
        conf: str = "0.5"
    ) -> str:
        session_id = uuid.uuid4().hex[:8]
        with self.sessions_lock:
            existing = self.video_sessions.get(session_id)
            if existing and existing.is_processing:
                existing.stop_flag = True
                time.sleep(0.3)
            session = VideoSession(session_id)
            self.video_sessions[session_id] = session

        kind, model_name = self._resolve_kind(model_key)
        session.data.update({
            "username": username,
            "weight": model_name,
            "conf": conf,
            "startTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "inputVideo": input_video,
            "kind": kind,
            "modelKey": model_key,
            "sessionId": session_id,
            "progress": 0,
            "frame_count": 0,
            "total_counts": {},
            "total_tracks": 0,
            "detections": [],
        })

        thread = threading.Thread(
            target=self._video_processing_thread,
            args=(session_id,),
            daemon=True
        )
        thread.start()

        return session_id

    def _video_processing_thread(self, session_id: str) -> None:
        with self.sessions_lock:
            session = self.video_sessions.get(session_id)
            if not session:
                return

        try:
            self._download_and_process_video(session)
        except Exception as e:
            logger.exception(f"Video processing thread failed for session {session_id}")
            socket_manager.emit_nowait(
                "video_error",
                {"sessionId": session_id, "error": str(e)}
            )
        finally:
            with self.sessions_lock:
                if session_id in self.video_sessions:
                    self.video_sessions[session_id].is_processing = False

    def _download_and_process_video(self, session: VideoSession) -> None:
        input_video = session.data.get("inputVideo", "")
        session_id = session.session_id

        try:
            if input_video.startswith("/"):
                local_source_path = self._resolve_local_path(input_video)
                shutil.copy2(local_source_path, session.download_path)
            else:
                self._download_file(input_video, session.download_path)
        except Exception as exc:
            logger.exception("Video download failed")
            socket_manager.emit_nowait(
                "video_error",
                {"sessionId": session_id, "error": f"Video download failed: {exc}"}
            )
            return

        if not session.download_path.exists() or session.download_path.stat().st_size == 0:
            socket_manager.emit_nowait(
                "video_error",
                {"sessionId": session_id, "error": "Downloaded video file is empty or missing"}
            )
            return

        cap = cv2.VideoCapture(str(session.download_path))
        if not cap.isOpened():
            socket_manager.emit_nowait(
                "video_error",
                {"sessionId": session_id, "error": "Unable to open the downloaded video file"}
            )
            return

        session.cap = cap
        kind = session.data.get("kind", "")
        model_config = self.runtime.config.get_model_config(kind)
        conf_threshold = model_config.get("conf_threshold", float(session.data.get("conf", 0.5)))
        tracker_type = self.runtime.tracker_config.DEFAULT_TRACKER
        original_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        session.video_writer = cv2.VideoWriter(
            str(session.video_output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            original_fps,
            (width, height),
        )
        session.tracker = self.runtime.TrackerPredictor(
            kind=kind,
            conf=conf_threshold,
            tracker_type=tracker_type,
            reset_id=True,
        )
        session.is_processing = True
        session.data_collector = DataCollector(oss_service, session_id, "video")

        frame_count = 0
        keyframe_interval = max(1, original_fps // 2)
        last_fps_time = time.time()
        fps_frame_count = 0
        processing_fps = 0.0
        all_detections = []
        keyframe_count = 0

        try:
            while cap.isOpened() and not session.stop_flag:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                fps_frame_count += 1
                now = time.time()
                if now - last_fps_time >= 1.0:
                    processing_fps = fps_frame_count / (now - last_fps_time)
                    fps_frame_count = 0
                    last_fps_time = now

                original_frame = frame.copy()
                results = session.tracker.track_frame(frame)
                processed_frame = session.tracker.draw_detections(original_frame, results, show_stats=False)

                detections = results.get("detections", [])
                for det in detections:
                    track_id = det.get("track_id")
                    if track_id is not None:
                        detection_info = {
                            "track_id": track_id,
                            "class": det.get("class_name", "unknown"),
                            "confidence": det.get("confidence", 0),
                            "frame": frame_count,
                            "bbox": det.get("bbox", [0, 0, 0, 0]),
                        }
                        all_detections.append(detection_info)
                        if session.data_collector:
                            session.data_collector.collect_detection(
                                original_frame,
                                track_id,
                                det.get("class_name", "unknown"),
                                det.get("bbox", [0, 0, 0, 0]),
                                det.get("confidence", 0),
                            )

                if frame_count % keyframe_interval == 0:
                    keyframe_count += 1

                stats = results.get("stats", {})
                current_frame = stats.get("current_frame", {})
                bayesian_stats = stats.get("bayesian_stats", {})
                progress = (frame_count / total_frames * 100) if total_frames > 0 else 0

                session.data["progress"] = progress
                session.data["frame_count"] = frame_count
                session.data["total_counts"] = stats.get("total_counts", {})
                session.data["total_tracks"] = stats.get("total_tracks", 0)
                session.data["detections"] = all_detections[-100:]

                track_stats = {
                    "sessionId": session_id,
                    "total_counts": stats.get("total_counts", {}),
                    "current_frame": current_frame,
                    "total_tracks": stats.get("total_tracks", 0),
                    "class_count": sum(1 for count in current_frame.values() if count > 0),
                    "interval": results.get("interval", 1),
                    "video_fps": original_fps,
                    "processing_fps": round(processing_fps, 1),
                    "frame_count": frame_count,
                    "total_frames": total_frames,
                    "progress": round(progress, 1),
                    "keyframe_count": keyframe_count,
                    "bayesian_stats": {
                        "rematch_count": bayesian_stats.get("rematch_count", 0),
                        "stable_library_size": bayesian_stats.get("stable_library_size", 0),
                        "sigma_sq": bayesian_stats.get("sigma_sq", 0),
                        "rematched_ids": bayesian_stats.get("rematched_ids", []),
                    },
                }
                socket_manager.emit_nowait("track_stats", track_stats)

                session.video_writer.write(processed_frame)

        finally:
            self._cleanup_video_session(session)
            try:
                if not session.stop_flag:
                    socket_manager.emit_nowait(
                        "video_complete",
                        {"sessionId": session_id, "message": "Processing complete"},
                    )
                    for progress_val in self.convert_avi_to_mp4(session.video_output_path, session.output_path):
                        socket_manager.emit_nowait("progress", {"sessionId": session_id, "data": progress_val})
                    uploaded_url = oss_service.upload_file(session.output_path, "video_predict")
                    session.data["outVideo"] = uploaded_url
                    final_stats = session.tracker.get_stats() if session.tracker else {}
                    session.data["trackStats"] = json.dumps(final_stats, ensure_ascii=False)
                    create_video_record({
                        "username": session.data.get("username", ""),
                        "modelKey": session.data.get("modelKey", ""),
                        "startTime": session.data.get("startTime", ""),
                        "inputVideo": session.data.get("inputVideo", ""),
                        "outVideo": session.data.get("outVideo", ""),
                        "trackStats": session.data.get("trackStats", ""),
                    })
                    if session.data_collector:
                        summary = session.data_collector.save_summary(session.data.get("username", ""))
                        if summary:
                            create_data_collection_record(summary)
                            socket_manager.emit_nowait(
                                "data_collection_complete",
                                {"sessionId": session_id, "summary": summary},
                            )
                else:
                    socket_manager.emit_nowait(
                        "video_stopped",
                        {"sessionId": session_id, "message": "Processing stopped"},
                    )
            finally:
                self._cleanup_video_files(session)
                with self.sessions_lock:
                    self.video_sessions.pop(session.session_id, None)

    def process_video_task(
        self,
        task_session_id: str,
        input_video: str,
        model_key: str,
        username: str,
        conf: str = "0.5",
        should_stop: Callable[[], bool] | None = None,
        progress_callback: Callable[[JSONDict], None] | None = None,
    ) -> JSONDict:
        session = VideoSession(task_session_id)
        kind, model_name = self._resolve_kind(model_key)
        session.data.update(
            {
                "username": username,
                "weight": model_name,
                "conf": conf,
                "startTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "inputVideo": input_video,
                "kind": kind,
                "modelKey": model_key,
                "sessionId": task_session_id,
                "progress": 0,
                "frame_count": 0,
                "total_counts": {},
                "total_tracks": 0,
                "detections": [],
            }
        )
        session.data_collector = DataCollector(oss_service, task_session_id, "video")

        if progress_callback:
            progress_callback(
                {
                    "status": "queued",
                    "progress": 0.0,
                    "frame_count": 0,
                    "total_counts": {},
                    "total_tracks": 0,
                    "detections": [],
                }
            )

        try:
            try:
                if input_video.startswith("/"):
                    local_source_path = self._resolve_local_path(input_video)
                    shutil.copy2(local_source_path, session.download_path)
                else:
                    self._download_file(input_video, session.download_path)
            except Exception as exc:
                logger.exception("Video download failed")
                return {"status": "failed", "error": f"Video download failed: {exc}"}

            if not session.download_path.exists() or session.download_path.stat().st_size == 0:
                return {"status": "failed", "error": "Downloaded video file is empty or missing"}

            cap = cv2.VideoCapture(str(session.download_path))
            if not cap.isOpened():
                return {"status": "failed", "error": "Unable to open the downloaded video file"}

            session.cap = cap
            model_config = self.runtime.config.get_model_config(kind)
            conf_threshold = model_config.get("conf_threshold", float(session.data.get("conf", 0.5)))
            tracker_type = self.runtime.tracker_config.DEFAULT_TRACKER
            original_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            session.video_writer = cv2.VideoWriter(
                str(session.video_output_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                original_fps,
                (width, height),
            )
            session.tracker = self.runtime.TrackerPredictor(
                kind=kind,
                conf=conf_threshold,
                tracker_type=tracker_type,
                reset_id=True,
            )
            session.is_processing = True

            frame_count = 0
            keyframe_interval = max(1, original_fps // 2)
            all_detections = []
            keyframe_count = 0

            while cap.isOpened() and not session.stop_flag:
                if should_stop and should_stop():
                    session.stop_flag = True
                    break

                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                original_frame = frame.copy()
                results = session.tracker.track_frame(frame)
                processed_frame = session.tracker.draw_detections(original_frame, results, show_stats=False)

                detections = results.get("detections", [])
                for det in detections:
                    track_id = det.get("track_id")
                    if track_id is None:
                        continue
                    detection_info = {
                        "track_id": track_id,
                        "class": det.get("class_name", "unknown"),
                        "confidence": det.get("confidence", 0),
                        "frame": frame_count,
                        "bbox": det.get("bbox", [0, 0, 0, 0]),
                    }
                    all_detections.append(detection_info)
                    if session.data_collector:
                        session.data_collector.collect_detection(
                            original_frame,
                            track_id,
                            det.get("class_name", "unknown"),
                            det.get("bbox", [0, 0, 0, 0]),
                            det.get("confidence", 0),
                        )

                if frame_count % keyframe_interval == 0:
                    keyframe_count += 1

                stats = results.get("stats", {})
                progress = (frame_count / total_frames * 100) if total_frames > 0 else 0
                session.data["progress"] = progress
                session.data["frame_count"] = frame_count
                session.data["total_counts"] = stats.get("total_counts", {})
                session.data["total_tracks"] = stats.get("total_tracks", 0)
                session.data["detections"] = all_detections[-100:]

                if progress_callback and (
                    frame_count == 1
                    or frame_count % keyframe_interval == 0
                    or (total_frames > 0 and frame_count >= total_frames)
                ):
                    progress_callback(
                        {
                            "status": "processing",
                            "progress": round(progress, 1),
                            "frame_count": frame_count,
                            "total_counts": session.data.get("total_counts", {}),
                            "total_tracks": int(session.data.get("total_tracks", 0)),
                            "detections": list(session.data.get("detections", [])),
                            "keyframe_count": keyframe_count,
                        }
                    )

                track_stats = {
                    "sessionId": task_session_id,
                    "total_counts": stats.get("total_counts", {}),
                    "current_frame": stats.get("current_frame", {}),
                    "total_tracks": stats.get("total_tracks", 0),
                    "class_count": sum(
                        1 for count in (stats.get("current_frame", {}) or {}).values() if count > 0
                    ),
                    "interval": results.get("interval", 1),
                    "video_fps": original_fps,
                    "processing_fps": 0.0,
                    "frame_count": frame_count,
                    "total_frames": total_frames,
                    "progress": round(progress, 1),
                    "keyframe_count": keyframe_count,
                    "bayesian_stats": stats.get("bayesian_stats", {}),
                }
                socket_manager.emit_nowait("track_stats", track_stats)
                session.video_writer.write(processed_frame)

            self._cleanup_video_session(session)

            final_stats = session.tracker.get_stats() if session.tracker else {}
            total_counts = session.data.get("total_counts", {})
            total_tracks = int(session.data.get("total_tracks", 0))
            detections_tail = list(session.data.get("detections", []))

            if session.stop_flag:
                if progress_callback:
                    progress_callback(
                        {
                            "status": "stopped",
                            "progress": round(float(session.data.get("progress", 0.0)), 1),
                            "frame_count": int(session.data.get("frame_count", 0)),
                            "total_counts": total_counts,
                            "total_tracks": total_tracks,
                            "detections": detections_tail,
                        }
                    )
                return {
                    "status": "stopped",
                    "frame_count": int(session.data.get("frame_count", 0)),
                    "total_counts": total_counts,
                    "total_tracks": total_tracks,
                    "detections": detections_tail,
                }

            for progress_val in self.convert_avi_to_mp4(session.video_output_path, session.output_path):
                socket_manager.emit_nowait("progress", {"sessionId": task_session_id, "data": progress_val})

            uploaded_url = oss_service.upload_file(session.output_path, "video_predict")
            session.data["outVideo"] = uploaded_url
            session.data["trackStats"] = json.dumps(final_stats, ensure_ascii=False)

            create_video_record(
                {
                    "username": session.data.get("username", ""),
                    "modelKey": session.data.get("modelKey", ""),
                    "startTime": session.data.get("startTime", ""),
                    "inputVideo": session.data.get("inputVideo", ""),
                    "outVideo": session.data.get("outVideo", ""),
                    "trackStats": session.data.get("trackStats", ""),
                }
            )

            if session.data_collector:
                summary = session.data_collector.save_summary(session.data.get("username", ""))
                if summary:
                    create_data_collection_record(summary)
                    socket_manager.emit_nowait(
                        "data_collection_complete",
                        {"sessionId": task_session_id, "summary": summary},
                    )

            if progress_callback:
                progress_callback(
                    {
                        "status": "completed",
                        "progress": 100.0,
                        "frame_count": int(session.data.get("frame_count", 0)),
                        "total_counts": total_counts,
                        "total_tracks": total_tracks,
                        "detections": detections_tail,
                        "output_url": uploaded_url,
                    }
                )

            return {
                "status": "completed",
                "output_url": uploaded_url,
                "frame_count": int(session.data.get("frame_count", 0)),
                "total_counts": total_counts,
                "total_tracks": total_tracks,
                "detections": detections_tail,
            }
        except Exception as exc:
            logger.exception("Video task processing failed")
            return {
                "status": "failed",
                "error": str(exc),
                "frame_count": int(session.data.get("frame_count", 0)),
                "total_counts": session.data.get("total_counts", {}),
                "total_tracks": int(session.data.get("total_tracks", 0)),
                "detections": list(session.data.get("detections", [])),
            }
        finally:
            self._cleanup_video_session(session)
            self._cleanup_video_files(session)

    def get_video_session_status(self, session_id: str) -> JSONDict | None:
        with self.sessions_lock:
            session = self.video_sessions.get(session_id)
            if not session:
                return None

            session_data = session.data.copy() if session.data else {}
            return {
                "session_id": session_id,
                "is_processing": session.is_processing,
                "progress": session_data.get("progress", 0),
                "frame_count": session_data.get("frame_count", 0),
                "total_counts": session_data.get("total_counts", {}),
                "total_tracks": session_data.get("total_tracks", 0),
                "detections": session_data.get("detections", []),
                "data": session_data
            }

    def get_video_stream(self, session_id: str):
        from fastapi.responses import StreamingResponse

        with self.sessions_lock:
            session = self.video_sessions.get(session_id)
            if not session:
                return JSONResponse({"error": "Session not found"}, status_code=404)

            if session.is_processing:
                return JSONResponse({"error": "Session still processing"}, status_code=409)

            if not session.output_path.exists():
                return JSONResponse({"error": "Output video not ready"}, status_code=404)

        def generate():
            with open(session.output_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        return StreamingResponse(
            generate(),
            media_type="video/mp4",
            headers={"Content-Disposition": f"inline; filename={session_id}.mp4"}
        )

    def stop_video_session(self, session_id: str) -> JSONDict:
        with self.sessions_lock:
            if session_id and session_id in self.video_sessions:
                self.video_sessions[session_id].stop_flag = True
                return {"status": 200, "message": "Stopping video processing", "code": 0}
        return {"status": 200, "message": "Session not found", "code": 404}

    def stop_video(self, session_id: str) -> JSONDict:
        with self.sessions_lock:
            if session_id and session_id in self.video_sessions:
                self.video_sessions[session_id].stop_flag = True
                return {"status": 200, "message": "Stopping video processing", "code": 0}
            if not session_id:
                for session in self.video_sessions.values():
                    if session.is_processing:
                        session.stop_flag = True
                return {"status": 200, "message": "Stopping all video processing", "code": 0}
        return {"status": 200, "message": "No active video processing", "code": 0}

    def predict_camera(
        self,
        *,
        model_key: str,
        username: str,
        start_time: str,
        conf: str,
        fps: str | None,
        stream_source: str,
        esp32_ip: str,
        esp32_port: int,
    ):
        with self.camera_lock:
            if self.camera_session and self.camera_session.get("is_processing"):
                return self._json_error("Camera is already in use")
            self.camera_session = {"is_processing": True, "stop_flag": False}

        kind, model_name = self._resolve_kind(model_key)
        model_config = self.runtime.config.get_model_config(kind)
        conf_threshold = model_config.get("conf_threshold", float(conf or 0.5))
        self.current_kind = kind
        self.current_conf = conf_threshold
        self.camera_meta = {
            "username": username,
            "weight": model_name,
            "kind": kind,
            "conf": conf_threshold,
            "startTime": start_time,
            "modelKey": model_key,
            "fps": fps,
            "streamSource": stream_source,
            "esp32Ip": esp32_ip,
            "esp32Port": esp32_port,
        }

        input_size = self.runtime.config.get_input_size(kind)
        tracker_type = self.runtime.tracker_config.DEFAULT_TRACKER
        tracker_config_dict = self.runtime.tracker_config.get_tracker_config(tracker_type)
        configured_fps = int(fps) if fps and fps.isdigit() else int(tracker_config_dict.get("frame_rate", 30))

        self.tracker = self.runtime.TrackerPredictor(
            kind=kind,
            conf=conf_threshold,
            tracker_type=tracker_type,
            reset_id=True,
        )

        is_esp32 = stream_source == "esp32" and bool(esp32_ip)
        if is_esp32:
            self._send_esp32_command(esp32_ip, 81, "start", video_port=esp32_port)
            self.esp32_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.esp32_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.esp32_socket.bind(("0.0.0.0", esp32_port))
            self.cap = None
        else:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, input_size[1])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, input_size[0])
            self.cap.set(cv2.CAP_PROP_FPS, configured_fps)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = None
                with self.camera_lock:
                    if self.camera_session:
                        self.camera_session["is_processing"] = False
                return self._json_error("Unable to open local camera", status_code=500, code=500)

        self.recording = True
        self.camera_data_collector = DataCollector(oss_service, str(uuid.uuid4()), "camera")

        def generate():
            consecutive_errors = 0
            max_consecutive_errors = 50
            esp32_first_frame = True
            frame_count = 0
            last_fps_time = time.time()
            fps_frame_count = 0
            processing_fps = 0.0
            video_fps = 0.0
            try:
                while self.recording and not self.camera_session.get("stop_flag"):
                    if is_esp32:
                        frame = self._receive_esp32_frame(wait_for_data=esp32_first_frame)
                        if esp32_first_frame:
                            esp32_first_frame = False
                        if frame is None:
                            consecutive_errors += 1
                            if consecutive_errors > max_consecutive_errors:
                                break
                            continue
                        consecutive_errors = 0
                    else:
                        ret, frame = self.cap.read()
                        if not ret:
                            break

                    frame_count += 1
                    fps_frame_count += 1
                    now = time.time()
                    elapsed = now - last_fps_time
                    if elapsed >= 1.0:
                        processing_fps = fps_frame_count / elapsed
                        if is_esp32:
                            video_fps = processing_fps
                        fps_frame_count = 0
                        last_fps_time = now

                    try:
                        results = self.tracker.track_frame(frame)
                        processed_frame = self.tracker.draw_detections(frame, results, show_stats=False)

                        if self.is_recording_video:
                            self.recorded_frames.append(processed_frame.copy())
                            self.recorded_original_frames.append(frame.copy())
                            if len(self.recorded_frames) > 3000:
                                self.recorded_frames.pop(0)
                                self.recorded_original_frames.pop(0)

                        detections = results.get("detections", [])
                        if self.camera_data_collector:
                            for det in detections:
                                track_id = det.get("track_id")
                                if track_id is not None:
                                    self.camera_data_collector.collect_detection(
                                        frame,
                                        track_id,
                                        det.get("class_name", "unknown"),
                                        det.get("bbox", [0, 0, 0, 0]),
                                        det.get("confidence", 0),
                                    )

                        stats = results.get("stats", {})
                        current_frame = stats.get("current_frame", {})
                        bayesian_stats = stats.get("bayesian_stats", {})
                        socket_manager.emit_nowait(
                            "camera_track_stats",
                            {
                                "total_counts": stats.get("total_counts", {}),
                                "current_frame": current_frame,
                                "total_tracks": stats.get("total_tracks", 0),
                                "class_count": sum(1 for count in current_frame.values() if count > 0),
                                "interval": results.get("interval", 1),
                                "video_fps": round(video_fps, 1) if is_esp32 else configured_fps,
                                "processing_fps": round(processing_fps, 1),
                                "frame_count": frame_count,
                                "bayesian_stats": {
                                    "rematch_count": bayesian_stats.get("rematch_count", 0),
                                    "stable_library_size": bayesian_stats.get("stable_library_size", 0),
                                    "sigma_sq": bayesian_stats.get("sigma_sq", 0),
                                    "rematched_ids": bayesian_stats.get("rematched_ids", []),
                                },
                            },
                        )

                        ok, jpeg = cv2.imencode(".jpg", processed_frame)
                        if ok:
                            yield (
                                b"--frame\r\n"
                                b"Content-Type: image/jpeg\r\n\r\n"
                                + jpeg.tobytes()
                                + b"\r\n"
                            )
                    except Exception:
                        consecutive_errors += 1
                        if consecutive_errors > max_consecutive_errors:
                            break
                        continue
            finally:
                if self.cap:
                    self.cap.release()
                    self.cap = None
                if is_esp32 and self.esp32_socket:
                    self.esp32_socket.close()
                    self.esp32_socket = None
                with self.camera_lock:
                    if self.camera_session:
                        self.camera_session["is_processing"] = False

        return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

    def start_camera_session(self, model_key: str, username: str) -> str:
        import uuid
        session_id = uuid.uuid4().hex[:8]

        with self.camera_lock:
            if self.camera_session and self.camera_session.get("is_processing"):
                self.stop_camera()

            kind, model_name = self._resolve_kind(model_key)
            model_config = self.runtime.config.get_model_config(kind)
            conf_threshold = model_config.get("conf_threshold", 0.35)

            self.camera_session = {
                "is_processing": True,
                "stop_flag": False,
                "session_id": session_id
            }
            self.camera_meta = {
                "username": username,
                "modelKey": model_key,
                "kind": kind,
                "conf": conf_threshold
            }

            input_size = self.runtime.config.get_input_size(kind)
            tracker_type = self.runtime.tracker_config.DEFAULT_TRACKER
            configured_fps = int(self.runtime.tracker_config.get_tracker_config(tracker_type).get("frame_rate", 30))

            self.tracker = self.runtime.TrackerPredictor(
                kind=kind,
                conf=conf_threshold,
                tracker_type=tracker_type,
                reset_id=True,
            )

            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, input_size[1])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, input_size[0])
            self.cap.set(cv2.CAP_PROP_FPS, configured_fps)

            self.recording = True
            self.camera_data_collector = DataCollector(oss_service, session_id, "camera")

        return session_id

    def get_camera_stream(self):
        from fastapi.responses import StreamingResponse

        with self.camera_lock:
            if not self.camera_session or not self.camera_session.get("is_processing"):
                return JSONResponse({"error": "Camera not started"}, status_code=404)

        def generate():
            while True:
                with self.camera_lock:
                    if not self.cap or not self.cap.isOpened():
                        break
                    if self.camera_session and self.camera_session.get("stop_flag"):
                        break

                ret, frame = self.cap.read()
                if not ret:
                    break

                original_frame = frame.copy()
                results = self.tracker.track_frame(frame)
                processed_frame = self.tracker.draw_detections(original_frame, results, show_stats=True)

                detections = results.get("detections", [])
                if self.camera_data_collector:
                    for det in detections:
                        track_id = det.get("track_id")
                        if track_id is not None:
                            self.camera_data_collector.collect_detection(
                                original_frame,
                                track_id,
                                det.get("class_name", "unknown"),
                                det.get("bbox", [0, 0, 0, 0]),
                                det.get("confidence", 0),
                            )

                stats = results.get("stats", {})
                socket_manager.emit_nowait("camera_stats", {
                    "sessionId": self.camera_session.get("session_id", ""),
                    "total_tracks": stats.get("total_tracks", 0),
                    "current_frame": stats.get("current_frame", {})
                })

                ok, jpeg = cv2.imencode(".jpg", processed_frame)
                if ok:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n"
                           + jpeg.tobytes()
                           + b"\r\n")

        return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

    def stop_camera(self) -> JSONDict:
        self.recording = False
        with self.camera_lock:
            if self.camera_session:
                self.camera_session["stop_flag"] = True

        if self.camera_meta.get("streamSource") == "esp32":
            esp32_ip = self.camera_meta.get("esp32Ip", "")
            if esp32_ip:
                self._send_esp32_command(esp32_ip, 81, "stop")

        if self.esp32_socket:
            self.esp32_socket.close()
            self.esp32_socket = None

        if self.camera_data_collector:
            summary = self.camera_data_collector.save_summary(self.camera_meta.get("username", ""))
            if summary:
                create_data_collection_record(summary)
            self.camera_data_collector = None

        return {"status": 200, "message": "Prediction completed", "code": 0}

    def start_recording(self) -> JSONDict:
        self.is_recording_video = True
        self.recorded_frames = []
        self.recorded_original_frames = []
        return {"status": 200, "message": "Recording started", "code": 0}

    def stop_recording(self, *, username: str, model_key: str, start_time: str) -> JSONDict:
        self.is_recording_video = False
        if not self.tracker:
            return {"status": 200, "message": "Recording stopped (no tracking data)", "code": 0}

        out_video_url = None
        input_video_url = None
        temp_dir = Path(tempfile.mkdtemp(prefix="camera_recording_"))
        try:
            final_stats = self.tracker.get_stats()
            if self.recorded_frames:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                height, width = self.recorded_frames[0].shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"XVID")
                fps = 20.0

                processed_path = temp_dir / f"camera_processed_{timestamp}.avi"
                original_path = temp_dir / f"camera_original_{timestamp}.avi"

                processed_writer = cv2.VideoWriter(str(processed_path), fourcc, fps, (width, height))
                for frame in self.recorded_frames:
                    processed_writer.write(frame)
                processed_writer.release()

                original_writer = cv2.VideoWriter(str(original_path), fourcc, fps, (width, height))
                for frame in self.recorded_original_frames:
                    original_writer.write(frame)
                original_writer.release()

                processed_final = self._convert_file_to_mp4_if_possible(processed_path)
                original_final = self._convert_file_to_mp4_if_possible(original_path)
                out_video_url = oss_service.upload_file(processed_final, "camera_predict")
                input_video_url = oss_service.upload_file(original_final, "camera_predict")

                self.recorded_frames = []
                self.recorded_original_frames = []

            create_camera_record(
                {
                    "modelKey": model_key,
                    "username": username,
                    "startTime": start_time,
                    "inputVideo": input_video_url,
                    "outVideo": out_video_url,
                    "trackStats": json.dumps(final_stats, ensure_ascii=False),
                }
            )
            return {"status": 200, "message": "Recording saved successfully", "code": 0, "videoUrl": out_video_url}
        except Exception as exc:
            logger.exception("stop_recording failed")
            return {"status": 500, "message": f"Save failed: {exc}", "code": -1}
        finally:
            cleanup_temp_dir(str(temp_dir))

    def convert_avi_to_mp4(self, temp_output: Path, output_path: Path):
        command = [
            settings.ffmpeg_binary,
            "-i",
            str(temp_output),
            "-vcodec",
            "libx264",
            str(output_path),
            "-y",
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        total_duration = self.get_video_duration(temp_output)
        if process.stderr is not None:
            for line in process.stderr:
                if "time=" not in line:
                    continue
                try:
                    time_str = line.split("time=")[1].split(" ")[0]
                    hours, minutes, seconds = map(float, time_str.split(":"))
                    processed_time = hours * 3600 + minutes * 60 + seconds
                    if total_duration > 0:
                        yield (processed_time / total_duration) * 100
                except Exception:
                    continue
        process.wait()
        yield 100

    def get_video_duration(self, path: Path) -> float:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        return total_frames / fps if fps > 0 else 0

    def _convert_file_to_mp4_if_possible(self, source_path: Path) -> Path:
        target_path = source_path.with_suffix(".mp4")
        command = [
            settings.ffmpeg_binary,
            "-i",
            str(source_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(target_path),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and target_path.exists():
                source_path.unlink(missing_ok=True)
                return target_path
        except Exception:
            pass
        return source_path

    def _get_local_ip(self) -> str:
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect(("8.8.8.8", 80))
            ip = probe.getsockname()[0]
            probe.close()
            return ip
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    def _send_esp32_command(self, esp32_ip: str, esp32_port: int, command: str, video_port: int | None = None) -> None:
        try:
            cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cmd_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            cmd_socket.bind((self._get_local_ip(), 0))
            payload = f"start:{video_port}" if command == "start" and video_port else command
            cmd_socket.sendto(payload.encode(), (esp32_ip, esp32_port))
            cmd_socket.close()
        except Exception:
            logger.exception("Failed to send ESP32 command")

    def _receive_esp32_frame(self, wait_for_data: bool = True):
        try:
            self.esp32_socket.settimeout(10.0 if wait_for_data else 1.0)
            frame_buffer = b""
            expected_length = 0
            receiving_frame = False
            packet_count = 0
            while self.recording:
                try:
                    data, _addr = self.esp32_socket.recvfrom(65535)
                    if len(data) >= 6 and data[0] == 0xAA and data[1] == 0xBB and data[2] == 0xCC:
                        expected_length = (data[3] << 8) | data[4]
                        frame_buffer = b""
                        receiving_frame = True
                        packet_count = 0
                        continue

                    if len(data) == 2 and data[0] == 0xDD and data[1] == 0xEE:
                        if receiving_frame and frame_buffer:
                            if expected_length > 0 and abs(len(frame_buffer) - expected_length) > 2000:
                                frame_buffer = b""
                                receiving_frame = False
                                continue
                            if len(frame_buffer) >= 2 and frame_buffer[0] == 0xFF and frame_buffer[1] == 0xD8:
                                image = cv2.imdecode(np.frombuffer(frame_buffer, dtype=np.uint8), cv2.IMREAD_COLOR)
                                if image is not None:
                                    return image
                        frame_buffer = b""
                        expected_length = 0
                        receiving_frame = False
                        packet_count = 0
                        continue

                    if receiving_frame and len(data) > 2:
                        frame_buffer += data[2:]
                        packet_count += 1
                        if packet_count > 1500 or len(frame_buffer) > 400000:
                            frame_buffer = b""
                            receiving_frame = False
                            packet_count = 0
                except socket.timeout:
                    if wait_for_data:
                        return None
                    continue
                except Exception:
                    continue
            return None
        except Exception:
            logger.exception("Failed to receive ESP32 frame")
            return None


prediction_service = PredictionService()
