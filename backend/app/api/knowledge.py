from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from typing import List
from uuid import UUID

from ..models import KnowledgeBase, User, get_db
from ..schemas import KnowledgeItem, KnowledgeDetail, KnowledgeCreate
from .auth import get_current_user, get_current_admin

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1),
    page: int = 1,
    page_size: int = 10,
    crop_type: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """搜索知识库"""
    query = select(KnowledgeBase).where(
        or_(
            KnowledgeBase.disease_name.ilike(f"%{q}%"),
            KnowledgeBase.symptoms.ilike(f"%{q}%"),
            KnowledgeBase.prevention.ilike(f"%{q}%")
        )
    )
    
    if crop_type:
        query = query.where(KnowledgeBase.crop_type == crop_type)
    
    from sqlalchemy import func
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # 如果没有结果，返回推荐
    if not items:
        recommend_result = await db.execute(
            select(KnowledgeBase).limit(5)
        )
        recommendations = recommend_result.scalars().all()
        
        return {
            "items": [],
            "recommendations": [
                KnowledgeItem(
                    id=r.id,
                    disease_name=r.disease_name,
                    crop_type=r.crop_type,
                    symptoms=r.symptoms,
                    image_urls=r.image_urls
                ).model_dump() for r in recommendations
            ]
        }
    
    return {
        "items": [
            KnowledgeItem(
                id=item.id,
                disease_name=item.disease_name,
                crop_type=item.crop_type,
                symptoms=item.symptoms,
                image_urls=item.image_urls
            ).model_dump() for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/recent")
async def get_recent_knowledge(
    page: int = 1,
    page_size: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取最近更新的知识条目"""
    query = select(KnowledgeBase).order_by(desc(KnowledgeBase.updated_at))
    
    from sqlalchemy import func
    total = await db.scalar(select(func.count()))
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return {
        "items": [
            KnowledgeItem(
                id=item.id,
                disease_name=item.disease_name,
                crop_type=item.crop_type,
                symptoms=item.symptoms,
                image_urls=item.image_urls
            ).model_dump() for item in items
        ],
        "total": total
    }


@router.get("/{knowledge_id}")
async def get_knowledge_detail(
    knowledge_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取知识条目详情"""
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在"
        )
    
    return KnowledgeDetail(
        id=item.id,
        disease_name=item.disease_name,
        crop_type=item.crop_type,
        symptoms=item.symptoms,
        conditions=item.conditions,
        prevention=item.prevention,
        cases=item.cases,
        image_urls=item.image_urls,
        updated_at=item.updated_at
    ).model_dump()


# ============ 管理端知识库CRUD ============

@router.post("", response_model=KnowledgeItem)
async def create_knowledge(
    data: KnowledgeCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """创建知识条目"""
    item = KnowledgeBase(
        disease_name=data.disease_name,
        crop_type=data.crop_type,
        symptoms=data.symptoms,
        conditions=data.conditions,
        prevention=data.prevention,
        cases=data.cases,
        image_urls=data.image_urls
    )
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    return KnowledgeItem(
        id=item.id,
        disease_name=item.disease_name,
        crop_type=item.crop_type,
        symptoms=item.symptoms,
        image_urls=item.image_urls
    )


@router.put("/{knowledge_id}")
async def update_knowledge(
    knowledge_id: UUID,
    data: KnowledgeCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新知识条目"""
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在"
        )
    
    for key, value in data.model_dump().items():
        if value is not None:
            setattr(item, key, value)
    
    await db.commit()
    
    return {"success": True, "message": "更新成功"}


@router.delete("/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除知识条目"""
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识条目不存在"
        )
    
    await db.delete(item)
    await db.commit()
    
    return {"success": True, "message": "删除成功"}
