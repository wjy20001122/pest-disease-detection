# Backend Regression Scripts

Run from `backend/` after installing `requirements.txt`.

```bash
python -m pytest --tb=short
python3 scripts/test_tracking_flow.py
python3 scripts/test_stats_flow.py
python3 scripts/test_environment_flow.py
python3 scripts/test_review_notifications_flow.py
python3 scripts/test_video_task_flow.py
python3 scripts/test_admin_core_flow.py
python3 scripts/predeploy_check.py
```

## Scripts

- `test_tracking_flow.py`: validates `/tracking` create, list, detail, update timeline, resolve flow, and user isolation.
- `test_stats_flow.py`: validates `/detection/stats/overview` and `/detection/stats` trend, distribution, confidence, and date-range behavior.
- `test_environment_flow.py`: validates environment current/manual fallback responses.
- `test_review_notifications_flow.py`: validates review-agent warning output plus notification persistence and read transitions.
- `test_video_task_flow.py`: validates `video_tasks` state transitions (queued -> processing -> stopped/completed/failed).
- `test_admin_core_flow.py`: validates admin core endpoints (dashboard/users/notifications/models/knowledge/stats/configs/audit/queue).
- `predeploy_check.py`: validates deployment prerequisites (DB, Redis, OSS, API health route).

Both scripts create temporary users and records, then clean them up before exiting.
