from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import User
from app.utils.common import (
    JSONDict,
    apply_user_payload,
    error,
    model_to_dict,
    paginate,
    success,
)


router = APIRouter(prefix="/api/user", tags=["users"])


@router.post("/login")
def login(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    if not username or not password:
        return error("400", "Username or password cannot be empty")

    user = db.query(User).filter(User.username == username, User.password == password).first()
    if user is None:
        return error("401", "Username or password is incorrect")

    return success({"user": model_to_dict(user)})


@router.get("")
@router.get("/")
def get_user_list(
    pageNum: int = Query(1),
    pageSize: int = Query(10),
    search: str = Query(""),
    db: Session = Depends(get_db),
) -> JSONDict:
    query = db.query(User)
    if search.strip():
        query = query.filter(User.username.like(f"%{search.strip()}%"))
    query = query.order_by(User.id.asc())
    return success(paginate(query, pageNum, pageSize))


@router.get("/{username}")
def get_user_by_username(username: str, db: Session = Depends(get_db)) -> JSONDict:
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return error("404", "User not found")
    return success(model_to_dict(user))


@router.post("/register")
def register(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    if not username or not password:
        return error("400", "Username or password cannot be empty")

    existing = db.query(User).filter(User.username == username).first()
    if existing is not None:
        return error("400", "Username already exists")

    user = User()
    apply_user_payload(user, payload)
    if user.time is None:
        user.time = datetime.now()
    db.add(user)
    db.commit()
    db.refresh(user)
    return success(model_to_dict(user))


@router.post("/update")
def update_user(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    user_id = payload.get("id")
    if user_id is None:
        return error("400", "User id is required")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return error("404", "User not found")

    apply_user_payload(user, payload)
    db.commit()
    db.refresh(user)
    return success(model_to_dict(user))


@router.post("")
@router.post("/")
def add_user(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    if not username or not password:
        return error("400", "Username or password cannot be empty")

    existing = db.query(User).filter(User.username == username).first()
    if existing is not None:
        return error("400", "Username already exists")

    user = User()
    apply_user_payload(user, payload)
    if user.time is None:
        user.time = datetime.now()
    db.add(user)
    db.commit()
    db.refresh(user)
    return success(model_to_dict(user))


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)) -> JSONDict:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return success()
    db.delete(user)
    db.commit()
    return success()

