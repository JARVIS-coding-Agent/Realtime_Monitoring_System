"""WebSocket 連線管理與廣播。"""
import asyncio

from fastapi import WebSocket

from app.core.logging import logger


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info(f"WebSocket 連線建立，目前連線數={len(self._connections)}")

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)
        logger.info(f"WebSocket 連線關閉，目前連線數={len(self._connections)}")

    async def broadcast(self, message: dict) -> None:
        """廣播 JSON 訊息給所有連線；失敗的連線自動移除。"""
        async with self._lock:
            targets = list(self._connections)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


ws_manager = WebSocketManager()
