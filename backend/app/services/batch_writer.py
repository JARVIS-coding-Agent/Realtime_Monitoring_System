"""即時資料批次寫入器：緩衝累積，依筆數或獨立 timer 觸發批次寫入。

設計（issue #3）：
- 獨立背景 flush loop：依 `batch_interval_seconds` 定期 flush，不依賴 `add()` 被呼叫，
  故低流量/閒置時尾端資料仍會被寫入。
- `add()` 僅在達筆數門檻時即時 flush（降低延遲）。
- flush 失敗時資料退回 buffer（前置），下輪重試而非靜默遺失；buffer 有上限，
  超過時丟棄最舊並告警（輕量 dead-letter，避免記憶體無限成長）。
"""
import asyncio
import time

from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.realtime_data import RealtimeData

# buffer 筆數硬上限（防止 DB 長時間不可用時記憶體無限成長）
_MAX_BUFFER = 10000


class BatchWriter:
    def __init__(self) -> None:
        self._buffer: list[dict] = []
        self._lock = asyncio.Lock()
        self._last_flush = time.monotonic()
        self._task: asyncio.Task | None = None
        self._running = False

    async def add(self, item: dict) -> None:
        """加入一筆資料；達筆數門檻時即時 flush（時間觸發由背景 loop 負責）。"""
        async with self._lock:
            self._buffer.append(item)
            # buffer 溢位保護：丟棄最舊資料並告警
            if len(self._buffer) > _MAX_BUFFER:
                dropped = len(self._buffer) - _MAX_BUFFER
                del self._buffer[:dropped]
                logger.error(f"批次緩衝溢位，丟棄最舊 {dropped} 筆（DB 可能持續不可用）")
            if len(self._buffer) >= settings.batch_size:
                await self._flush_locked()

    async def flush(self) -> None:
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> bool:
        """實際寫入；失敗時資料退回 buffer 前置，回傳是否成功。呼叫者須持有 _lock。"""
        if not self._buffer:
            return True
        pending = self._buffer
        self._buffer = []
        self._last_flush = time.monotonic()
        try:
            async with AsyncSessionLocal() as session:
                session.add_all([RealtimeData(**row) for row in pending])
                await session.commit()
            logger.debug(f"批次寫入 {len(pending)} 筆即時資料")
            return True
        except Exception as exc:
            # 失敗不丟棄：退回 buffer 前置，下輪重試
            self._buffer[:0] = pending
            logger.warning(f"批次寫入失敗，{len(pending)} 筆退回緩衝待重試：{exc}")
            return False

    async def _run(self) -> None:
        """獨立背景 loop：定期依時間間隔觸發 flush。"""
        logger.info("批次寫入器 flush loop 啟動")
        while self._running:
            await asyncio.sleep(settings.batch_interval_seconds)
            try:
                async with self._lock:
                    # 二次時間檢查（非冗餘）：sleep 期間 add() 可能已因達筆數門檻 flush 並
                    # 更新 _last_flush，此時距上次 flush 未滿 interval，不應重複觸發。
                    # 僅在「buffer 有資料」且「確實已過 interval」時才 flush。
                    if self._buffer and (
                        time.monotonic() - self._last_flush >= settings.batch_interval_seconds
                    ):
                        await self._flush_locked()
            except Exception as exc:
                logger.error(f"批次 flush loop 發生例外（繼續運行）：{exc}")

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
        await self.flush()  # 關閉前最終 flush
        logger.info("批次寫入器已停止")


batch_writer = BatchWriter()
