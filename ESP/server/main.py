from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .camera_service import camera_service
from .config import settings


class StartRequest(BaseModel):
    udp_host: str | None = Field(None, description="UDP bind host, defaults to ESP_UDP_HOST")
    udp_port: int | None = Field(None, ge=1, le=65535, description="UDP bind port")
    esp32_ip: str | None = Field(None, description="Optional ESP32-CAM IP. When set, backend sends start:<udp_port> to it.")
    esp32_cmd_port: int | None = Field(None, ge=1, le=65535, description="ESP32 command UDP port, defaults to 81")


app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "model_path": str(settings.model_path),
        "model_loaded": settings.model_path.exists(),
    }


@app.post("/camera/start")
def start_camera(payload: StartRequest | None = None):
    payload = payload or StartRequest()
    result = camera_service.start(payload.udp_host, payload.udp_port)
    esp32_ip = payload.esp32_ip or settings.esp32_ip
    if esp32_ip:
        camera_service.send_esp32_command(
            esp32_ip,
            f"start:{result['udp_port']}",
            payload.esp32_cmd_port or settings.esp32_cmd_port,
        )
        result["esp32_command"] = f"start:{result['udp_port']}"
        result["esp32_ip"] = esp32_ip
    return result


@app.post("/camera/stop")
def stop_camera(payload: StartRequest | None = None):
    payload = payload or StartRequest()
    esp32_ip = payload.esp32_ip or settings.esp32_ip
    if esp32_ip:
        camera_service.send_esp32_command(
            esp32_ip,
            "stop",
            payload.esp32_cmd_port or settings.esp32_cmd_port,
        )
    result = camera_service.stop()
    if esp32_ip:
        result["esp32_command"] = "stop"
        result["esp32_ip"] = esp32_ip
    return result


@app.get("/camera/status")
def camera_status():
    return camera_service.status()


@app.get("/camera/latest")
def camera_latest():
    return camera_service.latest()


@app.get("/camera/frame.mjpg")
def camera_frame():
    return StreamingResponse(
        camera_service.mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
