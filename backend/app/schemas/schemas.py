from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


# ============ 基础响应 ============
class BaseResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"


class ErrorResponse(BaseModel):
    success: bool = False
    error: dict


class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============ 用户认证 ============
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserProfile(BaseModel):
    id: UUID
    username: str
    email: str
    role: str
    phone: Optional[str] = None
    language: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UpdateProfile(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    language: Optional[str] = None


# ============ 检测模块 ============
class LocationData(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DiseaseResult(BaseModel):
    name: str
    confidence: float
    severity: str
    bounding_box: Optional[List[float]] = None
    symptoms: Optional[str] = None
    possible_causes: Optional[str] = None
    prevention: Optional[str] = None


class EnvironmentData(BaseModel):
    address: Optional[str] = None
    weather: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None


class DetectionResponse(BaseModel):
    id: UUID
    source: str
    crop_type: Optional[str] = None
    diseases: List[DiseaseResult]
    environment: Optional[EnvironmentData] = None
    created_at: datetime


class VideoTimeline(BaseModel):
    timestamp: float
    diseases: List[DiseaseResult]
    track_ids: Optional[List[str]] = None


class VideoDetectionResponse(BaseModel):
    id: UUID
    source: str
    total_frames: int
    detected_frames: int
    timeline: List[VideoTimeline]
    summary: dict
    environment: Optional[EnvironmentData] = None
    created_at: datetime


class DetectionHistoryItem(BaseModel):
    id: UUID
    detection_type: str
    source: str
    crop_type: Optional[str] = None
    disease_name: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[str] = None
    thumbnail_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 跟踪模块 ============
class TrackingCreate(BaseModel):
    detection_id: Optional[UUID] = None
    disease_name: str
    location: Optional[LocationData] = None
    severity: str = "medium"


class TrackingUpdateData(BaseModel):
    severity: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None  # base64


class TrackingResponse(BaseModel):
    id: UUID
    disease_name: str
    severity: str
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 知识库 ============
class KnowledgeItem(BaseModel):
    id: UUID
    disease_name: str
    crop_type: str
    symptoms: Optional[str] = None
    image_urls: Optional[List[str]] = None

    class Config:
        from_attributes = True


class KnowledgeDetail(BaseModel):
    id: UUID
    disease_name: str
    crop_type: str
    symptoms: Optional[str] = None
    conditions: Optional[str] = None
    prevention: Optional[str] = None
    cases: Optional[str] = None
    image_urls: Optional[List[str]] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 问答 ============
class QuestionRequest(BaseModel):
    question: str
    conversation_id: Optional[UUID] = None


class SourceInfo(BaseModel):
    type: str
    id: Optional[UUID] = None
    title: Optional[str] = None
    confidence: Optional[float] = None


class QnAResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    is_in_scope: bool
    disclaimer: str
    conversation_id: UUID


class ConversationItem(BaseModel):
    id: UUID
    messages: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 通知 ============
class NotificationItem(BaseModel):
    id: UUID
    type: str
    title: str
    content: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 管理后台 ============
class DashboardStats(BaseModel):
    total_users: int
    total_detections: int
    active_users_today: int
    warning_count: int
    system_status: dict


class ModelItem(BaseModel):
    id: UUID
    model_name: str
    model_version: str
    supported_pests: List[str]
    supported_crops: List[str]
    is_active: bool
    is_default: bool
    metrics: Optional[dict] = None
    deployed_at: datetime

    class Config:
        from_attributes = True


class ModelCreate(BaseModel):
    model_name: str
    model_version: str
    supported_pests: List[str]
    supported_crops: List[str]
    confidence_threshold: float = 0.5


class KnowledgeCreate(BaseModel):
    disease_name: str
    crop_type: str
    symptoms: Optional[str] = None
    conditions: Optional[str] = None
    prevention: Optional[str] = None
    cases: Optional[str] = None
    image_urls: Optional[List[str]] = None


class StatsFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    crop_type: Optional[str] = None
    region: Optional[str] = None
