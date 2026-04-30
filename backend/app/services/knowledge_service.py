from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeItem


SUPPORTED_CROPS = {"玉米", "小麦", "水稻"}
SUPPORTED_CATEGORIES = {"虫害", "病害"}


def _safe_json_load_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
    except Exception:
        return []
    return []


def knowledge_item_to_dict(item: KnowledgeItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "disease_name": item.disease_name,
        "crop_type": item.crop_type,
        "category": item.category,
        "shape": item.shape or "",
        "color": item.color or "",
        "size": item.size or "",
        "symptoms": item.symptoms or "",
        "conditions": item.conditions or "",
        "prevention": item.prevention or "",
        "tags": _safe_json_load_list(item.tags_json),
        "source_name": item.source_name or "",
        "source_url": item.source_url or "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def list_knowledge_items(
    db: Session,
    *,
    keyword: str = "",
    crop_type: str | None = None,
    category: str | None = None,
    shape: str | None = None,
    color: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    query = select(KnowledgeItem)
    keyword = (keyword or "").strip()
    crop_type = (crop_type or "").strip()
    category = (category or "").strip()
    shape = (shape or "").strip()
    color = (color or "").strip()

    if keyword:
        like_kw = f"%{keyword}%"
        query = query.where(
            or_(
                KnowledgeItem.title.like(like_kw),
                KnowledgeItem.disease_name.like(like_kw),
                KnowledgeItem.symptoms.like(like_kw),
                KnowledgeItem.tags_json.like(like_kw),
            )
        )

    if crop_type:
        query = query.where(KnowledgeItem.crop_type == crop_type)
    if category:
        query = query.where(KnowledgeItem.category == category)
    if shape:
        query = query.where(KnowledgeItem.shape.like(f"%{shape}%"))
    if color:
        query = query.where(KnowledgeItem.color.like(f"%{color}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(desc(KnowledgeItem.updated_at), desc(KnowledgeItem.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return [knowledge_item_to_dict(row) for row in rows], total


def get_recent_knowledge_items(db: Session, *, page_size: int = 5) -> list[dict[str, Any]]:
    rows = db.execute(
        select(KnowledgeItem).order_by(desc(KnowledgeItem.updated_at), desc(KnowledgeItem.id)).limit(page_size)
    ).scalars().all()
    return [knowledge_item_to_dict(row) for row in rows]


def get_knowledge_item_by_id(db: Session, item_id: int) -> dict[str, Any] | None:
    row = db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id)).scalar_one_or_none()
    if not row:
        return None
    return knowledge_item_to_dict(row)


def get_distinct_shapes(db: Session) -> list[str]:
    rows = db.execute(
        select(KnowledgeItem.shape)
        .where(KnowledgeItem.shape.is_not(None), KnowledgeItem.shape != "")
        .distinct()
        .order_by(KnowledgeItem.shape.asc())
    ).scalars().all()
    return [value for value in rows if value]


def get_distinct_colors(db: Session) -> list[str]:
    rows = db.execute(
        select(KnowledgeItem.color)
        .where(KnowledgeItem.color.is_not(None), KnowledgeItem.color != "")
        .distinct()
        .order_by(KnowledgeItem.color.asc())
    ).scalars().all()
    return [value for value in rows if value]


def _build_keywords(keyword: str, features: dict[str, str] | None = None) -> list[str]:
    tokens: list[str] = []
    if keyword:
        tokens.extend([part.strip() for part in keyword.split() if part.strip()])
        tokens.append(keyword.strip())
    if features:
        for key in ("shape", "color", "symptoms"):
            value = (features.get(key) or "").strip()
            if value:
                tokens.extend([part.strip() for part in value.replace("，", ",").split(",") if part.strip()])
                tokens.append(value)
    unique: list[str] = []
    seen = set()
    for item in tokens:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(item)
    return unique


def search_knowledge_for_matching(
    db: Session,
    *,
    keyword: str = "",
    crop_type: str | None = None,
    category: str | None = None,
    features: dict[str, str] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    query = select(KnowledgeItem)
    crop_type = (crop_type or "").strip()
    category = (category or "").strip()
    if crop_type:
        query = query.where(KnowledgeItem.crop_type == crop_type)
    if category:
        query = query.where(KnowledgeItem.category == category)

    rows = db.execute(query.limit(300)).scalars().all()
    keywords = _build_keywords(keyword, features)
    scored: list[tuple[int, KnowledgeItem]] = []
    for row in rows:
        score = 0
        haystack_title = f"{row.title} {row.disease_name}".lower()
        symptoms = (row.symptoms or "").lower()
        tags = " ".join(_safe_json_load_list(row.tags_json)).lower()
        shape = (row.shape or "").lower()
        color = (row.color or "").lower()
        for token in keywords:
            low_token = token.lower()
            if not low_token:
                continue
            if low_token in haystack_title:
                score += 6
            if low_token in tags:
                score += 4
            if low_token in symptoms:
                score += 2
            if low_token in shape:
                score += 2
            if low_token in color:
                score += 2

        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: (item[0], item[1].updated_at, item[1].id), reverse=True)
    return [knowledge_item_to_dict(item[1]) for item in scored[:limit]]


def seed_knowledge_items(db: Session, payloads: list[dict[str, Any]]) -> int:
    inserted = 0
    now = datetime.now()
    for payload in payloads:
        crop_type = str(payload.get("crop_type", "")).strip()
        category = str(payload.get("category", "")).strip()
        if crop_type not in SUPPORTED_CROPS or category not in SUPPORTED_CATEGORIES:
            continue

        title = str(payload.get("title") or payload.get("disease_name") or "").strip()
        disease_name = str(payload.get("disease_name") or "").strip()
        if not title or not disease_name:
            continue

        existing = db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.disease_name == disease_name,
                KnowledgeItem.crop_type == crop_type,
                KnowledgeItem.category == category,
            )
        ).scalar_one_or_none()
        tags = payload.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        tags = [str(item).strip() for item in tags if str(item).strip()]
        updated_at_raw = payload.get("updated_at")
        updated_at = now
        if isinstance(updated_at_raw, str) and updated_at_raw.strip():
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
                try:
                    updated_at = datetime.strptime(updated_at_raw.strip(), fmt)
                    break
                except ValueError:
                    continue

        if existing:
            existing.title = title
            existing.shape = str(payload.get("shape") or "")
            existing.color = str(payload.get("color") or "")
            existing.size = str(payload.get("size") or "")
            existing.symptoms = str(payload.get("symptoms") or "")
            existing.conditions = str(payload.get("conditions") or "")
            existing.prevention = str(payload.get("prevention") or "")
            existing.tags_json = json.dumps(tags, ensure_ascii=False)
            existing.source_name = str(payload.get("source_name") or "")
            existing.source_url = str(payload.get("source_url") or "")
            existing.updated_at = updated_at
            continue

        db.add(
            KnowledgeItem(
                title=title,
                disease_name=disease_name,
                crop_type=crop_type,
                category=category,
                shape=str(payload.get("shape") or ""),
                color=str(payload.get("color") or ""),
                size=str(payload.get("size") or ""),
                symptoms=str(payload.get("symptoms") or ""),
                conditions=str(payload.get("conditions") or ""),
                prevention=str(payload.get("prevention") or ""),
                tags_json=json.dumps(tags, ensure_ascii=False),
                source_name=str(payload.get("source_name") or ""),
                source_url=str(payload.get("source_url") or ""),
                updated_at=updated_at,
                created_at=now,
            )
        )
        inserted += 1
    db.commit()
    return inserted
