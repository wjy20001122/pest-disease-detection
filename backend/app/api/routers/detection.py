import uuid
import json
import asyncio
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, ImgRecord, VideoRecord, CameraRecord, Notification
from app.api.deps import get_current_user, get_current_user_from_header_or_query, decode_token
from app.services.oss_service import oss_service
from app.services.detection_router import detection_router, DetectionSource
from app.services.review_agent import review_agent

router = APIRouter(prefix="/detection", tags=["检测"])


camera_ws_sessions: Dict[str, Dict[str, Any]] = {}
MAX_CAMERA_WS_FRAME_BYTES = 5 * 1024 * 1024


async def trigger_review_task(detection_result: Dict, user_id: int, record_id: int, db: AsyncSession):
    """后台任务：触发智能体审查"""
    try:
        review_result = await review_agent.review(detection_result)

        if review_result and review_result.get("status") == "warning":
            warning = review_result.get("warning", {})

            notification = Notification(
                user_id=user_id,
                type="warning",
                title=warning.get("title", "病虫害预警"),
                content=warning.get("content", ""),
                is_read=False,
                related_detection_id=record_id
            )
            db.add(notification)
            await db.commit()
    except Exception:
        pass


@router.post("/image")
async def detect_image(
    file: UploadFile = File(...),
    crop_type: str = Query(""),
    latitude: float = Query(None),
    longitude: float = Query(None),
    address: str = Query(""),
    temperature: float = Query(None),
    humidity: float = Query(None),
    weather: str = Query(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未上传文件")

    file_bytes = await file.read()
    file_url = oss_service.upload_bytes(file_bytes, file.filename, "images")

    route_result = await detection_router.route_detection(file_url)

    source = route_result.get("source", DetectionSource.CLOUD_AI)
    has_pest = route_result.get("has_pest", True)
    merged_result = route_result.get("merged_result", {})
    ai_analysis = route_result.get("ai_analysis", {})
    local_detection = route_result.get("local_detection")
    knowledge_match = route_result.get("knowledge_match")
    confirmed_no_pest = route_result.get("confirmed_no_pest", False)
    message = route_result.get("message", "")

    labels = []
    confidences = []
    if local_detection and not local_detection.get("error"):
        labels = local_detection.get("labels", [])
        confidences = local_detection.get("confidences", [])

    labels_json = json.dumps(labels) if labels else "[]"
    confidences_json = json.dumps(confidences) if confidences else "[]"

    out_img = ""
    if local_detection and not local_detection.get("error"):
        out_img = local_detection.get("image", "")

    record = ImgRecord(
        username=current_user.username,
        modelKey=source.value if isinstance(source, DetectionSource) else source,
        cropType=crop_type or merged_result.get("crop_type", ""),
        inputImg=file_url,
        outImg=out_img,
        startTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        label=labels_json,
        confidence=confidences_json,
        conf="0.5"
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    response_data = {
        "id": record.id,
        "source": source.value if isinstance(source, DetectionSource) else source,
        "has_pest": has_pest,
        "confirmed_no_pest": confirmed_no_pest,
        "file_path": file_url,
        "created_at": record.startTime,
        "ai_analysis": ai_analysis,
        "knowledge_match": knowledge_match,
        "merged_result": merged_result if has_pest else None,
        "labels": labels if has_pest else [],
        "confidences": confidences if has_pest else [],
        "message": message
    }

    if has_pest:
        should_review = await detection_router.should_trigger_review(route_result)
        if should_review:
            response_data["needs_review"] = True
            response_data["review_triggered"] = True

            asyncio.create_task(
                trigger_review_task(route_result, current_user.id, record.id, db)
            )

    return response_data


@router.post("/video")
async def detect_video(
    file: UploadFile = File(...),
    model_key: str = Query("pest"),
    crop_type: str = Query(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未上传文件")

    file_bytes = await file.read()
    file_url = oss_service.upload_bytes(file_bytes, file.filename, "videos")

    from app.services.prediction_service import prediction_service
    session_id = prediction_service.create_video_session(
        input_video=file_url,
        model_key=model_key,
        username=current_user.username,
        conf="0.5"
    )

    record = VideoRecord(
        username=current_user.username,
        modelKey=model_key,
        inputVideo=file_url,
        startTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        trackStats="{}"
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "id": record.id,
        "session_id": session_id,
        "source": "video_detection",
        "file_path": file_url,
        "created_at": record.startTime,
        "status": "processing"
    }


@router.get("/video/{session_id}/status")
async def get_video_status(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    from app.services.prediction_service import prediction_service
    status = prediction_service.get_video_session_status(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    return status


@router.get("/video/{session_id}/stream")
async def get_video_stream(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    from fastapi.responses import StreamingResponse
    from app.services.prediction_service import prediction_service

    return prediction_service.get_video_stream(session_id)


@router.post("/video/{session_id}/stop")
async def stop_video_detection(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    from app.services.prediction_service import prediction_service
    result = prediction_service.stop_video_session(session_id)
    return result


@router.post("/camera/start")
async def start_camera_detection(
    model_key: str = Query("pest"),
    current_user: User = Depends(get_current_user)
):
    from app.services.prediction_service import prediction_service
    session_id = prediction_service.start_camera_session(
        model_key=model_key,
        username=current_user.username
    )
    return {
        "session_id": session_id,
        "status": "started"
    }


@router.get("/camera/stream")
async def get_camera_stream(
    current_user: User = Depends(get_current_user_from_header_or_query)
):
    from fastapi.responses import StreamingResponse
    from app.services.prediction_service import prediction_service
    return prediction_service.get_camera_stream()


@router.post("/camera/stop")
async def stop_camera_detection(
    current_user: User = Depends(get_current_user)
):
    from app.services.prediction_service import prediction_service
    result = prediction_service.stop_camera()
    return result


@router.websocket("/camera/ws")
async def camera_ws_detection(
    websocket: WebSocket,
    token: str = Query(""),
    model_key: str = Query("pest"),
    frame_interval_ms: int = Query(600, ge=100, le=3000),
):
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=1008, reason="Invalid token")
        return

    user_id = str(payload.get("sub"))
    session_id = str(uuid.uuid4())

    await websocket.accept()
    camera_ws_sessions[session_id] = {
        "user_id": user_id,
        "model_key": model_key,
        "frame_count": 0,
        "processed_count": 0,
        "started_at": datetime.now().isoformat(),
        "last_result": None,
        "last_frame_ts": 0.0,
    }

    await websocket.send_json(
        {
            "type": "session_started",
            "session_id": session_id,
            "frame_interval_ms": frame_interval_ms,
        }
    )

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "stop":
                await websocket.send_json({"type": "session_stopped", "session_id": session_id})
                break

            if msg_type != "frame":
                await websocket.send_json({"type": "error", "message": "Unsupported message type"})
                continue

            image_data = message.get("image")
            if not image_data or not isinstance(image_data, str):
                await websocket.send_json({"type": "error", "message": "Missing frame image"})
                continue

            camera_ws_sessions[session_id]["frame_count"] += 1

            now_ts = datetime.now().timestamp()
            min_interval_s = frame_interval_ms / 1000.0
            last_ts = camera_ws_sessions[session_id].get("last_frame_ts", 0.0)
            if now_ts - last_ts < min_interval_s:
                await websocket.send_json(
                    {
                        "type": "frame_skipped",
                        "reason": "rate_limited",
                        "min_interval_ms": frame_interval_ms,
                    }
                )
                continue

            if "," not in image_data:
                await websocket.send_json({"type": "error", "message": "Invalid frame format"})
                continue

            _, b64_data = image_data.split(",", 1)

            try:
                frame_bytes = base64.b64decode(b64_data)
            except Exception:
                await websocket.send_json({"type": "error", "message": "Invalid base64 frame"})
                continue

            if len(frame_bytes) > MAX_CAMERA_WS_FRAME_BYTES:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Frame too large",
                    }
                )
                continue

            frame_name = f"camera_ws_{session_id}_{camera_ws_sessions[session_id]['frame_count']}.jpg"
            frame_url = oss_service.upload_bytes(frame_bytes, frame_name, "camera")

            route_result = await detection_router.route_detection(frame_url)

            camera_ws_sessions[session_id]["processed_count"] += 1
            camera_ws_sessions[session_id]["last_result"] = route_result
            camera_ws_sessions[session_id]["last_frame_ts"] = now_ts

            await websocket.send_json(
                {
                    "type": "detection_result",
                    "session_id": session_id,
                    "frame_url": frame_url,
                    "source": route_result.get("source"),
                    "has_pest": route_result.get("has_pest"),
                    "confirmed_no_pest": route_result.get("confirmed_no_pest", False),
                    "merged_result": route_result.get("merged_result"),
                    "ai_analysis": route_result.get("ai_analysis"),
                    "knowledge_match": route_result.get("knowledge_match"),
                    "local_detection": route_result.get("local_detection"),
                }
            )
    except WebSocketDisconnect:
        pass
    finally:
        camera_ws_sessions.pop(session_id, None)


@router.get("/history")
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    detection_type: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * page_size

    if detection_type == "image":
        result = await db.execute(
            select(ImgRecord)
            .where(ImgRecord.username == current_user.username)
            .order_by(desc(ImgRecord.id))
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        total = await db.execute(
            select(ImgRecord)
            .where(ImgRecord.username == current_user.username)
        )
        total = len(total.scalars().all())
        records = [
            {
                "id": item.id,
                "type": "image",
                "input": item.inputImg,
                "output": item.outImg,
                "label": item.label,
                "confidence": item.confidence,
                "crop_type": item.cropType,
                "created_at": item.startTime
            }
            for item in items
        ]
    elif detection_type == "video":
        result = await db.execute(
            select(VideoRecord)
            .where(VideoRecord.username == current_user.username)
            .order_by(desc(VideoRecord.id))
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        total = await db.execute(
            select(VideoRecord)
            .where(VideoRecord.username == current_user.username)
        )
        total = len(total.scalars().all())
        records = [
            {
                "id": item.id,
                "type": "video",
                "input": item.inputVideo,
                "output": item.outVideo,
                "track_stats": item.trackStats,
                "created_at": item.startTime
            }
            for item in items
        ]
    elif detection_type == "camera":
        result = await db.execute(
            select(CameraRecord)
            .where(CameraRecord.username == current_user.username)
            .order_by(desc(CameraRecord.id))
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        total = await db.execute(
            select(CameraRecord)
            .where(CameraRecord.username == current_user.username)
        )
        total = len(total.scalars().all())
        records = [
            {
                "id": item.id,
                "type": "camera",
                "input": item.inputVideo,
                "output": item.outVideo,
                "track_stats": item.trackStats,
                "created_at": item.startTime
            }
            for item in items
        ]
    else:
        img_result = await db.execute(
            select(ImgRecord)
            .where(ImgRecord.username == current_user.username)
            .order_by(desc(ImgRecord.id))
            .offset(offset)
            .limit(page_size)
        )
        video_result = await db.execute(
            select(VideoRecord)
            .where(VideoRecord.username == current_user.username)
            .order_by(desc(VideoRecord.id))
            .offset(offset)
            .limit(page_size)
        )
        camera_result = await db.execute(
            select(CameraRecord)
            .where(CameraRecord.username == current_user.username)
            .order_by(desc(CameraRecord.id))
            .offset(offset)
            .limit(page_size)
        )

        records = []
        for item in img_result.scalars().all():
            records.append({
                "id": item.id,
                "type": "image",
                "input": item.inputImg,
                "output": item.outImg,
                "label": item.label,
                "confidence": item.confidence,
                "created_at": item.startTime
            })
        for item in video_result.scalars().all():
            records.append({
                "id": item.id,
                "type": "video",
                "input": item.inputVideo,
                "output": item.outVideo,
                "created_at": item.startTime
            })
        for item in camera_result.scalars().all():
            records.append({
                "id": item.id,
                "type": "camera",
                "input": item.inputVideo,
                "output": item.outVideo,
                "created_at": item.startTime
            })

        total = (len(img_result.scalars().all()) +
                 len(video_result.scalars().all()) +
                 len(camera_result.scalars().all()))

    records.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "items": records,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{record_id}")
async def get_detail(
    record_id: int,
    detection_type: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if detection_type == "image":
        result = await db.execute(
            select(ImgRecord).where(
                ImgRecord.id == record_id,
                ImgRecord.username == current_user.username
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="记录不存在")
        return {
            "id": item.id,
            "type": "image",
            "input": item.inputImg,
            "output": item.outImg,
            "label": item.label,
            "confidence": item.confidence,
            "crop_type": item.cropType,
            "created_at": item.startTime
        }
    elif detection_type == "video":
        result = await db.execute(
            select(VideoRecord).where(
                VideoRecord.id == record_id,
                VideoRecord.username == current_user.username
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="记录不存在")
        return {
            "id": item.id,
            "type": "video",
            "input": item.inputVideo,
            "output": item.outVideo,
            "track_stats": item.trackStats,
            "created_at": item.startTime
        }
    elif detection_type == "camera":
        result = await db.execute(
            select(CameraRecord).where(
                CameraRecord.id == record_id,
                CameraRecord.username == current_user.username
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="记录不存在")
        return {
            "id": item.id,
            "type": "camera",
            "input": item.inputVideo,
            "output": item.outVideo,
            "track_stats": item.trackStats,
            "created_at": item.startTime
        }
    else:
        raise HTTPException(status_code=400, detail="无效的检测类型")


@router.get("/stats/overview")
async def get_stats(
    period: str = Query("month", description="统计周期：day/week/month"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_

    now = datetime.now()
    if period == "day":
        start = now - timedelta(days=7)
    elif period == "week":
        start = now - timedelta(weeks=4)
    else:
        start = now - timedelta(days=90)

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = now

    img_result = await db.execute(
        select(ImgRecord).where(
            and_(
                ImgRecord.username == current_user.username,
                ImgRecord.startTime >= start.strftime("%Y-%m-%d"),
                ImgRecord.startTime <= end.strftime("%Y-%m-%d")
            )
        )
    )
    img_records = img_result.scalars().all()

    pest_distribution = {}
    daily_stats = {}
    confidence_stats = []

    for record in img_records:
        labels_json = record.label or "[]"
        confidences_json = record.confidence or "[]"

        try:
            import json
            labels = json.loads(labels_json)
            confidences = json.loads(confidences_json)

            date_key = record.startTime[:10] if record.startTime else "unknown"
            if date_key not in daily_stats:
                daily_stats[date_key] = {"count": 0, "pests": {}}

            daily_stats[date_key]["count"] += 1

            for label in labels:
                pest_distribution[label] = pest_distribution.get(label, 0) + 1
                if label not in daily_stats[date_key]["pests"]:
                    daily_stats[date_key]["pests"][label] = 0
                daily_stats[date_key]["pests"][label] += 1

            confidence_stats.extend([float(c) for c in confidences if c])

        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    avg_confidence = sum(confidence_stats) / len(confidence_stats) if confidence_stats else 0

    trend_data = [
        {"date": date, "count": stats["count"], "pests": stats["pests"]}
        for date, stats in sorted(daily_stats.items())
    ]

    return {
        "total": len(img_records),
        "period": period,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "pest_distribution": [
            {"name": name, "count": count}
            for name, count in sorted(pest_distribution.items(), key=lambda x: x[1], reverse=True)
        ],
        "trend_data": trend_data,
        "avg_confidence": round(avg_confidence, 2),
        "high_confidence_count": len([c for c in confidence_stats if c >= 0.8])
    }


@router.get("/export")
async def export_records(
    format: str = Query("json", description="导出格式：json 或 csv"),
    detection_type: str = Query(None, description="检测类型：image, video, camera"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导出用户检测记录"""
    from app.services.export_service import export_service

    data = await export_service.export_detection_records(
        db=db,
        username=current_user.username,
        start_date=start_date,
        end_date=end_date,
        detection_type=detection_type
    )

    records = data.get("records", [])

    if format == "csv":
        content = export_service.export_to_csv(records)
        return {
            "format": "csv",
            "content": content,
            "total": len(records)
        }
    else:
        content = export_service.export_to_json(data)
        return {
            "format": "json",
            "content": content,
            "total": len(records)
        }
