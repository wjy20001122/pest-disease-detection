from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.deps import get_password_hash  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402


E2E_USERS = [
    {
        "username": "e2e_admin",
        "password": "E2Epass123!",
        "email": "e2e_admin@example.com",
        "role": "admin",
        "name": "E2E Admin",
    },
    {
        "username": "e2e_user",
        "password": "E2Epass123!",
        "email": "e2e_user@example.com",
        "role": "user",
        "name": "E2E User",
    },
]


def upsert_user(payload: dict[str, str]) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == payload["username"]).first()
        password_hash = get_password_hash(payload["password"])
        if user is None:
            user = User(
                username=payload["username"],
                password=password_hash,
                email=payload["email"],
                name=payload["name"],
                role=payload["role"],
                is_active=1,
                time=datetime.now(),
            )
            db.add(user)
        else:
            user.password = password_hash
            user.email = payload["email"]
            user.name = payload["name"]
            user.role = payload["role"]
            user.is_active = 1
            user.time = datetime.now()
        db.commit()
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    for user in E2E_USERS:
        upsert_user(user)
    print("e2e users ready: e2e_admin / e2e_user")


if __name__ == "__main__":
    main()
