from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import Notification, User, get_db
from ..schemas import NotificationItem
from .auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["通知"])


@router.get("")
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    is_read: bool = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知列表"""
    query = select(Notification).where(Notification.user_id == user.id)
    
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    
    query = query.order_by(Notification.created_at.desc())
    
    from sqlalchemy import func
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    # 未读数
    unread_count = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.id,
            Notification.is_read == False
        )
    )
    
    return {
        "items": [
            NotificationItem(
                id=n.id,
                type=n.type.value,
                title=n.title,
                content=n.content,
                is_read=n.is_read,
                created_at=n.created_at
            ).model_dump() for n in notifications
        ],
        "total": total,
        "unread_count": unread_count or 0
    }


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """标记为已读"""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在"
        )
    
    notification.is_read = True
    await db.commit()
    
    return {"success": True}


@router.put("/read-all")
async def mark_all_as_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """全部标记为已读"""
    await db.execute(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.is_read == False
        )
    )
    
    from sqlalchemy import update
    await db.execute(
        update(Notification).where(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).values(is_read=True)
    )
    await db.commit()
    
    return {"success": True}
