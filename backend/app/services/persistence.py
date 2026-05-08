from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from app.db.models import (
    IMG_RECORD_FIELDS,
    VIDEO_RECORD_FIELDS,
    DataCollectionRecord,
    ImgRecord,
    VideoRecord,
)
from app.db.session import SessionLocal
from app.utils.common import (
    JSONDict,
    apply_data_collection_payload,
    apply_generic_payload,
    model_to_dict,
)


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_img_record(payload: JSONDict) -> JSONDict:
    with session_scope() as db:
        record = ImgRecord()
        apply_generic_payload(record, payload, IMG_RECORD_FIELDS)
        db.add(record)
        db.flush()
        db.refresh(record)
        return model_to_dict(record)


def create_video_record(payload: JSONDict) -> JSONDict:
    with session_scope() as db:
        record = VideoRecord()
        apply_generic_payload(record, payload, VIDEO_RECORD_FIELDS)
        db.add(record)
        db.flush()
        db.refresh(record)
        return model_to_dict(record)


def create_data_collection_record(payload: JSONDict) -> JSONDict:
    with session_scope() as db:
        record = DataCollectionRecord()
        apply_data_collection_payload(record, payload)
        db.add(record)
        db.flush()
        db.refresh(record)
        return model_to_dict(record)
