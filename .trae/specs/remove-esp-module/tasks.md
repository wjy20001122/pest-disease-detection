# Tasks
- [x] Task 1: 删除 ESP/ 目录
  - [x] SubTask 1.1: 删除 `ESP/` 全量目录（server/、qt_client/、firmware/、models/、scripts/、config/、文档与 spec 等）
  - [x] SubTask 1.2: 确认仓库根目录不再存在 `ESP/` 路径

- [x] Task 2: 移除后端录制相关遗留接口
  - [x] SubTask 2.1: 在 `backend/app/api/routers/prediction.py` 删除 `/startRecording` 与 `/stopRecording` 路由（含别名路由如果存在）
  - [x] SubTask 2.2: 确认后端路由注册链路中不再包含上述接口

- [x] Task 3: 移除前端录制相关 API 导出
  - [x] SubTask 3.1: 在 `frontend/src/api/index.js` 删除 `mlApi.startRecording` 与 `mlApi.stopRecording`
  - [x] SubTask 3.2: 全仓检索确认无前端代码再调用这两个方法

- [x] Task 4: 清理所有文档中的 ESP 引用
  - [x] SubTask 4.1: 更新 `README.md`，移除 ESP 相关介绍、启动命令与端口说明
  - [x] SubTask 4.2: 更新 `AGENTS.md`，移除 ESP 相关快速开始、命令与注意事项
  - [x] SubTask 4.3: 更新 `deploy/bt/README.md`，移除 ESP 不走宝塔/验收命令等说明
  - [x] SubTask 4.4: 更新 `backend/scripts/README.md`，移除 ESP 独立项目说明与检查片段
  - [x] SubTask 4.5: 更新根目录任务/流程相关文档（`任务清单文件.md`、`完整任务描述文件.md`、`完整任务流程文件.md`），移除 ESP 模块条目与相关说明

- [x] Task 5: 生成删除清单并完成验证
  - [x] SubTask 5.1: 在交付说明中列出删除的目录/文件与修改的文件、移除的接口
  - [x] SubTask 5.2: 全仓检索 `ESP/`、`ESP32`、`esp32`、`8010`、`9000`，确认无残留引用（必要时人工确认误报）
  - [x] SubTask 5.3: 验证核心开发链路可启动（建议按仓库约定在 WSL/Conda 环境执行 `./scripts/dev_start.sh`）
  - [x] SubTask 5.4: 运行后端测试（`cd backend && python3 -m pytest --tb=short`）

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Task 1
- Task 5 depends on Task 1, Task 2, Task 3, Task 4
