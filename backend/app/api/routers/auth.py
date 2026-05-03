from datetime import datetime, timedelta
import hashlib
import logging
import random
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db.models import EmailVerificationCode, User
from app.api.deps import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["认证"])
logger = logging.getLogger(__name__)


def _hash_email_code(email: str, purpose: str, code: str) -> str:
    payload = f"{email.strip().lower()}:{purpose}:{code}:{settings.app_name}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _create_plain_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def _normalize_purpose(purpose: str) -> str:
    purpose_value = (purpose or "").strip().lower()
    if purpose_value not in {"register", "reset_password"}:
        raise HTTPException(status_code=400, detail="验证码用途不支持")
    return purpose_value


def _send_email_code_impl(db: Session, email: str, purpose: str) -> None:
    now = datetime.now()
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=422, detail="邮箱不能为空")

    active_code = db.execute(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == normalized_email,
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.is_used == 0,
        )
        .order_by(EmailVerificationCode.created_at.desc())
    ).scalars().first()

    if active_code and (now - active_code.created_at).total_seconds() < settings.email_code_cooldown_seconds:
        raise HTTPException(
            status_code=429,
            detail=f"发送过于频繁，请在 {settings.email_code_cooldown_seconds} 秒后重试",
        )

    plain_code = _create_plain_code()
    try:
        email_service.send_verification_code(to_email=normalized_email, code=plain_code, purpose=purpose)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("send_email_code_failed email=%s purpose=%s", normalized_email, purpose)
        raise HTTPException(status_code=500, detail=f"验证码发送失败: {exc}") from exc

    db.execute(
        delete(EmailVerificationCode).where(
            EmailVerificationCode.email == normalized_email,
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.is_used == 0,
        )
    )
    db.add(
        EmailVerificationCode(
            email=normalized_email,
            purpose=purpose,
            code_hash=_hash_email_code(normalized_email, purpose, plain_code),
            is_used=0,
            created_at=now,
            expires_at=now + timedelta(minutes=settings.email_code_expire_minutes),
        )
    )
    db.commit()


def _verify_email_code_impl(db: Session, email: str, purpose: str, code: str) -> None:
    normalized_email = (email or "").strip().lower()
    code_value = (code or "").strip()
    if not code_value:
        raise HTTPException(status_code=422, detail="验证码不能为空")

    now = datetime.now()
    latest_code = db.execute(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == normalized_email,
            EmailVerificationCode.purpose == purpose,
        )
        .order_by(EmailVerificationCode.created_at.desc())
    ).scalars().first()

    if not latest_code:
        raise HTTPException(status_code=400, detail="请先获取验证码")
    if latest_code.is_used == 1:
        raise HTTPException(status_code=400, detail="验证码已使用，请重新获取")
    if latest_code.expires_at < now:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    if latest_code.code_hash != _hash_email_code(normalized_email, purpose, code_value):
        raise HTTPException(status_code=400, detail="验证码错误")

    latest_code.is_used = 1
    db.commit()


@router.post("/email/send-code")
async def send_email_code(
    email: str,
    purpose: str = "register",
    db: Session = Depends(get_db),
):
    normalized_purpose = _normalize_purpose(purpose)
    _send_email_code_impl(db, email, normalized_purpose)
    return {"message": "验证码已发送", "expire_minutes": settings.email_code_expire_minutes}


@router.post("/register")
async def register(
    username: str,
    password: str,
    email: str,
    email_code: str,
    name: str = "",
    db: Session = Depends(get_db)
):
    _verify_email_code_impl(db, email, "register", email_code)

    result = db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    result = db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = User(
        username=username,
        password=get_password_hash(password),
        email=email,
        name=name,
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "username": user.username, "email": user.email}


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    result = db.execute(
        select(User).where(
            (User.username == form_data.username) | (User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("login_failed reason=user_not_found username=%s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.password):
        logger.warning("login_failed reason=password_mismatch username=%s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_active == 0:
        logger.warning("login_failed reason=user_disabled username=%s", form_data.username)
        raise HTTPException(status_code=400, detail="用户已被禁用")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "name": current_user.name,
        "sex": current_user.sex,
        "tel": current_user.tel,
        "role": current_user.role,
        "avatar": current_user.avatar
    }


@router.put("/profile")
async def update_profile(
    name: str = None,
    sex: str = None,
    email: str = None,
    tel: str = None,
    avatar: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if name is not None:
        current_user.name = name
    if sex is not None:
        current_user.sex = sex
    if email is not None:
        current_user.email = email
    if tel is not None:
        current_user.tel = tel
    if avatar is not None:
        current_user.avatar = avatar

    db.commit()
    return {"message": "更新成功"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "登出成功"}


@router.post("/password/send-code")
async def send_reset_password_code(
    email: str,
    db: Session = Depends(get_db),
):
    normalized_email = (email or "").strip().lower()
    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="该邮箱未注册")
    _send_email_code_impl(db, normalized_email, "reset_password")
    return {"message": "重置验证码已发送", "expire_minutes": settings.email_code_expire_minutes}


@router.post("/password/reset")
async def reset_password(
    email: str,
    code: str,
    new_password: str,
    db: Session = Depends(get_db),
):
    if len(new_password or "") < 6:
        raise HTTPException(status_code=422, detail="新密码至少6位")

    normalized_email = (email or "").strip().lower()
    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="该邮箱未注册")

    _verify_email_code_impl(db, normalized_email, "reset_password", code)
    user.password = get_password_hash(new_password)
    db.commit()
    return {"message": "密码已重置，请重新登录"}
