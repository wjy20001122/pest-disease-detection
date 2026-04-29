from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.session import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(255))
    sex = Column(String(10))
    email = Column(String(255))
    tel = Column(String(50))
    role = Column(String(50))
    avatar = Column(String(500))
    is_active = Column(Integer, default=1)
    time = Column(DateTime)


class ImgRecord(Base):
    __tablename__ = "imgrecords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    modelKey = Column("model_key", String(255))
    cropType = Column("crop_type", String(50))
    inputImg = Column("input_img", String(500))
    outImg = Column("out_img", String(500))
    confidence = Column(Text)
    allTime = Column("all_time", String(50))
    conf = Column(String(50))
    label = Column(Text)
    username = Column(String(100))
    startTime = Column("start_time", String(50))


class VideoRecord(Base):
    __tablename__ = "videorecords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    modelKey = Column("model_key", String(255))
    inputVideo = Column("input_video", String(500))
    outVideo = Column("out_video", String(500))
    username = Column(String(100))
    startTime = Column("start_time", String(50))
    trackStats = Column("track_stats", Text)


class CameraRecord(Base):
    __tablename__ = "camerarecords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    modelKey = Column("model_key", String(255))
    inputVideo = Column("input_video", String(500))
    outVideo = Column("out_video", String(500))
    username = Column(String(100))
    startTime = Column("start_time", String(50))
    trackStats = Column("track_stats", Text)


class DataCollectionRecord(Base):
    __tablename__ = "datacollectionrecords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sessionId = Column("session_id", String(100))
    sessionType = Column("session_type", String(50))
    username = Column(String(100))
    startTime = Column("start_time", String(50))
    totalImages = Column("total_images", Integer)
    totalAnnotations = Column("total_annotations", Integer)
    totalCategories = Column("total_categories", Integer)
    categories = Column(Text)
    ossFolder = Column("oss_folder", String(255))
    ossImageUrls = Column("oss_image_urls", Text)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Integer, default=0, index=True)
    related_detection_id = Column(Integer, nullable=True)
    created_at = Column(DateTime)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    key_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    rate_limit = Column(Integer, default=60)
    is_active = Column(Integer, default=1)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime)


USER_FIELDS = {
    "id",
    "username",
    "password",
    "name",
    "sex",
    "email",
    "tel",
    "role",
    "avatar",
    "time",
}
IMG_RECORD_FIELDS = {
    "id",
    "username",
    "modelKey",
    "cropType",
    "label",
    "conf",
    "confidence",
    "allTime",
    "startTime",
    "inputImg",
    "outImg",
}
VIDEO_RECORD_FIELDS = {
    "id",
    "username",
    "modelKey",
    "startTime",
    "inputVideo",
    "outVideo",
    "trackStats",
}
CAMERA_RECORD_FIELDS = VIDEO_RECORD_FIELDS
DATA_COLLECTION_FIELDS = {
    "id",
    "sessionId",
    "sessionType",
    "username",
    "startTime",
    "totalImages",
    "totalAnnotations",
    "totalCategories",
    "categories",
    "ossFolder",
    "ossImageUrls",
}

