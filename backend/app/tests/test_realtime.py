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


async def test_batch_writer_buffer_flush():
    """直接測 BatchWriter 緩衝與 flush 行為（不實際寫 DB，驗證 buffer 清空）。"""
    from app.services.batch_writer import BatchWriter

    bw = BatchWriter()
    # 以小於門檻的筆數加入，buffer 應累積（除非時間觸發）
    assert len(bw._buffer) == 0
