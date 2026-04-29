from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Notification, User
from app.db.session import SessionLocal, get_db
from app.services.socket_manager import socket_manager

router = APIRouter(prefix="/notifications", tags=["通知"])


def _normalize_type(value: str | None) -> str | None:
    if value == "agent":
        return "agent_push"
    return value


def _notification_to_dict(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "type": notification.type,
        "title": notification.title,
        "content": notification.content,
        "is_read": bool(notification.is_read),
        "related_detection_id": notification.related_detection_id,
        "data": {"detection_id": notification.related_detection_id} if notification.related_detection_id else {},
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def create_notification(
    user_id: int,
    type: str,
    title: str,
    content: str,
    related_detection_id: int | None = None,
    db: Session | None = None,
) -> dict:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        notification = Notification(
            user_id=user_id,
            type=_normalize_type(type) or "system",
            title=title,
            content=content,
            is_read=0,
            related_detection_id=related_detection_id,
            created_at=datetime.now(),
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)
        payload = _notification_to_dict(notification)
    finally:
        if owns_session:
            session.close()

    socket_manager.emit_nowait(
        "notification",
        {"type": "new_notification", "notification": payload},
        to=f"user_{user_id}",
    )
    return payload


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    is_read: bool | None = Query(None),
    type: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification_type = _normalize_type(type)
    query = select(Notification).where(Notification.user_id == current_user.id)

    if is_read is not None:
        query = query.where(Notification.is_read == int(is_read))
    if notification_type:
        query = query.where(Notification.type == notification_type)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    unread_count = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == 0,
        )
    ) or 0

    notifications = db.execute(
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return {
        "items": [_notification_to_dict(item) for item in notifications],
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
    }


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="通知不存在")

    notification.is_read = 1
    db.commit()

    socket_manager.emit_nowait(
        "notification",
        {"type": "notification_read", "notification_id": notification_id},
        to=f"user_{current_user.id}",
    )
    return {"message": "已标记为已读"}


@router.put("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == 0,
        )
    ).scalars().all()

    for notification in notifications:
        notification.is_read = 1
    db.commit()

    if notifications:
        socket_manager.emit_nowait(
            "notification",
            {"type": "all_notifications_read", "count": len(notifications)},
            to=f"user_{current_user.id}",
        )
    return {"message": f"已标记 {len(notifications)} 条为已读"}
