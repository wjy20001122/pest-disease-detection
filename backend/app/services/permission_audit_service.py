from __future__ import annotations

from datetime import datetime

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import PermissionAuditLog


def record_permission_audit(
    db: Session,
    request: Request,
    status_code: int,
    reason: str,
    user_id: int | None = None,
) -> None:
    client_host = request.client.host if request.client else None
    entry = PermissionAuditLog(
        user_id=user_id,
        path=request.url.path,
        method=request.method,
        status_code=status_code,
        client_ip=client_host,
        reason=reason,
        created_at=datetime.now(),
    )
    db.add(entry)
    db.commit()

