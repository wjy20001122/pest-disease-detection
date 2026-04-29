# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [代码结构|代码模式|代码生成|构建方法|测试方法|依赖关系|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[病虫害检测系统需求设计]
- Date: 2026-04-28
- Context: 用户首次提出病虫害检测系统的完整需求
- Instructions:
  - 系统包含病虫害检测、视频检测、虫害跟踪、摄像头检测、数据采集、可视化统计、网页显示、病害知识库、天气/地址/温度集成、用户病害问答Agent、管理员数据查看与统计分析、智能体自动审查与警告推送等功能

[关联资料先解压再使用]
- Date: 2026-04-29
- Context: 用户在继续执行任务时补充执行要求
- Instructions:
  - 当任务与压缩包内容有关时，先解压（如 `monkeycode.zip`）再继续后续改动。

[后端存在两套数据库模型栈]
- Date: 2026-04-29
- Context: Agent 在执行“更新 AGENTS.md”时发现
- Category: 代码结构
- Instructions:
  - API 路由主要使用 `backend/app/db/*`（`pymysql` 同步引擎）。
  - 脚本主要使用 `backend/app/models/*`（`aiomysql` 异步引擎），例如 `scripts/init_db.py` 与 `scripts/test_db.py`。
  - 新改动不要混用两套导入路径。

[Vite 代理 WebSocket 约束]
- Date: 2026-04-29
- Context: Agent 在实现摄像头 WebSocket 检测链路时发现
- Category: 环境配置
- Instructions:
  - 当前前端通过 `/api` 反向代理访问后端，若新增 WebSocket 接口，`frontend/vite.config.js` 的 `/api` 代理需要开启 `ws: true`。
