import uuid
import json
import asyncio
import base64
import logging
import redis
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, delete, desc, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.db.models import User, ImgRecord, VideoRecord, CameraRecord, ModelPolicy
from app.api.deps import get_current_user, get_current_user_from_header_or_query, decode_token
from app.api.routers.notifications import create_notification
from app.core.config import settings
from app.services.oss_service import oss_service
from app.services.detection_router import detection_router, DetectionSource
from app.services.review_agent import review_agent
from app.services.video_task_service import (
    create_video_task_record,
    get_owned_video_task,
    mark_video_task_failed,
    request_stop_video_task,
    to_status_payload,
)
from app.services.system_config_service import get_system_config_int

router = APIRouter(prefix="/detection", tags=["检测"])
logger = logging.getLogger(__name__)


camera_ws_sessions: Dict[str, Dict[str, Any]] = {}
MAX_CAMERA_WS_FRAME_BYTES = 5 * 1024 * 1024

DEFAULT_FALLBACK_NOTICE = "本地模型未识别到有效结果，已回退云端分析，结论未必完全可信。"


def _ensure_admin_user(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可使用该功能")


def _assert_video_queue_ready() -> None:
    redis_client = None
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        redis_client.ping()
    except Exception as exc:
        logger.warning("Video queue redis ping failed: %s", exc)
        raise HTTPException(status_code=503, detail="视频任务队列不可用，请检查Redis服务")
    finally:
        if redis_client is not None:
            try:
                redis_client.close()
            except Exception:
                pass

    try:
        from app.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=1.5)
        ping_result = inspector.ping() if inspector else None
        if not ping_result:
            raise RuntimeError("no active celery workers")
    except Exception as exc:
        logger.warning("Video queue celery ping failed: %s", exc)
        raise HTTPException(status_code=503, detail="视频任务队列不可用，请检查Celery worker服务")


def _resolve_model_policy(
    db: Session,
    requested_model_key: str,
) -> dict[str, Any]:
    requested = (requested_model_key or "").strip()
    total_policies = db.scalar(select(func.count()).select_from(ModelPolicy)) or 0

    if total_policies == 0:
        return {
            "effective_model_key": requested or "pest",
            "fallback_to_cloud": True,
            "fallback_notice": DEFAULT_FALLBACK_NOTICE,
            "model_switched": False,
            "switch_message": "",
        }

    default_policy = db.execute(
        select(ModelPolicy).where(ModelPolicy.is_default == 1).order_by(ModelPolicy.id.asc())
    ).scalars().first()
    if default_policy is None:
        default_policy = db.execute(select(ModelPolicy).order_by(ModelPolicy.id.asc())).scalars().first()

    requested_policy = None
    if requested:
        requested_policy = db.execute(
            select(ModelPolicy).where(ModelPolicy.model_key == requested)
        ).scalar_one_or_none()

    chosen_policy = requested_policy or default_policy
    model_switched = False
    switch_message = ""

    if chosen_policy is None:
        return {
            "effective_model_key": requested or "pest",
            "fallback_to_cloud": True,
            "fallback_notice": DEFAULT_FALLBACK_NOTICE,
            "model_switched": False,
            "switch_message": "",
        }

    if not bool(chosen_policy.enabled):
        if default_policy is not None and bool(default_policy.enabled):
            chosen_policy = default_policy
            model_switched = True
            switch_message = "所选模型已禁用，已切换至默认模型。"
        else:
            raise HTTPException(status_code=400, detail="当前模型不可用，请联系管理员启用模型。")

    if requested and chosen_policy.model_key != requested:
        model_switched = True
        if not switch_message:
            switch_message = "所选模型不可用，已切换至默认模型。"

    return {
        "effective_model_key": chosen_policy.model_key,
        "fallback_to_cloud": bool(chosen_policy.fallback_to_cloud),
        "fallback_notice": chosen_policy.fallback_notice or DEFAULT_FALLBACK_NOTICE,
        "model_switched": model_switched,
        "switch_message": switch_message,
    }


async def trigger_review_task(detection_result: Dict, user_id: int, record_id: int):
    """后台任务：触发智能体审查"""
    payload = dict(detection_result)
    payload["record_id"] = record_id
    payload["user_id"] = user_id
    try:
        review_result = await review_agent.review(payload)

        if review_result and review_result.get("status") == "warning":
            warning = review_result.get("warning", {})
            create_notification(
                user_id=user_id,
                type="warning",
                title=warning.get("title", "病虫害预警"),
                content=warning.get("content", ""),
                related_detection_id=record_id,
            )

            regional_alert = review_result.get("regional_alert")
            if regional_alert:
                create_notification(
                    user_id=user_id,
                    type="regional_alert",
                    title=regional_alert.get("title", "区域病虫害预警"),
                    content=regional_alert.get("content", ""),
                    related_detection_id=record_id,
                )
    except Exception:
        logger.exception(
            "Review task failed",
            extra={"record_id": record_id, "user_id": user_id},
        )


@router.post("/image")
async def detect_image(
    file: UploadFile = File(...),
    model_key: str = Query("", description="管理员可选：直连本地模型键"),
    crop_type: str = Query("", description="作物类型：玉米/小麦/水稻"),
    category: str = Query("", description="类别：病害/虫害"),
    latitude: float = Query(None),
    longitude: float = Query(None),
    address: str = Query(""),
    temperature: float = Query(None),
    humidity: float = Query(None),
    weather: str = Query(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未上传文件")

    file_bytes = await file.read()
    try:
        file_url = oss_service.upload_bytes_for_category(file_bytes, file.filename, "images")
    except Exception:
        raise HTTPException(status_code=503, detail="OSS上传失败，请检查OSS配置")
    if not file_url:
        raise HTTPException(status_code=503, detail="OSS上传失败，请检查OSS配置")

    normalized_model_key = (model_key or "").strip()
    normalized_crop_type = (crop_type or "").strip()
    normalized_category = (category or "").strip()
    is_admin_direct = current_user.role == "admin" and bool(normalized_model_key)

    if not is_admin_direct:
        if not normalized_crop_type or not normalized_category:
            raise HTTPException(status_code=422, detail="普通用户检测必须选择作物和病虫害类别")

    policy = _resolve_model_policy(db, normalized_model_key or "pest")

    route_result = await detection_router.route_detection(
        file_url,
        db=db,
        preferred_model_key=policy["effective_model_key"] if is_admin_direct else None,
        crop_type=normalized_crop_type,
        category=normalized_category,
        enforce_user_selection=not is_admin_direct,
        skip_ai_routing=is_admin_direct,
        use_local_model=True,
        allow_cloud_fallback=(False if is_admin_direct else policy["fallback_to_cloud"]),
        include_ai_advice=not is_admin_direct,
        fallback_notice=policy["fallback_notice"],
    )
    selected_model = (route_result.get("matched_models") or ["pest"])[0]

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
        out_img = local_detection.get("outImg") or local_detection.get("image") or ""

    record = ImgRecord(
        username=current_user.username,
        modelKey=source.value if isinstance(source, DetectionSource) else source,
        cropType=normalized_crop_type or merged_result.get("crop_type", ""),
        inputImg=file_url,
        outImg=out_img,
        startTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        label=labels_json,
        confidence=confidences_json,
        conf="0.5"
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    response_data = {
        "id": record.id,
        "source": source.value if isinstance(source, DetectionSource) else source,
        "selected_model": selected_model,
        "has_pest": has_pest,
        "confirmed_no_pest": confirmed_no_pest,
        "maybe_unreliable": route_result.get("maybe_unreliable", False),
        "confidence_notice": route_result.get("confidence_notice", ""),
        "model_switched": policy["model_switched"],
        "model_message": (
            policy["switch_message"]
            if not is_admin_direct
            else (policy["switch_message"] or "管理员直连模型模式")
        ),
        "file_path": file_url,
        "input_image": file_url,
        "output_image": out_img,
        "created_at": record.startTime,
        "ai_analysis": ai_analysis,
        "local_detection": local_detection,
        "knowledge_match": knowledge_match,
        "knowledge_candidates": route_result.get("knowledge_candidates", []),
        "merged_result": merged_result if has_pest else None,
        "labels": labels if has_pest else [],
        "confidences": confidences if has_pest else [],
        "message": message
    }
    environment_data = {
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
        "temperature": temperature,
        "humidity": humidity,
        "weather": weather,
    }

    if has_pest:
        review_payload = {**route_result, "environment": environment_data, "record_id": record.id}
        should_review = await detection_router.should_trigger_review(review_payload)
        if should_review:
            response_data["needs_review"] = True
            response_data["review_triggered"] = True

            asyncio.create_task(
                trigger_review_task(review_payload, current_user.id, record.id)
            )

    return response_data


@router.post("/video")
async def detect_video(
    file: UploadFile = File(...),
    model_key: str = Query("pest"),
    crop_type: str = Query(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _ensure_admin_user(current_user)
    _assert_video_queue_ready()

    if not file.filename:
        raise HTTPException(status_code=400, detail="未上传文件")

    policy = _resolve_model_policy(db, model_key)
    effective_model_key = policy["effective_model_key"]

    file_bytes = await file.read()
    try:
        file_url = oss_service.upload_bytes_for_category(file_bytes, file.filename, "videos")
    except Exception:
        raise HTTPException(status_code=503, detail="OSS上传失败，请检查OSS配置")
    if not file_url:
        raise HTTPException(status_code=503, detail="OSS上传失败，请检查OSS配置")

    session_id = uuid.uuid4().hex
    task = create_video_task_record(
        db,
        session_id=session_id,
        username=current_user.username,
        model_key=effective_model_key,
    )

    try:
        from app.tasks.video_tasks import process_video_detection

        process_video_detection.apply_async(
            kwargs={
                "session_id": session_id,
                "input_video": file_url,
                "model_key": effective_model_key,
                "username": current_user.username,
                "conf": "0.5",
            },
            task_id=session_id,
            soft_time_limit=get_system_config_int(db, "video_task_soft_time_limit_sec"),
            time_limit=get_system_config_int(db, "video_task_hard_time_limit_sec"),
        )
    except Exception as exc:
        mark_video_task_failed(
            db,
            session_id=session_id,
            error_message=f"视频任务入队失败: {exc}",
        )
        raise HTTPException(status_code=503, detail="视频任务队列不可用，请检查Redis/Celery服务")

    return {
        "id": task.id,
        "session_id": session_id,
        "source": "video_detection",
        "selected_model": effective_model_key,
        "model_switched": policy["model_switched"],
        "model_message": policy["switch_message"],
        "file_path": file_url,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "processing"
    }


@router.get("/video/{session_id}/status")
async def get_video_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin_user(current_user)
    task = get_owned_video_task(db, session_id, current_user.username)
    if not task:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    if task.status == "queued":
        queued_timeout_sec = get_system_config_int(db, "video_task_queued_timeout_sec")
        if queued_timeout_sec <= 0:
            queued_timeout_sec = 60
        elapsed = (datetime.now() - task.created_at).total_seconds() if task.created_at else 0
        if elapsed >= queued_timeout_sec:
            mark_video_task_failed(
                db,
                session_id=session_id,
                error_message=f"视频任务排队超时（>{queued_timeout_sec}s），请检查Celery worker状态",
            )
            task = get_owned_video_task(db, session_id, current_user.username)

    return to_status_payload(task)


@router.get("/video/{session_id}/stream")
async def get_video_stream(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin_user(current_user)
    from fastapi.responses import RedirectResponse

    task = get_owned_video_task(db, session_id, current_user.username)
    if not task:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    if task.status in {"queued", "processing"}:
        raise HTTPException(status_code=409, detail="视频仍在处理中")
    if task.status == "failed":
        raise HTTPException(status_code=500, detail=task.error_message or "视频处理失败")
    if not task.output_url:
        raise HTTPException(status_code=404, detail="输出视频不存在")

    return RedirectResponse(task.output_url)


@router.post("/video/{session_id}/stop")
async def stop_video_detection(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin_user(current_user)
    task = get_owned_video_task(db, session_id, current_user.username)
    if not task:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    request_stop_video_task(db, session_id)
    return {"status": 200, "message": "Stopping video processing", "code": 0}


@router.post("/camera/start")
async def start_camera_detection(
    model_key: str = Query("pest"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_admin_user(current_user)
    policy = _resolve_model_policy(db, model_key)
    effective_model_key = policy["effective_model_key"]

    from app.services.prediction_service import prediction_service
    session_id = prediction_service.start_camera_session(
        model_key=effective_model_key,
        username=current_user.username
    )
    return {
        "session_id": session_id,
        "status": "started",
        "selected_model": effective_model_key,
        "model_switched": policy["model_switched"],
        "model_message": policy["switch_message"],
    }


@router.get("/camera/stream")
async def get_camera_stream(
    current_user: User = Depends(get_current_user_from_header_or_query)
):
    _ensure_admin_user(current_user)
    from fastapi.responses import StreamingResponse
    from app.services.prediction_service import prediction_service
    return prediction_service.get_camera_stream()


@router.post("/camera/stop")
async def stop_camera_detection(
    current_user: User = Depends(get_current_user)
):
    _ensure_admin_user(current_user)
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
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.id == int(user_id))).scalar_one_or_none()
    finally:
        db.close()

    if not user or user.role != "admin":
        await websocket.close(code=1008, reason="Admin required")
        return

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
            try:
                frame_url = oss_service.upload_bytes_for_category(frame_bytes, frame_name, "camera")
            except Exception:
                await websocket.send_json({"type": "error", "message": "OSS上传失败，请检查OSS配置"})
                continue
            if not frame_url:
                await websocket.send_json({"type": "error", "message": "OSS上传失败，请检查OSS配置"})
                continue

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
    type: str = Query(None),
    date_from: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    keyword: str | None = Query(None, description="关键词（模型/crop）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * page_size
    normalized_type = (detection_type or type or "").strip().lower() or None
    keyword = (keyword or "").strip()
    start_time_lower = f"{date_from} 00:00:00" if date_from else None
    start_time_upper = f"{date_to} 23:59:59" if date_to else None

    def _build_time_filters(column):
        filters = []
        if start_time_lower:
            filters.append(column >= start_time_lower)
        if start_time_upper:
            filters.append(column <= start_time_upper)
        return filters

    def _build_img_filters():
        filters = [ImgRecord.username == current_user.username, *_build_time_filters(ImgRecord.startTime)]
        if keyword:
            filters.append((ImgRecord.modelKey.like(f"%{keyword}%")) | (ImgRecord.cropType.like(f"%{keyword}%")))
        return filters

    def _build_video_filters():
        filters = [VideoRecord.username == current_user.username, *_build_time_filters(VideoRecord.startTime)]
        if keyword:
            filters.append(VideoRecord.modelKey.like(f"%{keyword}%"))
        return filters

    def _build_camera_filters():
        filters = [CameraRecord.username == current_user.username, *_build_time_filters(CameraRecord.startTime)]
        if keyword:
            filters.append(CameraRecord.modelKey.like(f"%{keyword}%"))
        return filters

    if normalized_type == "image":
        result = db.execute(
            select(ImgRecord)
            .where(*_build_img_filters())
            .order_by(desc(ImgRecord.id))
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        total = db.scalar(select(func.count()).select_from(ImgRecord).where(*_build_img_filters())) or 0
        records = [
            {
                "id": item.id,
                "type": "image",
                "detection_type": "image",
                "input": item.inputImg,
                "output": item.outImg,
                "label": item.label,
                "confidence": item.confidence,
                "crop_type": item.cropType,
                "created_at": item.startTime
            }
            for item in items
        ]
    elif normalized_type == "video":
        result = db.execute(
            select(VideoRecord)
            .where(*_build_video_filters())
            .order_by(desc(VideoRecord.id))
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        total = db.scalar(select(func.count()).select_from(VideoRecord).where(*_build_video_filters())) or 0
        records = [
            {
                "id": item.id,
                "type": "video",
                "detection_type": "video",
                "input": item.inputVideo,
                "output": item.outVideo,
                "track_stats": item.trackStats,
                "created_at": item.startTime
            }
            for item in items
        ]
    elif normalized_type == "camera":
        result = db.execute(
            select(CameraRecord)
            .where(*_build_camera_filters())
            .order_by(desc(CameraRecord.id))
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        total = db.scalar(select(func.count()).select_from(CameraRecord).where(*_build_camera_filters())) or 0
        records = [
            {
                "id": item.id,
                "type": "camera",
                "detection_type": "camera",
                "input": item.inputVideo,
                "output": item.outVideo,
                "track_stats": item.trackStats,
                "created_at": item.startTime
            }
            for item in items
        ]
    else:
        img_query = select(
            ImgRecord.id.label("id"),
            literal("image").label("detection_type"),
            ImgRecord.inputImg.label("input"),
            ImgRecord.outImg.label("output"),
            ImgRecord.label.label("label"),
            ImgRecord.confidence.label("confidence"),
            ImgRecord.cropType.label("crop_type"),
            literal(None).label("track_stats"),
            ImgRecord.startTime.label("created_at"),
        ).where(and_(*_build_img_filters()))
        video_query = select(
            VideoRecord.id.label("id"),
            literal("video").label("detection_type"),
            VideoRecord.inputVideo.label("input"),
            VideoRecord.outVideo.label("output"),
            literal(None).label("label"),
            literal(None).label("confidence"),
            literal(None).label("crop_type"),
            VideoRecord.trackStats.label("track_stats"),
            VideoRecord.startTime.label("created_at"),
        ).where(and_(*_build_video_filters()))
        camera_query = select(
            CameraRecord.id.label("id"),
            literal("camera").label("detection_type"),
            CameraRecord.inputVideo.label("input"),
            CameraRecord.outVideo.label("output"),
            literal(None).label("label"),
            literal(None).label("confidence"),
            literal(None).label("crop_type"),
            CameraRecord.trackStats.label("track_stats"),
            CameraRecord.startTime.label("created_at"),
        ).where(and_(*_build_camera_filters()))

        union_subquery = union_all(img_query, video_query, camera_query).subquery()
        total = db.scalar(select(func.count()).select_from(union_subquery)) or 0
        rows = db.execute(
            select(union_subquery)
            .order_by(union_subquery.c.created_at.desc(), union_subquery.c.id.desc())
            .offset(offset)
            .limit(page_size)
        ).mappings().all()
        records = [
            {
                "id": row["id"],
                "type": row["detection_type"],
                "detection_type": row["detection_type"],
                "input": row["input"],
                "output": row["output"],
                "label": row["label"],
                "confidence": row["confidence"],
                "crop_type": row["crop_type"],
                "track_stats": row["track_stats"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    return {
        "items": records,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.delete("/history")
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    img_deleted = db.execute(
        delete(ImgRecord).where(ImgRecord.username == current_user.username)
    ).rowcount or 0
    video_deleted = db.execute(
        delete(VideoRecord).where(VideoRecord.username == current_user.username)
    ).rowcount or 0
    camera_deleted = db.execute(
        delete(CameraRecord).where(CameraRecord.username == current_user.username)
    ).rowcount or 0
    db.commit()
    return {
        "deleted": {
            "image": img_deleted,
            "video": video_deleted,
            "camera": camera_deleted,
            "total": img_deleted + video_deleted + camera_deleted,
        }
    }


def _parse_stats_window(period: str, start_date: str | None, end_date: str | None) -> tuple[datetime, datetime]:
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
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    else:
        end = now
    return start, end


def _record_in_window(start_time: str | None, start: datetime, end: datetime) -> bool:
    if not start_time:
        return False
    try:
        value = datetime.strptime(start_time[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            value = datetime.strptime(start_time[:10], "%Y-%m-%d")
        except ValueError:
            return False
    return start <= value <= end


def _empty_day_stats(date_key: str, daily_stats: dict[str, dict]) -> dict:
    if date_key not in daily_stats:
        daily_stats[date_key] = {"count": 0, "pests": {}}
    return daily_stats[date_key]


def _build_detection_stats(
    period: str = Query("month", description="统计周期：day/week/month"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start, end = _parse_stats_window(period, start_date, end_date)
    img_result = db.execute(select(ImgRecord).where(ImgRecord.username == current_user.username))
    video_result = db.execute(select(VideoRecord).where(VideoRecord.username == current_user.username))
    camera_result = db.execute(select(CameraRecord).where(CameraRecord.username == current_user.username))

    img_records = img_result.scalars().all()
    video_records = video_result.scalars().all()
    camera_records = camera_result.scalars().all()

    pest_distribution = {}
    daily_stats = {}
    confidence_stats = []

    for record in img_records:
        if not _record_in_window(record.startTime, start, end):
            continue

        date_key = record.startTime[:10] if record.startTime else "unknown"
        day_stats = _empty_day_stats(date_key, daily_stats)
        day_stats["count"] += 1

        labels_json = record.label or "[]"
        confidences_json = record.confidence or "[]"

        try:
            labels = json.loads(labels_json)
            confidences = json.loads(confidences_json)

            for label in labels:
                pest_distribution[label] = pest_distribution.get(label, 0) + 1
                day_stats["pests"][label] = day_stats["pests"].get(label, 0) + 1

            confidence_stats.extend([float(c) for c in confidences if c])

        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    for record in [*video_records, *camera_records]:
        if not _record_in_window(record.startTime, start, end):
            continue
        date_key = record.startTime[:10] if record.startTime else "unknown"
        _empty_day_stats(date_key, daily_stats)["count"] += 1

    avg_confidence = sum(confidence_stats) / len(confidence_stats) if confidence_stats else 0

    trend_data = [
        {"date": date, "count": stats["count"], "pests": stats["pests"]}
        for date, stats in sorted(daily_stats.items())
    ]

    return {
        "total": sum(stats["count"] for stats in daily_stats.values()),
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


@router.get("/stats")
async def get_stats(data: dict = Depends(_build_detection_stats)):
    return data


@router.get("/stats/overview")
async def get_stats_overview(data: dict = Depends(_build_detection_stats)):
    return data


@router.get("/{record_id}")
async def get_detail(
    record_id: int,
    detection_type: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if detection_type == "image":
        result = db.execute(
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
        result = db.execute(
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
        result = db.execute(
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


@router.get("/export")
async def export_records(
    format: str = Query("json", description="导出格式：json 或 csv"),
    detection_type: str = Query(None, description="检测类型：image, video, camera"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
