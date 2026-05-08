# ESP32-CAM 本地实时检测部署文档

本文档用于把 `ESP/` 独立项目部署到嗨高乐小主机。数据只在局域网内流转：ESP32-CAM 通过 WiFi 等待小主机 UDP 命令，收到 `start:<port>` 后发送 JPEG 分包到小主机，小主机本地检测，Qt 界面实时显示。

## 1. 部署前准备

硬件：

- 嗨高乐小主机，建议 Ubuntu/WSL/Linux 环境。
- ESP32-CAM，推荐 AI Thinker ESP32-CAM。
- 小主机和 ESP32-CAM 连接同一个 WiFi。

软件：

- Windows 原生 Python 3.11 + `esp` 虚拟环境，推荐用于 ESP32-CAM UDP 实机联调
- Linux/小主机也可使用 Conda 环境：`pest_detect`
- Arduino IDE 或 Arduino CLI
- ESP32 Arduino Board 支持包

确认小主机 IP：

```bash
ip addr
```

找到 WiFi 网卡的局域网地址，例如 `10.107.67.5`。ESP32-CAM 固件里配置自己的固定 IP，例如 `10.107.67.6`，小主机启动接口里传这个 ESP32 IP。

## 2. Windows 原生 esp 环境部署（推荐实机联调）

ESP32-CAM 的 UDP 图像包要回到运行 FastAPI 的系统。Windows + WSL 场景下，ESP32 常把包发到 Windows 网卡，WSL 内服务收不到。因此实机联调建议在 Windows 原生 PowerShell 中启动 `ESP/server`。

安装 Python 3.11：

```powershell
winget install -e --id Python.Python.3.11
```

关闭并重新打开 PowerShell 后检查：

```powershell
py -3.11 --version
python --version
```

创建并激活名为 `esp` 的虚拟环境：

```powershell
cd D:\Will\Program\pest-disease-detection\ESP
py -3.11 -m venv esp
.\esp\Scripts\Activate.ps1
```

如果 PowerShell 阻止激活脚本，执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\esp\Scripts\Activate.ps1
```

安装依赖：

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

启动 FastAPI：

```powershell
python -m uvicorn server.main:app --host 0.0.0.0 --port 8010
```

Windows 防火墙弹窗时，允许专用网络访问。

另开一个 PowerShell，测试 ESP32 启动命令：

```powershell
curl.exe -X POST http://127.0.0.1:8010/camera/start `
  -H "Content-Type: application/json" `
  -d "{\"esp32_ip\":\"10.107.67.6\",\"esp32_cmd_port\":81,\"udp_port\":9000}"
```

查看状态：

```powershell
curl.exe http://127.0.0.1:8010/camera/status
```

如果 `received_packets` 增加，说明 Windows 原生 UDP 收包正常。

启动 Qt：

```powershell
cd D:\Will\Program\pest-disease-detection\ESP
.\esp\Scripts\Activate.ps1
python -m qt_client.main
```

## 3. Windows EXE 打包部署

如果希望交付一个完整可运行目录，可以在 Windows PowerShell 中构建 exe：

```powershell
cd D:\Will\Program\pest-disease-detection\ESP
.\scripts\build_windows.ps1
```

产物：

```text
D:\Will\Program\pest-disease-detection\ESP\dist\ESP-Edge\ESP-Edge.exe
```

运行 `ESP-Edge.exe` 后会自动启动后台 FastAPI/UDP 服务，并打开 Qt 界面。整个 `dist\ESP-Edge\` 目录需要一起复制，不能只复制单个 exe。详细说明见 `BUILD_WINDOWS.md`。

## 4. Linux/Conda 部署

进入项目：

```bash
cd /mnt/d/Will/Program/pest-disease-detection/ESP
conda activate pest_detect
pip install -r requirements.txt
```

确认模型已存在：

```bash
ls -lh models/
```

应看到：

- `yolo12.onnx`
- `deim2p3.onnx`

默认服务使用 `models/yolo12.onnx`。

## 5. 启动 FastAPI 检测服务

```bash
cd /mnt/d/Will/Program/pest-disease-detection/ESP
conda activate pest_detect
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8010
```

也可以使用脚本：

```bash
./scripts/start_server.sh
```

验证服务：

```bash
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/camera/status
```

启动 UDP 接收：

```bash
curl -X POST http://127.0.0.1:8010/camera/start \
  -H "Content-Type: application/json" \
  -d '{"esp32_ip":"10.107.67.6","esp32_cmd_port":81,"udp_port":9000}'
```

默认监听：

- UDP：`0.0.0.0:9000`
- HTTP：`0.0.0.0:8010`

## 6. 烧录 ESP32-CAM 固件

打开：

```text
ESP/firmware/esp32_cam_udp/esp32_cam_udp.ino
```

修改：

```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
IPAddress LOCAL_IP(10, 107, 67, 6);
IPAddress GATEWAY(10, 107, 67, 1);
IPAddress SUBNET(255, 255, 255, 0);
IPAddress DNS(8, 8, 8, 8);
const uint16_t COMMAND_PORT = 81;
```

Arduino IDE 设置：

- Board：`AI Thinker ESP32-CAM`
- PSRAM：`Enabled`
- Upload Speed：`115200` 或 `921600`
- Partition Scheme：如有 `Huge APP` 可选，优先选它

烧录后打开串口监视器，波特率 `115200`。正常输出应包含：

```text
[OK] WiFi connected
[INFO] ESP32-CAM IP: 10.107.67.6
[INFO] Waiting for backend start command...
[OK] UDP command listener started, port: 81
[INFO] Expected commands: start:<port> / stop
```

当小主机调用 `/camera/start` 后，串口应继续输出：

```text
[INFO] Command received: start:9000
[OK] Streaming to 10.107.67.x:9000
[INFO] frame=0 bytes=...
```

## 7. 启动 Qt 实时界面

另开一个终端：

```bash
cd /mnt/d/Will/Program/pest-disease-detection/ESP
conda activate pest_detect
python3 -m qt_client.main
```

也可以使用脚本：

```bash
./scripts/start_qt.sh
```

Qt 默认连接：

```text
http://127.0.0.1:8010
```

Qt 界面里的 ESP32 IP 默认是 `10.107.67.6`，命令端口默认 `81`，接收端口默认 `9000`。点击“启动接收”时会让后端先监听 UDP `9000`，再向 ESP32-CAM 的 UDP `81` 端口发送 `start:9000`。

点击“启动接收”后，界面应显示：

- 实时检测画面
- FPS
- UDP 来源地址
- 已接收帧数
- 检测类别与置信度

浏览器也可以直接打开调试画面：

```text
http://127.0.0.1:8010/camera/frame.mjpg
```

## 8. 开机自启动可选配置

如果小主机使用 systemd，可以创建服务：

```bash
sudo nano /etc/systemd/system/esp-edge.service
```

写入，按实际 Conda 路径调整 `ExecStart`：

```ini
[Unit]
Description=ESP32-CAM Local Edge Detection
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/mnt/d/Will/Program/pest-disease-detection/ESP
ExecStart=/bin/bash -lc 'source ~/miniconda3/etc/profile.d/conda.sh && conda activate pest_detect && python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8010'
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable esp-edge
sudo systemctl start esp-edge
sudo systemctl status esp-edge
```

Qt 界面通常建议登录桌面后手动启动；如果需要桌面自启动，再放到系统的 Startup Applications。

## 9. 故障排查

服务无法启动：

- 确认已 `conda activate pest_detect`
- 确认 `pip install -r requirements.txt` 成功
- 确认端口 `8010` 未被占用：

```bash
ss -lntp | grep 8010
```

收不到帧：

- 确认 FastAPI 已调用 `/camera/start`
- 确认 ESP32-CAM 固件里的 `HOST_IP` 是小主机 WiFi IP
- 确认小主机防火墙允许 UDP `9000`
- 查看状态：

```bash
curl http://127.0.0.1:8010/camera/status
```

如果 `received_packets` 一直为 `0`，通常是 IP、WiFi、端口或防火墙问题。
如果 ESP32 串口一直停在“Waiting for backend start command”，说明小主机没有成功向 ESP32 的 UDP `81` 端口发送 `start:<port>`。
如果在 WSL 中运行服务，ESP32 串口显示正在发送帧但 `received_packets` 仍为 `0`，请切换到 Windows 原生 `esp` 环境运行 FastAPI。

画面卡顿：

- 固件里降低帧率：增大 `FRAME_INTERVAL_MS`
- 固件里降低分辨率：保持 `FRAMESIZE_QVGA`，不要先提高到 VGA
- 固件里降低画质数据量：增大 `JPEG_QUALITY`，例如 `20`
- 服务端降低输出质量：设置 `ESP_OUTPUT_JPEG_QUALITY=70`

检测慢：

- 默认 CPU 推理，低功耗小主机可能只有几 FPS
- 可降低 ESP32 帧率，让推理跟得上
- 保持 QVGA 输入，先不要提高摄像头分辨率

Qt 没有画面：

- 先用浏览器打开 `http://127.0.0.1:8010/camera/frame.mjpg`
- 如果浏览器有画面，重启 Qt 客户端
- 如果浏览器也没有画面，优先检查 UDP 接收和 `/camera/status`

## 10. 停止服务

停止摄像头接收：

```bash
curl -X POST http://127.0.0.1:8010/camera/stop
```

如果要同时通知 ESP32-CAM 停止发送：

```bash
curl -X POST http://127.0.0.1:8010/camera/stop \
  -H "Content-Type: application/json" \
  -d '{"esp32_ip":"10.107.67.6","esp32_cmd_port":81}'
```

停止 FastAPI：

- 前台运行时按 `Ctrl+C`
- systemd 运行时：

```bash
sudo systemctl stop esp-edge
```

## 11. 数据边界

`ESP/` 独立项目不使用：

- OSS
- DeepSeek
- Celery
- 远程 MySQL
- 现有 Vue 前端

检测结果默认只在内存中保留，用于实时显示；重启服务后清空。
