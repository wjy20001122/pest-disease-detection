from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


FASTAPI_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = FASTAPI_ROOT.parent

load_dotenv(REPO_ROOT / ".env")
load_dotenv(FASTAPI_ROOT / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("FASTAPI_APP_NAME", "Corn Disease Detection FastAPI")
    host: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port: int = int(os.getenv("FASTAPI_PORT", "9999"))
    db_host: str = os.getenv("DB_HOST", "139.129.37.65")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_name: str = os.getenv("DB_NAME", "cropdisease")
    db_username: str = os.getenv("DB_USERNAME", "cropdisease")
    db_password: str = os.getenv("DB_PASSWORD", "cropdisease")
    oss_endpoint: str = os.getenv("OSS_ENDPOINT", "oss-cn-qingdao.aliyuncs.com").strip()
    oss_access_key_id: str = os.getenv("OSS_ACCESS_KEY_ID", "").strip()
    oss_access_key_secret: str = os.getenv("OSS_ACCESS_KEY_SECRET", "").strip()
    oss_bucket_name: str = os.getenv("OSS_BUCKET_NAME", "corpdisease").strip()
    oss_domain: str = os.getenv("OSS_DOMAIN", "").strip()
    request_timeout: int = int(os.getenv("FASTAPI_REQUEST_TIMEOUT", "60"))
    ffmpeg_binary: str = os.getenv("FFMPEG_BINARY", "ffmpeg")
    socketio_heartbeat_interval: int = int(os.getenv("SOCKETIO_HEARTBEAT_INTERVAL", "10"))

    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

    weather_api_key: str = os.getenv("WEATHER_API_KEY", "").strip()
    weather_api_base_url: str = os.getenv("WEATHER_API_BASE_URL", "https://devapi.qweather.com").strip()
    map_api_key: str = os.getenv("MAP_API_KEY", "").strip()
    map_api_base_url: str = os.getenv("MAP_API_BASE_URL", "https://restapi.amap.com").strip()

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


settings = Settings()
