# 后端回归脚本说明

更新时间：2026-05-03  
请在 `backend/` 目录、安装完 `requirements.txt` 后执行。

```bash
python3 -m pytest --tb=short
python3 scripts/test_tracking_flow.py
python3 scripts/test_stats_flow.py
python3 scripts/test_environment_flow.py
python3 scripts/test_review_notifications_flow.py
python3 scripts/test_video_task_flow.py
python3 scripts/test_admin_core_flow.py
python3 scripts/predeploy_check.py
```

## 脚本清单

- `test_tracking_flow.py`：校验 `/tracking` 创建、列表、详情、更新与隔离逻辑。
- `test_stats_flow.py`：校验 `/detection/stats/overview` 与趋势/分布/置信度统计。
- `test_environment_flow.py`：校验环境与天气接口响应。
- `test_review_notifications_flow.py`：校验审查预警、通知落库与已读流转。
- `test_video_task_flow.py`：校验 `video_tasks` 状态流转（queued -> processing -> stopped/completed/failed）。
- `test_admin_core_flow.py`：校验管理端核心接口（dashboard/users/notifications/models/knowledge/stats/configs/audit/queue）。
- `predeploy_check.py`：发布前检查（DB、Redis、OSS、API 健康路由）。

多数脚本会创建临时测试数据，并在结束前清理。
