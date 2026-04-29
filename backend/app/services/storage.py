import oss2
import uuid
from datetime import datetime
from typing import Optional, BinaryIO
from ..core.config import settings


class OSSStorage:
    def __init__(self):
        self.auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )
        self.bucket = oss2.Bucket(
            self.auth,
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET
        )
        self.bucket_name = settings.OSS_BUCKET

    def _generate_filename(self, original_filename: str, folder: str) -> str:
        ext = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        if ext:
            return f"{folder}/{timestamp}_{unique_id}.{ext}"
        return f"{folder}/{timestamp}_{unique_id}"

    async def upload_file(
        self,
        file_data: bytes | BinaryIO,
        filename: str,
        folder: str = "uploads",
        content_type: Optional[str] = None
    ) -> str:
        object_name = self._generate_filename(filename, folder)

        if isinstance(file_data, bytes):
            result = self.bucket.put_object(
                object_name,
                file_data,
                headers={'Content-Type': content_type} if content_type else None
            )
        else:
            result = self.bucket.put_object(
                object_name,
                file_data,
                headers={'Content-Type': content_type} if content_type else None
            )

        if result.status == 200:
            return f"https://{self.bucket_name}.{settings.OSS_ENDPOINT}/{object_name}"
        raise Exception(f"Failed to upload file to OSS: {result.status}")

    async def upload_image(
        self,
        file_data: bytes | BinaryIO,
        filename: str
    ) -> str:
        return await self.upload_file(file_data, filename, "images", "image/jpeg")

    async def upload_video(
        self,
        file_data: bytes | BinaryIO,
        filename: str
    ) -> str:
        return await self.upload_file(file_data, filename, "videos", "video/mp4")

    async def delete_file(self, file_url: str) -> bool:
        object_name = file_url.split(f"{self.bucket_name}.{settings.OSS_ENDPOINT}/")[-1]
        try:
            result = self.bucket.delete_object(object_name)
            return result.status == 204
        except Exception:
            return False

    def get_signed_url(self, object_name: str, expires: int = 3600) -> str:
        return self.bucket.sign_url('GET', object_name, expires)


oss_storage = OSSStorage()
