from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.deps import create_access_token  # noqa: E402
from app.db.models import CameraRecord, ImgRecord, User, VideoRecord  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import fastapi_app  # noqa: E402


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _cleanup(username: str) -> None:
    db = SessionLocal()
    try:
        db.query(ImgRecord).filter(ImgRecord.username == username).delete(synchronize_session=False)
        db.query(VideoRecord).filter(VideoRecord.username == username).delete(synchronize_session=False)
        db.query(CameraRecord).filter(CameraRecord.username == username).delete(synchronize_session=False)
        db.query(User).filter(User.username == username).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _seed(username: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            username=username,
            password="stats-flow-test",
            email=f"{username}@example.com",
            name="stats-flow-test",
            role="user",
            is_active=1,
        )
        db.add(user)
        db.flush()
        records = [
            ImgRecord(
                username=username,
                modelKey="test",
                cropType="corn",
                inputImg="in-a.jpg",
                outImg="out-a.jpg",
                label=json.dumps(["leaf_spot", "aphid"]),
                confidence=json.dumps([0.91, 0.72]),
                conf="0.5",
                startTime="2026-04-20 10:00:00",
            ),
            ImgRecord(
                username=username,
                modelKey="test",
                cropType="corn",
                inputImg="in-b.jpg",
                outImg="out-b.jpg",
                label=json.dumps(["leaf_spot"]),
                confidence=json.dumps([0.82]),
                conf="0.5",
                startTime="2026-04-21 11:00:00",
            ),
            VideoRecord(
                username=username,
                modelKey="test",
                inputVideo="in.mp4",
                outVideo="out.mp4",
                startTime="2026-04-21 12:00:00",
                trackStats="{}",
            ),
            CameraRecord(
                username=username,
                modelKey="test",
                inputVideo="camera-in.mp4",
                outVideo="camera-out.mp4",
                startTime="2026-04-22 13:00:00",
                trackStats="{}",
            ),
        ]
        db.add_all(records)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _assert_stats(payload: dict) -> None:
    assert payload["total"] == 4, payload
    assert payload["period"] == "month"
    assert payload["start_date"] == "2026-04-19"
    assert payload["end_date"] == "2026-04-22"
    assert payload["avg_confidence"] == 0.82, payload
    assert payload["high_confidence_count"] == 2, payload

    distribution = {item["name"]: item["count"] for item in payload["pest_distribution"]}
    assert distribution == {"leaf_spot": 2, "aphid": 1}, distribution

    trend = {item["date"]: item["count"] for item in payload["trend_data"]}
    assert trend == {"2026-04-20": 1, "2026-04-21": 2, "2026-04-22": 1}, trend


def main() -> None:
    Base.metadata.create_all(bind=engine)
    username = f"stats_user_{int(time.time())}"
    _cleanup(username)
    user = _seed(username)

    try:
        with TestClient(fastapi_app) as client:
            headers = _auth_headers(user.id)
            params = {
                "period": "month",
                "start_date": "2026-04-19",
                "end_date": "2026-04-22",
            }
            overview_res = client.get("/detection/stats/overview", headers=headers, params=params)
            assert overview_res.status_code == 200, overview_res.text
            _assert_stats(overview_res.json())

            stats_res = client.get("/detection/stats", headers=headers, params=params)
            assert stats_res.status_code == 200, stats_res.text
            _assert_stats(stats_res.json())

        print("stats flow ok: overview/stats trend/distribution/confidence/date-range")
    finally:
        _cleanup(username)


if __name__ == "__main__":
    main()
