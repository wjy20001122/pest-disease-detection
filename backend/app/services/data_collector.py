from __future__ import annotations

import json
from datetime import datetime

from app.services.oss_service import OSSService


class DataCollector:
    def __init__(self, storage: OSSService, session_id: str, session_type: str = "video") -> None:
        self.storage = storage
        self.session_id = session_id
        self.session_type = session_type
        self.collected_tracks: set[int] = set()
        self.oss_image_urls: list[str] = []
        self.categories: dict[str, int] = {}
        self.total_annotations = 0
        self.username = ""
        self.start_time = datetime.now().isoformat()
        self.folder_name = f"{session_type}_{session_id[:8]}"

    def collect_detection(
        self,
        frame,
        track_id: int,
        class_name: str,
        bbox,
        confidence: float,
    ) -> bool:
        del bbox, confidence
        if track_id in self.collected_tracks:
            return False

        self.collected_tracks.add(track_id)

        image_id = len(self.oss_image_urls) + 1
        image_filename = f"img_{image_id:04d}_{track_id}_{class_name}.jpg"
        object_name = f"data-collection/{self.folder_name}/{image_filename}"
        oss_url = self.storage.upload_frame(frame, object_name)

        if not oss_url:
            self.collected_tracks.discard(track_id)
            return False

        self.oss_image_urls.append(oss_url)
        self.total_annotations += 1
        self.categories[class_name] = self.categories.get(class_name, 0) + 1
        return True

    def save_summary(self, username: str = "") -> dict | None:
        self.username = username
        if not self.oss_image_urls:
            return None

        return {
            "sessionId": self.session_id,
            "sessionType": self.session_type,
            "username": self.username,
            "startTime": self.start_time,
            "totalImages": len(self.oss_image_urls),
            "totalAnnotations": self.total_annotations,
            "totalCategories": len(self.categories),
            "categories": json.dumps(self.categories, ensure_ascii=False),
            "ossImageUrls": self.oss_image_urls,
            "ossFolder": f"data-collection/{self.folder_name}",
        }

