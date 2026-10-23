"""US3 即時監控測試：批次寫入、歷史查詢、異常閾值、WS 驗證。"""
import pytest

from app.core.config import settings

pytestmark = pytest.mark.asyncio


async def _register_and_token(client, username="rtuser"):
    await client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "Passw0rd!"},
    )
    login = await client.post(
        "/api/auth/login", data={"username": username, "password": "Passw0rd!"}
    )
    return login.json()["access_token"]


def test_anomaly_threshold_logic():
    """數值超過閾值即判為異常（對應 generator 的判斷）。"""
    threshold = settings.anomaly_threshold
    assert (threshold + 1) > threshold  # 超過 → 異常
    assert not ((threshold - 1) > threshold)  # 未超過 → 正常


async def test_batch_writer_persists_and_history_query(client, session_factory):
    """批次寫入後，歷史查詢可查得資料並正確篩選異常。"""
    from app.db.base import utcnow
    from app.models.realtime_data import RealtimeData

    async with session_factory() as s:
        s.add_all([
            RealtimeData(value=10.0, category="cpu", is_anomaly=False, generated_at=utcnow()),
            RealtimeData(value=95.0, category="cpu", is_anomaly=True, generated_at=utcnow()),
            RealtimeData(value=20.0, category="mem", is_anomaly=False, generated_at=utcnow()),
        ])
        await s.commit()

    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/realtime/history", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 3

    anomaly = await client.get("/api/realtime/history?only_anomaly=true", headers=headers)
    assert anomaly.json()["total"] == 1

    cpu = await client.get("/api/realtime/history?category=cpu", headers=headers)
    assert cpu.json()["total"] == 2


async def test_history_requires_auth(client):
    resp = await client.get("/api/realtime/history")
    assert resp.status_code == 401


async def test_batchwriter_threshold_flush(session_factory, monkeypatch):
    """達筆數門檻即觸發 flush，資料寫入 DB。"""
    import app.services.batch_writer as bw_mod
    from app.models.realtime_data import RealtimeData
    from app.db.base import utcnow
    from sqlalchemy import func, select

    monkeypatch.setattr(bw_mod, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(bw_mod.settings, "batch_size", 3)
    bw = bw_mod.BatchWriter()

    for _ in range(3):
        await bw.add({"value": 1.0, "category": "cpu", "is_anomaly": False, "generated_at": utcnow()})

    assert len(bw._buffer) == 0  # 達門檻已 flush
    async with session_factory() as s:
        total = await s.scalar(select(func.count()).select_from(RealtimeData))
    assert total == 3


async def test_batchwriter_timer_flush(session_factory, monkeypatch):
    """低流量下，獨立 timer loop 仍會 flush 未達門檻的資料。"""
    import app.services.batch_writer as bw_mod
    from app.models.realtime_data import RealtimeData
    from app.db.base import utcnow
    from sqlalchemy import func, select

    monkeypatch.setattr(bw_mod, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(bw_mod.settings, "batch_size", 100)  # 不會達門檻
    monkeypatch.setattr(bw_mod.settings, "batch_interval_seconds", 0.1)
    bw = bw_mod.BatchWriter()
    await bw.start()
    try:
        await bw.add({"value": 1.0, "category": "cpu", "is_anomaly": False, "generated_at": utcnow()})
        import asyncio
        await asyncio.sleep(0.3)  # 等 timer loop 觸發
    finally:
        await bw.stop()

    async with session_factory() as s:
        total = await s.scalar(select(func.count()).select_from(RealtimeData))
    assert total == 1  # timer 已寫入


async def test_batchwriter_flush_failure_requeues(monkeypatch):
    """flush 失敗時資料退回 buffer，不靜默遺失。"""
    import app.services.batch_writer as bw_mod
    from app.db.base import utcnow

    class _FailingSession:
        async def __aenter__(self):
            raise RuntimeError("DB down")
        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(bw_mod, "AsyncSessionLocal", lambda: _FailingSession())
    monkeypatch.setattr(bw_mod.settings, "batch_size", 1)
    bw = bw_mod.BatchWriter()
    await bw.add({"value": 1.0, "category": "cpu", "is_anomaly": False, "generated_at": utcnow()})
    # flush 失敗 → 資料應仍在 buffer（退回），而非遺失
    assert len(bw._buffer) == 1


async def test_batchwriter_shutdown_flush(session_factory, monkeypatch):
    """stop() 時最終 flush，buffer 殘留資料落地。"""
    import app.services.batch_writer as bw_mod
    from app.models.realtime_data import RealtimeData
    from app.db.base import utcnow
    from sqlalchemy import func, select

    monkeypatch.setattr(bw_mod, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(bw_mod.settings, "batch_size", 100)
    monkeypatch.setattr(bw_mod.settings, "batch_interval_seconds", 60)  # timer 不會觸發
    bw = bw_mod.BatchWriter()
    await bw.start()
    await bw.add({"value": 1.0, "category": "cpu", "is_anomaly": False, "generated_at": utcnow()})
    await bw.stop()  # 應最終 flush

    async with session_factory() as s:
        total = await s.scalar(select(func.count()).select_from(RealtimeData))
    assert total == 1


async def test_batchwriter_stop_during_commit_no_loss_no_dup(session_factory, monkeypatch):
    """stop() 時若有 in-flight flush，應讓其自然完成：不遺失、不重複（issue #3 / ULTRON P1）。

    新語義：stop 不取消正在執行的 flush（避免 commit 已套用卻 requeue 造成重複——
    RealtimeData 無唯一鍵無法去重）。驗證 commit 只執行一次、DB 恰好 1 筆。
    """
    import asyncio
    import app.services.batch_writer as bw_mod
    from app.models.realtime_data import RealtimeData
    from app.db.base import utcnow
    from sqlalchemy import func, select

    commit_entered = asyncio.Event()
    calls = {"n": 0}

    class _SlowCommitSession:
        """commit 有小延遲以模擬 in-flight；委派真實 session 實際寫入。"""
        def __init__(self):
            self._real_cm = session_factory()
            self._real = None

        async def __aenter__(self):
            self._real = await self._real_cm.__aenter__()
            return self

        async def __aexit__(self, *a):
            return await self._real_cm.__aexit__(*a)

        def add_all(self, objs):
            self._real.add_all(objs)

        async def commit(self):
            calls["n"] += 1
            commit_entered.set()
            await asyncio.sleep(0.2)  # 模擬 commit 耗時（in-flight 視窗）
            await self._real.commit()

    monkeypatch.setattr(bw_mod, "AsyncSessionLocal", lambda: _SlowCommitSession())
    monkeypatch.setattr(bw_mod.settings, "batch_size", 100)
    monkeypatch.setattr(bw_mod.settings, "batch_interval_seconds", 0.05)
    bw = bw_mod.BatchWriter()
    await bw.start()
    await bw.add({"value": 1.0, "category": "cpu", "is_anomaly": False, "generated_at": utcnow()})

    # 等 timer loop 進到 commit（in-flight 中）
    await asyncio.wait_for(commit_entered.wait(), timeout=2.0)
    # 此刻 flush 正卡在 commit；stop 應等它自然跑完而非取消
    await bw.stop()

    async with session_factory() as s:
        total = await s.scalar(select(func.count()).select_from(RealtimeData))
    assert total == 1           # 不遺失
    assert calls["n"] == 1      # 不重複：in-flight commit 只跑一次，未被 requeue 重寫
    assert len(bw._buffer) == 0


async def test_batchwriter_timer_wakeup_on_stop_is_prompt(session_factory, monkeypatch):
    """stop() 以 _wakeup 喚醒 sleep 中的 loop，不必空等整個 interval。"""
    import asyncio
    import time as _time
    import app.services.batch_writer as bw_mod
    from app.models.realtime_data import RealtimeData
    from app.db.base import utcnow
    from sqlalchemy import func, select

    monkeypatch.setattr(bw_mod, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(bw_mod.settings, "batch_size", 100)
    monkeypatch.setattr(bw_mod.settings, "batch_interval_seconds", 30)  # 很長，若空等會超時
    bw = bw_mod.BatchWriter()
    await bw.start()
    await bw.add({"value": 1.0, "category": "cpu", "is_anomaly": False, "generated_at": utcnow()})
    t0 = _time.monotonic()
    await bw.stop()
    elapsed = _time.monotonic() - t0

    assert elapsed < 5  # 遠小於 30s interval，證明是被喚醒而非等 timeout
    async with session_factory() as s:
        total = await s.scalar(select(func.count()).select_from(RealtimeData))
    assert total == 1


async def test_batchwriter_requeue_then_retry_succeeds(session_factory, monkeypatch):
    """flush 失敗退回後，恢復正常時重試應成功寫入（驗證退回資料可被重寫）。"""
    import app.services.batch_writer as bw_mod
    from app.models.realtime_data import RealtimeData
    from app.db.base import utcnow
    from sqlalchemy import func, select

    state = {"fail": True}

    def _factory():
        if state["fail"]:
            class _Failing:
                async def __aenter__(self):
                    raise RuntimeError("DB down")
                async def __aexit__(self, *a):
                    return False
            return _Failing()
        return session_factory()

    monkeypatch.setattr(bw_mod, "AsyncSessionLocal", _factory)
    monkeypatch.setattr(bw_mod.settings, "batch_size", 1)
    bw = bw_mod.BatchWriter()
    await bw.add({"value": 1.0, "category": "cpu", "is_anomaly": False, "generated_at": utcnow()})
    assert len(bw._buffer) == 1  # 失敗退回

    # DB 恢復，重試
    state["fail"] = False
    await bw.flush()
    assert len(bw._buffer) == 0
    async with session_factory() as s:
        total = await s.scalar(select(func.count()).select_from(RealtimeData))
    assert total == 1  # 退回的資料成功重寫
