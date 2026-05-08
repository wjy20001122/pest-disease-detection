# ESP 独立本地实时检测

`ESP/` 是独立于主 `backend/` 的本地边缘实时检测项目。ESP32-CAM 通过 WiFi 等待小主机 UDP 命令，收到 `start:<port>` 后发送 JPEG 分包到小主机，小主机本地重组、ONNX 推理，并通过 FastAPI 输出 MJPEG 给 PySide6 Qt 客户端显示。

## 目录

- `firmware/esp32_cam_udp/`：ESP32-CAM Arduino 固件
- `server/`：FastAPI UDP 接收和本地检测服务
- `qt_client/`：PySide6 实时显示界面
- `models/`：本地模型文件，已复制 `yolo12.onnx` 和 `deim2p3.onnx`
- `config/`：本地环境变量示例
- `scripts/`：启动脚本

## 运行

安装依赖：

```bash
conda activate pest_detect
cd ESP
pip install -r requirements.txt
```

启动服务：

```bash
conda activate pest_detect
cd ESP
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8010
```

另开终端启动 Qt：

```bash
conda activate pest_detect
cd ESP
python3 -m qt_client.main
```

Qt 默认 ESP32 IP 为 `10.107.67.6`、命令端口 `81`、小主机 UDP 接收端口 `9000`。点击“启动接收”会自动调用后端并向 ESP32-CAM 发送 `start:9000`。

服务接口：

- `GET /health`
- `POST /camera/start`
- `POST /camera/stop`
- `GET /camera/status`
- `GET /camera/latest`
- `GET /camera/frame.mjpg`

完整部署步骤见 `DEPLOY.md`。

## 固件配置

编辑 `firmware/esp32_cam_udp/esp32_cam_udp.ino`：

- `WIFI_SSID`
- `WIFI_PASSWORD`
- `LOCAL_IP/GATEWAY/SUBNET/DNS`：ESP32-CAM 固定 IP 配置
- `COMMAND_PORT`：默认 `81`，用于接收小主机 `start:<port>` / `stop` 命令

烧录后串口会输出 WiFi 地址，并等待后端发送 `start:<port>`。

启动 UDP 接收并通知 ESP32-CAM：

```bash
curl -X POST http://127.0.0.1:8010/camera/start \
  -H "Content-Type: application/json" \
  -d '{"esp32_ip":"10.107.67.6","esp32_cmd_port":81,"udp_port":9000}'
```

停止：

```bash
curl -X POST http://127.0.0.1:8010/camera/stop \
  -H "Content-Type: application/json" \
  -d '{"esp32_ip":"10.107.67.6","esp32_cmd_port":81}'
```

## UDP 协议

每个 UDP 包包含 16 字节帧头：

- magic: `ECAM`
- frame_id: `uint32`
- total_size: `uint32`
- packet_index: `uint8`
- packet_count: `uint8`
- payload_size: `uint16`

多包按 `frame_id` 重组成一帧 JPEG，超时未收齐的残帧会丢弃。

## 本地隐私

该独立项目不使用 OSS、DeepSeek、Celery、远程 MySQL，也不依赖现有 Vue 前端。检测结果默认只保存在内存中，用于实时显示。

## 验证

```bash
python3 -m compileall server qt_client
curl http://127.0.0.1:8010/health
curl -X POST http://127.0.0.1:8010/camera/start -H "Content-Type: application/json" -d '{}'
curl http://127.0.0.1:8010/camera/status
```
