from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
from PySide6.QtWidgets import QApplication, QMessageBox

from qt_client.main import MainWindow
from server.main import app


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def configure_packaged_paths() -> None:
    root = app_root()
    model_path = root / "models" / "yolo12.onnx"
    os.environ.setdefault("ESP_MODEL_PATH", str(model_path))


def wait_for_port(host: str, port: int, timeout_sec: float = 15.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def start_server_thread() -> threading.Thread:
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8010,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread


def main() -> int:
    configure_packaged_paths()
    start_server_thread()

    qt_app = QApplication(sys.argv)
    if not wait_for_port("127.0.0.1", 8010):
        QMessageBox.critical(None, "启动失败", "FastAPI 服务未能在 8010 端口启动。")
        return 1

    window = MainWindow()
    window.base_url_input.setText("http://127.0.0.1:8010")
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
