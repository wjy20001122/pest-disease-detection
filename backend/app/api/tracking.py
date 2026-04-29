from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from uuid import UUID

from ..models import TrackingTask, TrackingUpdate, User, TrackingStatus, Severity, get_db
from ..schemas import TrackingCreate, TrackingUpdateData, TrackingResponse
from .auth import get_current_user

router = APIRouter(prefix="/tracking", tags=["跟踪"])


@router.post("", response_model=TrackingResponse, status_code=status.HTTP_201_CREATED)
async def create_tracking(
    data: TrackingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建跟踪任务"""
    # 检查活跃任务数量
    active_count = await db.scalar(
        select(TrackingTask).where(
            TrackingTask.user_id == user.id,
            TrackingTask.status == TrackingStatus.ACTIVE
        ).count()
    )
    
    if active_count >= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="活跃跟踪任务已达上限(100条)，请先归档已完成的任务"
        )
    
    task = TrackingTask(
        user_id=user.id,
        detection_id=data.detection_id,
        disease_name=data.disease_name,
        severity=Severity(data.severity),
        status=TrackingStatus.ACTIVE,
        latitude=data.location.latitude if data.location else None,
        longitude=data.location.longitude if data.location else None
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return TrackingResponse(
        id=task.id,
        disease_name=task.disease_name,
        severity=task.severity.value,
        status=task.status.value,
        latitude=task.latitude,
        longitude=task.longitude,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.get("")
async def list_tracking_tasks(
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取跟踪任务列表"""
    query = select(TrackingTask).where(TrackingTask.user_id == user.id)
    
    if status:
        query = query.where(TrackingTask.status == TrackingStatus(status))
    
    query = query.order_by(desc(TrackingTask.updated_at))
    
    from sqlalchemy import func
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "items": [
            TrackingResponse(
                id=t.id,
                disease_name=t.disease_name,
                severity=t.severity.value,
                status=t.status.value,
                latitude=t.latitude,
                longitude=t.longitude,
                created_at=t.created_at,
                updated_at=t.updated_at
            ).model_dump() for t in tasks
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{task_id}")
async def get_tracking_detail(
    task_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取跟踪详情"""
    result = await db.execute(
        select(TrackingTask).where(
            TrackingTask.id == task_id,
            TrackingTask.user_id == user.id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="跟踪任务不存在"
        )
    
    # 获取更新记录
    updates_result = await db.execute(
        select(TrackingUpdate).where(
            TrackingUpdate.task_id == task_id
        ).order_by(desc(TrackingUpdate.created_at))
    )
    updates = updates_result.scalars().all()
    
    return {
        "id": str(task.id),
        "disease_name": task.disease_name,
        "severity": task.severity.value,
        "status": task.status.value,
        "latitude": task.latitude,
        "longitude": task.longitude,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "resolved_measure": task.resolved_measure,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "updates": [
            {
                "id": str(u.id),
                "description": u.description,
                "severity": u.severity.value if u.severity else None,
                "image_path": u.image_path,
                "created_at": u.created_at.isoformat()
            } for u in updates
        ]
    }


@router.put("/{task_id}/resolve")
async def resolve_tracking(
    task_id: UUID,
    measure: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """解决跟踪任务"""
    from datetime import datetime
    
    result = await db.execute(
        select(TrackingTask).where(
            TrackingTask.id == task_id,
            TrackingTask.user_id == user.id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="跟踪任务不存在"
        )
    
    task.status = TrackingStatus.RESOLVED
    task.resolved_at = datetime.utcnow()
    task.resolved_measure = measure
    
    await db.commit()
    
    return {"success": True, "message": "跟踪任务已解决"}


@router.post("/{task_id}/updates")
async def add_tracking_update(
    task_id: UUID,
    data: TrackingUpdateData,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加跟踪更新"""
    result = await db.execute(
        select(TrackingTask).where(
            TrackingTask.id == task_id,
            TrackingTask.user_id == user.id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="跟踪任务不存在"
        )
    
    if task.status != TrackingStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能更新活跃状态的跟踪任务"
        )
    
    update = TrackingUpdate(
        task_id=task_id,
        description=data.description,
        image_path=data.image,
        severity=Severity(data.severity) if data.severity else None
    )
    
    # 更新任务严重程度
    if data.severity:
        task.severity = Severity(data.severity)
    
    task.updated_at = update.created_at
    
    db.add(update)
    await db.commit()
    
    return {"success": True, "message": "更新已添加"}
