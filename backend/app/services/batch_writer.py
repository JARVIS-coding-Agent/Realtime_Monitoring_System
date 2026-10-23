"""即時資料批次寫入器：緩衝累積，依筆數或獨立 timer 觸發批次寫入。

設計（issue #3）：
- 獨立背景 flush loop：依 `batch_interval_seconds` 定期 flush，不依賴 `add()` 被呼叫，
  故低流量/閒置時尾端資料仍會被寫入。
- `add()` 僅在達筆數門檻時即時 flush（降低延遲）。
- flush 失敗時資料退回 buffer（前置），下輪重試而非靜默遺失；buffer 有上限，
  超過時丟棄最舊並告警（輕量 dead-letter，避免記憶體無限成長）。
- 優雅停止：stop() 不取消正在執行的 flush（避免 commit 已套用卻 requeue 造成
  重複寫入——RealtimeData 無唯一鍵，無法去重）。改用 event 喚醒 sleep 中的 loop，
  讓 in-flight flush 自然完成後才結束，再做最終 flush。兼顧「不遺失」與「不重複」。
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
        # 用於喚醒 sleep 中的 flush loop（stop 時提早觸發最終迴圈，取代 cancel）
        self._wakeup = asyncio.Event()

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
        """獨立背景 loop：依時間間隔觸發 flush；stop 時經 _wakeup 提早喚醒並結束。

        以 wait_for(_wakeup, timeout=interval) 取代純 sleep：
        - 逾時（interval 到）→ 正常定期 flush。
        - 被 _wakeup 喚醒（stop 觸發）→ 立即做最後一次 flush 後結束，不必空等整個 interval。
        不使用 task.cancel()：若取消正好打在 commit 已套用、client 未收回應之際，
        requeue 會導致最終 flush 重複寫入（無唯一鍵無法去重）。故改讓 in-flight flush
        自然完成。
        """
        logger.info("批次寫入器 flush loop 啟動")
        while self._running:
            try:
                await asyncio.wait_for(self._wakeup.wait(), timeout=settings.batch_interval_seconds)
            except asyncio.TimeoutError:
                pass  # interval 到，正常觸發
            self._wakeup.clear()
            try:
                async with self._lock:
                    # 停止中：無條件 flush 殘留；運行中：達時間間隔才 flush。
                    # （二次時間檢查非冗餘：_wakeup 期間 add() 可能剛因筆數門檻 flush 並
                    #  更新 _last_flush，此時距上次 flush 未滿 interval，不應重複觸發。）
                    should_flush = self._buffer and (
                        not self._running
                        or time.monotonic() - self._last_flush >= settings.batch_interval_seconds
                    )
                    if should_flush:
                        await self._flush_locked()
            except Exception as exc:
                logger.error(f"批次 flush loop 發生例外（繼續運行）：{exc}")

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._wakeup.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        self._wakeup.set()  # 喚醒 sleep 中的 loop，使其跑完最後一輪後結束
        if self._task:
            try:
                # 等 loop 自然收尾：若正有 in-flight flush，會等它完成而非中途取消。
                await self._task
            except Exception as exc:
                logger.error(f"等待 flush loop 結束時發生例外：{exc}")
        # 防禦性落地：正常情況 _run() 最後一輪（not self._running 分支）已清空 buffer，
        # 此 flush 通常為空。保留作為 safety net，涵蓋 loop 未啟動、或最後一輪 flush
        # 失敗退回等邊角情形，確保停止時盡力把殘留資料寫出。
        await self.flush()
        logger.info("批次寫入器已停止")


batch_writer = BatchWriter()
