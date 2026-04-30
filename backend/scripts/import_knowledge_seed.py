from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.session import SessionLocal
from app.services.knowledge_service import seed_knowledge_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Import knowledge seed data into MySQL")
    parser.add_argument(
        "--file",
        default=str(Path(__file__).resolve().parents[1] / "data" / "knowledge_seed.json"),
        help="Path to knowledge seed json file",
    )
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Seed file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        payloads = json.load(f)
    if not isinstance(payloads, list):
        raise SystemExit("Seed file must be a JSON array")

    db = SessionLocal()
    try:
        inserted = seed_knowledge_items(db, payloads)
    finally:
        db.close()

    print(f"knowledge seed import done, inserted={inserted}, file={path}")


if __name__ == "__main__":
    main()
