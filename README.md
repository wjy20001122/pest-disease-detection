# Pest Disease Detection（病虫害检测系统）

更新时间：2026-05-03

一个基于 `FastAPI + Vue3 + Element Plus + Celery/Redis` 的农业病虫害检测平台，支持普通用户与管理员分级能力：

- 普通用户：图像检测（AI 约束分析）
- 管理员：图像/视频/摄像头检测（本地模型直连 + 异步任务）

---

## 项目结构

- `backend/`：FastAPI 主服务、数据库模型、业务服务、Celery 任务
- `frontend/`：Vue3 + Vite 前端工作台
- `deploy/`：宝塔部署脚本、PM2 与 Nginx 配置
- `backend/scripts/`：回归脚本、发布前检查、数据导入脚本

---

## 核心功能

- 检测中心：图像/视频/摄像头（按角色展示）
- 视频异步：Celery + Redis + `video_tasks` 状态持久化
- 知识库：MySQL 持久化，支持检索、筛选、详情、来源元数据
- 智能问答：会话持久化，失败明确错误态，支持作物/类别约束
- 管理后台：用户、通知、模型、配置、权限审计、队列指标
- 工作台：7 天天气可视化 + 检测统计总览

---

## 本地开发启动

默认开发环境：WSL + Python 3.11 + Conda 环境 `pest_detect`。后端相关命令均建议在该环境内执行。

### 0) 一键启动开发全栈（推荐，含前端/后端/Redis/Celery）

```bash
./scripts/dev_start.sh
```

### 1) 启动后端（8000）

```bash
cd backend
conda activate pest_detect
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2) 启动 Celery Worker（视频检测必需）

```bash
cd backend
conda activate pest_detect
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --pool=threads --concurrency=1
```

### 3) 启动前端 Dev（3000）

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

---

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，至少配置：

- MySQL：`DB_HOST/DB_PORT/DB_NAME/DB_USERNAME/DB_PASSWORD`
- Redis/Celery：`REDIS_URL/CELERY_BROKER_URL/CELERY_RESULT_BACKEND`
- 地图天气（可选增强）：`MAP_API_KEY/WEATHER_API_KEY`
- AI（可选增强）：`DEEPSEEK_API_KEY`

> 未启动 Redis/Celery 时，视频任务会按当前设计快速失败并返回明确错误。

---

## 视频处理依赖

视频检测功能需要系统安装 `ffmpeg`：

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg -y

# CentOS/RHEL
sudo yum install ffmpeg -y

# macOS (Homebrew)
brew install ffmpeg
```
