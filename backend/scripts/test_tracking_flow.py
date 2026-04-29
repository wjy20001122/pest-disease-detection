from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.deps import create_access_token  # noqa: E402
from app.db.models import TrackingTask, TrackingUpdate, User  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import fastapi_app  # noqa: E402


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _create_user(username: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            username=username,
            password="tracking-flow-test",
            email=f"{username}@example.com",
            name="tracking-flow-test",
            role="user",
            is_active=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _cleanup(*usernames: str) -> None:
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.username.in_(usernames)).all()
        user_ids = [user.id for user in users]
        task_ids = [
            task.id
            for task in db.query(TrackingTask).filter(TrackingTask.user_id.in_(user_ids)).all()
        ]
        if task_ids:
            db.query(TrackingUpdate).filter(TrackingUpdate.task_id.in_(task_ids)).delete(synchronize_session=False)
            db.query(TrackingTask).filter(TrackingTask.id.in_(task_ids)).delete(synchronize_session=False)
        if user_ids:
            db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    suffix = int(time.time())
    owner_name = f"tracking_owner_{suffix}"
    other_name = f"tracking_other_{suffix}"
    _cleanup(owner_name, other_name)

    owner = _create_user(owner_name)
    other = _create_user(other_name)

    try:
        with TestClient(fastapi_app) as client:
            owner_headers = _auth_headers(owner.id)
            other_headers = _auth_headers(other.id)

            create_res = client.post(
                "/tracking",
                headers=owner_headers,
                json={
                    "disease_name": "玉米叶斑病",
                    "severity": "high",
                    "location": "测试田块A",
                    "notes": "初始测试任务",
                },
            )
            assert create_res.status_code == 200, create_res.text
            task = create_res.json()
            task_id = task["id"]
            assert task["status"] == "active"
            assert task["location"] == "测试田块A"

            list_res = client.get("/tracking", headers=owner_headers, params={"status": "active"})
            assert list_res.status_code == 200, list_res.text
            listed = list_res.json()
            assert listed["total"] >= 1
            assert any(item["id"] == task_id for item in listed["items"])

            detail_res = client.get(f"/tracking/{task_id}", headers=owner_headers)
            assert detail_res.status_code == 200, detail_res.text
            assert detail_res.json()["updates"] == []

            update_res = client.post(
                f"/tracking/{task_id}/updates",
                headers=owner_headers,
                data={"status": "monitoring", "note": "复查后继续观察"},
            )
            assert update_res.status_code == 200, update_res.text
            assert update_res.json()["status"] == "monitoring"

            alias_res = client.post(
                f"/api/v1/tracking/{task_id}/updates",
                headers=owner_headers,
                data={"status": "monitoring", "note": "兼容前端硬编码路径"},
            )
            assert alias_res.status_code == 200, alias_res.text

            resolved_res = client.put(
                f"/tracking/{task_id}",
                headers=owner_headers,
                json={"status": "resolved", "notes": "处理完成"},
            )
            assert resolved_res.status_code == 200, resolved_res.text
            resolved = resolved_res.json()
            assert resolved["status"] == "resolved"
            assert resolved["resolved_at"]

            forbidden_res = client.get(f"/tracking/{task_id}", headers=other_headers)
            assert forbidden_res.status_code == 404, forbidden_res.text

        print("tracking flow ok: create/list/detail/update/api-v1-alias/resolve/isolation")
    finally:
        _cleanup(owner_name, other_name)


if __name__ == "__main__":
    main()
