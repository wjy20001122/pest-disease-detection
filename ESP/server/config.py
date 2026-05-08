from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ESP_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    app_name: str = "ESP Local Realtime Detection"
    udp_host: str = os.getenv("ESP_UDP_HOST", "0.0.0.0")
    udp_port: int = int(os.getenv("ESP_UDP_PORT", "9000"))
    esp32_ip: str = os.getenv("ESP32_IP", "").strip()
    esp32_cmd_port: int = int(os.getenv("ESP32_CMD_PORT", "81"))
    frame_timeout_sec: float = float(os.getenv("ESP_FRAME_TIMEOUT_SEC", "1.0"))
    stale_frame_sec: float = float(os.getenv("ESP_STALE_FRAME_SEC", "3.0"))
    max_frame_bytes: int = int(os.getenv("ESP_MAX_FRAME_BYTES", str(300 * 1024)))
    max_packet_payload: int = int(os.getenv("ESP_MAX_PACKET_PAYLOAD", "1200"))
    model_key: str = os.getenv("ESP_MODEL_KEY", "pest")
    model_path: Path = Path(os.getenv("ESP_MODEL_PATH", ESP_ROOT / "models" / "yolo12.onnx"))
    conf_threshold: float = float(os.getenv("ESP_CONF_THRESHOLD", "0.35"))
    iou_threshold: float = float(os.getenv("ESP_IOU_THRESHOLD", "0.5"))
    input_width: int = int(os.getenv("ESP_INPUT_WIDTH", "640"))
    input_height: int = int(os.getenv("ESP_INPUT_HEIGHT", "640"))
    target_fps: float = float(os.getenv("ESP_TARGET_FPS", "8"))
    jpeg_quality: int = int(os.getenv("ESP_OUTPUT_JPEG_QUALITY", "80"))


settings = Settings()


CLASSES = ["蚜虫", "玉米粘虫幼虫", "玉米螟幼虫", "玉米螟成虫"]
ENGLISH_LABELS = [
    "aphid",
    "Corn_fall_armyworm_larva",
    "Corn_yellow_stem_borer_larva",
    "Corn_yellow_stem_borer",
]
BOX_COLORS = [
    (0, 0, 255),
    (0, 180, 0),
    (255, 80, 0),
    (180, 0, 255),
]
