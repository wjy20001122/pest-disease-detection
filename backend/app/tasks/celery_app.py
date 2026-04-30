from __future__ import annotations

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "pdds",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    broker_connection_retry_on_startup=True,
    imports=("app.tasks.video_tasks",),
)
