from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import QnAConversation, QnAMessage, User
from app.db.session import get_db
from app.services.deepseek_service import deepseek_service
from app.services.knowledge_service import search_knowledge_for_matching

router = APIRouter(prefix="/qna", tags=["问答"])


class AskPayload(BaseModel):
    question: str
    conversation_id: str | None = None
    crop_type: str | None = None
    category: str | None = None


def _to_iso(value: datetime | None) -> str:
    if not value:
        return ""
    return value.isoformat()


def _safe_sources(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    except Exception:
        return []
    return []


def _build_context_from_knowledge(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    context_parts: list[str] = []
    for item in items:
        context_parts.append(
            f"【{item['title']}】\n"
            f"作物类型：{item.get('crop_type', '')}\n"
            f"类别：{item.get('category', '')}\n"
            f"形状特征：{item.get('shape', '')}\n"
            f"颜色特征：{item.get('color', '')}\n"
            f"症状：{item.get('symptoms', '')}\n"
            f"发生条件：{item.get('conditions', '')}\n"
            f"防治方法：{item.get('prevention', '')}"
        )
    return "\n\n".join(context_parts)


def _get_or_create_conversation(
    db: Session,
    *,
    current_user: User,
    question: str,
    conversation_id: str | None,
    crop_type: str | None,
    category: str | None,
) -> QnAConversation:
    if conversation_id:
        existing = db.execute(
            select(QnAConversation).where(
                QnAConversation.conversation_id == conversation_id,
                QnAConversation.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=404, detail="对话不存在")
        if crop_type:
            existing.crop_type = crop_type
        if category:
            existing.category = category
        return existing

    now = datetime.now()
    conversation = QnAConversation(
        conversation_id=uuid.uuid4().hex,
        user_id=current_user.id,
        title=question[:50],
        crop_type=crop_type,
        category=category,
        created_at=now,
        updated_at=now,
    )
    db.add(conversation)
    db.flush()
    return conversation


@router.post("/ask")
async def ask(
    payload: AskPayload | None = Body(None),
    question: str | None = Query(None),
    conversation_id: str | None = Query(None),
    crop_type: str | None = Query(None, description="作物类型筛选"),
    category: str | None = Query(None, description="类别筛选：虫害/病害"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    actual_question = (payload.question if payload else question or "").strip()
    actual_conversation_id = (payload.conversation_id if payload else conversation_id) or None
    actual_crop_type = (payload.crop_type if payload else crop_type) or None
    actual_category = (payload.category if payload else category) or None

    if not actual_question:
        raise HTTPException(status_code=422, detail="问题不能为空")

    conversation = _get_or_create_conversation(
        db,
        current_user=current_user,
        question=actual_question,
        conversation_id=actual_conversation_id,
        crop_type=actual_crop_type,
        category=actual_category,
    )

    now = datetime.now()
    db.add(
        QnAMessage(
            conversation_id=conversation.conversation_id,
            role="user",
            content=actual_question,
            sources_json=None,
            created_at=now,
        )
    )

    sources = search_knowledge_for_matching(
        db,
        keyword=actual_question,
        crop_type=actual_crop_type,
        category=actual_category,
        limit=3,
    )
    context = _build_context_from_knowledge(sources)

    try:
        answer = await deepseek_service.ask_with_context(
            actual_question,
            context=context,
            sources=sources,
            selection_context={
                "crop_type": actual_crop_type or "",
                "category": actual_category or "",
                "strict_selection": True,
            },
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"AI 服务错误: {exc}")

    db.add(
        QnAMessage(
            conversation_id=conversation.conversation_id,
            role="assistant",
            content=answer,
            sources_json=json.dumps(
                [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "disease_name": item["disease_name"],
                        "crop_type": item["crop_type"],
                        "category": item["category"],
                    }
                    for item in sources
                ],
                ensure_ascii=False,
            ),
            created_at=datetime.now(),
        )
    )
    conversation.updated_at = datetime.now()
    db.commit()

    return {
        "answer": answer,
        "sources": [
            {
                "id": item["id"],
                "title": item["title"],
                "disease_name": item["disease_name"],
                "crop_type": item["crop_type"],
                "category": item["category"],
            }
            for item in sources
        ],
        "conversation_id": conversation.conversation_id,
    }


@router.get("/conversations")
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(QnAConversation).where(QnAConversation.user_id == current_user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(desc(QnAConversation.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    items = [
        {
            "id": row.conversation_id,
            "user_id": row.user_id,
            "title": row.title,
            "crop_type": row.crop_type,
            "category": row.category,
            "created_at": _to_iso(row.created_at),
            "updated_at": _to_iso(row.updated_at),
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/conversations/{conv_id}")
async def get_conversation(
    conv_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = db.execute(
        select(QnAConversation).where(
            QnAConversation.conversation_id == conv_id,
            QnAConversation.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = db.execute(
        select(QnAMessage)
        .where(QnAMessage.conversation_id == conv_id)
        .order_by(QnAMessage.id.asc())
    ).scalars().all()
    return {
        "id": conversation.conversation_id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "crop_type": conversation.crop_type,
        "category": conversation.category,
        "created_at": _to_iso(conversation.created_at),
        "updated_at": _to_iso(conversation.updated_at),
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "sources": _safe_sources(message.sources_json),
                "created_at": _to_iso(message.created_at),
            }
            for message in messages
        ],
    }
