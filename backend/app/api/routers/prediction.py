from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile

from app.services.prediction_service import prediction_service
from app.utils.common import JSONDict


router = APIRouter(tags=["prediction"])


@router.get("/get_models")
@router.get("/api/flask/get_models")
def get_models() -> JSONDict:
    return prediction_service.get_models()


@router.get("/file_names")
@router.get("/api/flask/file_names")
def file_names(
    modelKey: str | None = Query(None),
    kind: str | None = Query(None),
    model_name: str | None = Query(None),
) -> JSONDict:
    return prediction_service.file_names(modelKey or kind or model_name)


@router.post("/predictImg")
@router.post("/api/flask/predictImg")
def predict_img(payload: JSONDict):
    return prediction_service.predict_image(payload)


@router.get("/predictVideo")
@router.get("/api/flask/predictVideo")
def predict_video(
    sessionId: str | None = Query(None),
    modelKey: str = Query(""),
    inputVideo: str = Query(""),
    username: str = Query(""),
    startTime: str = Query(""),
    conf: str = Query("0.5"),
    fps: str | None = Query(None),
):
    return prediction_service.predict_video(
        session_id=sessionId,
        model_key=modelKey,
        input_video=inputVideo,
        username=username,
        start_time=startTime,
        conf=conf,
        fps=fps,
    )


@router.get("/stopVideo")
@router.get("/api/flask/stopVideo")
def stop_video(sessionId: str | None = Query(None)) -> JSONDict:
    return prediction_service.stop_video(sessionId or "")


@router.get("/predictCamera")
@router.get("/api/flask/predictCamera")
def predict_camera(
    modelKey: str = Query(""),
    username: str = Query(""),
    startTime: str = Query(""),
    conf: str = Query("0.5"),
    fps: str | None = Query(None),
    streamSource: str = Query("local"),
    esp32Ip: str = Query(""),
    esp32Port: int = Query(81),
):
    return prediction_service.predict_camera(
        model_key=modelKey,
        username=username,
        start_time=startTime,
        conf=conf,
        fps=fps,
        stream_source=streamSource,
        esp32_ip=esp32Ip,
        esp32_port=esp32Port,
    )


@router.get("/stopCamera")
@router.get("/api/flask/stopCamera")
def stop_camera() -> JSONDict:
    return prediction_service.stop_camera()


@router.get("/startRecording")
@router.get("/api/flask/startRecording")
def start_recording() -> JSONDict:
    return prediction_service.start_recording()


@router.get("/stopRecording")
@router.get("/api/flask/stopRecording")
def stop_recording(
    username: str = Query(""),
    modelKey: str = Query(""),
    startTime: str = Query(""),
) -> JSONDict:
    return prediction_service.stop_recording(
        username=username,
        model_key=modelKey,
        start_time=startTime,
    )


@router.post("/upload")
@router.post("/api/flask/upload")
async def upload_file(file: UploadFile = File(...), category: str = "img_predict"):
    return await prediction_service.upload_file(file, category)


@router.get("/uploads/{category:path}/{filename:path}")
@router.get("/api/flask/uploads/{category:path}/{filename:path}")
def serve_upload(category: str, filename: str):
    return prediction_service.serve_upload(category, filename)

