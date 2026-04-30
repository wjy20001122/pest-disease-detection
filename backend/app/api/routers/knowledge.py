from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.knowledge_service import (
    SUPPORTED_CATEGORIES,
    SUPPORTED_CROPS,
    get_distinct_colors,
    get_distinct_shapes,
    get_knowledge_item_by_id,
    get_recent_knowledge_items,
    list_knowledge_items,
)

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("/search")
async def search(
    keyword: str = Query(""),
    crop_type: str = Query(None, description="作物类型：玉米/小麦/水稻"),
    category: str = Query(None, description="类别：虫害/病害"),
    shape: str = Query(None, description="形状特征"),
    color: str = Query(None, description="颜色特征"),
    source_name: str = Query(None, description="来源机构或文献名称关键词"),
    source_type: str = Query(None, description="来源类型：official/book/journal"),
    updated_from: str = Query(None, description="开始日期 YYYY-MM-DD"),
    updated_to: str = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    items, total = list_knowledge_items(
        db,
        keyword=keyword,
        crop_type=crop_type,
        category=category,
        shape=shape,
        color=color,
        source_name=source_name,
        source_type=source_type,
        updated_from=updated_from,
        updated_to=updated_to,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/recent")
async def get_recent(
    page_size: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return {"items": get_recent_knowledge_items(db, page_size=page_size)}


@router.get("/crops")
async def get_crops():
    return {"crops": sorted(SUPPORTED_CROPS)}


@router.get("/categories")
async def get_categories():
    return {"categories": sorted(SUPPORTED_CATEGORIES)}


@router.get("/shapes")
async def get_shapes(db: Session = Depends(get_db)):
    return {"shapes": get_distinct_shapes(db)}


@router.get("/colors")
async def get_colors(db: Session = Depends(get_db)):
    return {"colors": get_distinct_colors(db)}


@router.get("/{item_id}")
async def get_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = get_knowledge_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return item
