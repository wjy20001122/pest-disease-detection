# ESP Windows EXE 打包说明

本项目可以打包成 Windows 一体化目录：

- `ESP-Edge.exe` 启动后会在后台启动 FastAPI/UDP 服务。
- 同一个 exe 会打开 PySide6 Qt 实时界面。
- 模型文件会复制到 `dist/ESP-Edge/models/`。
- ESP32-CAM 仍通过 UDP `81` 接收 `start:9000` 命令，并向 Windows UDP `9000` 回传图像。
- 构建脚本使用项目内 `esp` 虚拟环境目录。

## 1. 准备 Python

在 PowerShell 中安装 Python 3.11：

```powershell
winget install -e --id Python.Python.3.11
```

关闭并重新打开 PowerShell，检查：

```powershell
py -3.11 --version
```

## 2. 一键构建

```powershell
cd D:\Will\Program\pest-disease-detection\ESP
.\scripts\build_windows.ps1
```

如果 PowerShell 阻止脚本：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\build_windows.ps1
```

构建成功后产物在：

```text
ESP\dist\ESP-Edge\ESP-Edge.exe
```

整个 `dist\ESP-Edge\` 目录都要保留，不能只复制单个 exe，因为模型和依赖库在同一目录内。

## 3. 运行

双击：

```text
dist\ESP-Edge\ESP-Edge.exe
```

或在 PowerShell 中运行：

```powershell
cd D:\Will\Program\pest-disease-detection\ESP
.\dist\ESP-Edge\ESP-Edge.exe
```

Windows 防火墙弹窗时，允许专用网络访问。

Qt 默认值：

- FastAPI 服务：`http://127.0.0.1:8010`
- ESP32 IP：`10.107.67.6`
- ESP32 命令端口：`81`
- Windows UDP 接收端口：`9000`

点击“启动接收”后，ESP32 串口应出现：

```text
[INFO] Command received: start:9000
[OK] Streaming to ...
[INFO] frame=0 bytes=...
```

## 4. 不打包直接运行

```powershell
cd D:\Will\Program\pest-disease-detection\ESP
.\scripts\run_windows.ps1
```

## 5. 常见问题

如果 Qt 打开但没有画面：

```powershell
curl.exe http://127.0.0.1:8010/camera/status
```

如果 `received_packets` 是 `0`：

- 确认 ESP32 串口是否收到 `start:9000`
- 确认 Windows 防火墙允许 `ESP-Edge.exe`
- 确认 ESP32 和 Windows 在同一 WiFi
- 确认 ESP32 固件中的固定 IP、网关和当前网络一致
