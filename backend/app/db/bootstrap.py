from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import inspect, text

from app.db.models import KnowledgeItem
from app.db.session import SessionLocal, engine
from app.services.knowledge_service import seed_knowledge_items
from app.services.system_config_service import ensure_default_system_configs


HISTORY_INDEX_TARGETS = [
    ("imgrecords", "idx_imgrecords_username_start_time", "username, start_time"),
    ("videorecords", "idx_videorecords_username_start_time", "username, start_time"),
    ("camerarecords", "idx_camerarecords_username_start_time", "username, start_time"),
]


def ensure_history_indexes() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table_name, index_name, columns in HISTORY_INDEX_TARGETS:
            try:
                indexes = inspector.get_indexes(table_name)
            except Exception:
                continue
            existing_names = {item.get("name") for item in indexes}
            if index_name in existing_names:
                continue
            try:
                conn.execute(text(f"CREATE INDEX {index_name} ON {table_name} ({columns})"))
            except Exception:
                continue


def bootstrap_runtime_data() -> None:
    db = SessionLocal()
    try:
        ensure_default_system_configs(db)
        existing = db.query(KnowledgeItem).count()
        if existing == 0:
            seed_path = Path(__file__).resolve().parents[2] / "data" / "knowledge_seed.json"
            if seed_path.exists():
                with seed_path.open("r", encoding="utf-8") as f:
                    payloads = json.load(f)
                if isinstance(payloads, list):
                    seed_knowledge_items(db, payloads)
    finally:
        db.close()
    ensure_history_indexes()
