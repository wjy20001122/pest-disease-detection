from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import get_db
from app.db.models import (
    CAMERA_RECORD_FIELDS,
    DATA_COLLECTION_FIELDS,
    IMG_RECORD_FIELDS,
    VIDEO_RECORD_FIELDS,
    CameraRecord,
    DataCollectionRecord,
    ImgRecord,
    VideoRecord,
)
from app.services.oss_service import oss_service
from app.utils.common import (
    JSONDict,
    apply_data_collection_payload,
    apply_generic_payload,
    cleanup_temp_dir,
    download_url_to_path,
    error,
    model_to_dict,
    paginate,
    parse_json_list,
    success,
)


router = APIRouter(tags=["records"])


def delete_oss_values(values: list[Optional[str]]) -> None:
    for value in values:
        oss_service.delete_file(value)


@router.get("/api/imgRecords/all")
def get_all_img_records(db: Session = Depends(get_db)) -> JSONDict:
    records = db.query(ImgRecord).order_by(ImgRecord.id.desc()).all()
    return success([model_to_dict(record) for record in records])


@router.get("/api/imgRecords/{record_id}")
def get_img_record(record_id: int, db: Session = Depends(get_db)) -> JSONDict:
    record = db.query(ImgRecord).filter(ImgRecord.id == record_id).first()
    return success(model_to_dict(record) if record else None)


@router.get("/api/imgRecords")
def get_img_records(
    pageNum: int = Query(1),
    pageSize: int = Query(10),
    search: str = Query(""),
    search1: str = Query(""),
    search2: str = Query(""),
    search3: str = Query(""),
    db: Session = Depends(get_db),
) -> JSONDict:
    query = db.query(ImgRecord)
    if search.strip():
        query = query.filter(ImgRecord.username.like(f"%{search.strip()}%"))
    if search1.strip():
        query = query.filter(ImgRecord.modelKey.like(f"%{search1.strip()}%"))
    if search2.strip():
        query = query.filter(ImgRecord.label.like(f"%{search2.strip()}%"))
    if search3.strip():
        query = query.filter(ImgRecord.cropType.like(f"%{search3.strip()}%"))
    query = query.order_by(ImgRecord.startTime.desc())
    return success(paginate(query, pageNum, pageSize))


@router.post("/api/imgRecords/update")
def update_img_record(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    record_id = payload.get("id")
    if record_id is None:
        return error("400", "Record id is required")
    record = db.query(ImgRecord).filter(ImgRecord.id == record_id).first()
    if record is None:
        return error("404", "Record not found")
    apply_generic_payload(record, payload, IMG_RECORD_FIELDS)
    db.commit()
    db.refresh(record)
    return success(model_to_dict(record))


@router.post("/api/imgRecords")
def add_img_record(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    record = ImgRecord()
    apply_generic_payload(record, payload, IMG_RECORD_FIELDS)
    db.add(record)
    db.commit()
    db.refresh(record)
    return success(model_to_dict(record))


@router.delete("/api/imgRecords/all")
def delete_all_img_records(db: Session = Depends(get_db)) -> JSONDict:
    records = db.query(ImgRecord).all()
    for record in records:
        delete_oss_values([record.inputImg, record.outImg])
        db.delete(record)
    db.commit()
    return success()


@router.delete("/api/imgRecords/{record_id}")
def delete_img_record(record_id: int, db: Session = Depends(get_db)) -> JSONDict:
    record = db.query(ImgRecord).filter(ImgRecord.id == record_id).first()
    if record is None:
        return success()
    delete_oss_values([record.inputImg, record.outImg])
    db.delete(record)
    db.commit()
    return success()


@router.get("/api/videoRecords/all")
def get_all_video_records(db: Session = Depends(get_db)) -> JSONDict:
    records = db.query(VideoRecord).order_by(VideoRecord.id.desc()).all()
    return success([model_to_dict(record) for record in records])


@router.get("/api/videoRecords/{record_id}")
def get_video_record(record_id: int, db: Session = Depends(get_db)) -> JSONDict:
    record = db.query(VideoRecord).filter(VideoRecord.id == record_id).first()
    return success(model_to_dict(record) if record else None)


@router.get("/api/videoRecords")
def get_video_records(
    pageNum: int = Query(1),
    pageSize: int = Query(10),
    search: str = Query(""),
    search1: str = Query(""),
    search2: str = Query(""),
    search3: str = Query(""),
    db: Session = Depends(get_db),
) -> JSONDict:
    del search2, search3
    query = db.query(VideoRecord)
    if search.strip():
        query = query.filter(VideoRecord.username.like(f"%{search.strip()}%"))
    if search1.strip():
        query = query.filter(VideoRecord.modelKey.like(f"%{search1.strip()}%"))
    query = query.order_by(VideoRecord.startTime.desc())
    return success(paginate(query, pageNum, pageSize))


@router.post("/api/videoRecords/update")
def update_video_record(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    record_id = payload.get("id")
    if record_id is None:
        return error("400", "Record id is required")
    record = db.query(VideoRecord).filter(VideoRecord.id == record_id).first()
    if record is None:
        return error("404", "Record not found")
    apply_generic_payload(record, payload, VIDEO_RECORD_FIELDS)
    db.commit()
    db.refresh(record)
    return success(model_to_dict(record))


@router.post("/api/videoRecords")
def add_video_record(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    record = VideoRecord()
    apply_generic_payload(record, payload, VIDEO_RECORD_FIELDS)
    db.add(record)
    db.commit()
    db.refresh(record)
    return success(model_to_dict(record))


@router.delete("/api/videoRecords/all")
def delete_all_video_records(db: Session = Depends(get_db)) -> JSONDict:
    records = db.query(VideoRecord).all()
    for record in records:
        delete_oss_values([record.inputVideo, record.outVideo])
        db.delete(record)
    db.commit()
    return success()


@router.delete("/api/videoRecords/{record_id}")
def delete_video_record(record_id: int, db: Session = Depends(get_db)) -> JSONDict:
    record = db.query(VideoRecord).filter(VideoRecord.id == record_id).first()
    if record is None:
        return success()
    delete_oss_values([record.inputVideo, record.outVideo])
    db.delete(record)
    db.commit()
    return success()


@router.get("/api/cameraRecords/all")
def get_all_camera_records(db: Session = Depends(get_db)) -> JSONDict:
    records = db.query(CameraRecord).order_by(CameraRecord.id.desc()).all()
    return success([model_to_dict(record) for record in records])


@router.get("/api/cameraRecords/{record_id}")
def get_camera_record(record_id: int, db: Session = Depends(get_db)) -> JSONDict:
    record = db.query(CameraRecord).filter(CameraRecord.id == record_id).first()
    return success(model_to_dict(record) if record else None)


@router.get("/api/cameraRecords")
def get_camera_records(
    pageNum: int = Query(1),
    pageSize: int = Query(10),
    search: str = Query(""),
    search1: str = Query(""),
    search2: str = Query(""),
    search3: str = Query(""),
    db: Session = Depends(get_db),
) -> JSONDict:
    del search2, search3
    query = db.query(CameraRecord)
    if search.strip():
        query = query.filter(CameraRecord.username.like(f"%{search.strip()}%"))
    if search1.strip():
        query = query.filter(CameraRecord.modelKey.like(f"%{search1.strip()}%"))
    query = query.order_by(CameraRecord.startTime.desc())
    return success(paginate(query, pageNum, pageSize))


@router.post("/api/cameraRecords/update")
def update_camera_record(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    record_id = payload.get("id")
    if record_id is None:
        return error("400", "Record id is required")
    record = db.query(CameraRecord).filter(CameraRecord.id == record_id).first()
    if record is None:
        return error("404", "Record not found")
    apply_generic_payload(record, payload, CAMERA_RECORD_FIELDS)
    db.commit()
    db.refresh(record)
    return success(model_to_dict(record))


@router.post("/api/cameraRecords")
def add_camera_record(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    record = CameraRecord()
    apply_generic_payload(record, payload, CAMERA_RECORD_FIELDS)
    db.add(record)
    db.commit()
    db.refresh(record)
    return success(model_to_dict(record))


@router.delete("/api/cameraRecords/all")
def delete_all_camera_records(db: Session = Depends(get_db)) -> JSONDict:
    records = db.query(CameraRecord).all()
    for record in records:
        delete_oss_values([record.inputVideo, record.outVideo])
        db.delete(record)
    db.commit()
    return success()


@router.delete("/api/cameraRecords/{record_id}")
def delete_camera_record(record_id: int, db: Session = Depends(get_db)) -> JSONDict:
    record = db.query(CameraRecord).filter(CameraRecord.id == record_id).first()
    if record is None:
        return success()
    delete_oss_values([record.inputVideo, record.outVideo])
    db.delete(record)
    db.commit()
    return success()


@router.post("/api/datacollection/save")
def save_data_collection(payload: JSONDict, db: Session = Depends(get_db)) -> JSONDict:
    record = DataCollectionRecord()
    apply_data_collection_payload(record, payload)
    db.add(record)
    db.commit()
    db.refresh(record)
    return success(model_to_dict(record))


@router.get("/api/datacollection/list")
def list_data_collections(
    pageNum: int = Query(1),
    pageSize: int = Query(10),
    username: Optional[str] = Query(None),
    sessionType: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> JSONDict:
    query = db.query(DataCollectionRecord)
    if username and username.strip():
        query = query.filter(DataCollectionRecord.username.like(f"%{username.strip()}%"))
    if sessionType and sessionType.strip():
        query = query.filter(DataCollectionRecord.sessionType == sessionType.strip())
    query = query.order_by(DataCollectionRecord.startTime.desc())
    return success(paginate(query, pageNum, pageSize))


@router.get("/api/datacollection/detail/{record_id}")
def data_collection_detail(record_id: int, db: Session = Depends(get_db)) -> JSONDict:
    record = db.query(DataCollectionRecord).filter(DataCollectionRecord.id == record_id).first()
    return success(model_to_dict(record) if record else None)


@router.delete("/api/datacollection/delete/{record_id}")
def delete_data_collection(record_id: int, db: Session = Depends(get_db)) -> JSONDict:
    record = db.query(DataCollectionRecord).filter(DataCollectionRecord.id == record_id).first()
    if record is None:
        return success()
    for oss_url in parse_json_list(record.ossImageUrls):
        oss_service.delete_file(oss_url)
    db.delete(record)
    db.commit()
    return success()


@router.get("/api/datacollection/download/{record_id}", response_model=None)
def download_data_collection(record_id: int, db: Session = Depends(get_db)):
    record = db.query(DataCollectionRecord).filter(DataCollectionRecord.id == record_id).first()
    if record is None:
        return PlainTextResponse("Record not found", status_code=404)

    temp_dir = Path(tempfile.mkdtemp(prefix="data_collection_download_"))
    images_dir = temp_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        image_urls = parse_json_list(record.ossImageUrls)
        for index, image_url in enumerate(image_urls, start=1):
            if not image_url:
                continue
            original_name = Path(image_url).name or "image.jpg"
            if "." not in original_name:
                original_name = f"{original_name}.jpg"
            safe_name = f"img_{index:04d}_{original_name}"
            download_url_to_path(image_url, images_dir / safe_name)

        zip_name = f"data_collection_{record.sessionId or record.id}.zip"
        zip_path = temp_dir / zip_name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in images_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(images_dir).as_posix())

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=zip_name,
            background=BackgroundTask(cleanup_temp_dir, str(temp_dir)),
        )
    except Exception as exc:
        cleanup_temp_dir(str(temp_dir))
        return PlainTextResponse(f"Download failed: {exc}", status_code=500)

