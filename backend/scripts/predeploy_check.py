from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path

import redis
from fastapi.testclient import TestClient
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.db.models import SystemConfig  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import fastapi_app  # noqa: E402
from app.services.oss_service import oss_service  # noqa: E402


def check_db_rw() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    key = f"predeploy_check_{uuid.uuid4().hex[:12]}"
    try:
        db.execute(text("SELECT 1"))
        row = SystemConfig(
            key=key,
            value="ok",
            updated_at=datetime.now(),
        )
        db.add(row)
        db.commit()
        db.query(SystemConfig).filter(SystemConfig.key == key).delete(synchronize_session=False)
        db.commit()
        print("[OK] DB read/write")
    finally:
        db.close()


def check_redis() -> None:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        pong = client.ping()
        if not pong:
            raise RuntimeError("redis ping failed")
        print("[OK] Redis connectivity")
    finally:
        client.close()


def check_oss() -> None:
    if not settings.oss_access_key_id or not settings.oss_access_key_secret:
        raise RuntimeError("OSS credentials are missing")
    object_name = f"corn-disease-detection/health/predeploy-{uuid.uuid4().hex[:8]}.txt"
    uploaded = oss_service.upload_bytes(object_name, b"predeploy-check")
    if not uploaded:
        raise RuntimeError("OSS upload failed")
    oss_service.delete_file(uploaded)
    print("[OK] OSS auth/upload/delete")


def check_api_health() -> None:
    with TestClient(fastapi_app) as client:
        response = client.get("/health")
        if response.status_code != 200:
            raise RuntimeError(f"health endpoint failed: {response.status_code}")
    print("[OK] API health route")


def main() -> None:
    check_db_rw()
    check_redis()
    check_oss()
    check_api_health()
    print("predeploy check passed")


if __name__ == "__main__":
    main()
