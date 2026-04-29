import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/tracking", tags=["跟踪"])


class TrackingTask:
    pass


tasks_db = {}


@router.post("")
async def create_task(
    disease_name: str = Query(...),
    severity: str = Query("medium"),
    latitude: float = Query(None),
    longitude: float = Query(None),
    location: str = Query(""),
    notes: str = Query(""),
    detection_id: int = Query(None),
    current_user: User = Depends(get_current_user)
):
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "user_id": current_user.id,
        "disease_name": disease_name,
        "severity": severity,
        "latitude": latitude,
        "longitude": longitude,
        "location": location,
        "notes": notes,
        "detection_id": detection_id,
        "status": "active",
        "update_count": 0,
        "last_update": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "updates": []
    }
    tasks_db[task_id] = task

    return task


@router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    current_user: User = Depends(get_current_user)
):
    user_tasks = [
        t for t in tasks_db.values()
        if t["user_id"] == current_user.id and (status is None or t["status"] == status)
    ]

    user_tasks.sort(key=lambda x: x.get("last_update", ""), reverse=True)

    offset = (page - 1) * page_size
    items = user_tasks[offset:offset + page_size]

    return {
        "items": items,
        "total": len(user_tasks),
        "page": page,
        "page_size": page_size
    }


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="跟踪任务不存在")

    if task["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权限访问此任务")

    return task


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    status: str = Query(None),
    severity: str = Query(None),
    notes: str = Query(None),
    current_user: User = Depends(get_current_user)
):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="跟踪任务不存在")

    if task["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权限修改此任务")

    if status is not None:
        task["status"] = status
        if status == "resolved":
            task["resolved_at"] = datetime.now().isoformat()

    if severity is not None:
        task["severity"] = severity

    if notes is not None:
        task["notes"] = notes

    task["last_update"] = datetime.now().isoformat()

    return task


@router.post("/{task_id}/updates")
async def add_update(
    task_id: str,
    status: str = Query(None),
    note: str = Query(""),
    current_user: User = Depends(get_current_user)
):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="跟踪任务不存在")

    if task["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权限修改此任务")

    update = {
        "id": str(uuid.uuid4()),
        "status": status or task["status"],
        "note": note,
        "created_at": datetime.now().isoformat()
    }

    task["updates"].append(update)
    task["update_count"] = len(task["updates"])
    task["last_update"] = datetime.now().isoformat()

    if status:
        task["status"] = status

    return update


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="跟踪任务不存在")

    if task["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权限删除此任务")

    del tasks_db[task_id]

    return {"message": "删除成功"}
