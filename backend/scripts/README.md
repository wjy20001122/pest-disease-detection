# Backend Regression Scripts

Run from `backend/` after installing `requirements.txt`.

```bash
python3 scripts/test_tracking_flow.py
python3 scripts/test_stats_flow.py
python3 scripts/test_environment_flow.py
python3 scripts/test_review_notifications_flow.py
```

## Scripts

- `test_tracking_flow.py`: validates `/tracking` create, list, detail, update timeline, resolve flow, and user isolation.
- `test_stats_flow.py`: validates `/detection/stats/overview` and `/detection/stats` trend, distribution, confidence, and date-range behavior.
- `test_environment_flow.py`: validates environment current/manual fallback responses.
- `test_review_notifications_flow.py`: validates review-agent warning output plus notification persistence and read transitions.

Both scripts create temporary users and records, then clean them up before exiting.
