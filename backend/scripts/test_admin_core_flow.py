from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.deps import create_access_token  # noqa: E402
from app.db.models import Notification, PermissionAuditLog, SystemConfig, User  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import fastapi_app  # noqa: E402


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _cleanup(admin_username: str, user_username: str) -> None:
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.username.in_([admin_username, user_username])).all()
        user_ids = [item.id for item in users]
        if user_ids:
            db.query(Notification).filter(Notification.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(PermissionAuditLog).filter(PermissionAuditLog.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.query(SystemConfig).filter(SystemConfig.key.like("admin_flow_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _create_user(username: str, role: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            username=username,
            password="admin-core-flow-test",
            email=f"{username}@example.com",
            name=f"{role}-tester",
            role=role,
            is_active=1,
            time=datetime.now(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    stamp = int(time.time())
    admin_username = f"admin_core_{stamp}"
    user_username = f"user_core_{stamp}"
    _cleanup(admin_username, user_username)
    admin = _create_user(admin_username, "admin")
    normal_user = _create_user(user_username, "user")

    try:
        with TestClient(fastapi_app) as client:
            admin_headers = _auth_headers(admin.id)
            user_headers = _auth_headers(normal_user.id)

            # 触发一次403审计
            forbidden = client.get("/admin/dashboard", headers=user_headers)
            assert forbidden.status_code == 403, forbidden.text

            dashboard = client.get("/admin/dashboard", headers=admin_headers)
            assert dashboard.status_code == 200, dashboard.text

            users_res = client.get("/admin/users", headers=admin_headers, params={"page": 1, "page_size": 20})
            assert users_res.status_code == 200, users_res.text
            assert users_res.json()["items"], users_res.json()

            update_res = client.patch(
                f"/admin/users/{normal_user.id}",
                headers=admin_headers,
                json={"name": "updated-name"},
            )
            assert update_res.status_code == 200, update_res.text

            notifications_res = client.get("/admin/notifications", headers=admin_headers)
            assert notifications_res.status_code == 200, notifications_res.text

            broadcast_res = client.post(
                "/admin/notifications/broadcast",
                headers=admin_headers,
                json={"type": "system", "title": "admin-core-flow", "content": "ok", "user_ids": [normal_user.id]},
            )
            assert broadcast_res.status_code == 200, broadcast_res.text

            read_all_res = client.put("/admin/notifications/read-all", headers=admin_headers)
            assert read_all_res.status_code == 200, read_all_res.text

            models_res = client.get("/admin/models", headers=admin_headers)
            assert models_res.status_code == 200, models_res.text
            models = models_res.json().get("items") or []
            assert models, models_res.json()
            first_model = models[0]["model_key"]
            update_model_res = client.put(
                f"/admin/models/{first_model}",
                headers=admin_headers,
                json={"display_name": "admin-flow-model"},
            )
            assert update_model_res.status_code == 200, update_model_res.text

            stats_res = client.get("/admin/stats", headers=admin_headers)
            assert stats_res.status_code == 200, stats_res.text

            knowledge_res = client.get("/admin/knowledge", headers=admin_headers)
            assert knowledge_res.status_code == 200, knowledge_res.text

            configs_res = client.get("/admin/configs", headers=admin_headers)
            assert configs_res.status_code == 200, configs_res.text
            configs = configs_res.json().get("items") or {}
            assert "review_trigger_confidence" in configs, configs

            put_configs_res = client.put(
                "/admin/configs",
                headers=admin_headers,
                json={"values": {"queue_backlog_warn_threshold": 25, "queue_backlog_critical_threshold": 55}},
            )
            assert put_configs_res.status_code == 200, put_configs_res.text

            queue_res = client.get("/admin/queue/metrics", headers=admin_headers)
            assert queue_res.status_code == 200, queue_res.text
            assert "level" in queue_res.json(), queue_res.json()

            audit_res = client.get("/admin/audit/permissions", headers=admin_headers, params={"status_code": 403})
            assert audit_res.status_code == 200, audit_res.text
            assert audit_res.json()["total"] >= 1, audit_res.json()

        print("admin core flow ok: dashboard/users/notifications/models/knowledge/stats/configs/audit/queue")
    finally:
        _cleanup(admin_username, user_username)


if __name__ == "__main__":
    main()

