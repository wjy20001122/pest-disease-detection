from __future__ import annotations

import sys

import requests
from PySide6.QtCore import QThread, QTimer, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class MjpegWorker(QThread):
    frame_received = Signal(bytes)
    error = Signal(str)

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        url = f"{self.base_url}/camera/frame.mjpg"
        buffer = b""
        try:
            with requests.get(url, stream=True, timeout=10) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=4096):
                    if not self._running:
                        break
                    if not chunk:
                        continue
                    buffer += chunk
                    while True:
                        start = buffer.find(b"\xff\xd8")
                        end = buffer.find(b"\xff\xd9")
                        if start == -1 or end == -1 or end <= start:
                            if len(buffer) > 2_000_000:
                                buffer = b""
                            break
                        jpeg = buffer[start : end + 2]
                        buffer = buffer[end + 2 :]
                        self.frame_received.emit(jpeg)
        except Exception as exc:
            if self._running:
                self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ESP32-CAM 本地实时检测")
        self.resize(1180, 760)
        self.worker: MjpegWorker | None = None

        self.base_url_input = QLineEdit("http://127.0.0.1:8010")
        self.esp32_ip_input = QLineEdit("10.107.67.6")
        self.esp32_cmd_port_input = QLineEdit("81")
        self.udp_port_input = QLineEdit("9000")
        self.status_label = QLabel("未连接")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.video_label = QLabel("等待视频流")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(820, 560)
        self.video_label.setStyleSheet("background:#111;color:#ddd;border:1px solid #333;")

        self.start_button = QPushButton("启动接收")
        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        self.result_text = QPlainTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumWidth(300)

        self.start_button.clicked.connect(self.start_camera)
        self.stop_button.clicked.connect(self.stop_camera)

        top = QGridLayout()
        top.addWidget(QLabel("FastAPI 服务"), 0, 0)
        top.addWidget(self.base_url_input, 0, 1)
        top.addWidget(QLabel("ESP32 IP"), 1, 0)
        top.addWidget(self.esp32_ip_input, 1, 1)
        top.addWidget(QLabel("命令端口"), 1, 2)
        top.addWidget(self.esp32_cmd_port_input, 1, 3)
        top.addWidget(QLabel("接收端口"), 2, 0)
        top.addWidget(self.udp_port_input, 2, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        top.addLayout(buttons, 2, 2)
        top.addWidget(self.status_label, 2, 3)
        top.setColumnStretch(1, 1)

        main_area = QHBoxLayout()
        main_area.addWidget(self.video_label, stretch=1)
        main_area.addWidget(self.result_text)

        root = QVBoxLayout()
        root.addLayout(top)
        root.addLayout(main_area, stretch=1)
        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh_status)

    def base_url(self) -> str:
        return self.base_url_input.text().strip().rstrip("/")

    def command_payload(self) -> dict:
        payload = {
            "esp32_ip": self.esp32_ip_input.text().strip(),
            "esp32_cmd_port": int(self.esp32_cmd_port_input.text().strip() or "81"),
            "udp_port": int(self.udp_port_input.text().strip() or "9000"),
        }
        return payload

    def start_camera(self) -> None:
        base_url = self.base_url()
        try:
            response = requests.post(f"{base_url}/camera/start", json=self.command_payload(), timeout=5)
            response.raise_for_status()
        except Exception as exc:
            QMessageBox.warning(self, "启动失败", str(exc))
            return

        self.worker = MjpegWorker(base_url)
        self.worker.frame_received.connect(self.show_frame)
        self.worker.error.connect(self.on_stream_error)
        self.worker.start()
        self.timer.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("运行中")

    def stop_camera(self) -> None:
        base_url = self.base_url()
        self.timer.stop()
        if self.worker:
            self.worker.stop()
            self.worker.wait(1500)
            self.worker = None
        try:
            requests.post(f"{base_url}/camera/stop", json=self.command_payload(), timeout=3)
        except Exception:
            pass
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("已停止")

    def show_frame(self, jpeg: bytes) -> None:
        image = QImage.fromData(jpeg, "JPG")
        if image.isNull():
            return
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(
            pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def refresh_status(self) -> None:
        try:
            response = requests.get(f"{self.base_url()}/camera/status", timeout=2)
            response.raise_for_status()
            status = response.json()
        except Exception as exc:
            self.status_label.setText(f"状态异常: {exc}")
            return

        latest = status.get("latest", {})
        detections = latest.get("detections", [])
        lines = [
            f"运行状态: {'运行中' if status.get('running') else '已停止'}",
            f"UDP: {status.get('udp_host')}:{status.get('udp_port')}",
            f"来源: {status.get('last_sender') or '-'}",
            f"FPS: {status.get('fps', 0)}",
            f"帧数: {status.get('received_frames', 0)}",
            f"丢帧: {status.get('dropped_frames', 0)}",
            f"解码错误: {status.get('decode_errors', 0)}",
            f"推理耗时: {latest.get('inference_ms', 0)} ms",
            f"最近帧: {latest.get('frame_id')}",
            "",
            "检测结果:",
        ]
        if detections:
            for det in detections:
                bbox = det.get("bbox", [])
                lines.append(
                    f"- {det.get('label')} / {det.get('english_label')} "
                    f"{det.get('confidence', 0):.2f} bbox={bbox}"
                )
        else:
            lines.append("- 无")
        if status.get("error"):
            lines.extend(["", f"错误: {status['error']}"])
        self.result_text.setPlainText("\n".join(lines))
        self.status_label.setText(f"FPS {status.get('fps', 0)}")

    def on_stream_error(self, message: str) -> None:
        self.status_label.setText(f"视频流异常: {message}")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.stop_camera()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
