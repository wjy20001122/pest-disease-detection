from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID, uuid4
import json

from ..models import Conversation, User, KnowledgeBase, get_db
from ..schemas import QuestionRequest, QnAResponse, SourceInfo, ConversationItem
from .auth import get_current_user

router = APIRouter(prefix="/qna", tags=["问答"])


async def query_knowledge_base(question: str, db: AsyncSession) -> List[dict]:
    """从知识库检索相关内容"""
    from sqlalchemy import or_
    
    result = await db.execute(
        select(KnowledgeBase).where(
            or_(
                KnowledgeBase.disease_name.ilike(f"%{question}%"),
                KnowledgeBase.symptoms.ilike(f"%{question}%"),
                KnowledgeBase.prevention.ilike(f"%{question}%")
            )
        ).limit(5)
    )
    
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "disease_name": item.disease_name,
            "content": f"{item.symptoms or ''}\n{item.prevention or ''}"
        }
        for item in items
    ]


async def generate_answer(question: str, context: List[dict]) -> str:
    """生成回答（实际应调用LLM）"""
    if not context:
        return f"关于「{question}」，我暂时没有找到相关的知识库内容。建议您咨询专业农技人员获取准确信息。"
    
    answer_parts = []
    for item in context[:3]:
        answer_parts.append(f"**{item['disease_name']}**：{item['content'][:200]}...")
    
    return f"根据您的描述，可能是以下病虫害：\n\n" + "\n\n".join(answer_parts) + "\n\n以上信息仅供参考，建议联系当地农技人员确认。"


def is_pest_related_question(question: str) -> bool:
    """判断问题是否与病虫害相关"""
    pest_keywords = [
        "病", "虫", "害", "叶", "黄", "斑", "枯", "萎", "烂",
        "虫害", "病害", "作物", "农业", "种植", "施肥", "农药"
    ]
    return any(keyword in question for keyword in pest_keywords)


@router.post("/ask", response_model=QnAResponse)
async def ask_question(
    data: QuestionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提问"""
    # 意图识别
    if not is_pest_related_question(data.question):
        return QnAResponse(
            answer="抱歉，我专注于农作物病虫害相关问题。您可以咨询其他领域的专业人士获取帮助。",
            sources=[],
            is_in_scope=False,
            disclaimer="以上回答仅供参考，请以专业农技人员意见为准。",
            conversation_id=uuid4()
        )
    
    # RAG检索
    relevant_docs = await query_knowledge_base(data.question, db)
    
    # 生成回答
    answer = await generate_answer(data.question, relevant_docs)
    
    # 构建来源信息
    sources = [
        SourceInfo(
            type="knowledge_base",
            id=UUID(doc["id"]) if doc.get("id") else None,
            title=doc["disease_name"],
            confidence=0.85
        )
        for doc in relevant_docs[:3]
    ]
    if not sources:
        sources.append(SourceInfo(type="llm_inference", confidence=0.7))
    
    # 保存对话
    conversation_id = data.conversation_id or uuid4()
    
    if data.conversation_id:
        # 更新现有对话
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == data.conversation_id,
                Conversation.user_id == user.id
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            messages = conversation.messages or []
            messages.extend([
                {"role": "user", "content": data.question},
                {"role": "assistant", "content": answer}
            ])
            conversation.messages = messages
        else:
            conversation = Conversation(
                id=conversation_id,
                user_id=user.id,
                messages=[
                    {"role": "user", "content": data.question},
                    {"role": "assistant", "content": answer}
                ]
            )
            db.add(conversation)
    else:
        # 新对话
        conversation = Conversation(
            id=conversation_id,
            user_id=user.id,
            messages=[
                {"role": "user", "content": data.question},
                {"role": "assistant", "content": answer}
            ]
        )
        db.add(conversation)
    
    await db.commit()
    
    return QnAResponse(
        answer=answer,
        sources=sources,
        is_in_scope=True,
        disclaimer="以上建议仅供参考，请以专业农技人员意见为准。",
        conversation_id=conversation_id
    )


@router.get("/conversations")
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取对话列表"""
    query = select(Conversation).where(
        Conversation.user_id == user.id
    ).order_by(desc(Conversation.updated_at))
    
    from sqlalchemy import func
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(c.id),
                "preview": c.messages[-1]["content"][:100] if c.messages else "",
                "created_at": c.created_at.isoformat()
            }
            for c in conversations
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取对话详情"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return {
        "id": str(conversation.id),
        "messages": conversation.messages,
        "created_at": conversation.created_at.isoformat()
    }


@router.post("/feedback")
async def submit_feedback(
    conversation_id: UUID,
    helpful: bool,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交回答反馈"""
    # 实际项目中应保存反馈数据用于优化问答质量
    return {"success": True, "message": "感谢您的反馈"}
