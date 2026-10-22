"""即時資料批次寫入器：緩衝累積，依筆數或時間間隔觸發批次寫入。"""
import asyncio
import time

from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.realtime_data import RealtimeData


class BatchWriter:
    def __init__(self) -> None:
        self._buffer: list[dict] = []
        self._lock = asyncio.Lock()
        self._last_flush = time.monotonic()

    async def add(self, item: dict) -> None:
        """加入一筆資料；達到批次門檻（筆數或時間）即觸發寫入。"""
        async with self._lock:
            self._buffer.append(item)
            size_reached = len(self._buffer) >= settings.batch_size
            time_reached = (time.monotonic() - self._last_flush) >= settings.batch_interval_seconds
            if size_reached or time_reached:
                await self._flush_locked()

    async def flush(self) -> None:
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        if not self._buffer:
            return
        pending = self._buffer
        self._buffer = []
        self._last_flush = time.monotonic()
        try:
            async with AsyncSessionLocal() as session:
                session.add_all([RealtimeData(**row) for row in pending])
                await session.commit()
            logger.debug(f"批次寫入 {len(pending)} 筆即時資料")
        except Exception as exc:
            logger.error(f"批次寫入失敗，{len(pending)} 筆資料遺失：{exc}")


batch_writer = BatchWriter()
