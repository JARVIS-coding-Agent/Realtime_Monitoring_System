"""後端 REST API 客戶端。"""
import os

import httpx
import streamlit as st

from state import clear_auth, get_token

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _headers() -> dict:
    token = get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _handle(resp: httpx.Response):
    if resp.status_code == 401:
        clear_auth()
        raise ApiError(401, "登入已過期，請重新登入。")
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise ApiError(resp.status_code, str(detail))
    return resp


def login(username: str, password: str) -> dict:
    with httpx.Client(base_url=API_BASE_URL, timeout=10) as c:
        resp = c.post("/api/auth/login", data={"username": username, "password": password})
    return _handle(resp).json()


def register(username: str, email: str, password: str) -> dict:
    with httpx.Client(base_url=API_BASE_URL, timeout=10) as c:
        resp = c.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": password},
        )
    return _handle(resp).json()


def get_json(path: str, params: dict | None = None):
    with httpx.Client(base_url=API_BASE_URL, timeout=30) as c:
        resp = c.get(path, params=params, headers=_headers())
    return _handle(resp).json()


def post_json(path: str, json: dict):
    with httpx.Client(base_url=API_BASE_URL, timeout=30) as c:
        resp = c.post(path, json=json, headers=_headers())
    return _handle(resp).json()


def put_json(path: str, json: dict):
    with httpx.Client(base_url=API_BASE_URL, timeout=30) as c:
        resp = c.put(path, json=json, headers=_headers())
    return _handle(resp).json()


def delete(path: str):
    with httpx.Client(base_url=API_BASE_URL, timeout=30) as c:
        resp = c.delete(path, headers=_headers())
    return _handle(resp)


def upload_file(path: str, filename: str, content: bytes):
    with httpx.Client(base_url=API_BASE_URL, timeout=60) as c:
        resp = c.post(path, files={"file": (filename, content)}, headers=_headers())
    return _handle(resp).json()


def get_bytes(path: str, params: dict | None = None) -> bytes:
    with httpx.Client(base_url=API_BASE_URL, timeout=60) as c:
        resp = c.get(path, params=params, headers=_headers())
    return _handle(resp).content
