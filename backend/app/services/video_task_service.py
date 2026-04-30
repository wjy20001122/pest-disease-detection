from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import VideoTask


TERMINAL_VIDEO_TASK_STATUSES = {"completed", "failed", "stopped"}


def _safe_json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return "{}"


def _safe_json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def create_video_task_record(db: Session, session_id: str, username: str, model_key: str) -> VideoTask:
    now = datetime.now()
    task = VideoTask(
        session_id=session_id,
        username=username,
        model_key=model_key,
        status="queued",
        progress=0.0,
        frame_count=0,
        total_counts_json="{}",
        total_tracks=0,
        detections_json="[]",
        stop_requested=0,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_video_task_by_session_id(db: Session, session_id: str) -> VideoTask | None:
    return db.execute(
        select(VideoTask).where(VideoTask.session_id == session_id)
    ).scalar_one_or_none()


def get_owned_video_task(db: Session, session_id: str, username: str) -> VideoTask | None:
    return db.execute(
        select(VideoTask).where(
            VideoTask.session_id == session_id,
            VideoTask.username == username,
        )
    ).scalar_one_or_none()


def to_status_payload(task: VideoTask) -> dict[str, Any]:
    total_counts = _safe_json_loads(task.total_counts_json, {})
    detections = _safe_json_loads(task.detections_json, [])
    return {
        "session_id": task.session_id,
        "is_processing": task.status in {"queued", "processing"},
        "status": task.status,
        "progress": float(task.progress or 0.0),
        "frame_count": int(task.frame_count or 0),
        "total_counts": total_counts if isinstance(total_counts, dict) else {},
        "total_tracks": int(task.total_tracks or 0),
        "detections": detections if isinstance(detections, list) else [],
        "output_url": task.output_url,
        "error_message": task.error_message,
        "stop_requested": bool(task.stop_requested),
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def update_video_task_progress(
    db: Session,
    session_id: str,
    progress: float,
    frame_count: int,
    total_counts: dict[str, Any],
    total_tracks: int,
    detections: list[dict[str, Any]],
) -> bool:
    task = get_video_task_by_session_id(db, session_id)
    if not task:
        return False

    if task.status not in TERMINAL_VIDEO_TASK_STATUSES:
        task.status = "processing"
    task.progress = float(progress)
    task.frame_count = int(frame_count)
    task.total_counts_json = _safe_json_dumps(total_counts)
    task.total_tracks = int(total_tracks)
    task.detections_json = _safe_json_dumps(detections)
    task.updated_at = datetime.now()
    db.commit()
    return True


def mark_video_task_completed(
    db: Session,
    session_id: str,
    output_url: str,
    frame_count: int,
    total_counts: dict[str, Any],
    total_tracks: int,
    detections: list[dict[str, Any]],
) -> bool:
    task = get_video_task_by_session_id(db, session_id)
    if not task:
        return False

    task.status = "completed"
    task.progress = 100.0
    task.frame_count = int(frame_count)
    task.total_counts_json = _safe_json_dumps(total_counts)
    task.total_tracks = int(total_tracks)
    task.detections_json = _safe_json_dumps(detections)
    task.output_url = output_url
    task.error_message = None
    task.updated_at = datetime.now()
    db.commit()
    return True


def mark_video_task_failed(db: Session, session_id: str, error_message: str) -> bool:
    task = get_video_task_by_session_id(db, session_id)
    if not task:
        return False

    task.status = "failed"
    task.error_message = error_message
    task.updated_at = datetime.now()
    db.commit()
    return True


def mark_video_task_stopped(
    db: Session,
    session_id: str,
    frame_count: int,
    total_counts: dict[str, Any],
    total_tracks: int,
    detections: list[dict[str, Any]],
    output_url: str | None = None,
) -> bool:
    task = get_video_task_by_session_id(db, session_id)
    if not task:
        return False

    task.status = "stopped"
    task.frame_count = int(frame_count)
    task.total_counts_json = _safe_json_dumps(total_counts)
    task.total_tracks = int(total_tracks)
    task.detections_json = _safe_json_dumps(detections)
    if output_url:
        task.output_url = output_url
    task.updated_at = datetime.now()
    db.commit()
    return True


def request_stop_video_task(db: Session, session_id: str) -> bool:
    task = get_video_task_by_session_id(db, session_id)
    if not task:
        return False

    task.stop_requested = 1
    if task.status == "queued":
        task.status = "stopped"
    task.updated_at = datetime.now()
    db.commit()
    return True


def is_stop_requested(db: Session, session_id: str) -> bool:
    task = get_video_task_by_session_id(db, session_id)
    if not task:
        return True
    return bool(task.stop_requested)
