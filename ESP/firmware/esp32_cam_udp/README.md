# ESP32-CAM UDP Firmware

This sketch targets the common AI Thinker ESP32-CAM board and sends JPEG frames to the local `ESP/server` service over UDP.

Before flashing, edit `esp32_cam_udp.ino`:

- `WIFI_SSID`
- `WIFI_PASSWORD`
- `HOST_IP` to the local mini-host IP
- `HOST_PORT`, default `9000`

Arduino IDE settings:

- Board: `AI Thinker ESP32-CAM`
- PSRAM: enabled
- Partition scheme: huge app if available

Protocol:

- UDP packet header is 16 bytes, network byte order.
- Header fields: magic `ECAM`, `frame_id`, `total_size`, `packet_index`, `packet_count`, `payload_size`.
- Payload is a slice of one JPEG frame.

Runtime defaults:

- Host UDP port: `9000`
- Frame size: `FRAMESIZE_QVGA`
- Approximate frame rate: 8 FPS
- Packet payload size: 1200 bytes

After flashing, start the mini-host service:

```bash
cd ESP
conda activate pest_detect
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8010
curl -X POST http://127.0.0.1:8010/camera/start -H "Content-Type: application/json" -d '{}'
```

Full deployment notes are in `ESP/DEPLOY.md`.
