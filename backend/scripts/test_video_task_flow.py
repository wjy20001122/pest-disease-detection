from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import VideoTask  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.services.video_task_service import (  # noqa: E402
    create_video_task_record,
    get_video_task_by_session_id,
    is_stop_requested,
    mark_video_task_completed,
    mark_video_task_failed,
    mark_video_task_stopped,
    request_stop_video_task,
    to_status_payload,
    update_video_task_progress,
)


def _cleanup(prefix: str) -> None:
    db = SessionLocal()
    try:
        db.query(VideoTask).filter(VideoTask.session_id.like(f"{prefix}%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _new_session_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:20]}"


def main() -> None:
    Base.metadata.create_all(bind=engine)
    prefix = f"video_task_test_{int(time.time())}_"
    _cleanup(prefix)

    try:
        # 1) queued -> processing
        session_id = _new_session_id(prefix)
        db = SessionLocal()
        try:
            create_video_task_record(db, session_id=session_id, username="video-task-user", model_key="pest")
            ok = update_video_task_progress(
                db,
                session_id=session_id,
                progress=31.5,
                frame_count=42,
                total_counts={"aphid": 3},
                total_tracks=2,
                detections=[{"class": "aphid", "confidence": 0.88, "frame": 42}],
            )
            assert ok
            task = get_video_task_by_session_id(db, session_id)
            assert task is not None
            payload = to_status_payload(task)
            assert payload["status"] == "processing", payload
            assert payload["frame_count"] == 42, payload
            assert payload["total_counts"].get("aphid") == 3, payload
        finally:
            db.close()

        # 2) request stop
        db = SessionLocal()
        try:
            assert request_stop_video_task(db, session_id)
            assert is_stop_requested(db, session_id) is True
            assert mark_video_task_stopped(
                db,
                session_id=session_id,
                frame_count=45,
                total_counts={"aphid": 4},
                total_tracks=2,
                detections=[],
            )
            task = get_video_task_by_session_id(db, session_id)
            assert task is not None and task.status == "stopped"
        finally:
            db.close()

        # 3) completed
        completed_id = _new_session_id(prefix)
        db = SessionLocal()
        try:
            create_video_task_record(db, session_id=completed_id, username="video-task-user", model_key="pest")
            assert mark_video_task_completed(
                db,
                session_id=completed_id,
                output_url="https://example.com/output.mp4",
                frame_count=100,
                total_counts={"worm": 5},
                total_tracks=3,
                detections=[],
            )
            task = get_video_task_by_session_id(db, completed_id)
            assert task is not None and task.status == "completed"
            assert task.output_url == "https://example.com/output.mp4"
        finally:
            db.close()

        # 4) failed
        failed_id = _new_session_id(prefix)
        db = SessionLocal()
        try:
            create_video_task_record(db, session_id=failed_id, username="video-task-user", model_key="pest")
            assert mark_video_task_failed(db, session_id=failed_id, error_message="mock error")
            task = get_video_task_by_session_id(db, failed_id)
            assert task is not None and task.status == "failed"
            assert task.error_message == "mock error"
        finally:
            db.close()

        print("video task flow ok: queued/processing/stopped/completed/failed")
    finally:
        _cleanup(prefix)


if __name__ == "__main__":
    main()
