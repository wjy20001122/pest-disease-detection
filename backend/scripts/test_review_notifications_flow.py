from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.deps import create_access_token  # noqa: E402
from app.api.routers.notifications import create_notification  # noqa: E402
from app.db.models import Notification, ReviewEvent, User  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import fastapi_app  # noqa: E402
from app.services.review_agent import review_agent  # noqa: E402


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _cleanup(username: str) -> None:
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.username == username).all()
        user_ids = [user.id for user in users]
        if user_ids:
            db.query(Notification).filter(Notification.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(ReviewEvent).filter(ReviewEvent.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _create_user(username: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            username=username,
            password="review-notification-test",
            email=f"{username}@example.com",
            name="review-notification-test",
            role="user",
            is_active=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _review_payload() -> dict:
    return {
        "has_pest": True,
        "merged_result": {
            "diseases": [
                {"name": "玉米螟幼虫", "confidence": 0.91, "severity": "high"}
            ]
        },
        "environment": {"address": "测试田块A", "weather": "晴", "temperature": 28},
        "regional_history": [
            {"disease_name": "玉米螟幼虫", "address": "测试田块A", "created_at": datetime.now().isoformat()},
            {"disease_name": "玉米螟幼虫", "address": "测试田块A", "created_at": datetime.now().isoformat()},
        ],
    }

def _false_positive_payload(user_id: int) -> tuple[dict, dict]:
    detection_payload = {
        "record_id": 9001,
        "user_id": user_id,
        "has_pest": True,
        "merged_result": {
            "diseases": [
                {"name": "疑似误报目标", "confidence": 0.82, "severity": "medium"}
            ]
        },
    }
    assessment_payload = {
        "risk_level": "low",
        "risk_score": 0.2,
        "risk_factors": ["图像质量较低", "目标边界模糊"],
        "recommendations": ["建议人工复核"],
        "is_false_positive": True,
        "reasoning": "检测框与典型病虫害形态不一致",
    }
    return detection_payload, assessment_payload


def main() -> None:
    Base.metadata.create_all(bind=engine)
    username = f"review_user_{int(time.time())}"
    _cleanup(username)
    user = _create_user(username)

    try:
        review_result = asyncio.run(review_agent.review(_review_payload()))
        assert review_result["status"] == "warning", review_result
        assert review_result["warning"]["title"], review_result
        assert review_result["regional_alert"], review_result

        false_detection, false_assessment = _false_positive_payload(user.id)
        asyncio.run(review_agent.record_false_positive(false_detection, false_assessment))

        db = SessionLocal()
        try:
            false_event = (
                db.query(ReviewEvent)
                .filter(ReviewEvent.user_id == user.id, ReviewEvent.record_id == 9001)
                .order_by(ReviewEvent.id.desc())
                .first()
            )
            assert false_event is not None, "误报审查事件未落库"
            assert false_event.status == "false_positive"
            assert false_event.risk_assessment
            assert false_event.detection_snapshot
        finally:
            db.close()

        create_notification(
            user_id=user.id,
            type="warning",
            title=review_result["warning"]["title"],
            content=review_result["warning"]["content"],
            related_detection_id=10001,
        )

        with TestClient(fastapi_app) as client:
            headers = _auth_headers(user.id)
            list_res = client.get("/notifications", headers=headers)
            assert list_res.status_code == 200, list_res.text
            listing = list_res.json()
            assert listing["total"] == 1, listing
            assert listing["unread_count"] == 1, listing
            notification_id = listing["items"][0]["id"]
            assert listing["items"][0]["data"]["detection_id"] == 10001

            read_res = client.put(f"/notifications/{notification_id}/read", headers=headers)
            assert read_res.status_code == 200, read_res.text

            unread_res = client.get("/notifications", headers=headers, params={"is_read": False})
            assert unread_res.status_code == 200, unread_res.text
            assert unread_res.json()["unread_count"] == 0, unread_res.json()

            create_notification(
                user_id=user.id,
                type="agent_push",
                title="智能体审查报告",
                content="审查已完成",
            )
            agent_res = client.get("/notifications", headers=headers, params={"type": "agent"})
            assert agent_res.status_code == 200, agent_res.text
            assert agent_res.json()["total"] == 1, agent_res.json()

            read_all_res = client.put("/notifications/read-all", headers=headers)
            assert read_all_res.status_code == 200, read_all_res.text

        print("review notifications flow ok: review/warning/regional/db/list/read/read-all")
    finally:
        _cleanup(username)


if __name__ == "__main__":
    main()
