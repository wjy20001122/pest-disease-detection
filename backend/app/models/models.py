import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from .database import Base
import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class DetectionType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    CAMERA = "camera"


class DetectionSource(str, enum.Enum):
    LOCAL_MODEL = "local_model"
    CLOUD_AI = "cloud_ai"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrackingStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    FALSE_POSITIVE = "false_positive"


class NotificationType(str, enum.Enum):
    WARNING = "warning"
    SYSTEM = "system"
    AGENT_PUSH = "agent_push"
    REGIONAL_ALERT = "regional_alert"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    phone = Column(String(20), nullable=True)
    language = Column(String(5), default="zh")
    is_active = Column(Boolean, default=True)
    login_fail_count = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    detections = relationship("Detection", back_populates="user")
    tracking_tasks = relationship("TrackingTask", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    detection_type = Column(Enum(DetectionType), nullable=False)
    source = Column(Enum(DetectionSource), nullable=False)

    file_path = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)

    crop_type = Column(String(50), nullable=True)
    disease_name = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    severity = Column(Enum(Severity), nullable=True)
    bounding_boxes = Column(JSON, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    prevention_advice = Column(Text, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(200), nullable=True)
    weather = Column(String(50), nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)

    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING)
    review_result = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="detections")
    tracking_tasks = relationship("TrackingTask", back_populates="detection")
    video_frames = relationship("VideoFrame", back_populates="detection")


class TrackingTask(Base):
    __tablename__ = "tracking_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    detection_id = Column(String(36), ForeignKey("detections.id"), nullable=True)

    disease_name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    severity = Column(Enum(Severity), default=Severity.MEDIUM)
    status = Column(Enum(TrackingStatus), default=TrackingStatus.ACTIVE, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_measure = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="tracking_tasks")
    detection = relationship("Detection", back_populates="tracking_tasks")
    updates = relationship("TrackingUpdate", back_populates="task")


class TrackingUpdate(Base):
    __tablename__ = "tracking_updates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tracking_tasks.id"), nullable=False)
    description = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True)
    severity = Column(Enum(Severity), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("TrackingTask", back_populates="updates")


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name = Column(String(100), nullable=False, unique=True)
    model_version = Column(String(20), nullable=False)
    model_path = Column(String(500), nullable=False)
    supported_pests = Column(JSON, nullable=False)
    supported_crops = Column(JSON, nullable=False)
    input_size = Column(String(20), default="640x640")
    confidence_threshold = Column(Float, default=0.5)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    metrics = Column(JSON, nullable=True)
    deployed_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    related_detection_id = Column(String(36), ForeignKey("detections.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="notifications")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    disease_name = Column(String(100), nullable=False, index=True)
    crop_type = Column(String(50), nullable=False, index=True)
    symptoms = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)
    prevention = Column(Text, nullable=True)
    cases = Column(Text, nullable=True)
    image_urls = Column(JSON, nullable=True)
    language = Column(String(5), default="zh")
    embedding_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VideoFrame(Base):
    __tablename__ = "video_frames"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    detection_id = Column(String(36), ForeignKey("detections.id"), nullable=False)
    frame_index = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)
    detections = Column(JSON, nullable=True)
    track_ids = Column(JSON, nullable=True)
    annotated_frame_path = Column(String(500), nullable=True)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    rate_limit = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    resource = Column(String(100), nullable=True)
    detail = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    messages = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
