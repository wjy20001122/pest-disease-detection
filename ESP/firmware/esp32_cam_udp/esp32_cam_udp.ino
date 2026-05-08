#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>

// AI Thinker ESP32-CAM pins.
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
IPAddress LOCAL_IP(10, 107, 67, 6);
IPAddress GATEWAY(10, 107, 67, 1);
IPAddress SUBNET(255, 255, 255, 0);
IPAddress DNS(8, 8, 8, 8);
const uint16_t COMMAND_PORT = 81;

const uint16_t PACKET_PAYLOAD_SIZE = 1200;
const uint32_t FRAME_INTERVAL_MS = 125;  // ~8 FPS
const uint8_t JPEG_QUALITY = 18;         // Lower is better quality. 10-20 is a practical range.

WiFiUDP udp;
WiFiUDP command_udp;
IPAddress host_ip;
uint16_t host_port = 9000;
uint32_t frame_id = 0;
bool streaming = false;

struct __attribute__((packed)) PacketHeader {
  char magic[4];
  uint32_t frame_id;
  uint32_t total_size;
  uint8_t packet_index;
  uint8_t packet_count;
  uint16_t payload_size;
};

uint32_t htonl32(uint32_t value) {
  return ((value & 0x000000FFUL) << 24) |
         ((value & 0x0000FF00UL) << 8) |
         ((value & 0x00FF0000UL) >> 8) |
         ((value & 0xFF000000UL) >> 24);
}

uint16_t htons16(uint16_t value) {
  return ((value & 0x00FF) << 8) | ((value & 0xFF00) >> 8);
}

bool setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = JPEG_QUALITY;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }

  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor) {
    sensor->set_framesize(sensor, FRAMESIZE_QVGA);
    sensor->set_quality(sensor, JPEG_QUALITY);
  }
  return true;
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  if (!WiFi.config(LOCAL_IP, GATEWAY, SUBNET, DNS)) {
    Serial.println("[WARN] Failed to configure static IP");
  } else {
    Serial.print("[INFO] Static IP configured: ");
    Serial.println(LOCAL_IP);
  }
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[INFO] Connecting WiFi: ");
  Serial.println(WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("[OK] WiFi connected");
  Serial.print("[INFO] ESP32-CAM IP: ");
  Serial.println(WiFi.localIP());
}

void handleCommand() {
  int packet_size = command_udp.parsePacket();
  if (packet_size <= 0) {
    return;
  }

  char command[64];
  int len = command_udp.read(command, sizeof(command) - 1);
  if (len <= 0) {
    return;
  }
  command[len] = '\0';

  String value = String(command);
  value.trim();
  Serial.print("[INFO] Command received: ");
  Serial.println(value);

  if (value.startsWith("start")) {
    int colon = value.indexOf(':');
    if (colon >= 0) {
      int requested_port = value.substring(colon + 1).toInt();
      if (requested_port > 0 && requested_port <= 65535) {
        host_port = (uint16_t)requested_port;
      }
    }
    host_ip = command_udp.remoteIP();
    streaming = true;
    frame_id = 0;
    Serial.print("[OK] Streaming to ");
    Serial.print(host_ip);
    Serial.print(":");
    Serial.println(host_port);
    return;
  }

  if (value == "stop") {
    streaming = false;
    Serial.println("[OK] Streaming stopped");
    return;
  }

  Serial.println("[WARN] Unknown command. Expected start:<port> or stop");
}

void sendFrame(camera_fb_t* fb) {
  if (!fb || !fb->buf || fb->len == 0) {
    return;
  }

  uint8_t packet_count = (fb->len + PACKET_PAYLOAD_SIZE - 1) / PACKET_PAYLOAD_SIZE;
  if (packet_count == 0 || packet_count > 255) {
    Serial.printf("Frame too large for protocol: %u bytes\n", fb->len);
    return;
  }

  uint8_t packet[sizeof(PacketHeader) + PACKET_PAYLOAD_SIZE];
  for (uint8_t index = 0; index < packet_count; index++) {
    size_t offset = index * PACKET_PAYLOAD_SIZE;
    uint16_t payload_size = min((size_t)PACKET_PAYLOAD_SIZE, fb->len - offset);

    PacketHeader header;
    header.magic[0] = 'E';
    header.magic[1] = 'C';
    header.magic[2] = 'A';
    header.magic[3] = 'M';
    header.frame_id = htonl32(frame_id);
    header.total_size = htonl32(fb->len);
    header.packet_index = index;
    header.packet_count = packet_count;
    header.payload_size = htons16(payload_size);

    memcpy(packet, &header, sizeof(PacketHeader));
    memcpy(packet + sizeof(PacketHeader), fb->buf + offset, payload_size);

    udp.beginPacket(host_ip, host_port);
    udp.write(packet, sizeof(PacketHeader) + payload_size);
    udp.endPacket();
    delayMicroseconds(800);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  connectWiFi();
  if (!setupCamera()) {
    Serial.println("Camera setup failed. Restarting.");
    delay(3000);
    ESP.restart();
  }
  udp.begin(0);
  command_udp.begin(COMMAND_PORT);
  Serial.println("[INFO] Waiting for backend start command...");
  Serial.printf("[OK] UDP command listener started, port: %u\n", COMMAND_PORT);
  Serial.println("[INFO] Expected commands: start:<port> / stop");
}

void loop() {
  handleCommand();

  if (!streaming) {
    delay(20);
    return;
  }

  static uint32_t last_frame_at = 0;
  uint32_t now = millis();
  if (now - last_frame_at < FRAME_INTERVAL_MS) {
    delay(2);
    return;
  }
  last_frame_at = now;

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  sendFrame(fb);
  Serial.printf("[INFO] frame=%lu bytes=%u target=%s:%u\n", (unsigned long)frame_id, fb->len, host_ip.toString().c_str(), host_port);
  frame_id++;
  esp_camera_fb_return(fb);
}
