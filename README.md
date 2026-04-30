# Pest Disease Detection

Pest Disease Detection is a full-stack project for agricultural pest and disease detection, with a FastAPI backend and a Vue 3 frontend.

## Project Structure

- `backend/`: FastAPI API, ML inference code, and service integrations
- `frontend/`: Vue 3 + Vite web application
- `scripts/`: database initialization and utility scripts
- `deploy/`: deployment-related files

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --pool=threads --concurrency=1
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment

Copy `backend/.env.example` to `backend/.env` and fill in the required values before running the backend.
For video async detection, make sure Redis and Celery worker are running.
