# 技术设计文档

## 1. 系统概述

病虫害检测系统（PDDS）采用前后端分离架构，核心检测流程为"云端AI优先分析 + 本地YOLO模型增强"的两级路由策略。系统面向通用农作物场景，覆盖粮食、蔬菜、水果、经济作物等类型。

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Vue 3 + Vite)                     │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐ │
│  │检测页│ │跟踪页│ │统计页│ │知识库│ │问答页│ │管理后台  │ │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └────┬─────┘ │
└─────┼────────┼────────┼────────┼────────┼──────────┼────────┘
      │        │        │        │        │          │
      ▼        ▼        ▼        ▼        ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway (Nginx)                        │
│              反向代理 + 静态资源 + SSL                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 后端服务 (FastAPI)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │认证模块  │ │检测路由  │ │检测服务  │ │跟踪服务      │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │环境数据  │ │知识库    │ │问答Agent │ │统计服务      │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │通知服务  │ │管理服务  │ │模型管理  │ │监控日志      │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└────┬──────────┬──────────┬──────────┬───────────────────────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌─────────┐ ┌───────┐ ┌───────┐ ┌──────────────────┐
│PostgreSQL│ │ Redis │ │ MinIO │ │  模型推理服务     │
│关系数据  │ │缓存/  │ │文件   │ │  (YOLO/TensorRT) │
│          │ │消息队列│ │存储   │ │  GPU加速推理      │
└─────────┘ └───────┘ └───────┘ └──────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ 向量数据库    │
                    │ (Milvus/     │
                    │  ChromaDB)   │
                    │ 知识库嵌入   │
                    └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │云端AI    │ │天气API   │ │地图API   │
       │(DeepSeek)│ │          │ │          │
       └──────────┘ └──────────┘ └──────────┘
```

### 2.2 技术栈选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + TypeScript | 组合式API，响应式设计 |
| UI组件库 | Element Plus | 桌面端组件，配合移动端适配 |
| 图表库 | ECharts | 可视化统计图表 |
| 地图 | Leaflet + OpenStreetMap | 开源地图，虫害跟踪标注 |
| 视频播放 | video.js | 视频检测结果回放 |
| 后端框架 | FastAPI | 高性能异步API框架 |
| 任务队列 | Celery + Redis | 异步检测任务、智能体审查 |
| WebSocket | FastAPI WebSocket | 摄像头实时检测、通知推送 |
| 关系数据库 | PostgreSQL | 用户、检测记录、知识库结构化数据 |
| ORM | SQLAlchemy 2.0 | 异步数据库操作 |
| 缓存 | Redis | 会话缓存、限流、消息队列Broker |
| 文件存储 | MinIO | 图片、视频、模型文件存储 |
| 向量数据库 | ChromaDB | 知识库向量嵌入，RAG检索 |
| 模型推理 | YOLOv8/v11 + TensorRT | 本地GPU加速推理 |
| 云端AI | DeepSeek API | 检测路由第一级 + 问答Agent |
| 容器化 | Docker + Docker Compose | 服务编排与部署 |
| 反向代理 | Nginx | SSL终止、静态资源、反向代理 |

## 3. 核心模块设计

### 3.1 检测路由模块（核心）

#### 3.1.1 检测路由流程

```
用户提交检测请求
       │
       ▼
┌──────────────────┐
│ 1. 文件预处理     │  验证格式、大小、提取帧
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. 云端AI分析     │  调用DeepSeek API
│    (第一级判断)   │  发送图片/关键帧 + Prompt
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. 模型匹配       │  将AI分析结果中的病虫害类型
│                   │  与本地模型注册表比对
└──┬──────────┬────┘
   │          │
   ▼          ▼
匹配成功    匹配失败
   │          │
   ▼          ▼
┌────────┐ ┌────────────┐
│4a.本地 │ │4b.返回云端 │
│YOLO   │ │AI分析结果  │
│精确检测│ │+防治建议   │
└───┬────┘ └─────┬──────┘
    │            │
    ▼            ▼
┌──────────────────────┐
│ 5. 结果汇总与存储     │
│  标注检测来源         │
│  关联环境数据         │
│  触发智能体审查       │
└──────────────────────┘
```

#### 3.1.2 模型注册表设计

```python
class ModelRegistry:
    """
    本地检测模型注册表
    存储在数据库中，管理员可通过后台管理
    """
    model_id: str          # 模型唯一标识
    model_name: str        # 模型名称，如 "rice-blast-yolov8"
    model_version: str     # 版本号
    model_path: str        # MinIO中的模型文件路径
    supported_pests: list  # 支持的病虫害类型列表
    supported_crops: list  # 支持的作物类型列表
    input_size: tuple      # 模型输入尺寸
    confidence_threshold: float  # 默认置信度阈值
    is_active: bool        # 是否启用
    is_default: bool       # 是否为默认版本
    deployed_at: datetime  # 部署时间
    metrics: dict          # 模型指标(mAP, precision, recall)
```

#### 3.1.3 云端AI Prompt设计

```
系统提示：你是一个农作物病虫害识别专家。请分析用户上传的作物图片，识别可能存在的病虫害。

输出格式（JSON）：
{
  "crop_type": "作物类型",
  "diseases": [
    {
      "name": "病虫害名称",
      "confidence": 0.85,
      "severity": "低/中/高",
      "symptoms": "症状描述",
      "possible_causes": "可能原因",
      "prevention": "防治建议"
    }
  ],
  "has_pest": true/false,
  "model_match_keywords": ["关键词1", "关键词2"]  // 用于本地模型匹配
}
```

### 3.2 检测服务模块

#### 3.2.1 图像检测

```python
class ImageDetectionService:
    async def detect(self, user_id: str, image_file: UploadFile,
                     location: LocationData = None) -> DetectionResult:
        # 1. 预处理：验证格式、调整尺寸
        image = await self.preprocess(image_file)

        # 2. 云端AI初步分析
        ai_result = await self.cloud_ai_analyze(image)

        # 3. 模型匹配
        matched_models = self.match_local_models(ai_result.model_match_keywords)

        if matched_models:
            # 4a. 本地YOLO精确检测
            local_result = await self.local_model_detect(image, matched_models)
            result = self.merge_results(ai_result, local_result)
            result.source = "local_model"
        else:
            # 4b. 直接返回云端AI结果
            result = ai_result
            result.source = "cloud_ai"

        # 5. 关联环境数据并保存
        result.environment = await self.get_environment_data(location)
        await self.save_detection_record(user_id, result)

        # 6. 触发智能体审查（异步）
        await self.trigger_agent_review(result)

        return result
```

#### 3.2.2 视频检测

```python
class VideoDetectionService:
    FRAME_RATE = 3  # 每秒采样帧数

    async def detect(self, user_id: str, video_file: UploadFile,
                     location: LocationData = None) -> VideoDetectionResult:
        # 1. 预处理：验证格式、提取元信息
        video_meta = await self.preprocess(video_file)

        # 2. 关键帧采样
        key_frames = await self.extract_key_frames(video_file, self.FRAME_RATE)

        # 3. 云端AI分析（对首帧和中间帧采样分析）
        sample_frames = self.select_sample_frames(key_frames, count=3)
        ai_results = await self.cloud_ai_batch_analyze(sample_frames)

        # 4. 模型匹配
        matched_models = self.match_local_models(ai_results)

        if matched_models:
            # 4a. 本地YOLO全帧检测 + 目标跟踪
            frame_results = []
            tracker = ByteTracker()  # 多目标跟踪器

            for i, frame in enumerate(key_frames):
                detections = await self.local_model_detect(frame, matched_models)
                tracked = tracker.update(detections)
                frame_results.append(TrackFrameResult(
                    frame_index=i, timestamp=i / self.FRAME_RATE,
                    detections=tracked
                ))
                # WebSocket推送进度
                await self.push_progress(user_id, i, len(key_frames))

            result = self.compile_video_report(frame_results, ai_results)
            result.source = "local_model"
        else:
            result = self.compile_ai_video_report(ai_results, key_frames)
            result.source = "cloud_ai"

        # 5. 保存并触发审查
        result.environment = await self.get_environment_data(location)
        await self.save_detection_record(user_id, result)
        await self.trigger_agent_review(result)

        return result
```

#### 3.2.3 摄像头实时检测

```python
class CameraDetectionService:
    async def stream_detect(self, websocket: WebSocket, user_id: str,
                            camera_id: str, location: LocationData = None):
        await websocket.accept()

        frame_interval = 1.0  # 1帧/秒
        last_detect_time = 0
        tracker = ByteTracker()
        matched_models = None

        try:
            while True:
                frame_data = await websocket.receive_bytes()
                current_time = time.time()

                if current_time - last_detect_time < frame_interval:
                    continue

                frame = decode_frame(frame_data)
                last_detect_time = current_time

                if matched_models is None:
                    # 首次检测：走完整路由流程
                    ai_result = await self.cloud_ai_analyze(frame)
                    matched_models = self.match_local_models(ai_result)
                else:
                    ai_result = None

                if matched_models:
                    detections = await self.local_model_detect(frame, matched_models)
                    tracked = tracker.update(detections)
                    annotated_frame = draw_detections(frame, tracked)
                    await websocket.send_json({
                        "type": "detection",
                        "source": "local_model",
                        "detections": serialize(tracked),
                        "annotated_frame": encode_frame(annotated_frame)
                    })
                else:
                    if ai_result:
                        await websocket.send_json({
                            "type": "detection",
                            "source": "cloud_ai",
                            "analysis": ai_result.dict()
                        })
        except WebSocketDisconnect:
            await self.save_camera_session(user_id, camera_id, location)
```

### 3.3 智能体模块

#### 3.3.1 自动审查智能体

```python
class ReviewAgent:
    """
    自动审查智能体：基于检测结果触发风险评估和警告推送
    """

    async def review(self, detection_result: DetectionResult):
        # 1. 判断是否需要审查
        if not self.should_review(detection_result):
            return

        # 2. 构建审查上下文
        context = await self.build_review_context(detection_result)

        # 3. 调用LLM进行风险评估
        risk_assessment = await self.llm_assess_risk(context)

        # 4. 判断是否误报
        if risk_assessment.is_false_positive:
            await self.record_false_positive(detection_result, risk_assessment)
            return

        # 5. 生成警告信息
        warning = await self.generate_warning(detection_result, risk_assessment)

        # 6. 推送给相关用户
        await self.push_warning(warning)

        # 7. 检查是否需要区域预警
        await self.check_regional_alert(detection_result, risk_assessment)

    async def build_review_context(self, result: DetectionResult) -> dict:
        return {
            "detection": result.dict(),
            "environment": result.environment,
            "regional_history": await self.get_regional_history(
                result.location, result.disease_name
            ),
            "knowledge_base": await self.query_knowledge(result.disease_name),
            "recent_detections": await self.get_recent_similar_detections(
                result.disease_name, days=7
            )
        }

    async def check_regional_alert(self, result, assessment):
        """检查同地区是否有多个用户检测到相同病虫害"""
        nearby_detections = await self.get_nearby_detections(
            location=result.location,
            disease_name=result.disease_name,
            radius_km=50,
            days=3
        )
        if len(nearby_detections) >= 3:
            regional_users = await self.get_users_in_region(result.location, radius_km=50)
            alert = await self.generate_regional_alert(result, nearby_detections)
            await self.push_to_users(regional_users, alert)
```

#### 3.3.2 问答Agent

```python
class QnAAgent:
    """
    用户病害问答Agent：基于RAG的智能问答
    """

    async def answer(self, user_id: str, question: str,
                     conversation_id: str = None) -> QnAResponse:
        # 1. 意图识别
        intent = await self.classify_intent(question)
        if not intent.is_pest_related:
            return QnAResponse(
                answer="该问题超出病虫害专业范围，请咨询相关领域专家。",
                sources=[], is_in_scope=False
            )

        # 2. RAG检索：从知识库向量数据库检索相关文档
        relevant_docs = await self.vector_search(question, top_k=5)

        # 3. 构建Prompt
        prompt = self.build_rag_prompt(question, relevant_docs)

        # 4. 调用LLM生成回答
        llm_response = await self.llm_generate(prompt)

        # 5. 标注来源
        sources = self.extract_sources(relevant_docs)

        # 6. 保存对话记录
        await self.save_conversation(user_id, conversation_id, question, llm_response)

        return QnAResponse(
            answer=llm_response,
            sources=sources,
            is_in_scope=True,
            disclaimer="以上建议仅供参考，请以专业农技人员意见为准。"
        )
```

### 3.4 环境数据模块

```python
class EnvironmentService:
    async def get_environment(self, latitude: float, longitude: float) -> EnvironmentData:
        # 并行获取地址和天气
        address_task = self.reverse_geocode(latitude, longitude)
        weather_task = self.get_weather(latitude, longitude)
        address, weather = await asyncio.gather(address_task, weather_task)

        return EnvironmentData(
            latitude=latitude, longitude=longitude,
            address=address, weather=weather.condition,
            temperature=weather.temperature,
            humidity=weather.humidity,
            wind_speed=weather.wind_speed,
            recorded_at=datetime.utcnow()
        )

    async def reverse_geocode(self, lat, lng) -> str:
        """调用地图API逆地理编码"""
        # 使用高德/百度地图API

    async def get_weather(self, lat, lng) -> WeatherData:
        """调用天气API获取实时天气"""
        # 使用和风天气/OpenWeatherMap API
```

### 3.5 通知推送模块

```python
class NotificationService:
    async def push_notification(self, user_id: str, notification: Notification):
        # 1. 保存到数据库
        await self.save_notification(user_id, notification)

        # 2. 站内WebSocket推送
        if self.is_user_online(user_id):
            await self.websocket_push(user_id, notification)

        # 3. 网页通知（Service Worker）
        await self.send_web_push(user_id, notification)

    async def push_regional_alert(self, location, radius_km, alert):
        """区域预警推送"""
        users = await self.get_users_in_region(location, radius_km)
        for user in users:
            await self.push_notification(user.id, alert)
```

## 4. 数据库设计

### 4.1 ER关系图

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  users   │────<│  detections  │>────│  disease_    │
│          │     │              │     │  info        │
└────┬─────┘     └──────┬───────┘     └──────────────┘
     │                  │
     │           ┌──────┴───────┐
     │           │              │
     │           ▼              ▼
     │    ┌────────────┐ ┌──────────────┐
     │    │ video_     │ │ tracking_    │
     │    │ frames     │ │ tasks       │
     │    └────────────┘ └──────────────┘
     │                        │
     │                        ▼
     │                  ┌──────────────┐
     │                  │ tracking_    │
     │                  │ updates      │
     │                  └──────────────┘
     │
     ├──────────────────────┐
     │                      │
     ▼                      ▼
┌──────────┐        ┌──────────────┐
│notifi-   │        │ api_keys     │
│cations   │        └──────────────┘
└──────────┘
                           │
┌──────────────┐          │
│ model_       │          │
│ registry     │          │
└──────────────┘          │
                           │
┌──────────────┐     ┌────┴─────────┐
│ knowledge_   │     │ operation_   │
│ base         │     │ logs         │
└──────────────┘     └──────────────┘
```

### 4.2 核心表结构

#### users - 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | VARCHAR(50) | 用户名，唯一 |
| email | VARCHAR(100) | 邮箱，唯一 |
| password_hash | VARCHAR(255) | 密码哈希 |
| role | ENUM(user, admin) | 角色 |
| phone | VARCHAR(20) | 手机号（可选） |
| location | POINT | 默认地理位置 |
| language | VARCHAR(5) | 语言偏好 |
| is_active | BOOLEAN | 是否激活 |
| login_fail_count | INT | 连续登录失败次数 |
| locked_until | TIMESTAMP | 锁定截止时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### detections - 检测记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键->users |
| detection_type | ENUM(image, video, camera) | 检测类型 |
| source | ENUM(local_model, cloud_ai) | 检测来源 |
| file_path | VARCHAR(500) | 原始文件MinIO路径 |
| thumbnail_path | VARCHAR(500) | 缩略图路径 |
| crop_type | VARCHAR(50) | 作物类型 |
| disease_name | VARCHAR(100) | 病虫害名称 |
| confidence | FLOAT | 置信度 |
| severity | ENUM(low, medium, high) | 严重等级 |
| bounding_boxes | JSONB | 检测框坐标（本地模型） |
| ai_analysis | JSONB | 云端AI完整分析结果 |
| prevention_advice | TEXT | 防治建议 |
| location | POINT | 检测地理位置 |
| address | VARCHAR(200) | 地址 |
| weather | VARCHAR(50) | 天气 |
| temperature | FLOAT | 温度 |
| humidity | FLOAT | 湿度 |
| review_status | ENUM(pending, reviewed, false_positive) | 审查状态 |
| review_result | JSONB | 智能体审查结果 |
| created_at | TIMESTAMP | 创建时间 |

#### tracking_tasks - 虫害跟踪表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键->users |
| detection_id | UUID | 外键->detections |
| disease_name | VARCHAR(100) | 病虫害名称 |
| location | POINT | 跟踪位置 |
| severity | ENUM(low, medium, high) | 当前严重等级 |
| status | ENUM(active, resolved, archived) | 跟踪状态 |
| resolved_at | TIMESTAMP | 解决时间 |
| resolved_measure | TEXT | 解决措施 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### tracking_updates - 跟踪更新记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| task_id | UUID | 外键->tracking_tasks |
| description | TEXT | 更新描述 |
| image_path | VARCHAR(500) | 更新图片路径 |
| severity | ENUM(low, medium, high) | 更新时严重等级 |
| created_at | TIMESTAMP | 创建时间 |

#### model_registry - 模型注册表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| model_name | VARCHAR(100) | 模型名称 |
| model_version | VARCHAR(20) | 版本号 |
| model_path | VARCHAR(500) | 模型文件MinIO路径 |
| supported_pests | JSONB | 支持的病虫害列表 |
| supported_crops | JSONB | 支持的作物列表 |
| input_size | VARCHAR(20) | 输入尺寸如"640x640" |
| confidence_threshold | FLOAT | 默认置信度阈值 |
| is_active | BOOLEAN | 是否启用 |
| is_default | BOOLEAN | 是否默认版本 |
| metrics | JSONB | 模型指标 |
| deployed_at | TIMESTAMP | 部署时间 |

#### notifications - 通知表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键->users |
| type | ENUM(warning, system, agent_push, regional_alert) | 通知类型 |
| title | VARCHAR(200) | 标题 |
| content | TEXT | 内容 |
| is_read | BOOLEAN | 是否已读 |
| related_detection_id | UUID | 关联检测记录ID |
| created_at | TIMESTAMP | 创建时间 |

#### knowledge_base - 病害知识库表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| disease_name | VARCHAR(100) | 病虫害名称 |
| crop_type | VARCHAR(50) | 作物类型 |
| symptoms | TEXT | 症状描述 |
| conditions | TEXT | 发病条件 |
| prevention | TEXT | 防治措施 |
| cases | TEXT | 相关案例 |
| image_urls | JSONB | 图片URL列表 |
| language | VARCHAR(5) | 语言 |
| embedding_id | VARCHAR(100) | 向量数据库ID |
| updated_at | TIMESTAMP | 更新时间 |

#### video_frames - 视频检测帧表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| detection_id | UUID | 外键->detections |
| frame_index | INT | 帧序号 |
| timestamp | FLOAT | 时间点（秒） |
| detections | JSONB | 该帧检测结果 |
| track_ids | JSONB | 跟踪目标ID列表 |
| annotated_frame_path | VARCHAR(500) | 标注后帧图片路径 |

#### api_keys - API密钥表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键->users |
| key_hash | VARCHAR(255) | 密钥哈希 |
| name | VARCHAR(100) | 密钥名称 |
| rate_limit | INT | 速率限制（次/分钟） |
| is_active | BOOLEAN | 是否启用 |
| expires_at | TIMESTAMP | 过期时间 |
| created_at | TIMESTAMP | 创建时间 |

#### operation_logs - 操作日志表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 操作用户 |
| action | VARCHAR(50) | 操作类型 |
| resource | VARCHAR(100) | 操作资源 |
| detail | JSONB | 操作详情 |
| ip_address | VARCHAR(45) | IP地址 |
| created_at | TIMESTAMP | 操作时间 |

## 5. API设计

### 5.1 API路由结构

```
/api/v1
├── /auth
│   ├── POST   /register          # 用户注册
│   ├── POST   /login             # 用户登录
│   ├── POST   /logout            # 用户登出
│   └── PUT    /profile           # 修改个人信息
│
├── /detection
│   ├── POST   /image             # 图像检测
│   ├── POST   /video             # 视频检测
│   ├── WS     /camera            # 摄像头实时检测
│   ├── GET    /history           # 检测历史列表
│   ├── GET    /{id}              # 检测记录详情
│   └── GET    /stats             # 个人统计
│
├── /tracking
│   ├── POST   /                  # 创建跟踪任务
│   ├── GET    /                  # 跟踪任务列表
│   ├── GET    /{id}              # 跟踪任务详情
│   ├── PUT    /{id}              # 更新跟踪任务
│   ├── POST   /{id}/updates      # 添加跟踪更新
│   └── PUT    /{id}/resolve      # 解决跟踪任务
│
├── /environment
│   ├── GET    /current           # 获取当前环境数据
│   └── POST   /manual            # 手动补充环境数据
│
├── /knowledge
│   ├── GET    /search            # 知识库搜索
│   ├── GET    /{id}              | 知识条目详情
│   └── GET    /recent            # 最近更新条目
│
├── /qna
│   ├── POST   /ask               # 提问
│   ├── GET    /conversations     # 对话列表
│   ├── GET    /conversations/{id}# 对话详情
│   └── POST   /feedback          | 回答反馈
│
├── /notifications
│   ├── GET    /                  # 通知列表
│   ├── PUT    /{id}/read         # 标记已读
│   └── PUT    /read-all          # 全部标记已读
│
├── /admin
│   ├── GET    /dashboard         # 管理仪表板
│   ├── GET    /users             # 用户列表
│   ├── GET    /users/{id}/data   # 用户数据
│   ├── GET    /stats             # 全局统计
│   ├── GET    /stats/export      # 导出统计
│   ├── CRUD   /models            # 模型管理
│   ├── CRUD   /knowledge         # 知识库管理
│   ├── GET    /logs              # 操作日志
│   └── GET    /monitoring        # 系统监控
│
└── /api-keys
    ├── POST   /                  # 创建API密钥
    ├── GET    /                  # 密钥列表
    └── DELETE /{id}              # 删除密钥
```

### 5.2 核心API接口定义

#### 图像检测

```
POST /api/v1/detection/image
Content-Type: multipart/form-data

Request:
  file: 图片文件 (JPG/PNG/WebP, max 20MB)
  latitude: 纬度 (可选)
  longitude: 经度 (可选)
  manual_address: 手动地址 (可选)

Response:
{
  "id": "uuid",
  "source": "local_model" | "cloud_ai",
  "crop_type": "水稻",
  "diseases": [
    {
      "name": "稻瘟病",
      "confidence": 0.92,
      "severity": "high",
      "bounding_box": [x1, y1, x2, y2],  // 本地模型时返回
      "symptoms": "叶片出现菱形病斑",
      "possible_causes": "高温高湿环境",
      "prevention": "选用抗病品种，合理施肥"
    }
  ],
  "environment": {
    "address": "湖南省长沙市",
    "weather": "多云",
    "temperature": 28.5,
    "humidity": 75
  },
  "created_at": "2026-04-28T10:00:00Z"
}
```

#### 视频检测

```
POST /api/v1/detection/video
Content-Type: multipart/form-data

Request:
  file: 视频文件 (MP4/AVI/MOV, max 500MB)
  latitude: 纬度 (可选)
  longitude: 经度 (可选)

Response:
{
  "id": "uuid",
  "source": "local_model" | "cloud_ai",
  "total_frames": 150,
  "detected_frames": 45,
  "timeline": [
    {
      "timestamp": 2.5,
      "diseases": [...],
      "track_ids": ["t1", "t2"]
    }
  ],
  "summary": {
    "crop_type": "水稻",
    "diseases": [...],
    "max_severity": "high"
  },
  "environment": {...}
}
```

## 6. 前端页面设计

### 6.1 页面结构

```
/ (首页)
├── /detect                    # 检测中心
│   ├── /detect/image          # 图像检测
│   ├── /detect/video          # 视频检测
│   └── /detect/camera         # 摄像头检测
├── /tracking                  # 虫害跟踪
│   ├── /tracking/list         # 跟踪列表
│   └── /tracking/:id          # 跟踪详情
├── /history                   # 检测历史
│   ├── /history/list          # 记录列表
│   └── /history/:id           # 记录详情
├── /statistics                # 可视化统计
├── /knowledge                 # 病害知识库
│   ├── /knowledge/search      # 搜索
│   └── /knowledge/:id         # 条目详情
├── /qna                       # 问答Agent
├── /notifications             # 消息中心
├── /settings                  # 个人设置
│   ├── /settings/profile      # 个人信息
│   ├── /settings/language     # 语言设置
│   └── /settings/api-keys     # API密钥管理
└── /admin                     # 管理后台
    ├── /admin/dashboard       # 管理仪表板
    ├── /admin/users           # 用户管理
    ├── /admin/models          # 模型管理
    ├── /admin/knowledge       # 知识库管理
    ├── /admin/stats           # 全局统计
    ├── /admin/logs            # 操作日志
    └── /admin/monitoring      # 系统监控
```

### 6.2 核心页面交互流程

#### 检测页面

```
用户选择检测类型
       │
       ├─图像检测──> 上传图片 ──> 显示检测进度 ──> 展示结果
       │                                              │
       │                                    ┌─────────┴─────────┐
       │                                    │ 标注来源标签       │
       │                                    │ 本地模型: 边界框   │
       │                                    │ 云端AI: 分析报告   │
       │                                    └─────────┬─────────┘
       │                                              │
       │                                    确认保存 ──> 关联环境数据
       │                                              │
       │                                    触发智能体审查(后台)
       │
       ├─视频检测──> 上传视频 ──> 实时进度条 ──> 视频报告+时间轴
       │
       └─摄像头──> 授权设备 ──> 实时画面+标注 ──> 停止并保存记录
```

## 7. 部署架构

### 7.1 Docker Compose编排

```yaml
services:
  # 前端
  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [backend]

  # 后端API
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis, minio, model-server]

  # 模型推理服务
  model-server:
    build: ./model-server
    runtime: nvidia
    volumes:
      - model_data:/models
    environment:
      - NVIDIA_VISIBLE_DEVICES=all

  # Celery Worker - 检测任务
  celery-worker-detect:
    build: ./backend
    command: celery -A app.celery worker -Q detection -c 4
    depends_on: [redis, postgres]

  # Celery Worker - 智能体审查
  celery-worker-agent:
    build: ./backend
    command: celery -A app.celery worker -Q agent -c 2
    depends_on: [redis, postgres]

  # PostgreSQL
  postgres:
    image: postgres:16
    volumes: [pg_data:/var/lib/postgresql/data]

  # Redis
  redis:
    image: redis:7-alpine

  # MinIO
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]

  # ChromaDB
  chromadb:
    image: chromadb/chroma
    volumes: [chroma_data:/chroma/chroma]

  # Nginx
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    depends_on: [frontend, backend]
```

### 7.2 GPU推理服务

```python
# model-server: 独立的模型推理服务
# 使用 FastAPI + TensorRT/ONNX Runtime
# 支持多模型动态加载

app = FastAPI()

class ModelManager:
    def __init__(self):
        self.models: Dict[str, YOLOModel] = {}

    def load_model(self, model_id: str, model_path: str):
        model = YOLO(model_path)
        self.models[model_id] = model

    def predict(self, model_id: str, image: np.ndarray) -> List[Detection]:
        return self.models[model_id].predict(image)

@app.post("/predict")
async def predict(request: PredictRequest):
    result = model_manager.predict(request.model_id, request.image)
    return {"detections": result}

@app.post("/models/{model_id}/load")
async def load_model(model_id: str, model_path: str):
    model_manager.load_model(model_id, model_path)
    return {"status": "loaded"}
```

## 8. 安全设计

### 8.1 认证与授权

- JWT Token认证，Access Token有效期2小时，Refresh Token有效期7天
- RBAC角色权限控制：user角色仅访问自身数据，admin角色可访问全部数据
- API密钥认证用于第三方集成，独立限流

### 8.2 数据安全

- HTTPS全站加密传输
- 密码使用bcrypt哈希存储
- 管理员查看用户数据时脱敏手机号、邮箱
- 异常访问检测：同一IP短时间内大量请求自动限流

### 8.3 文件上传安全

- 验证文件类型（Magic Number校验，不依赖扩展名）
- 文件大小限制
- 上传文件重命名存储，防止路径遍历
- 文件扫描（防病毒）

## 9. 性能设计

### 9.1 关键性能指标

| 操作 | 目标响应时间 |
|------|------------|
| 图像检测（含路由） | < 5秒 |
| 视频检测（每分钟视频） | < 30秒 |
| 摄像头实时检测 | > 1 FPS |
| 统计图表渲染 | < 3秒 |
| 检测记录查询 | < 2秒 |
| 首页加载 | < 3秒 |

### 9.2 性能优化策略

- 数据库：索引优化（user_id, created_at, disease_name, location空间索引）
- 缓存：Redis缓存统计热点数据、知识库热门条目
- 异步：Celery异步处理检测任务和智能体审查
- CDN：静态资源和知识库图片通过CDN分发
- 分页：检测历史记录分页加载，默认每页20条
- WebSocket：摄像头检测和实时通知使用WebSocket长连接
