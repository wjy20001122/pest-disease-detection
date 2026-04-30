from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routers.notifications import create_notification
from app.core.config import settings
from app.db.models import Notification, User, VideoTask
from app.services.system_config_service import get_system_config_int

QUEUE_ALERT_COOLDOWN_MINUTES = 15


def _get_queue_length() -> int:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        return int(client.llen("celery"))
    finally:
        client.close()


def _should_send_alert(db: Session, title: str) -> bool:
    cutoff = datetime.now() - timedelta(minutes=QUEUE_ALERT_COOLDOWN_MINUTES)
    latest = db.execute(
        select(Notification)
        .where(
            Notification.type == "system",
            Notification.title == title,
            Notification.created_at >= cutoff,
        )
        .order_by(Notification.created_at.desc())
    ).scalars().first()
    return latest is None


def _notify_admins(db: Session, title: str, content: str) -> int:
    if not _should_send_alert(db, title):
        return 0
    admins = db.execute(
        select(User).where(User.role == "admin", User.is_active == 1)
    ).scalars().all()
    created = 0
    for admin in admins:
        create_notification(
            user_id=admin.id,
            type="system",
            title=title,
            content=content,
            db=db,
        )
        created += 1
    return created


def get_queue_metrics(db: Session) -> dict[str, Any]:
    queue_length = 0
    queue_error = None
    try:
        queue_length = _get_queue_length()
    except Exception as exc:
        queue_error = str(exc)

    queued_count = db.scalar(
        select(func.count()).select_from(VideoTask).where(VideoTask.status == "queued")
    ) or 0
    processing_count = db.scalar(
        select(func.count()).select_from(VideoTask).where(VideoTask.status == "processing")
    ) or 0
    failed_count = db.scalar(
        select(func.count()).select_from(VideoTask).where(VideoTask.status == "failed")
    ) or 0
    stopped_count = db.scalar(
        select(func.count()).select_from(VideoTask).where(VideoTask.status == "stopped")
    ) or 0

    warn_threshold = get_system_config_int(db, "queue_backlog_warn_threshold")
    critical_threshold = get_system_config_int(db, "queue_backlog_critical_threshold")

    level = "normal"
    if queue_length >= critical_threshold:
        level = "critical"
    elif queue_length >= warn_threshold:
        level = "warn"

    created_alerts = 0
    if level in {"warn", "critical"}:
        title = "队列积压告警" if level == "warn" else "队列积压严重告警"
        content = (
            f"当前Celery队列长度为 {queue_length}，"
            f"阈值 warn={warn_threshold}, critical={critical_threshold}。"
            "请检查worker消费能力。"
        )
        created_alerts = _notify_admins(db, title, content)

    return {
        "queue_length": queue_length,
        "queued_count": int(queued_count),
        "processing_count": int(processing_count),
        "failed_count": int(failed_count),
        "stopped_count": int(stopped_count),
        "warn_threshold": warn_threshold,
        "critical_threshold": critical_threshold,
        "level": level,
        "created_alerts": created_alerts,
        "queue_error": queue_error,
    }

