from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta

from ..models import User, Detection, Notification, ModelRegistry, OperationLog, get_db
from ..schemas import DashboardStats, ModelItem, NotificationItem
from .auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["管理后台"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取管理仪表板数据"""
    # 用户总数
    total_users = await db.scalar(select(func.count()).select_from(User))
    
    # 检测总数
    total_detections = await db.scalar(select(func.count()).select_from(Detection))
    
    # 今日活跃用户
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active_users_today = await db.scalar(
        select(func.count(func.distinct(Detection.user_id))).where(
            Detection.created_at >= today_start
        )
    )
    
    # 待处理警告数
    warning_count = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.type == "warning",
            Notification.is_read == False
        )
    )
    
    # 系统状态（简化）
    system_status = {
        "api_response_time_ms": 120,
        "error_rate": 0.02,
        "cpu_usage": 45,
        "gpu_usage": 78
    }
    
    return DashboardStats(
        total_users=total_users or 0,
        total_detections=total_detections or 0,
        active_users_today=active_users_today or 0,
        warning_count=warning_count or 0,
        system_status=system_status
    )


@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """用户列表"""
    query = select(User)
    
    if keyword:
        query = query.where(
            User.username.ilike(f"%{keyword}%") |
            User.email.ilike(f"%{keyword}%")
        )
    
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(desc(User.created_at))
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # 获取每个用户的检测数
    user_data = []
    for user in users:
        detection_count = await db.scalar(
            select(func.count()).select_from(Detection).where(
                Detection.user_id == user.id
            )
        )
        
        # 脱敏手机号
        phone = None
        if user.phone:
            phone = user.phone[:3] + "****" + user.phone[-4:]
        
        user_data.append({
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "phone": phone,
            "role": user.role.value,
            "detection_count": detection_count,
            "created_at": user.created_at.isoformat()
        })
    
    return {
        "items": user_data,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/users/{user_id}/data")
async def get_user_data(
    user_id,
    page: int = 1,
    page_size: int = 20,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """用户数据详情"""
    # 获取用户信息
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return {"error": "用户不存在"}
    
    # 获取检测记录
    query = select(Detection).where(
        Detection.user_id == user_id
    ).order_by(desc(Detection.created_at))
    
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    detections = result.scalars().all()
    
    return {
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "created_at": user.created_at.isoformat()
        },
        "detections": [
            {
                "id": str(d.id),
                "detection_type": d.detection_type.value,
                "disease_name": d.disease_name,
                "severity": d.severity.value if d.severity else None,
                "created_at": d.created_at.isoformat()
            }
            for d in detections
        ],
        "total": total
    }


@router.get("/stats")
async def get_global_stats(
    start_date: str = None,
    end_date: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """全局统计"""
    query = select(Detection)
    
    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.where(Detection.created_at >= start)
    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.where(Detection.created_at <= end)
    
    # 病虫害分布
    disease_dist = await db.execute(
        select(
            Detection.disease_name,
            func.count(Detection.id).label("count")
        ).where(
            Detection.disease_name.isnot(None)
        ).group_by(Detection.disease_name).order_by(desc("count")).limit(20)
    )
    
    # 作物分布
    crop_dist = await db.execute(
        select(
            Detection.crop_type,
            func.count(Detection.id).label("count")
        ).where(
            Detection.crop_type.isnot(None)
        ).group_by(Detection.crop_type).order_by(desc("count"))
    )
    
    # 每日趋势
    daily_trend = await db.execute(
        select(
            func.date(Detection.created_at).label("date"),
            func.count(Detection.id).label("count")
        ).group_by("date").order_by("date")
    )
    
    return {
        "disease_distribution": [
            {"name": r[0], "count": r[1]} for r in disease_dist.all()
        ],
        "crop_distribution": [
            {"name": r[0], "count": r[1]} for r in crop_dist.all()
        ],
        "daily_trend": [
            {"date": str(r[0]), "count": r[1]} for r in daily_trend.all()
        ]
    }


@router.get("/models")
async def list_models(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """模型列表"""
    result = await db.execute(
        select(ModelRegistry).order_by(desc(ModelRegistry.deployed_at))
    )
    models = result.scalars().all()
    
    return {
        "items": [
            ModelItem(
                id=m.id,
                model_name=m.model_name,
                model_version=m.model_version,
                supported_pests=m.supported_pests,
                supported_crops=m.supported_crops,
                is_active=m.is_active,
                is_default=m.is_default,
                metrics=m.metrics,
                deployed_at=m.deployed_at
            ).model_dump() for m in models
        ]
    }


@router.get("/notifications")
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    notification_type: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """通知列表"""
    query = select(Notification)

    if notification_type:
        query = query.where(Notification.type == notification_type)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(desc(Notification.created_at))

    result = await db.execute(query)
    notifications = result.scalars().all()

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
        "total": total
    }


@router.get("/knowledge")
async def list_knowledge_for_admin(
    page: int = 1,
    page_size: int = 20,
    crop_type: str = None,
    category: str = None,
    keyword: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理端知识库列表"""
    from ..models import KnowledgeBase
    from sqlalchemy import or_

    query = select(KnowledgeBase)

    if keyword:
        query = query.where(
            or_(
                KnowledgeBase.disease_name.ilike(f"%{keyword}%"),
                KnowledgeBase.symptoms.ilike(f"%{keyword}%")
            )
        )

    if crop_type:
        query = query.where(KnowledgeBase.crop_type == crop_type)

    if category:
        query = query.where(KnowledgeBase.category == category)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(desc(KnowledgeBase.updated_at))

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": str(item.id),
                "disease_name": item.disease_name,
                "crop_type": item.crop_type,
                "category": item.category,
                "symptoms": item.symptoms[:100] + "..." if item.symptoms and len(item.symptoms) > 100 else item.symptoms,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/logs")
async def get_operation_logs(
    page: int = 1,
    page_size: int = 50,
    action: str = None,
    start_date: str = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """操作日志"""
    query = select(OperationLog)
    
    if action:
        query = query.where(OperationLog.action == action)
    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.where(OperationLog.created_at >= start)
    
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(desc(OperationLog.created_at))
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "resource": log.resource,
                "detail": log.detail,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ],
        "total": total
    }
