# AGENTS

## 快速开始（已验证）
- 仓库分为两部分：`frontend/`（Vue 3 + Vite）与 `backend/`（FastAPI）。
- 前端 API 基地址在 `frontend/src/api/index.js` 固定为 `/api`；开发环境通过 `frontend/vite.config.js` 的代理转发到后端。
- `frontend/vite.config.js` 中必须保留 `server.allowedHosts: ['.monkeycode-ai.online']`。

## 常用命令（直接可用）
- 一键启动开发全栈（默认 Conda 环境，含前端/后端/Redis/Celery）：`./scripts/dev_start.sh`
- 前端安装依赖：`cd frontend && npm install`
- 前端开发启动：`cd frontend && npm run dev -- --host 0.0.0.0 --port 3000`
- 前端构建：`cd frontend && npm run build`
- 后端安装依赖（Conda）：`conda activate pest_detect && cd backend && pip install -r requirements.txt`
- 后端开发启动（Conda，可配合前端代理）：`conda activate pest_detect && cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

## 运行注意事项（容易忽略）
- `python backend/main.py` 使用 `backend/app/core/config.py` 中的 `settings.port`，当前默认已统一为 `8000`，与前端代理一致。
- 后端启动时会在 `backend/app/main.py` 自动执行建表（`Base.metadata.create_all`）。
- 仓库里有两套数据库/模型栈：
  - 主 API 栈：`backend/app/db/*`（同步 SQLAlchemy，引入于路由主链路）
  - 脚本栈：`backend/app/models/*`（异步引擎，供 `scripts/init_db.py` 与 `scripts/test_db.py` 使用）
  新增代码时不要混用这两套导入。
- 视频检测功能需要系统安装 ffmpeg：`sudo apt install ffmpeg -y`（Ubuntu/Debian）

## 测试现状
- 仓库当前没有本地 lint/typecheck 配置（无 ESLint/Prettier）。
- `backend/pytest.ini` 已存在并作为后端测试默认配置。
- 后端测试命令（Conda）：`conda activate pest_detect && cd backend && python3 -m pytest --tb=short`。

## 部署提示
- 类生产环境的 nginx + PM2 模板位于 `deploy/bt/`。
- PM2 配置通过 `backend/main.py` 启动后端（`deploy/bt/ecosystem.config.json`），因此端口与环境变量一致性很关键。
开发环境默认在 WSL 上，Python 3.11，Conda 环境 `pest_detect`。
- 默认不要使用系统 Python 直接执行 `pip install`，避免触发 PEP 668 限制。
- Conda 环境启动后端：`conda activate pest_detect && cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
