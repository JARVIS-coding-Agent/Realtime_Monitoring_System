"""資料保留清理：定期刪除逾期的即時資料與系統日誌。"""
import asyncio
from datetime import timedelta

from sqlalchemy import delete

from app.core.config import settings
from app.core.logging import logger
from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models.realtime_data import RealtimeData
from app.models.system_log import SystemLog


async def cleanup_once() -> dict:
    """執行一次清理，回傳刪除筆數。"""
    now = utcnow()
    rt_cutoff = now - timedelta(days=settings.realtime_retention_days)
    log_cutoff = now - timedelta(days=settings.log_retention_days)
    async with AsyncSessionLocal() as session:
        rt_result = await session.execute(
            delete(RealtimeData).where(RealtimeData.generated_at < rt_cutoff)
        )
        log_result = await session.execute(
            delete(SystemLog).where(SystemLog.created_at < log_cutoff)
        )
        await session.commit()
    deleted = {"realtime": rt_result.rowcount or 0, "logs": log_result.rowcount or 0}
    logger.info(f"保留清理完成：{deleted}")
    return deleted


class RetentionCleaner:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def _run(self) -> None:
        interval = settings.retention_cleanup_interval_hours * 3600
        while self._running:
            try:
                await cleanup_once()
            except Exception as exc:
                logger.error(f"保留清理失敗：{exc}")
            await asyncio.sleep(interval)

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


retention_cleaner = RetentionCleaner()
