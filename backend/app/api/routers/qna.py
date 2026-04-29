import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.deepseek_service import deepseek_service
from app.api.routers.knowledge import search_knowledge

router = APIRouter(prefix="/qna", tags=["问答"])


conversations_db = {}
current_conversation_id = 1


def build_context_from_knowledge(items: List[dict]) -> str:
    """从知识库条目构建上下文"""
    if not items:
        return ""

    context_parts = []
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


@router.post("/ask")
async def ask(
    question: str = Query(...),
    conversation_id: str = Query(None),
    crop_type: str = Query(None, description="作物类型筛选"),
    category: str = Query(None, description="类别筛选：虫害/病害"),
    current_user: User = Depends(get_current_user)
):
    global current_conversation_id

    if not conversation_id:
        conversation_id = str(current_conversation_id)
        current_conversation_id += 1
        conversations_db[conversation_id] = {
            "id": conversation_id,
            "user_id": current_user.id,
            "title": question[:50],
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="对话不存在")

    conv = conversations_db[conversation_id]

    user_message = {
        "role": "user",
        "content": question,
        "created_at": datetime.now().isoformat()
    }
    conv["messages"].append(user_message)

    relevant_knowledge = search_knowledge(
        keyword=question,
        crop_type=crop_type,
        category=category
    )

    context = build_context_from_knowledge(relevant_knowledge[:3])

    try:
        answer = await deepseek_service.ask_with_context(question, context, relevant_knowledge[:3])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务错误: {str(e)}")

    assistant_message = {
        "role": "assistant",
        "content": answer,
        "sources": [
            {
                "id": item["id"],
                "title": item["title"],
                "disease_name": item["disease_name"],
                "crop_type": item["crop_type"],
                "category": item["category"]
            }
            for item in relevant_knowledge[:3]
        ],
        "created_at": datetime.now().isoformat()
    }
    conv["messages"].append(assistant_message)
    conv["updated_at"] = datetime.now().isoformat()

    return {
        "answer": answer,
        "sources": assistant_message["sources"],
        "conversation_id": conversation_id
    }


@router.get("/conversations")
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    user_convs = [
        {k: v for k, v in conv.items() if k != "messages"}
        for conv in conversations_db.values()
        if conv.get("user_id") == current_user.id
    ]

    user_convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    offset = (page - 1) * page_size
    items = user_convs[offset:offset + page_size]

    return {
        "items": items,
        "total": len(user_convs),
        "page": page,
        "page_size": page_size
    }


@router.get("/conversations/{conv_id}")
async def get_conversation(
    conv_id: str,
    current_user: User = Depends(get_current_user)
):
    if conv_id not in conversations_db:
        raise HTTPException(status_code=404, detail="对话不存在")

    conv = conversations_db[conv_id]
    if conv.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="无权限访问此对话")

    return conv
