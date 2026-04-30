from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.api.routers.notifications import _notification_to_dict, create_notification
from app.db.models import (
    CameraRecord,
    ImgRecord,
    KnowledgeItem,
    ModelPolicy,
    Notification,
    PermissionAuditLog,
    User,
    VideoRecord,
)
from app.db.session import get_db
from app.services.knowledge_service import knowledge_item_to_dict
from app.services.legacy_runtime import load_legacy_runtime
from app.services.queue_monitor_service import get_queue_metrics
from app.services.system_config_service import list_system_configs, update_system_configs

router = APIRouter(prefix="/admin", tags=["管理后台"])


def _to_bool_flag(value: int | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(int(value))


def _discover_model_candidates() -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = [("pest", "通用病虫害检测")]
    try:
        runtime = load_legacy_runtime()
        for key, cfg in runtime.config.MODELS_CONFIG.items():
            display_name = cfg.get("name", key)
            candidates.append((key, display_name))
    except Exception:
        pass

    seen = set()
    deduped: list[tuple[str, str]] = []
    for key, display_name in candidates:
        if key in seen:
            continue
        seen.add(key)
        deduped.append((key, display_name))
    return deduped


def _ensure_model_policies(db: Session) -> None:
    candidates = _discover_model_candidates()
    now = datetime.now()
    for key, display_name in candidates:
        policy = db.execute(select(ModelPolicy).where(ModelPolicy.model_key == key)).scalar_one_or_none()
        if policy is None:
            db.add(
                ModelPolicy(
                    model_key=key,
                    display_name=display_name,
                    enabled=1,
                    is_default=1 if key == "pest" else 0,
                    fallback_to_cloud=1,
                    fallback_notice="本地模型未识别到有效结果，已回退云端分析，结论未必完全可信。",
                    updated_at=now,
                )
            )
    db.commit()

    default_policy = db.execute(
        select(ModelPolicy).where(ModelPolicy.is_default == 1).order_by(ModelPolicy.id.asc())
    ).scalars().first()
    if default_policy is None:
        first = db.execute(select(ModelPolicy).order_by(ModelPolicy.id.asc())).scalars().first()
        if first is not None:
            first.is_default = 1
            first.updated_at = now
            db.commit()


def _model_policy_to_dict(policy: ModelPolicy) -> dict[str, Any]:
    return {
        "model_key": policy.model_key,
        "display_name": policy.display_name or policy.model_key,
        "enabled": _to_bool_flag(policy.enabled, True),
        "is_default": _to_bool_flag(policy.is_default, False),
        "fallback_to_cloud": _to_bool_flag(policy.fallback_to_cloud, True),
        "fallback_notice": policy.fallback_notice
        or "本地模型未识别到有效结果，已回退云端分析，结论未必完全可信。",
        "updated_by": policy.updated_by,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


def _parse_stats_window(period: str, start_date: str | None, end_date: str | None) -> tuple[datetime, datetime]:
    now = datetime.now()
    if period == "day":
        start = now - timedelta(days=7)
    elif period == "week":
        start = now - timedelta(weeks=4)
    else:
        start = now - timedelta(days=90)

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    else:
        end = now
    return start, end


def _record_in_window(start_time: str | None, start: datetime, end: datetime) -> bool:
    if not start_time:
        return False
    try:
        value = datetime.strptime(start_time[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            value = datetime.strptime(start_time[:10], "%Y-%m-%d")
        except ValueError:
            return False
    return start <= value <= end


def _safe_load_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return value
    except (json.JSONDecodeError, TypeError):
        return []
    return []


@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    _ensure_model_policies(db)

    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    today_prefix = datetime.now().strftime("%Y-%m-%d")

    new_users_today = db.scalar(
        select(func.count()).select_from(User).where(func.date(User.time) == today_prefix)
    ) or 0

    image_count = db.scalar(select(func.count()).select_from(ImgRecord)) or 0
    video_count = db.scalar(select(func.count()).select_from(VideoRecord)) or 0
    camera_count = db.scalar(select(func.count()).select_from(CameraRecord)) or 0
    total_detections = image_count + video_count + camera_count

    detections_today = (
        (db.scalar(select(func.count()).select_from(ImgRecord).where(ImgRecord.startTime.like(f"{today_prefix}%"))) or 0)
        + (db.scalar(select(func.count()).select_from(VideoRecord).where(VideoRecord.startTime.like(f"{today_prefix}%"))) or 0)
        + (db.scalar(select(func.count()).select_from(CameraRecord).where(CameraRecord.startTime.like(f"{today_prefix}%"))) or 0)
    )

    active_alerts = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.type.in_(["warning", "regional_alert"]),
            Notification.is_read == 0,
        )
    ) or 0

    enabled_models = db.scalar(
        select(func.count()).select_from(ModelPolicy).where(ModelPolicy.enabled == 1)
    ) or 0

    return {
        "total_users": total_users,
        "new_users_today": new_users_today,
        "total_detections": total_detections,
        "detections_today": detections_today,
        "active_alerts": active_alerts,
        "enabled_models": enabled_models,
        "detection_breakdown": {
            "image": image_count,
            "video": video_count,
            "camera": camera_count,
        },
    }


@router.get("/stats")
async def get_admin_stats(
    period: str = Query("month", description="统计周期：day/week/month"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    start, end = _parse_stats_window(period, start_date, end_date)

    img_records = db.execute(select(ImgRecord)).scalars().all()
    video_records = db.execute(select(VideoRecord)).scalars().all()
    camera_records = db.execute(select(CameraRecord)).scalars().all()

    pest_distribution: dict[str, int] = {}
    crop_distribution: dict[str, int] = {}
    daily_stats: dict[str, int] = {}
    confidence_stats: list[float] = []

    for record in img_records:
        if not _record_in_window(record.startTime, start, end):
            continue
        date_key = record.startTime[:10] if record.startTime else "unknown"
        daily_stats[date_key] = daily_stats.get(date_key, 0) + 1

        labels = _safe_load_json_list(record.label)
        confidences = _safe_load_json_list(record.confidence)
        crop_name = (record.cropType or "").strip()

        if crop_name:
            crop_distribution[crop_name] = crop_distribution.get(crop_name, 0) + 1

        for label in labels:
            label_name = str(label).strip()
            if label_name:
                pest_distribution[label_name] = pest_distribution.get(label_name, 0) + 1
        for confidence in confidences:
            try:
                confidence_stats.append(float(confidence))
            except (TypeError, ValueError):
                continue

    for record in [*video_records, *camera_records]:
        if not _record_in_window(record.startTime, start, end):
            continue
        date_key = record.startTime[:10] if record.startTime else "unknown"
        daily_stats[date_key] = daily_stats.get(date_key, 0) + 1

    trend_data = [
        {"date": date, "count": count}
        for date, count in sorted(daily_stats.items(), key=lambda item: item[0])
    ]

    return {
        "total": sum(daily_stats.values()),
        "period": period,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "disease_distribution": [
            {"name": name, "count": count}
            for name, count in sorted(pest_distribution.items(), key=lambda x: x[1], reverse=True)
        ],
        "crop_distribution": [
            {"name": name, "count": count}
            for name, count in sorted(crop_distribution.items(), key=lambda x: x[1], reverse=True)
        ],
        "daily_trend": trend_data,
        "avg_confidence": round(sum(confidence_stats) / len(confidence_stats), 2) if confidence_stats else 0,
        "high_confidence_count": len([value for value in confidence_stats if value >= 0.8]),
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    query = select(User)
    if keyword:
        query = query.where((User.username.like(f"%{keyword}%")) | (User.email.like(f"%{keyword}%")))
    if role in {"admin", "user"}:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == int(is_active))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.execute(
        query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    items: list[dict[str, Any]] = []
    for user in users:
        detection_count = (
            (db.scalar(select(func.count()).select_from(ImgRecord).where(ImgRecord.username == user.username)) or 0)
            + (db.scalar(select(func.count()).select_from(VideoRecord).where(VideoRecord.username == user.username)) or 0)
            + (db.scalar(select(func.count()).select_from(CameraRecord).where(CameraRecord.username == user.username)) or 0)
        )
        items.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "tel": user.tel,
                "role": user.role or "user",
                "is_active": _to_bool_flag(user.is_active, True),
                "detections": detection_count,
                "created_at": user.time.isoformat() if user.time else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class UserPatchPayload(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    name: str | None = None
    tel: str | None = None
    email: str | None = None


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    payload: UserPatchPayload,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    if payload.role is not None:
        if payload.role not in {"admin", "user"}:
            raise HTTPException(status_code=400, detail="角色仅支持 admin/user")
        if user.id == current_user.id and payload.role != "admin":
            raise HTTPException(status_code=400, detail="不能将自己降级为普通用户")
        user.role = payload.role

    if payload.is_active is not None:
        if user.id == current_user.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="不能停用当前登录管理员")
        user.is_active = 1 if payload.is_active else 0

    if payload.name is not None:
        user.name = payload.name
    if payload.tel is not None:
        user.tel = payload.tel
    if payload.email is not None:
        user.email = payload.email

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role or "user",
        "is_active": _to_bool_flag(user.is_active, True),
        "email": user.email,
        "name": user.name,
        "tel": user.tel,
    }


@router.get("/notifications")
async def list_all_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None),
    is_read: bool | None = Query(None),
    user_id: int | None = Query(None),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    query = select(Notification)
    if type:
        query = query.where(Notification.type == type)
    if is_read is not None:
        query = query.where(Notification.is_read == int(is_read))
    if user_id is not None:
        query = query.where(Notification.user_id == user_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    unread_count = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.is_read == 0)
    ) or 0

    items = db.execute(
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return {
        "items": [_notification_to_dict(item) for item in items],
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
    }


class BroadcastPayload(BaseModel):
    title: str
    content: str
    type: str = "system"
    user_ids: list[int] | None = None


@router.post("/notifications/broadcast")
async def broadcast_notifications(
    payload: BroadcastPayload,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    targets: list[User]
    if payload.user_ids:
        targets = db.execute(select(User).where(User.id.in_(payload.user_ids))).scalars().all()
    else:
        targets = db.execute(select(User).where(User.is_active == 1)).scalars().all()

    created = 0
    for target in targets:
        create_notification(
            user_id=target.id,
            type=payload.type,
            title=payload.title,
            content=payload.content,
            db=db,
        )
        created += 1

    db.commit()
    return {
        "message": "广播通知已发送",
        "created_count": created,
        "operator_id": current_user.id,
    }


@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    type: str | None = Query(None),
    user_id: int | None = Query(None),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    query = select(Notification).where(Notification.is_read == 0)
    if type:
        query = query.where(Notification.type == type)
    if user_id is not None:
        query = query.where(Notification.user_id == user_id)

    notifications = db.execute(query).scalars().all()
    for item in notifications:
        item.is_read = 1
    db.commit()
    return {"message": f"已标记 {len(notifications)} 条通知为已读", "updated_count": len(notifications)}


@router.get("/models")
async def list_models(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    _ensure_model_policies(db)
    policies = db.execute(
        select(ModelPolicy).order_by(ModelPolicy.is_default.desc(), ModelPolicy.model_key.asc())
    ).scalars().all()
    return {"items": [_model_policy_to_dict(policy) for policy in policies]}


class ModelPolicyPayload(BaseModel):
    display_name: str | None = None
    enabled: bool | None = None
    is_default: bool | None = None
    fallback_to_cloud: bool | None = None
    fallback_notice: str | None = None


class ConfigsUpdatePayload(BaseModel):
    values: dict[str, Any]


@router.put("/models/{model_key}")
async def update_model_policy(
    model_key: str,
    payload: ModelPolicyPayload,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    _ensure_model_policies(db)
    policy = db.execute(select(ModelPolicy).where(ModelPolicy.model_key == model_key)).scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail="模型不存在")

    if payload.display_name is not None:
        policy.display_name = payload.display_name
    if payload.enabled is not None:
        policy.enabled = 1 if payload.enabled else 0
    if payload.fallback_to_cloud is not None:
        policy.fallback_to_cloud = 1 if payload.fallback_to_cloud else 0
    if payload.fallback_notice is not None:
        policy.fallback_notice = payload.fallback_notice.strip() or policy.fallback_notice

    if payload.is_default is not None:
        if payload.is_default:
            all_policies = db.execute(select(ModelPolicy)).scalars().all()
            for item in all_policies:
                item.is_default = 1 if item.model_key == model_key else 0
        else:
            policy.is_default = 0

    policy.updated_by = current_user.id
    policy.updated_at = datetime.now()
    db.commit()
    db.refresh(policy)
    return _model_policy_to_dict(policy)


@router.get("/knowledge")
async def list_knowledge(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    crop_type: str | None = Query(None),
    category: str | None = Query(None),
    source_name: str | None = Query(None),
    source_type: str | None = Query(None),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user

    normalized_keyword = (keyword or "").strip().lower()
    normalized_crop = (crop_type or "").strip()
    normalized_category = (category or "").strip()
    normalized_source_name = (source_name or "").strip().lower()
    normalized_source_type = (source_type or "").strip()
    query = select(KnowledgeItem)
    if normalized_keyword:
        query = query.where(
            (KnowledgeItem.title.like(f"%{normalized_keyword}%"))
            | (KnowledgeItem.disease_name.like(f"%{normalized_keyword}%"))
            | (KnowledgeItem.symptoms.like(f"%{normalized_keyword}%"))
            | (KnowledgeItem.tags_json.like(f"%{normalized_keyword}%"))
            | (KnowledgeItem.source_name.like(f"%{normalized_keyword}%"))
        )
    if normalized_crop:
        query = query.where(KnowledgeItem.crop_type == normalized_crop)
    if normalized_category:
        query = query.where(KnowledgeItem.category == normalized_category)
    if normalized_source_name:
        query = query.where(KnowledgeItem.source_name.like(f"%{normalized_source_name}%"))
    if normalized_source_type:
        query = query.where(KnowledgeItem.source_type == normalized_source_type)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(KnowledgeItem.updated_at.desc(), KnowledgeItem.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    items = [
        {
            "id": item["id"],
            "title": item["title"],
            "disease_name": item["disease_name"],
            "crop_type": item["crop_type"],
            "category": item["category"],
            "source_type": item["source_type"],
            "source_name": item["source_name"],
            "source_url": item["source_url"],
            "book_title": item["book_title"],
            "publisher": item["publisher"],
            "publish_year": item["publish_year"],
            "chapter_ref": item["chapter_ref"],
            "updated_at": item["updated_at"],
            "tags": item["tags"],
        }
        for item in (knowledge_item_to_dict(row) for row in rows)
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/configs")
async def get_configs(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    return {"items": list_system_configs(db)}


@router.put("/configs")
async def put_configs(
    payload: ConfigsUpdatePayload,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    updated = update_system_configs(db, payload.values or {}, operator_id=current_user.id)
    return {"items": updated}


@router.get("/audit/permissions")
async def list_permission_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status_code: int | None = Query(None),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    query = select(PermissionAuditLog)
    if status_code in {401, 403}:
        query = query.where(PermissionAuditLog.status_code == status_code)
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where(PermissionAuditLog.created_at >= start)
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.where(PermissionAuditLog.created_at <= end)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.execute(
        query.order_by(PermissionAuditLog.created_at.desc(), PermissionAuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return {
        "items": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "path": item.path,
                "method": item.method,
                "status_code": item.status_code,
                "client_ip": item.client_ip,
                "reason": item.reason,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/queue/metrics")
async def get_queue_monitor_metrics(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    del current_user
    return get_queue_metrics(db)
