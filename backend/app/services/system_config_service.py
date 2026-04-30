from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import SystemConfig


DEFAULT_SYSTEM_CONFIGS: dict[str, Any] = {
    "review_trigger_confidence": 0.8,
    "regional_alert_threshold": 3,
    "regional_alert_days": 3,
    "video_task_soft_time_limit_sec": settings.celery_video_task_soft_time_limit_sec,
    "video_task_hard_time_limit_sec": settings.celery_video_task_hard_time_limit_sec,
    "video_task_max_retries": settings.celery_video_task_max_retries,
    "video_task_retry_backoff_sec": settings.celery_video_task_retry_backoff_sec,
    "queue_backlog_warn_threshold": 20,
    "queue_backlog_critical_threshold": 50,
}

CONFIG_VALUE_TYPE: dict[str, type] = {
    "review_trigger_confidence": float,
    "regional_alert_threshold": int,
    "regional_alert_days": int,
    "video_task_soft_time_limit_sec": int,
    "video_task_hard_time_limit_sec": int,
    "video_task_max_retries": int,
    "video_task_retry_backoff_sec": int,
    "queue_backlog_warn_threshold": int,
    "queue_backlog_critical_threshold": int,
}


def _coerce_value(key: str, value: Any) -> Any:
    target_type = CONFIG_VALUE_TYPE.get(key, str)
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    return str(value)


def _parse_stored_value(key: str, value: str) -> Any:
    target_type = CONFIG_VALUE_TYPE.get(key, str)
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    return value


def ensure_default_system_configs(db: Session) -> None:
    now = datetime.now()
    updated = False
    for key, default_value in DEFAULT_SYSTEM_CONFIGS.items():
        current = db.execute(select(SystemConfig).where(SystemConfig.key == key)).scalar_one_or_none()
        if current is None:
            db.add(
                SystemConfig(
                    key=key,
                    value=str(default_value),
                    updated_at=now,
                )
            )
            updated = True
    if updated:
        db.commit()


def list_system_configs(db: Session) -> dict[str, Any]:
    ensure_default_system_configs(db)
    rows = db.execute(select(SystemConfig)).scalars().all()
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row.key] = _parse_stored_value(row.key, row.value)
        except (TypeError, ValueError):
            result[row.key] = DEFAULT_SYSTEM_CONFIGS.get(row.key, row.value)
    return result


def get_system_config(db: Session, key: str) -> Any:
    default_value = DEFAULT_SYSTEM_CONFIGS.get(key)
    row = db.execute(select(SystemConfig).where(SystemConfig.key == key)).scalar_one_or_none()
    if row is None:
        return default_value
    try:
        return _parse_stored_value(key, row.value)
    except (TypeError, ValueError):
        return default_value


def get_system_config_int(db: Session, key: str) -> int:
    value = get_system_config(db, key)
    return int(value if value is not None else DEFAULT_SYSTEM_CONFIGS.get(key, 0))


def get_system_config_float(db: Session, key: str) -> float:
    value = get_system_config(db, key)
    return float(value if value is not None else DEFAULT_SYSTEM_CONFIGS.get(key, 0.0))


def update_system_configs(db: Session, payload: dict[str, Any], operator_id: int | None) -> dict[str, Any]:
    ensure_default_system_configs(db)
    now = datetime.now()
    for key, raw_value in payload.items():
        if key not in DEFAULT_SYSTEM_CONFIGS:
            continue
        value = _coerce_value(key, raw_value)
        row = db.execute(select(SystemConfig).where(SystemConfig.key == key)).scalar_one_or_none()
        if row is None:
            row = SystemConfig(
                key=key,
                value=str(value),
                updated_at=now,
            )
            db.add(row)
        else:
            row.value = str(value)
            row.updated_at = now
        row.updated_by = operator_id
    db.commit()
    return list_system_configs(db)
