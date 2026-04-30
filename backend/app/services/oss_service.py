from __future__ import annotations

import mimetypes
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import cv2
import oss2

from app.core.config import settings


class OSSService:
    CATEGORY_PREFIXES = {
        "img_predict": "corn-disease-detection/images",
        "video_predict": "corn-disease-detection/videos",
        "camera_predict": "corn-disease-detection/camera",
        "camera": "corn-disease-detection/camera",
        "avatar": "corn-disease-detection/avatars",
        "images": "corn-disease-detection/images",
        "videos": "corn-disease-detection/videos",
    }

    def __init__(self) -> None:
        self._bucket: oss2.Bucket | None = None

    def _get_bucket(self) -> oss2.Bucket:
        if self._bucket is None:
            auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
            self._bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)
        return self._bucket

    def build_file_url(self, object_name: str) -> str:
        if settings.oss_domain:
            return f"https://{settings.oss_domain.strip('/')}/{object_name}"
        return f"https://{settings.oss_bucket_name}.{settings.oss_endpoint}/{object_name}"

    def build_object_name(self, category: str, original_filename: str) -> str:
        base_prefix = self.CATEGORY_PREFIXES.get(category, self.CATEGORY_PREFIXES["images"])
        safe_name = Path(original_filename).name or "file"
        return f"{base_prefix}/{int(time.time())}_{uuid.uuid4().hex[:8]}_{safe_name}"

    def extract_object_name(self, value: str) -> str:
        if not value:
            return ""
        if ".aliyuncs.com" in value or value.startswith("http://") or value.startswith("https://"):
            parsed = urlparse(value)
            if parsed.path:
                return parsed.path.lstrip("/")
        return value.lstrip("/")

    def upload_bytes(self, object_name: str, data: bytes) -> str | None:
        if not data:
            return None
        result = self._get_bucket().put_object(object_name, data)
        if result.status == 200:
            return self.build_file_url(object_name)
        return None

    def upload_bytes_for_category(self, data: bytes, filename: str, category: str) -> str | None:
        return self.upload_bytes(self.build_object_name(category, filename), data)

    def upload_file(
        self,
        file_path: str | Path,
        category: str = "img_predict",
        custom_object_name: str | None = None,
    ) -> str | None:
        file_path = Path(file_path)
        if not file_path.exists():
            return None
        object_name = custom_object_name or self.build_object_name(category, file_path.name)
        return self.upload_bytes(object_name, file_path.read_bytes())

    def upload_frame(self, frame, object_name: str) -> str | None:
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            return None
        return self.upload_bytes(object_name, encoded.tobytes())

    def download_bytes(self, value: str) -> bytes | None:
        object_name = self.extract_object_name(value)
        if not object_name:
            return None
        try:
            result = self._get_bucket().get_object(object_name)
            return result.read()
        except Exception:
            return None

    def delete_file(self, value: str | None) -> None:
        object_name = self.extract_object_name(value or "")
        if not object_name:
            return
        try:
            self._get_bucket().delete_object(object_name)
        except Exception:
            return

    def guess_media_type(self, file_name: str) -> str:
        return mimetypes.guess_type(file_name)[0] or "application/octet-stream"


oss_service = OSSService()
