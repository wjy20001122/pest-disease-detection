from __future__ import annotations

import asyncio
import logging
from typing import Any

import socketio


logger = logging.getLogger(__name__)


class SocketManager:
    def __init__(self) -> None:
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._register_events()

    def _register_events(self) -> None:
        @self.sio.event
        async def connect(sid, environ, auth):  # type: ignore[no-redef]
            del environ
            user_id = auth.get("user_id") if auth else None
            if user_id:
                await self.sio.enter_room(sid, f"user_{user_id}")
            await self.sio.emit("message", {"data": "Connected to WebSocket server!"}, to=sid)

        @self.sio.event
        async def disconnect(sid):  # type: ignore[no-redef]
            del sid

    def emit_to_user(self, user_id: int, event: str, data: Any) -> None:
        self.emit_nowait(event, data, to=f"user_{user_id}")

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def emit_nowait(self, event: str, data: Any, to: str | None = None) -> None:
        if self._loop is None:
            return
        coroutine = self.sio.emit(event, data, to=to)
        try:
            asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        except RuntimeError:
            logger.debug("Socket.IO loop is unavailable for event %s", event)

    def create_asgi_app(self, fastapi_app):
        return socketio.ASGIApp(self.sio, other_asgi_app=fastapi_app, socketio_path="socket.io")


socket_manager = SocketManager()

