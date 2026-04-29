# AGENTS

## Fast Start (Verified)
- Repo is split: `frontend/` (Vue 3 + Vite) and `backend/` (FastAPI).
- Frontend API base is fixed to `/api` in `frontend/src/api/index.js`; dev proxy forwards to backend in `frontend/vite.config.js`.
- Vite dev server must keep `server.allowedHosts: ['.monkeycode-ai.online']` in `frontend/vite.config.js`.

## Commands You Actually Need
- Frontend install: `cd frontend && npm install`
- Frontend dev: `cd frontend && npm run dev -- --host 0.0.0.0 --port 3000`
- Frontend build: `cd frontend && npm run build`
- Backend install: `cd backend && pip install -r requirements.txt`
- Backend dev (works with frontend proxy): `cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Non-Obvious Runtime Gotchas
- `python backend/main.py` uses `settings.port` from `backend/app/core/config.py` (default `9999`), which does not match frontend proxy target (`8000`). If you run `main.py`, set `FASTAPI_PORT=8000`.
- Backend startup auto-creates DB tables (`Base.metadata.create_all`) on app startup in `backend/app/main.py`.
- There are two DB/model stacks:
  - Active API stack: `backend/app/db/*` (sync SQLAlchemy engine, used by routers).
  - Script stack: `backend/app/models/*` (async engine, used by `scripts/init_db.py` and `scripts/test_db.py`).
  Do not mix imports between these stacks in new code.

## Testing / CI Reality
- No local lint/typecheck config is present in repo (no ESLint/Prettier/pytest config files).
- CI workflow is `.github/workflows/deploy.yml` and currently runs backend tests as non-blocking: `pytest --tb=short || true`.
- CI deploy trigger is branch `main` (not `master`).

## Deployment Clues
- Production-like nginx + PM2 templates live in `deploy/bt/`.
- PM2 config runs backend from `backend/main.py` (`deploy/bt/ecosystem.config.json`), so port/env consistency matters.
