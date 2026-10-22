"""US1 認證測試：契約（register/login/me）與 security 單元測試。"""
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.asyncio


# === 單元測試：security（T018）===

def test_password_hash_and_verify():
    h = hash_password("Secret@123")
    assert h != "Secret@123"
    assert verify_password("Secret@123", h) is True
    assert verify_password("wrong", h) is False


def test_jwt_roundtrip():
    token = create_access_token(subject=42, role="admin")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_jwt_invalid_returns_none():
    assert decode_access_token("not-a-valid-token") is None


# === 契約測試：auth 端點（T017）===

async def test_register_success(client):
    resp = await client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "Passw0rd!"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "user"
    assert "hashed_password" not in body


async def test_register_duplicate_conflict(client):
    payload = {"username": "bob", "email": "bob@example.com", "password": "Passw0rd!"}
    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201
    dup = await client.post("/api/auth/register", json=payload)
    assert dup.status_code == 409


async def test_login_success_and_me(client):
    await client.post(
        "/api/auth/register",
        json={"username": "carol", "email": "carol@example.com", "password": "Passw0rd!"},
    )
    login = await client.post(
        "/api/auth/login",
        data={"username": "carol", "password": "Passw0rd!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "carol"


async def test_login_wrong_password_unified_401(client):
    await client.post(
        "/api/auth/register",
        json={"username": "dave", "email": "dave@example.com", "password": "Passw0rd!"},
    )
    resp = await client.post(
        "/api/auth/login",
        data={"username": "dave", "password": "WrongPass!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "帳號或密碼錯誤"


async def test_me_without_token_401(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
