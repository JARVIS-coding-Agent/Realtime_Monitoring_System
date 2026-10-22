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


@pytest.mark.skipif(not _IS_MARIADB, reason="trend 使用 date_format，需 MariaDB")
async def test_trend(client, session_factory):
    headers = await _setup_data(client, session_factory)
    resp = await client.get("/api/analytics/trend?interval=day", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
