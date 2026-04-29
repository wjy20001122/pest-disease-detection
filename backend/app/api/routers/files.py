from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import PlainTextResponse, Response

from app.services.oss_service import oss_service
from app.utils.common import JSONDict, build_inline_file_response, error, success


router = APIRouter(tags=["files"])


@router.post("/api/files/upload/oss")
async def upload_to_oss(file: UploadFile = File(...), category: str = "images") -> JSONDict:
    original_filename = file.filename or ""
    if not original_filename:
        return error("400", "Filename cannot be empty")

    file_bytes = await file.read()
    uploaded_url = oss_service.upload_bytes_for_category(file_bytes, original_filename, category)
    if uploaded_url:
        return success(uploaded_url)
    return error("500", "OSS upload failed")


@router.get("/api/files/{flag:path}", response_model=None)
def get_file(flag: str) -> Response | PlainTextResponse:
    file_bytes = oss_service.download_bytes(flag)
    if not file_bytes:
        return PlainTextResponse("File not found", status_code=404)
    file_name = Path(flag).name or "file"
    return build_inline_file_response(file_name, file_bytes)

