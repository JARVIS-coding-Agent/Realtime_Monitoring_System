"""US6 系統管理測試：使用者列表、角色管理、最後 Admin 保護、日誌、DB 狀態、授權。"""
import pytest
from sqlalchemy import select

from app.models.enums import Role
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _register(client, username):
    await client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "Passw0rd!"},
    )
    login = await client.post(
        "/api/auth/login", data={"username": username, "password": "Passw0rd!"}
    )
    return login.json()["access_token"]


async def _make_admin_and_token(client, session_factory, username):
    await _register(client, username)
    async with session_factory() as s:
        user = await s.scalar(select(User).where(User.username == username))
        user.role = Role.admin
        await s.commit()
    login = await client.post(
        "/api/auth/login", data={"username": username, "password": "Passw0rd!"}
    )
    return login.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_list_users_admin_only(client, session_factory):
    admin_token = await _make_admin_and_token(client, session_factory, "root")
    await _register(client, "member")
    resp = await client.get("/api/admin/users", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_non_admin_forbidden(client):
    token = await _register(client, "plainuser")
    resp = await client.get("/api/admin/users", headers=_auth(token))
    assert resp.status_code == 403


async def test_change_role_takes_effect(client, session_factory):
    admin_token = await _make_admin_and_token(client, session_factory, "root2")
    await _register(client, "target")
    async with session_factory() as s:
        target = await s.scalar(select(User).where(User.username == "target"))
        target_id = target.id
    resp = await client.put(
        f"/api/admin/users/{target_id}/role",
        json={"role": "admin"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_cannot_demote_last_admin(client, session_factory):
    admin_token = await _make_admin_and_token(client, session_factory, "soleadmin")
    async with session_factory() as s:
        admin = await s.scalar(select(User).where(User.username == "soleadmin"))
        admin_id = admin.id
    resp = await client.put(
        f"/api/admin/users/{admin_id}/role",
        json={"role": "user"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 409


async def test_logs_and_db_status(client, session_factory):
    admin_token = await _make_admin_and_token(client, session_factory, "root3")
    logs = await client.get("/api/admin/logs", headers=_auth(admin_token))
    assert logs.status_code == 200
    assert "items" in logs.json()
    dbs = await client.get("/api/admin/db-status", headers=_auth(admin_token))
    assert dbs.status_code == 200
    assert "connected" in dbs.json()
