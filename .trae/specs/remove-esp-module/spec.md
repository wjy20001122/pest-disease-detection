# 移除 ESP 边缘检测模块 Spec

## Why
仓库当前包含独立 `ESP/` 边缘实时检测子项目，但该模块不再需要。移除后可降低维护成本并避免无效入口与文档误导。

## What Changes
- 删除整个 `ESP/` 目录及其全部内容（本地服务、Qt 客户端、固件、模型、脚本、文档、配置示例等）。
- 清理全仓对 `ESP/` 的引用与说明（含启动命令、部署说明、模块清单等）。
- 移除后端与前端中“摄像头录制”相关的遗留接口与调用（原先提示迁移到 ESP 的那部分）。
- 产出“删除清单”，在交付说明中明确：删除了哪些目录/文件、修改了哪些文件、移除了哪些接口。

## Impact
- Affected specs: ESP32-CAM 本地实时检测（UDP + 本地推理 + Qt 展示）能力整体移除
- Affected code:
  - `ESP/**`（整目录删除）
  - `backend/app/api/routers/prediction.py`（移除录制相关路由与 ESP 提示）
  - `frontend/src/api/index.js`（移除 `mlApi.startRecording/stopRecording`）
  - `README.md`、`AGENTS.md`、`deploy/bt/README.md`、`backend/scripts/README.md`、根目录任务/流程文档（移除 ESP 相关章节）

## ADDED Requirements
### Requirement: ESP 模块完全移除
系统 SHALL 在仓库中不再包含 `ESP/` 目录与任何 ESP 边缘检测实现代码、资源文件、模型权重与固件工程。

#### Scenario: 成功移除
- **WHEN** 代码库完成变更并在仓库根目录执行全文检索 `ESP/`、`ESP32`、`esp32`、`8010`、`9000`
- **THEN** 除非属于无关字符串（需要人工确认），否则不应再出现与 ESP 边缘检测模块相关的引用

### Requirement: 录制接口移除（破坏性变更）
系统 SHALL 移除以下后端路由与前端调用点，以避免保留无意义的接口：
- 后端：`GET /startRecording`、`GET /stopRecording`（以及兼容路由别名，如果存在）
- 前端：`mlApi.startRecording`、`mlApi.stopRecording`

#### Scenario: 前端不再依赖录制接口
- **WHEN** 前端运行并触发与检测/历史/管理端相关的现有功能
- **THEN** 不应出现对 `/startRecording` 或 `/stopRecording` 的请求

### Requirement: 删除清单可追溯
系统 SHALL 在交付说明中提供删除清单，至少包含：
- 被删除的顶层目录与关键子路径（如 `ESP/server`、`ESP/qt_client`、`ESP/firmware`、`ESP/models` 等）
- 被修改的文件列表与修改点概述（不包含敏感信息）
- 被移除的 API 路由与前端导出

## MODIFIED Requirements
### Requirement: 仓库文档不得引导 ESP 启动/部署
仓库现有文档（`README.md`、`AGENTS.md`、`deploy/bt/README.md`、`backend/scripts/README.md`、根目录任务/流程文档） SHALL 不再包含 ESP 的启动命令、端口、部署指引或模块介绍。

## REMOVED Requirements
### Requirement: ESP32-CAM 本地实时检测
**Reason**: 产品范围收缩，不再维护 ESP 边缘实时检测独立链路。
**Migration**: 无迁移；如需恢复该能力，应通过单独仓库/分支维护并以子模块方式引入。
