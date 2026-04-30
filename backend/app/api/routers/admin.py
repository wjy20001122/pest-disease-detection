from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.api.routers.notifications import _notification_to_dict, create_notification
from app.db.models import CameraRecord, ImgRecord, ModelPolicy, Notification, User, VideoRecord
from app.db.session import get_db
from app.services.legacy_runtime import load_legacy_runtime

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
async def list_knowledge_placeholder(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_admin_user),
):
    del current_user
    return {"items": [], "total": 0, "page": page, "page_size": page_size}
