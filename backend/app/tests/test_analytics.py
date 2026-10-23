"""US4 資料分析測試：stats、aggregate、export、trend（trend 需 MariaDB）。"""
import os

import pytest

pytestmark = pytest.mark.asyncio

_IS_MARIADB = "mysql" in os.getenv("TEST_DATABASE_URL", "")


async def _setup_data(client, session_factory):
    await client.post(
        "/api/auth/register",
        json={"username": "analyst", "email": "analyst@example.com", "password": "Passw0rd!"},
    )
    login = await client.post(
        "/api/auth/login", data={"username": "analyst", "password": "Passw0rd!"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(4):
        await client.post(
            "/api/data",
            json={"title": f"t{i}", "value": float(i * 10), "category": "cpu" if i < 2 else "mem"},
            headers=headers,
        )
    return headers


async def test_stats(client, session_factory):
    headers = await _setup_data(client, session_factory)
    resp = await client.get("/api/analytics/stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 4
    assert body["sum"] == 60.0  # 0+10+20+30
    assert body["min"] == 0.0
    assert body["max"] == 30.0


async def test_aggregate(client, session_factory):
    headers = await _setup_data(client, session_factory)
    resp = await client.get("/api/analytics/aggregate", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    cats = {item["category"]: item for item in body}
    assert cats["cpu"]["count"] == 2
    assert cats["mem"]["count"] == 2


async def test_export_returns_xlsx(client, session_factory):
    headers = await _setup_data(client, session_factory)
    resp = await client.get("/api/analytics/export", headers=headers)
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
    assert len(resp.content) > 0


async def test_analytics_requires_auth(client):
    resp = await client.get("/api/analytics/stats")
    assert resp.status_code == 401


async def test_trend(client, session_factory):
    # trend 已跨方言（MariaDB date_format / SQLite strftime），兩種 DB 皆執行（issue #4）
    headers = await _setup_data(client, session_factory)
    resp = await client.get("/api/analytics/trend?interval=day", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # _setup_data 建立 4 筆同日資料 → day 分桶應聚為 1 桶、count=4
    assert len(body) == 1
    assert body[0]["count"] == 4


async def test_trend_empty_range_returns_empty(client, session_factory):
    # 時間範圍無資料應回空陣列（空狀態，非錯誤）
    headers = await _setup_data(client, session_factory)
    resp = await client.get(
        "/api/analytics/trend?interval=day&start=1990-01-01T00:00:00&end=1990-01-02T00:00:00",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []
