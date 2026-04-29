from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional, List
from uuid import UUID
import json
import base64

from ..models import Detection, User, DetectionType, DetectionSource, Severity, get_db
from ..schemas import (
    DetectionResponse, VideoDetectionResponse, DetectionHistoryItem,
    DiseaseResult, EnvironmentData
)
from .auth import get_current_user
from ..utils.security import validate_file_security, get_file_type_by_magic

router = APIRouter(prefix="/detection", tags=["检测"])


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/quicktime"}


async def save_upload_file(upload_file: UploadFile, folder: str) -> str:
    """保存上传文件并返回路径"""
    import os
    from ..core.config import settings
    
    # 生成唯一文件名
    import uuid
    ext = upload_file.filename.split(".")[-1] if "." in upload_file.filename else "bin"
    filename = f"{uuid.uuid4()}.{ext}"
    
    # 实际项目中应保存到MinIO，这里简化处理
    file_path = f"{folder}/{filename}"
    
    # 读取内容（实际应上传到对象存储）
    content = await upload_file.read()
    
    return file_path, content


async def get_environment_data(latitude: float = None, longitude: float = None) -> dict:
    """获取环境数据（天气、地址等）"""
    # 简化处理，实际应调用天气API和地图API
    return {
        "address": "湖南省长沙市" if latitude else None,
        "weather": "晴" if latitude else None,
        "temperature": 25.5 if latitude else None,
        "humidity": 65.0 if latitude else None
    }


async def cloud_ai_analyze(image_content: bytes) -> dict:
    """云端AI初步分析"""
    # 实际项目中应调用DeepSeek API
    # 这里返回模拟数据
    return {
        "crop_type": "水稻",
        "diseases": [
            {
                "name": "稻瘟病",
                "confidence": 0.85,
                "severity": "high",
                "symptoms": "叶片出现灰绿色病斑",
                "possible_causes": "高温高湿环境",
                "prevention": "选用抗病品种，合理施肥"
            }
        ],
        "has_pest": True,
        "model_match_keywords": ["稻瘟病", "水稻"]
    }


async def local_model_detect(image_content: bytes) -> dict:
    """本地YOLO模型检测"""
    # 实际项目中应调用本地YOLO模型
    # 这里返回模拟数据
    return {
        "diseases": [
            {
                "name": "稻瘟病",
                "confidence": 0.92,
                "severity": "high",
                "bounding_box": [100, 100, 300, 250],
                "symptoms": "叶片出现菱形病斑",
                "possible_causes": "高温高湿环境",
                "prevention": "选用抗病品种，合理施肥"
            }
        ]
    }


@router.post("/image", response_model=DetectionResponse)
async def detect_image(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """图像检测"""
    # 验证文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片格式，请上传 {', '.join(ALLOWED_IMAGE_TYPES)} 格式"
        )

    # 读取文件内容
    content = await file.read()

    # 魔数验证（防止伪装成图片的恶意文件）
    is_safe, error_msg = validate_file_security(content, file.filename, file.content_type)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件安全验证失败: {error_msg}"
        )

    # 验证文件大小
    if len(content) > 20 * 1024 * 1024:  # 20MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片大小不能超过20MB"
        )
    
    # 保存文件
    file_path, _ = await save_upload_file(file, "images")
    
    # 1. 云端AI初步分析
    ai_result = await cloud_ai_analyze(content)
    
    # 2. 检查是否匹配本地模型（简化处理）
    matched_models = ["稻瘟病"]  # 模拟匹配结果
    
    detection_source = DetectionSource.LOCAL_MODEL
    diseases = []
    
    if ai_result["model_match_keywords"] and matched_models:
        # 3a. 本地模型精确检测
        local_result = await local_model_detect(content)
        diseases = local_result["diseases"]
    else:
        # 3b. 直接返回云端AI结果
        detection_source = DetectionSource.CLOUD_AI
        diseases = ai_result["diseases"]
    
    # 4. 获取环境数据
    env_data = await get_environment_data(latitude, longitude)
    
    # 5. 保存检测记录
    detection = Detection(
        user_id=user.id,
        detection_type=DetectionType.IMAGE,
        source=detection_source,
        file_path=file_path,
        crop_type=ai_result.get("crop_type"),
        disease_name=diseases[0]["name"] if diseases else None,
        confidence=diseases[0]["confidence"] if diseases else None,
        severity=Severity(diseases[0]["severity"]) if diseases else None,
        bounding_boxes=[d.get("bounding_box") for d in diseases if d.get("bounding_box")],
        ai_analysis=ai_result,
        latitude=latitude,
        longitude=longitude,
        address=env_data.get("address"),
        weather=env_data.get("weather"),
        temperature=env_data.get("temperature"),
        humidity=env_data.get("humidity")
    )
    
    db.add(detection)
    await db.commit()
    await db.refresh(detection)
    
    return DetectionResponse(
        id=detection.id,
        source=detection_source.value,
        crop_type=detection.crop_type,
        diseases=[DiseaseResult(**d) for d in diseases],
        environment=EnvironmentData(**env_data),
        created_at=detection.created_at
    )


@router.post("/video", status_code=status.HTTP_202_ACCEPTED)
async def detect_video(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """视频检测（异步处理）"""
    # 验证文件类型
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的视频格式，请上传 {', '.join(ALLOWED_VIDEO_TYPES)} 格式"
        )
    
    # 读取并保存文件
    content = await file.read()
    if len(content) > 500 * 1024 * 1024:  # 500MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="视频大小不能超过500MB"
        )
    
    file_path, _ = await save_upload_file(file, "videos")
    
    # 保存检测记录
    detection = Detection(
        user_id=user.id,
        detection_type=DetectionType.VIDEO,
        source=DetectionSource.LOCAL_MODEL,
        file_path=file_path,
        latitude=latitude,
        longitude=longitude,
        review_status=None  # 待处理状态
    )
    
    db.add(detection)
    await db.commit()
    await db.refresh(detection)
    
    # 实际项目中应启动Celery异步任务处理视频
    # 这里返回任务ID
    
    return {
        "task_id": str(detection.id),
        "status": "processing",
        "message": "视频检测任务已提交，请稍后查询结果"
    }


@router.get("/history")
async def get_detection_history(
    page: int = 1,
    page_size: int = 20,
    detection_type: Optional[str] = None,
    severity: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取检测历史"""
    query = select(Detection).where(Detection.user_id == user.id)
    
    if detection_type:
        query = query.where(Detection.detection_type == DetectionType(detection_type))
    if severity:
        query = query.where(Detection.severity == Severity(severity))
    
    query = query.order_by(desc(Detection.created_at))
    
    # 分页
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    detections = result.scalars().all()
    
    return {
        "items": [
            DetectionHistoryItem(
                id=d.id,
                detection_type=d.detection_type.value,
                source=d.source.value,
                crop_type=d.crop_type,
                disease_name=d.disease_name,
                confidence=d.confidence,
                severity=d.severity.value if d.severity else None,
                thumbnail_path=d.thumbnail_path,
                created_at=d.created_at
            ).model_dump() for d in detections
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0
    }


@router.get("/{detection_id}")
async def get_detection_detail(
    detection_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取检测记录详情"""
    result = await db.execute(
        select(Detection).where(
            Detection.id == detection_id,
            Detection.user_id == user.id
        )
    )
    detection = result.scalar_one_or_none()
    
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="检测记录不存在"
        )
    
    return {
        "id": str(detection.id),
        "detection_type": detection.detection_type.value,
        "source": detection.source.value,
        "crop_type": detection.crop_type,
        "disease_name": detection.disease_name,
        "confidence": detection.confidence,
        "severity": detection.severity.value if detection.severity else None,
        "bounding_boxes": detection.bounding_boxes,
        "ai_analysis": detection.ai_analysis,
        "environment": {
            "address": detection.address,
            "weather": detection.weather,
            "temperature": detection.temperature,
            "humidity": detection.humidity
        } if detection.address else None,
        "created_at": detection.created_at.isoformat()
    }


@router.get("/stats/overview")
async def get_detection_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取个人统计概览"""
    from datetime import datetime, timedelta
    
    # 今日检测数
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db.scalar(
        select(func.count()).select_from(Detection).where(
            Detection.user_id == user.id,
            Detection.created_at >= today_start
        )
    )
    
    # 总检测数
    total_count = await db.scalar(
        select(func.count()).select_from(Detection).where(
            Detection.user_id == user.id
        )
    )
    
    # 病虫害分布
    disease_result = await db.execute(
        select(
            Detection.disease_name,
            func.count(Detection.id).label("count")
        ).where(
            Detection.user_id == user.id,
            Detection.disease_name.isnot(None)
        ).group_by(Detection.disease_name).order_by(desc("count")).limit(10)
    )
    disease_dist = [{"name": r[0], "count": r[1]} for r in disease_result.all()]
    
    # 月度趋势（最近30天）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    trend_result = await db.execute(
        select(
            func.date(Detection.created_at).label("date"),
            func.count(Detection.id).label("count")
        ).where(
            Detection.user_id == user.id,
            Detection.created_at >= thirty_days_ago
        ).group_by("date").order_by("date")
    )
    trend = [{"date": str(r[0]), "count": r[1]} for r in trend_result.all()]
    
    return {
        "today_count": today_count or 0,
        "total_count": total_count or 0,
        "disease_distribution": disease_dist,
        "monthly_trend": trend
    }
