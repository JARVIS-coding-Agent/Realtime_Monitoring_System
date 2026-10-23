"""US2 資料管理測試：CRUD 契約與擁有者權限規則。"""
import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, username, role_cannot_set=True):
    """註冊一個 user（預設角色 user）並回傳 token。"""
    await client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "Passw0rd!"},
    )
    login = await client.post(
        "/api/auth/login", data={"username": username, "password": "Passw0rd!"}
    )
    return login.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _make_admin(session_factory, username):
    """直接在 DB 將某使用者設為 admin。"""
    from sqlalchemy import select
    from app.models.enums import Role
    from app.models.user import User

    async with session_factory() as s:
        user = await s.scalar(select(User).where(User.username == username))
        user.role = Role.admin
        await s.commit()


async def test_create_and_get(client):
    token = await _register(client, "u1")
    resp = await client.post(
        "/api/data",
        json={"title": "CPU", "value": 42.0, "category": "cpu"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    rid = resp.json()["id"]
    got = await client.get(f"/api/data/{rid}", headers=_auth(token))
    assert got.status_code == 200
    assert got.json()["title"] == "CPU"


async def test_list_pagination_filter_sort(client):
    token = await _register(client, "u2")
    for i in range(5):
        await client.post(
            "/api/data",
            json={"title": f"t{i}", "value": float(i), "category": "cpu" if i % 2 else "mem"},
            headers=_auth(token),
        )
    resp = await client.get(
        "/api/data?category=cpu&sort_by=value&order=asc&page=1&page_size=10",
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(item["category"] == "cpu" for item in body["items"])


async def test_non_owner_cannot_update_or_delete(client):
    owner_token = await _register(client, "owner")
    created = await client.post(
        "/api/data",
        json={"title": "x", "value": 1.0, "category": "cpu"},
        headers=_auth(owner_token),
    )
    rid = created.json()["id"]

    other_token = await _register(client, "intruder")
    upd = await client.put(
        f"/api/data/{rid}", json={"value": 99.0}, headers=_auth(other_token)
    )
    assert upd.status_code == 403
    dele = await client.delete(f"/api/data/{rid}", headers=_auth(other_token))
    assert dele.status_code == 403


async def test_owner_can_update(client):
    token = await _register(client, "owner2")
    created = await client.post(
        "/api/data",
        json={"title": "x", "value": 1.0, "category": "cpu"},
        headers=_auth(token),
    )
    rid = created.json()["id"]
    upd = await client.put(f"/api/data/{rid}", json={"value": 99.0}, headers=_auth(token))
    assert upd.status_code == 200
    assert upd.json()["value"] == 99.0


async def test_admin_can_modify_others(client, session_factory):
    owner_token = await _register(client, "owner3")
    created = await client.post(
        "/api/data",
        json={"title": "x", "value": 1.0, "category": "cpu"},
        headers=_auth(owner_token),
    )
    rid = created.json()["id"]

    admin_token = await _register(client, "boss")
    await _make_admin(session_factory, "boss")
    # 重新登入取得含 admin role 的 token
    login = await client.post("/api/auth/login", data={"username": "boss", "password": "Passw0rd!"})
    admin_token = login.json()["access_token"]

    upd = await client.put(f"/api/data/{rid}", json={"value": 77.0}, headers=_auth(admin_token))
    assert upd.status_code == 200


async def test_viewer_cannot_create(client, session_factory):
    from sqlalchemy import select
    from app.models.enums import Role
    from app.models.user import User

    await _register(client, "spectator")
    async with session_factory() as s:
        user = await s.scalar(select(User).where(User.username == "spectator"))
        user.role = Role.viewer
        await s.commit()
    login = await client.post(
        "/api/auth/login", data={"username": "spectator", "password": "Passw0rd!"}
    )
    token = login.json()["access_token"]
    resp = await client.post(
        "/api/data", json={"title": "x", "value": 1.0, "category": "cpu"}, headers=_auth(token)
    )
    assert resp.status_code == 403


# === US5 批量導入 ===

async def test_import_csv_success(client):
    token = await _register(client, "importer")
    csv = b"title,value,category\nCPU,10.5,cpu\nMEM,20.0,memory\n"
    resp = await client.post(
        "/api/data/import",
        files={"file": ("data.csv", csv, "text/csv")},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success_count"] == 2
    assert body["failed_count"] == 0


async def test_import_partial_errors(client):
    token = await _register(client, "importer2")
    # 第二列 value 非數字 → 應失敗並回報
    csv = b"title,value,category\nOK,10.5,cpu\nBAD,notnum,mem\n"
    resp = await client.post(
        "/api/data/import",
        files={"file": ("data.csv", csv, "text/csv")},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success_count"] == 1
    assert body["failed_count"] == 1
    assert body["errors"][0]["row"] == 2


async def test_import_viewer_forbidden(client, session_factory):
    from sqlalchemy import select
    from app.models.enums import Role
    from app.models.user import User

    await _register(client, "viewer_imp")
    async with session_factory() as s:
        user = await s.scalar(select(User).where(User.username == "viewer_imp"))
        user.role = Role.viewer
        await s.commit()
    login = await client.post(
        "/api/auth/login", data={"username": "viewer_imp", "password": "Passw0rd!"}
    )
    token = login.json()["access_token"]
    csv = b"title,value,category\nCPU,10.5,cpu\n"
    resp = await client.post(
        "/api/data/import",
        files={"file": ("data.csv", csv, "text/csv")},
        headers=_auth(token),
    )
    assert resp.status_code == 403



# === H4：NaN / Infinity 輸入驗證 ===


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
async def test_create_rejects_non_finite_via_api(client, bad):
    """真實 API regression：裸 NaN/Infinity 經 POST /api/data 應回 422。

    Python 的 json 解析（starlette 底層）預設接受非標準字面值 NaN/Infinity，
    因此這類輸入會通過 JSON parse 進到 Pydantic，由 value 的 field_validator 擋下。
    這也驗證 FastAPI 回傳 422 時 error detail 能被正常序列化，不會因 input
    含非有限數而意外噴 500。
    """
    # 帳號名需唯一：strip('-') 會讓 Infinity 與 -Infinity 碰撞，改用 replace 保留區別
    token = await _register(client, f"nan_{bad.replace('-', 'neg').lower()}")
    # 手動組非標準 JSON（httpx 的 json= 等同 Python json.dumps(allow_nan=True)）
    body = f'{{"title": "x", "value": {bad}, "category": "cpu"}}'
    resp = await client.post(
        "/api/data",
        content=body,
        headers={**_auth(token), "Content-Type": "application/json"},
    )
    assert resp.status_code == 422, resp.text
    # error detail 必須可被 JSON 序列化（回應成功解析即證明未噴 500）
    assert "detail" in resp.json()


async def test_import_rejects_nan_row(client):
    token = await _register(client, "nanimporter")
    # CSV 內含 NaN 值的列應被驗證擋下（計入 failed）
    csv = b"title,value,category\nOK,10.5,cpu\nBAD,NaN,cpu\n"
    resp = await client.post(
        "/api/data/import",
        files={"file": ("data.csv", csv, "text/csv")},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success_count"] == 1
    assert body["failed_count"] == 1
