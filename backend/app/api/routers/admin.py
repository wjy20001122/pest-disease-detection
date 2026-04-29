from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, ImgRecord, VideoRecord, CameraRecord
from app.api.deps import get_admin_user

router = APIRouter(prefix="/admin", tags=["管理后台"])


@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar() or 0

    img_count = await db.execute(select(func.count(ImgRecord.id)))
    video_count = await db.execute(select(func.count(VideoRecord.id)))
    camera_count = await db.execute(select(func.count(CameraRecord.id)))
    total_detections = (img_count.scalar() or 0) + (video_count.scalar() or 0) + (camera_count.scalar() or 0)

    return {
        "total_users": total_users,
        "new_users_today": 0,
        "total_detections": total_detections,
        "detections_today": 0,
        "active_alerts": 0,
        "ai_models": 3
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(None),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User)

    if keyword:
        query = query.where(User.username.like(f"%{keyword}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    items = []
    for user in users:
        items.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.time.isoformat() if user.time else None
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/stats")
async def get_stats(
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    img_result = await db.execute(select(func.count(ImgRecord.id)))
    video_result = await db.execute(select(func.count(VideoRecord.id)))
    camera_result = await db.execute(select(func.count(CameraRecord.id)))

    return {
        "total_detections": (img_result.scalar() or 0) + (video_result.scalar() or 0) + (camera_result.scalar() or 0),
        "image_detections": img_result.scalar() or 0,
        "video_detections": video_result.scalar() or 0,
        "camera_detections": camera_result.scalar() or 0
    }


@router.get("/models")
async def list_models(
    current_user: User = Depends(get_admin_user)
):
    return {
        "items": [
            {
                "id": 1,
                "name": "水稻病害检测",
                "version": "v2.1",
                "pests": "稻飞虱、纹枯病、稻瘟病",
                "accuracy": 0.945,
                "status": "active"
            },
            {
                "id": 2,
                "name": "玉米病害检测",
                "version": "v1.5",
                "pests": "大斑病、小斑病",
                "accuracy": 0.912,
                "status": "active"
            },
            {
                "id": 3,
                "name": "通用虫害检测",
                "version": "v3.0",
                "pests": "二化螟、三化螟",
                "accuracy": 0.938,
                "status": "inactive"
            }
        ]
    }


@router.get("/notifications")
async def list_all_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_admin_user)
):
    from app.api.routers.notifications import notifications_db

    items = notifications_db[(page - 1) * page_size:page * page_size]

    return {
        "items": items,
        "total": len(notifications_db),
        "page": page,
        "page_size": page_size
    }
