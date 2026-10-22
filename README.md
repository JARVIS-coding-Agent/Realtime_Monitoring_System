# 即時資料分析與監控系統

一套容器化的全端即時資料分析與監控系統，提供 RESTful API、WebSocket 即時推送、JWT 認證與角色權限、資料分析與系統管理。

## 專案介紹

本系統模擬即時資料的產生、推送、持久化與分析，涵蓋五大模組：

- **使用者管理**：註冊、登入（JWT）、三種角色（Admin／User／Viewer）與權限控制
- **資料管理**：資料記錄 CRUD、分頁／篩選／排序、批量導入（CSV／JSON）
- **即時監控**：每秒產生模擬資料，透過 WebSocket 即時推送，前端即時圖表更新並標記異常
- **資料分析**：統計（總計／平均／最大／最小）、分類聚合、時間趨勢、Excel 匯出
- **系統管理**（Admin）：使用者列表與角色管理、系統日誌、資料庫狀態、即時資料歷史

## 技術棧

| 層 | 技術 |
|----|------|
| 後端 | FastAPI、Uvicorn（非同步、REST + WebSocket、Swagger 自動文件） |
| 認證 | python-jose（JWT）、passlib[bcrypt]（密碼雜湊） |
| 驗證 | Pydantic v2 |
| ORM | SQLAlchemy 2.0（async）— **全程 ORM，禁止原生 SQL** |
| DB 驅動 | asyncmy（MariaDB 非同步） |
| 遷移 | Alembic |
| 資料庫 | MariaDB 11.7（連接池、Volume 持久化） |
| 前端 | Streamlit（多頁面、Session 狀態） |
| 圖表 | Plotly |
| 匯出 | pandas、openpyxl |
| 部署 | Docker、Docker Compose（多階段構建） |
| 測試 | pytest、pytest-asyncio、httpx |

## 系統架構

詳見 [`docs/architecture.md`](docs/architecture.md)。

```
┌──────────────┐  HTTP/REST   ┌───────────────────────┐
│  Streamlit   │ ───────────► │     FastAPI 後端       │
│  前端 (8501) │ ◄─WebSocket─ │       (8000)           │
└──────────────┘              │  REST + WS + JWT       │
                              │  SQLAlchemy(async) ORM │
                              └───────────┬───────────┘
                                          │ asyncmy
                              ┌───────────▼───────────┐
                              │   MariaDB 11.7 (3306)  │
                              │   + Volume 持久化       │
                              └───────────────────────┘
背景任務：每秒生成即時資料 → WebSocket 廣播 + 批次寫入 DB；定期保留清理
```

## Docker 部署（建議）

```bash
# 1. 由範本建立 .env 並填入值（至少修改 JWT_SECRET 與各密碼）
cp .env.example .env

# 2. 一鍵啟動（backend 會自動跑 Alembic 遷移 + 種子資料）
docker-compose up --build
```

- 前端：http://localhost:8501
- 後端 Swagger API 文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

啟動順序：`db`（healthcheck 通過）→ `backend`（遷移 + 種子）→ `frontend`。

## 本地開發（不使用 Docker）

需求：Python 3.12、執行中的 MariaDB 11.7。

```bash
# --- 後端 ---
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 設定環境變數（參考 .env.example），確保 DB 連線正確
alembic upgrade head          # 建立資料表
python -m app.db.init_db      # 建立種子測試帳號
uvicorn app.main:app --reload # 啟動後端（http://localhost:8000）

# --- 前端（另開終端）---
cd frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 設定 API_BASE_URL=http://localhost:8000、WS_BASE_URL=ws://localhost:8000
streamlit run app/Home.py     # 啟動前端（http://localhost:8501）
```

## API 文件

啟動後端後開啟 Swagger UI：**http://localhost:8000/docs**

主要端點：

- `POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/me`
- `GET/POST /api/data`、`GET/PUT/DELETE /api/data/{id}`、`POST /api/data/import`
- `GET /api/analytics/stats | aggregate | trend | export`
- `WS /ws/realtime`、`GET /api/realtime/history`
- `GET /api/admin/users`、`PUT /api/admin/users/{id}/role`、`GET /api/admin/logs`、`GET /api/admin/db-status`
- `GET /health`

## 測試帳號

系統初始化時由 `app/db/init_db.py` 建立以下種子帳號（預設密碼見 `.env.example`，正式環境請務必修改）：

| 帳號 | 密碼 | 角色 | 權限 |
|------|------|------|------|
| admin | Admin@12345 | Admin | 全部功能，含系統管理 |
| user | User@12345 | User | 建立／管理自己的資料、批量導入 |
| viewer | Viewer@12345 | Viewer | 僅瀏覽資料與圖表 |

## 權限矩陣

| 操作 | Admin | User | Viewer |
|------|:-----:|:----:|:------:|
| 瀏覽資料／分析圖表 | ✅ | ✅ | ✅ |
| 建立／更新刪除自己的資料 | ✅ | ✅ | ❌ |
| 更新／刪除他人資料 | ✅ | ❌ | ❌ |
| 批量導入 | ✅ | ✅ | ❌ |
| 使用者／日誌／DB 狀態管理 | ✅ | ❌ | ❌ |

## 測試

```bash
cd backend
pytest -q
```

整合測試預設使用 in-memory SQLite 快速驗證邏輯；若要對 MariaDB 執行（貼近正式環境），設定 `TEST_DATABASE_URL`，例如：

```bash
TEST_DATABASE_URL="mysql+asyncmy://user:pass@localhost:3306/test_db" pytest -q
```

## 開發方法論

本專案採 Spec-Driven Development（規格驅動開發），完整的規格、計畫、資料模型、API 契約與任務拆解見 [`specs/`](specs/) 目錄，開發歷程依使用者故事分階段提交。

## 專案結構

```
.
├── backend/            # FastAPI 後端（app/、alembic/、tests/）
├── frontend/           # Streamlit 前端（app/Home.py、pages/）
├── docs/               # 架構圖、範例 CSV
├── specs/              # 規格與設計文件（Spec-Driven Development）
├── docker-compose.yml
└── .env.example
```
