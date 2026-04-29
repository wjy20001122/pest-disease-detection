from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import TrackingTask, TrackingUpdate, User
from app.db.session import get_db

router = APIRouter(prefix="/tracking", tags=["跟踪"])

VALID_STATUSES = {"active", "monitoring", "worsening", "improving", "treated", "resolved", "archived"}
VALID_SEVERITIES = {"low", "medium", "high"}


class LocationPayload(BaseModel):
    latitude: float | None = None
    longitude: float | None = None


class TrackingCreatePayload(BaseModel):
    detection_id: int | None = None
    disease_name: str = Field(min_length=1)
    severity: str = "medium"
    location: LocationPayload | str | None = None
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = None


class TrackingUpdatePayload(BaseModel):
    status: str | None = None
    severity: str | None = None
    notes: str | None = None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="无效的跟踪状态")
    return normalized


def _normalize_severity(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in VALID_SEVERITIES:
        raise HTTPException(status_code=400, detail="无效的严重程度")
    return normalized


def _extract_location(payload: TrackingCreatePayload) -> tuple[float | None, float | None, str | None]:
    latitude = payload.latitude
    longitude = payload.longitude
    location_text = None

    if isinstance(payload.location, LocationPayload):
        latitude = payload.location.latitude if payload.location.latitude is not None else latitude
        longitude = payload.location.longitude if payload.location.longitude is not None else longitude
    elif isinstance(payload.location, str):
        location_text = payload.location

    return latitude, longitude, location_text


def _task_to_dict(task: TrackingTask, updates: list[TrackingUpdate] | None = None) -> dict[str, Any]:
    created_at = task.created_at or datetime.now()
    updated_at = task.updated_at or created_at
    days_active = max((datetime.now() - created_at).days + 1, 1)
    item = {
        "id": task.id,
        "user_id": task.user_id,
        "detection_id": task.detection_id,
        "disease_name": task.disease_name,
        "severity": task.severity,
        "status": task.status,
        "latitude": task.latitude,
        "longitude": task.longitude,
        "location": task.location,
        "notes": task.notes,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "last_update": updated_at.isoformat(),
        "days_active": days_active,
    }
    if updates is not None:
        item["updates"] = [_update_to_dict(update) for update in updates]
        item["update_count"] = len(updates)
    return item


def _update_to_dict(update: TrackingUpdate) -> dict[str, Any]:
    return {
        "id": update.id,
        "task_id": update.task_id,
        "status": update.status,
        "note": update.note,
        "image": update.image,
        "created_at": update.created_at.isoformat() if update.created_at else None,
    }


def _get_owned_task(db: Session, task_id: int, user_id: int) -> TrackingTask:
    task = db.execute(
        select(TrackingTask).where(
            TrackingTask.id == task_id,
            TrackingTask.user_id == user_id,
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="跟踪任务不存在")
    return task


@router.post("")
async def create_task(
    payload: TrackingCreatePayload = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    severity = _normalize_severity(payload.severity) or "medium"
    active_count = db.scalar(
        select(func.count()).select_from(TrackingTask).where(
            TrackingTask.user_id == current_user.id,
            TrackingTask.status.in_(["active", "monitoring"]),
        )
    )
    if (active_count or 0) >= 100:
        raise HTTPException(status_code=400, detail="活跃跟踪任务已达上限(100条)，请先归档已完成的任务")

    latitude, longitude, location_text = _extract_location(payload)
    now = datetime.now()
    task = TrackingTask(
        user_id=current_user.id,
        detection_id=payload.detection_id,
        disease_name=payload.disease_name.strip(),
        severity=severity,
        status="active",
        latitude=latitude,
        longitude=longitude,
        location=location_text,
        notes=payload.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task, [])


@router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalized_status = _normalize_status(status)
    query = select(TrackingTask).where(TrackingTask.user_id == current_user.id)
    if normalized_status:
        query = query.where(TrackingTask.status == normalized_status)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    tasks = db.execute(
        query.order_by(TrackingTask.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return {
        "items": [_task_to_dict(task) for task in tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, task_id, current_user.id)
    updates = db.execute(
        select(TrackingUpdate)
        .where(TrackingUpdate.task_id == task.id)
        .order_by(TrackingUpdate.created_at.desc())
    ).scalars().all()
    return _task_to_dict(task, updates)


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    payload: TrackingUpdatePayload = Body(default_factory=TrackingUpdatePayload),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, task_id, current_user.id)
    normalized_status = _normalize_status(payload.status)
    normalized_severity = _normalize_severity(payload.severity)

    if normalized_status:
        task.status = normalized_status
        task.resolved_at = datetime.now() if normalized_status == "resolved" else task.resolved_at
    if normalized_severity:
        task.severity = normalized_severity
    if payload.notes is not None:
        task.notes = payload.notes

    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.post("/{task_id}/updates")
async def add_update(
    task_id: int,
    status: str | None = Form(None),
    note: str = Form(""),
    image: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, task_id, current_user.id)
    normalized_status = _normalize_status(status)
    now = datetime.now()
    image_name = image.filename if image and image.filename else None
    update = TrackingUpdate(
        task_id=task.id,
        status=normalized_status or task.status,
        note=note,
        image=image_name,
        created_at=now,
    )

    if normalized_status:
        task.status = normalized_status
        task.resolved_at = now if normalized_status == "resolved" else task.resolved_at
    task.updated_at = now

    db.add(update)
    db.commit()
    db.refresh(update)
    return _update_to_dict(update)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, task_id, current_user.id)
    db.query(TrackingUpdate).filter(TrackingUpdate.task_id == task.id).delete()
    db.delete(task)
    db.commit()
    return {"message": "删除成功"}
