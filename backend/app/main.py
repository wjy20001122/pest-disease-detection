from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import files, prediction, records, system, users
from app.api.routers import auth, detection, tracking, knowledge, qna, notifications, admin, environment
from app.api.api_keys import router as api_keys_router
from app.core.config import settings
from app.db.bootstrap import bootstrap_runtime_data
from app.db.session import Base, engine
from app.services.prediction_service import prediction_service
from app.services.socket_manager import socket_manager


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def create_fastapi_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(system.router)
    app.include_router(users.router)
    app.include_router(records.router)
    app.include_router(files.router)
    app.include_router(prediction.router)

    app.include_router(auth.router)
    app.include_router(detection.router)
    app.include_router(tracking.router)
    app.include_router(tracking.router, prefix="/api/v1")
    app.include_router(knowledge.router)
    app.include_router(qna.router)
    app.include_router(notifications.router)
    app.include_router(admin.router)
    app.include_router(environment.router)
    app.include_router(api_keys_router)

    @app.on_event("startup")
    async def startup() -> None:
        Base.metadata.create_all(bind=engine)
        bootstrap_runtime_data()
        socket_manager.attach_loop(asyncio.get_running_loop())
        prediction_service.start()

    return app


fastapi_app = create_fastapi_app()
app = socket_manager.create_asgi_app(fastapi_app)
