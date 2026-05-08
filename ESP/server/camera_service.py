from __future__ import annotations

import socket
import threading
import time
from collections import deque
from typing import Any

import cv2
import numpy as np

from .config import settings
from .detector import EdgeDetectionEngine
from .protocol import PartialFrame, parse_packet


class CameraService:
    def __init__(self) -> None:
        self.detector: EdgeDetectionEngine | None = None
        self.lock = threading.Lock()
        self.frame_ready = threading.Condition(self.lock)
        self.running = False
        self.thread: threading.Thread | None = None
        self.sock: socket.socket | None = None
        self.partial_frames: dict[int, PartialFrame] = {}
        self.latest_jpeg: bytes | None = None
        self.latest_raw_jpeg: bytes | None = None
        self.latest_summary: dict[str, Any] = {
            "detections": [],
            "inference_ms": 0,
            "frame_id": None,
            "updated_at": None,
        }
        self.stats: dict[str, Any] = {
            "udp_host": settings.udp_host,
            "udp_port": settings.udp_port,
            "received_packets": 0,
            "received_frames": 0,
            "dropped_frames": 0,
            "decode_errors": 0,
            "inference_errors": 0,
            "fps": 0.0,
            "last_frame_age_sec": None,
            "last_sender": None,
            "error": None,
        }
        self._frame_times: deque[float] = deque(maxlen=30)

    def _get_detector(self) -> EdgeDetectionEngine:
        if self.detector is None:
            self.detector = EdgeDetectionEngine()
        return self.detector

    def start(self, udp_host: str | None = None, udp_port: int | None = None) -> dict[str, Any]:
        host = udp_host or settings.udp_host
        port = udp_port or settings.udp_port
        with self.lock:
            if self.running:
                already_running = True
            else:
                already_running = False
                self.running = True
                self.stats["error"] = None
                self.stats["udp_host"] = host
                self.stats["udp_port"] = port
                self.thread = threading.Thread(
                    target=self._run,
                    args=(host, port),
                    daemon=True,
                )
                self.thread.start()
        if already_running:
            return self.status()
        return self.status()

    def stop(self) -> dict[str, Any]:
        with self.lock:
            self.running = False
            sock = self.sock
            self.sock = None
            self.frame_ready.notify_all()
        if sock:
            try:
                sock.close()
            except OSError:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        return self.status()

    def status(self) -> dict[str, Any]:
        with self.lock:
            updated_at = self.latest_summary.get("updated_at")
            age = round(time.time() - updated_at, 2) if updated_at else None
            self.stats["last_frame_age_sec"] = age
            return {
                "running": self.running,
                "udp_host": self.stats.get("udp_host", settings.udp_host),
                "udp_port": self.stats.get("udp_port", settings.udp_port),
                "model_path": str(settings.model_path),
                **self.stats,
                "latest": {
                    "frame_id": self.latest_summary.get("frame_id"),
                    "detections": self.latest_summary.get("detections", []),
                    "inference_ms": self.latest_summary.get("inference_ms", 0),
                },
            }

    def latest(self) -> dict[str, Any]:
        with self.lock:
            return dict(self.latest_summary)

    def mjpeg_stream(self):
        boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
        while True:
            with self.frame_ready:
                self.frame_ready.wait(timeout=2.0)
                if not self.running:
                    break
                jpeg = self.latest_jpeg
            if jpeg:
                yield boundary + jpeg + b"\r\n"

    def _run(self, host: str, port: int) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.5)
        try:
            sock.bind((host, port))
            with self.lock:
                self.sock = sock
            while self._is_running():
                try:
                    data, addr = sock.recvfrom(2048)
                except socket.timeout:
                    self._drop_stale_frames()
                    continue
                except OSError:
                    break

                packet = parse_packet(data, settings.max_frame_bytes)
                if not packet:
                    continue
                with self.lock:
                    self.stats["received_packets"] += 1
                    self.stats["last_sender"] = f"{addr[0]}:{addr[1]}"

                partial = self.partial_frames.get(packet.frame_id)
                if partial is None:
                    partial = PartialFrame(packet.frame_id, packet.total_size, packet.packet_count)
                    self.partial_frames[packet.frame_id] = partial
                partial.add(packet)
                if partial.is_complete():
                    frame_bytes = partial.build()
                    self.partial_frames.pop(packet.frame_id, None)
                    if frame_bytes:
                        self._handle_frame(packet.frame_id, frame_bytes)
                self._drop_stale_frames()
        except Exception as exc:
            with self.lock:
                self.stats["error"] = str(exc)
        finally:
            try:
                sock.close()
            except OSError:
                pass
            with self.lock:
                self.running = False
                if self.sock is sock:
                    self.sock = None
                self.frame_ready.notify_all()

    def _is_running(self) -> bool:
        with self.lock:
            return self.running

    def _drop_stale_frames(self) -> None:
        now = time.monotonic()
        stale_ids = [
            frame_id
            for frame_id, partial in self.partial_frames.items()
            if now - partial.created_at > settings.frame_timeout_sec
        ]
        if not stale_ids:
            return
        for frame_id in stale_ids:
            self.partial_frames.pop(frame_id, None)
        with self.lock:
            self.stats["dropped_frames"] += len(stale_ids)

    def _handle_frame(self, frame_id: int, frame_bytes: bytes) -> None:
        image = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            with self.lock:
                self.stats["decode_errors"] += 1
            return

        try:
            result = self._get_detector().detect(image)
            annotated = result["annotated"]
        except Exception as exc:
            result = {"detections": [], "inference_ms": 0}
            annotated = image
            with self.lock:
                self.stats["inference_errors"] += 1
                self.stats["error"] = str(exc)

        ok, jpeg = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), settings.jpeg_quality])
        if not ok:
            return

        now = time.time()
        with self.frame_ready:
            self._frame_times.append(now)
            fps = 0.0
            if len(self._frame_times) >= 2:
                duration = self._frame_times[-1] - self._frame_times[0]
                fps = (len(self._frame_times) - 1) / duration if duration > 0 else 0.0
            self.latest_jpeg = jpeg.tobytes()
            self.latest_raw_jpeg = frame_bytes
            self.latest_summary = {
                "detections": result.get("detections", []),
                "inference_ms": result.get("inference_ms", 0),
                "frame_id": frame_id,
                "updated_at": now,
            }
            self.stats["received_frames"] += 1
            self.stats["fps"] = round(fps, 2)
            self.frame_ready.notify_all()


camera_service = CameraService()
