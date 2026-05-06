from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import KnowledgeItem  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _build_symptoms(item: KnowledgeItem) -> str:
    base = _normalize_text(item.symptoms)
    shape = _normalize_text(item.shape)
    color = _normalize_text(item.color)
    size = _normalize_text(item.size)

    parts: list[str] = []
    if base:
        parts.append(base.rstrip("。；;") + "。")
    parts.append("田间表现建议从叶片、茎秆和关键器官同时排查，重点观察病斑扩展速度与分布范围。")
    if shape or color or size:
        parts.append(f"典型病斑特征：形状{shape or '待补充'}，颜色{color or '待补充'}，大小{size or '待补充'}。")
    parts.append("发病初期常出现局部轻微症状，若不干预可能在3-7天内明显加重。")
    return "\n".join(parts)


def _build_conditions(item: KnowledgeItem) -> str:
    base = _normalize_text(item.conditions)
    parts: list[str] = []
    if base:
        parts.append(base.rstrip("。；;") + "。")
    parts.append("高湿、连阴雨、通风透光不足时，病害发生风险通常上升。")
    parts.append("偏施氮肥、田间排水不畅或植株长势不均时，植株抗性下降更易发病。")
    parts.append("建议结合当地气象变化与田块管理记录，提前做好预警巡查。")
    return "\n".join(parts)


def _build_prevention(item: KnowledgeItem) -> str:
    base = _normalize_text(item.prevention)
    parts: list[str] = []
    if base:
        parts.append(base.rstrip("。；;") + "。")
    parts.append("农业防治：清除病残体、合理轮作、优化密植并改善通风透光条件。")
    parts.append("田间管理：平衡施肥与水分管理，降低长时间高湿环境带来的侵染压力。")
    parts.append("药剂防治：按作物与病害登记用药要求轮换作用机制，严格遵循安全间隔期。")
    parts.append("复查建议：处理后3-7天回访病斑变化，必要时按分区二次处置。")
    return "\n".join(parts)


def enrich(apply: bool) -> tuple[int, int]:
    db = SessionLocal()
    try:
        items = db.query(KnowledgeItem).all()
        updated = 0
        for item in items:
            new_symptoms = _build_symptoms(item)
            new_conditions = _build_conditions(item)
            new_prevention = _build_prevention(item)

            changed = (
                _normalize_text(item.symptoms) != _normalize_text(new_symptoms)
                or _normalize_text(item.conditions) != _normalize_text(new_conditions)
                or _normalize_text(item.prevention) != _normalize_text(new_prevention)
            )
            if not changed:
                continue

            updated += 1
            if apply:
                item.symptoms = new_symptoms
                item.conditions = new_conditions
                item.prevention = new_prevention
                item.updated_at = datetime.now()

        if apply:
            db.commit()
        return len(items), updated
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich knowledge symptoms/conditions/prevention fields.")
    parser.add_argument("--apply", action="store_true", help="Write changes to DB. Without this flag, dry-run only.")
    args = parser.parse_args()

    total, updated = enrich(apply=args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] knowledge_items total={total}, to_update={updated}")


if __name__ == "__main__":
    main()
