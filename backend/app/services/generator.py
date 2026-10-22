"""即時資料生成器：每秒產生模擬資料，推送 WS 並送入批次寫入器。"""
import asyncio
import random

from app.core.config import settings
from app.core.logging import logger
from app.db.base import utcnow
from app.services.batch_writer import batch_writer
from app.services.ws_manager import ws_manager


class Generator:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def _run(self) -> None:
        logger.info("即時資料生成器啟動")
        while self._running:
            category = random.choice(settings.category_list)
            value = round(random.uniform(0, 100), 2)
            is_anomaly = value > settings.anomaly_threshold
            now = utcnow()

            message = {
                "value": value,
                "category": category,
                "is_anomaly": is_anomaly,
                "generated_at": now.isoformat(),
            }
            await ws_manager.broadcast(message)
            await batch_writer.add(
                {"value": value, "category": category, "is_anomaly": is_anomaly, "generated_at": now}
            )
            await asyncio.sleep(settings.generator_interval_seconds)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await batch_writer.flush()
        logger.info("即時資料生成器已停止")


generator = Generator()
