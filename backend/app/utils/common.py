from __future__ import annotations

import json
import math
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlalchemy.inspection import inspect as sa_inspect

from app.core.config import settings
from app.db.models import DATA_COLLECTION_FIELDS, DataCollectionRecord, USER_FIELDS, User


JSONDict = dict[str, Any]


def success(data: Any = None, msg: str = "success") -> JSONDict:
    return {"code": "0", "msg": msg, "data": data}


def error(code: str, msg: str) -> JSONDict:
    return {"code": str(code), "msg": msg, "data": None}


def model_to_dict(instance: Any) -> JSONDict:
    data: JSONDict = {}
    for attr in sa_inspect(instance).mapper.column_attrs:
        data[attr.key] = getattr(instance, attr.key)

    if isinstance(instance, DataCollectionRecord):
        data["ossImageUrls"] = parse_json_list(instance.ossImageUrls)

    return jsonable_encoder(data)


def parse_json_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def parse_datetime_value(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


def filtered_payload(payload: JSONDict, allowed_fields: set[str]) -> JSONDict:
    return {key: value for key, value in payload.items() if key in allowed_fields}


def apply_user_payload(instance: User, payload: JSONDict) -> None:
    for key, value in filtered_payload(payload, USER_FIELDS).items():
        if key == "time":
            setattr(instance, key, parse_datetime_value(value))
        else:
            setattr(instance, key, value)


def apply_data_collection_payload(instance: DataCollectionRecord, payload: JSONDict) -> None:
    data = filtered_payload(payload, DATA_COLLECTION_FIELDS)
    if "ossImageUrls" in data and isinstance(data["ossImageUrls"], list):
        data["ossImageUrls"] = json.dumps(data["ossImageUrls"], ensure_ascii=False)
    if "categories" in data and isinstance(data["categories"], (dict, list)):
        data["categories"] = json.dumps(data["categories"], ensure_ascii=False)
    for key, value in data.items():
        setattr(instance, key, value)


def apply_generic_payload(instance: Any, payload: JSONDict, allowed_fields: set[str]) -> None:
    for key, value in filtered_payload(payload, allowed_fields).items():
        setattr(instance, key, value)


def paginate(query: Any, page_num: int, page_size: int) -> JSONDict:
    safe_page_num = max(page_num, 1)
    safe_page_size = max(page_size, 1)
    total = query.count()
    records = query.offset((safe_page_num - 1) * safe_page_size).limit(safe_page_size).all()
    return {
        "records": [model_to_dict(record) for record in records],
        "total": total,
        "size": safe_page_size,
        "current": safe_page_num,
        "pages": math.ceil(total / safe_page_size) if safe_page_size else 0,
    }


def build_inline_file_response(file_name: str, file_bytes: bytes) -> Response:
    media_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    headers = {"Content-Disposition": f"inline; filename={quote(file_name)}"}
    return Response(content=file_bytes, media_type=media_type, headers=headers)


def cleanup_temp_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


def download_url_to_path(url: str, target_path: Path) -> None:
    with requests.get(url, stream=True, timeout=settings.request_timeout) as remote_response:
        remote_response.raise_for_status()
        with target_path.open("wb") as file_handle:
            for chunk in remote_response.iter_content(chunk_size=8192):
                if chunk:
                    file_handle.write(chunk)
