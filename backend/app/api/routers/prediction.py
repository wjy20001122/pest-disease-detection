from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import JSONResponse

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


@router.get("/startRecording")
@router.get("/api/flask/startRecording")
def start_recording() -> JSONDict:
    return JSONResponse(
        status_code=410,
        content={
            "status": 410,
            "message": "Camera recording moved to the standalone ESP local service under ESP/.",
            "code": 410,
        },
    )


@router.get("/stopRecording")
@router.get("/api/flask/stopRecording")
def stop_recording(
    username: str = Query(""),
    modelKey: str = Query(""),
    startTime: str = Query(""),
) -> JSONDict:
    del username, modelKey, startTime
    return JSONResponse(
        status_code=410,
        content={
            "status": 410,
            "message": "Camera recording moved to the standalone ESP local service under ESP/.",
            "code": 410,
        },
    )


@router.post("/upload")
@router.post("/api/flask/upload")
async def upload_file(file: UploadFile = File(...), category: str = "img_predict"):
    return await prediction_service.upload_file(file, category)


@router.get("/uploads/{category:path}/{filename:path}")
@router.get("/api/flask/uploads/{category:path}/{filename:path}")
def serve_upload(category: str, filename: str):
    return prediction_service.serve_upload(category, filename)
