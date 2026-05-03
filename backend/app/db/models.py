from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text

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


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"
    __table_args__ = (
        Index("idx_email_code_email_purpose", "email", "purpose"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    purpose = Column(String(32), nullable=False)
    code_hash = Column(String(128), nullable=False)
    is_used = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)


class ImgRecord(Base):
    __tablename__ = "imgrecords"
    __table_args__ = (
        Index("idx_imgrecords_username_start_time", "username", "start_time"),
    )

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
    __table_args__ = (
        Index("idx_videorecords_username_start_time", "username", "start_time"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    modelKey = Column("model_key", String(255))
    inputVideo = Column("input_video", String(500))
    outVideo = Column("out_video", String(500))
    username = Column(String(100))
    startTime = Column("start_time", String(50))
    trackStats = Column("track_stats", Text)


class CameraRecord(Base):
    __tablename__ = "camerarecords"
    __table_args__ = (
        Index("idx_camerarecords_username_start_time", "username", "start_time"),
    )

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


class TrackingTask(Base):
    __tablename__ = "tracking_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    detection_id = Column(Integer, nullable=True, index=True)
    disease_name = Column(String(100), nullable=False)
    severity = Column(String(20), default="medium", index=True)
    status = Column(String(20), default="active", index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class TrackingUpdate(Base):
    __tablename__ = "tracking_updates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), nullable=True)
    note = Column(Text, nullable=True)
    image = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)


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


class ModelPolicy(Base):
    __tablename__ = "model_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_key = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(120), nullable=True)
    enabled = Column(Integer, default=1, nullable=False)
    is_default = Column(Integer, default=0, nullable=False)
    fallback_to_cloud = Column(Integer, default=1, nullable=False)
    fallback_notice = Column(
        Text,
        default="本地模型未识别到有效结果，已回退云端分析，结论未必完全可信。",
        nullable=True,
    )
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    status = Column(String(50), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    risk_assessment = Column(Text, nullable=True)
    detection_snapshot = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)


class VideoTask(Base):
    __tablename__ = "video_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    model_key = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, index=True, default="queued")
    progress = Column(Float, nullable=False, default=0.0)
    frame_count = Column(Integer, nullable=False, default=0)
    total_counts_json = Column(Text, nullable=True)
    total_tracks = Column(Integer, nullable=False, default=0)
    detections_json = Column(Text, nullable=True)
    output_url = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    stop_requested = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=False)


class PermissionAuditLog(Base):
    __tablename__ = "permission_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    path = Column(String(500), nullable=False)
    method = Column(String(20), nullable=False)
    status_code = Column(Integer, nullable=False, index=True)
    client_ip = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, index=True)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    disease_name = Column(String(120), nullable=False, index=True)
    crop_type = Column(String(50), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    shape = Column(String(255), nullable=True)
    color = Column(String(255), nullable=True)
    size = Column(String(255), nullable=True)
    symptoms = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)
    prevention = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)
    source_type = Column(String(50), nullable=True)
    source_name = Column(String(255), nullable=True)
    source_url = Column(String(500), nullable=True)
    book_title = Column(String(255), nullable=True)
    publisher = Column(String(255), nullable=True)
    publish_year = Column(String(20), nullable=True)
    chapter_ref = Column(String(255), nullable=True)
    updated_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)


class QnAConversation(Base):
    __tablename__ = "qna_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    crop_type = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, index=True)


class QnAMessage(Base):
    __tablename__ = "qna_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)


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
    "is_active",
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
VIDEO_TASK_FIELDS = {
    "id",
    "session_id",
    "username",
    "model_key",
    "status",
    "progress",
    "frame_count",
    "total_counts_json",
    "total_tracks",
    "detections_json",
    "output_url",
    "error_message",
    "stop_requested",
    "created_at",
    "updated_at",
}
SYSTEM_CONFIG_FIELDS = {
    "id",
    "key",
    "value",
    "updated_by",
    "updated_at",
}
PERMISSION_AUDIT_LOG_FIELDS = {
    "id",
    "user_id",
    "path",
    "method",
    "status_code",
    "client_ip",
    "reason",
    "created_at",
}
KNOWLEDGE_ITEM_FIELDS = {
    "id",
    "title",
    "disease_name",
    "crop_type",
    "category",
    "shape",
    "color",
    "size",
    "symptoms",
    "conditions",
    "prevention",
    "tags_json",
    "source_name",
    "source_url",
    "updated_at",
    "created_at",
}
