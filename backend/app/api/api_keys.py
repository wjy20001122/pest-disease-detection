import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, ApiKey
from app.api.deps import get_current_user

router = APIRouter(prefix="/api-keys", tags=["API密钥"])


def generate_api_key() -> str:
    """生成随机 API 密钥"""
    return f"pdds_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    """哈希 API 密钥"""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, key_hash: str) -> bool:
    """验证 API 密钥"""
    return hashlib.sha256(key.encode()).hexdigest() == key_hash


@router.post("")
async def create_api_key(
    name: str,
    rate_limit: int = 60,
    expires_days: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的 API 密钥"""
    key = generate_api_key()
    key_hash = hash_api_key(key)

    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    api_key = ApiKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=name,
        rate_limit=rate_limit,
        expires_at=expires_at,
        is_active=1,
        created_at=datetime.utcnow(),
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "key": key,
        "name": name,
        "rate_limit": rate_limit,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": api_key.created_at.isoformat()
    }


@router.get("")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的 API 密钥列表"""
    query = select(ApiKey).where(
        ApiKey.user_id == current_user.id
    ).order_by(desc(ApiKey.created_at))

    result = db.execute(query)
    keys = result.scalars().all()

    return {
        "items": [
            {
                "id": k.id,
                "name": k.name,
                "rate_limit": k.rate_limit,
                "is_active": k.is_active,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "created_at": k.created_at.isoformat()
            }
            for k in keys
        ]
    }


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除 API 密钥"""
    result = db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API密钥不存在"
        )

    db.delete(api_key)
    db.commit()

    return {"message": "API密钥已删除"}


@router.post("/{key_id}/toggle")
async def toggle_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """启用/禁用 API 密钥"""
    result = db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API密钥不存在"
        )

    api_key.is_active = not api_key.is_active
    db.commit()

    return {"message": f"API密钥已{'启用' if api_key.is_active else '禁用'}"}
