from __future__ import annotations

from sqlalchemy import select
from celery.exceptions import SoftTimeLimitExceeded

from app.db.models import VideoTask
from app.db.session import Base, SessionLocal, engine
from app.services.prediction_service import prediction_service
from app.services.system_config_service import get_system_config_int
from app.services.video_task_service import (
    is_stop_requested,
    mark_video_task_completed,
    mark_video_task_failed,
    mark_video_task_stopped,
    update_video_task_progress,
)
from app.tasks.celery_app import celery_app

RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)


def _load_retry_policy() -> tuple[int, int]:
    db = SessionLocal()
    try:
        max_retries = get_system_config_int(db, "video_task_max_retries")
        retry_backoff_sec = get_system_config_int(db, "video_task_retry_backoff_sec")
    finally:
        db.close()
    return max_retries, retry_backoff_sec


@celery_app.task(name="app.tasks.video_tasks.process_video_detection", bind=True)
def process_video_detection(
    self,
    session_id: str,
    input_video: str,
    model_key: str,
    username: str,
    conf: str = "0.5",
) -> dict:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        task = db.execute(
            select(VideoTask).where(VideoTask.session_id == session_id)
        ).scalar_one_or_none()
        if task is None:
            return {"status": "failed", "error": "video task record not found"}

        if task.stop_requested:
            task.status = "stopped"
            db.commit()
            return {"status": "stopped"}

        if task.status not in {"queued", "processing"}:
            return {"status": task.status}

        task.status = "processing"
        db.commit()
    finally:
        db.close()

    def should_stop() -> bool:
        local_db = SessionLocal()
        try:
            return is_stop_requested(local_db, session_id)
        finally:
            local_db.close()

    def progress_callback(payload: dict) -> None:
        status = payload.get("status", "processing")
        local_db = SessionLocal()
        try:
            if status == "processing":
                update_video_task_progress(
                    local_db,
                    session_id=session_id,
                    progress=float(payload.get("progress", 0.0)),
                    frame_count=int(payload.get("frame_count", 0)),
                    total_counts=payload.get("total_counts", {}) or {},
                    total_tracks=int(payload.get("total_tracks", 0)),
                    detections=payload.get("detections", []) or [],
                )
            elif status == "stopped":
                mark_video_task_stopped(
                    local_db,
                    session_id=session_id,
                    frame_count=int(payload.get("frame_count", 0)),
                    total_counts=payload.get("total_counts", {}) or {},
                    total_tracks=int(payload.get("total_tracks", 0)),
                    detections=payload.get("detections", []) or [],
                )
            elif status == "completed":
                mark_video_task_completed(
                    local_db,
                    session_id=session_id,
                    output_url=payload.get("output_url", ""),
                    frame_count=int(payload.get("frame_count", 0)),
                    total_counts=payload.get("total_counts", {}) or {},
                    total_tracks=int(payload.get("total_tracks", 0)),
                    detections=payload.get("detections", []) or [],
                )
        finally:
            local_db.close()

    try:
        result = prediction_service.process_video_task(
            task_session_id=session_id,
            input_video=input_video,
            model_key=model_key,
            username=username,
            conf=conf,
            should_stop=should_stop,
            progress_callback=progress_callback,
        )
    except SoftTimeLimitExceeded:
        result = {"status": "failed", "error": "视频任务超时（soft time limit exceeded）"}
    except RETRYABLE_EXCEPTIONS as exc:
        max_retries, retry_backoff_sec = _load_retry_policy()
        if self.request.retries < max_retries:
            raise self.retry(exc=exc, countdown=retry_backoff_sec, max_retries=max_retries)
        result = {"status": "failed", "error": f"视频任务重试耗尽: {exc}"}
    except Exception as exc:
        result = {"status": "failed", "error": str(exc)}

    status = result.get("status", "failed")
    local_db = SessionLocal()
    try:
        if status == "completed":
            mark_video_task_completed(
                local_db,
                session_id=session_id,
                output_url=result.get("output_url", ""),
                frame_count=int(result.get("frame_count", 0)),
                total_counts=result.get("total_counts", {}) or {},
                total_tracks=int(result.get("total_tracks", 0)),
                detections=result.get("detections", []) or [],
            )
        elif status == "stopped":
            mark_video_task_stopped(
                local_db,
                session_id=session_id,
                frame_count=int(result.get("frame_count", 0)),
                total_counts=result.get("total_counts", {}) or {},
                total_tracks=int(result.get("total_tracks", 0)),
                detections=result.get("detections", []) or [],
                output_url=result.get("output_url"),
            )
        else:
            mark_video_task_failed(local_db, session_id=session_id, error_message=result.get("error", "unknown error"))
    finally:
        local_db.close()

    return result
