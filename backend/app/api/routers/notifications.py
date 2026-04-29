import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.socket_manager import socket_manager

router = APIRouter(prefix="/notifications", tags=["通知"])


notifications_db = []
current_notification_id = 1


def create_notification(
    user_id: int,
    type: str,
    title: str,
    content: str,
    related_detection_id: int = None
):
    global current_notification_id

    notification = {
        "id": current_notification_id,
        "user_id": user_id,
        "type": type,
        "title": title,
        "content": content,
        "is_read": False,
        "related_detection_id": related_detection_id,
        "created_at": datetime.now().isoformat()
    }
    current_notification_id += 1
    notifications_db.insert(0, notification)

    socket_manager.emit_nowait("notification", {
        "type": "new_notification",
        "notification": notification
    }, to=f"user_{user_id}")

    return notification


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    is_read: bool = Query(None),
    type: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_notifs = [
        n for n in notifications_db
        if n.get("user_id") == current_user.id
    ]

    if is_read is not None:
        user_notifs = [n for n in user_notifs if n.get("is_read") == is_read]

    if type:
        user_notifs = [n for n in user_notifs if n.get("type") == type]

    user_notifs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    offset = (page - 1) * page_size
    items = user_notifs[offset:offset + page_size]
    unread_count = len([n for n in notifications_db if n.get("user_id") == current_user.id and not n.get("is_read")])

    return {
        "items": items,
        "total": len(user_notifs),
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size
    }


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user)
):
    for n in notifications_db:
        if n.get("id") == notification_id and n.get("user_id") == current_user.id:
            n["is_read"] = True

            socket_manager.emit_nowait("notification", {
                "type": "notification_read",
                "notification_id": notification_id
            }, to=f"user_{current_user.id}")

            return {"message": "已标记为已读"}

    return {"message": "通知不存在"}


@router.put("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user)
):
    count = 0
    for n in notifications_db:
        if n.get("user_id") == current_user.id and not n.get("is_read"):
            n["is_read"] = True
            count += 1

    if count > 0:
        socket_manager.emit_nowait("notification", {
            "type": "all_notifications_read",
            "count": count
        }, to=f"user_{current_user.id}")

    return {"message": f"已标记 {count} 条为已读"}
