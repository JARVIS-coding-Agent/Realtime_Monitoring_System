"""端到端 API 驗證工具（對執行中的後端）。

用途：`docker compose up -d` 後，驗證主要使用者流程與權限控制是否正常。
此為手動驗證腳本（非 pytest 單元測試），需要運行中的服務。

用法：
    # 預設對 http://localhost:8000，使用 .env.example 的種子帳號密碼
    python scripts/e2e_verify.py

    # 自訂位址與帳密（環境變數覆寫）
    API_BASE_URL=http://localhost:8000 \
    ADMIN_PASSWORD=... USER_PASSWORD=... VIEWER_PASSWORD=... \
        python scripts/e2e_verify.py

離開碼：0 = 全部通過；1 = 有項目失敗（適合用於 CI/腳本串接）。
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "Admin@12345")
VIEWER_PW = os.getenv("VIEWER_PASSWORD", "Viewer@12345")

_results: list[bool] = []


def _req(method, path, token=None, data=None, form=None):
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _check(label, status, expected):
    ok = status == expected
    _results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: got={status} expected={expected}")


def main() -> int:
    s, b = _req("GET", "/health")
    _check("health", s, 200)

    s, b = _req("POST", "/api/auth/login", form={"username": "admin", "password": ADMIN_PW})
    _check("admin login", s, 200)
    admin = json.loads(b)["access_token"] if s == 200 else None

    s, b = _req("GET", "/api/auth/me", token=admin)
    _check("GET /api/auth/me", s, 200)

    s, b = _req("POST", "/api/data", token=admin,
                data={"title": "CPU", "value": 42.5, "category": "cpu"})
    _check("POST /api/data create", s, 201)
    rec_id = json.loads(b)["id"] if s == 201 else None

    s, b = _req("GET", "/api/data", token=admin)
    _check("GET /api/data list", s, 200)

    if rec_id:
        s, b = _req("PUT", f"/api/data/{rec_id}", token=admin, data={"value": 99.9})
        _check("PUT /api/data/{id} update", s, 200)

    s, b = _req("GET", "/api/analytics/stats", token=admin)
    _check("GET /api/analytics/stats", s, 200)

    s, b = _req("GET", "/api/analytics/aggregate", token=admin)
    _check("GET /api/analytics/aggregate", s, 200)

    s, b = _req("GET", "/api/admin/users", token=admin)
    _check("GET /api/admin/users", s, 200)

    s, b = _req("GET", "/api/realtime/history", token=admin)
    _check("GET /api/realtime/history", s, 200)

    s, b = _req("POST", "/api/auth/login", form={"username": "viewer", "password": VIEWER_PW})
    _check("viewer login", s, 200)
    viewer = json.loads(b)["access_token"] if s == 200 else None

    s, b = _req("POST", "/api/data", token=viewer,
                data={"title": "x", "value": 1.0, "category": "cpu"})
    _check("viewer create denied (403)", s, 403)

    s, b = _req("GET", "/api/admin/users", token=viewer)
    _check("viewer access admin denied (403)", s, 403)

    s, b = _req("GET", "/api/auth/me")
    _check("no-token denied (401)", s, 401)

    passed = sum(_results)
    total = len(_results)
    print(f"\nTOTAL {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
