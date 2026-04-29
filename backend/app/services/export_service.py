import csv
import json
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session


class ExportService:
    """数据导出服务"""

    def export_to_json(self, records: List[Dict[str, Any]]) -> str:
        """导出为JSON格式"""
        export_data = {
            "export_time": datetime.now().isoformat(),
            "total_records": len(records),
            "records": records
        }
        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def export_to_csv(self, records: List[Dict[str, Any]]) -> str:
        """导出为CSV格式"""
        if not records:
            return ""

        output = io.StringIO()

        flattened_records = []
        for record in records:
            flattened = self._flatten_record(record)
            flattened_records.append(flattened)

        if flattened_records:
            fieldnames = list(flattened_records[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_records)

        return output.getvalue()

    def _flatten_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """将嵌套记录展平为单层字典"""
        flattened = {}

        for key, value in record.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flattened[f"{key}_{sub_key}"] = sub_value
            elif isinstance(value, list):
                flattened[key] = "; ".join(str(v) for v in value) if value else ""
            else:
                flattened[key] = value

        return flattened

    async def export_detection_records(
        self,
        db: Session,
        username: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        detection_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """导出用户的检测记录"""
        from app.db.models import ImgRecord, VideoRecord, CameraRecord

        records = []

        if detection_type is None or detection_type == "image":
            query = select(ImgRecord).where(ImgRecord.username == username)
            if start_date:
                query = query.where(ImgRecord.startTime >= start_date)
            if end_date:
                query = query.where(ImgRecord.startTime <= end_date)

            result = db.execute(query)
            for item in result.scalars().all():
                records.append({
                    "id": item.id,
                    "type": "image",
                    "crop_type": item.cropType,
                    "model_key": item.modelKey,
                    "labels": json.loads(item.label) if item.label and item.label != "[]" else [],
                    "confidences": json.loads(item.confidence) if item.confidence and item.confidence != "[]" else [],
                    "input_image": item.inputImg,
                    "output_image": item.outImg,
                    "created_at": item.startTime
                })

        if detection_type is None or detection_type == "video":
            query = select(VideoRecord).where(VideoRecord.username == username)
            if start_date:
                query = query.where(VideoRecord.startTime >= start_date)
            if end_date:
                query = query.where(VideoRecord.startTime <= end_date)

            result = db.execute(query)
            for item in result.scalars().all():
                records.append({
                    "id": item.id,
                    "type": "video",
                    "model_key": item.modelKey,
                    "input_video": item.inputVideo,
                    "output_video": item.outVideo,
                    "track_stats": json.loads(item.trackStats) if item.trackStats and item.trackStats != "{}" else {},
                    "created_at": item.startTime
                })

        if detection_type is None or detection_type == "camera":
            query = select(CameraRecord).where(CameraRecord.username == username)
            if start_date:
                query = query.where(CameraRecord.startTime >= start_date)
            if end_date:
                query = query.where(CameraRecord.startTime <= end_date)

            result = db.execute(query)
            for item in result.scalars().all():
                records.append({
                    "id": item.id,
                    "type": "camera",
                    "model_key": item.modelKey,
                    "input_video": item.inputVideo,
                    "output_video": item.outVideo,
                    "track_stats": json.loads(item.trackStats) if item.trackStats and item.trackStats != "{}" else {},
                    "created_at": item.startTime
                })

        records.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {
            "records": records,
            "total": len(records),
            "filters": {
                "username": username,
                "start_date": start_date,
                "end_date": end_date,
                "detection_type": detection_type
            }
        }


export_service = ExportService()
