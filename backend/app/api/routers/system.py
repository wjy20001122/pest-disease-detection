from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings
from app.utils.common import JSONDict, success


router = APIRouter()


@router.get("/")
def root() -> JSONDict:
    return success({"service": settings.app_name})


@router.get("/health")
@router.get("/api/flask/health")
def health() -> JSONDict:
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

