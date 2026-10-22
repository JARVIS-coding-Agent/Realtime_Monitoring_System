# 第二題：即時資料分析與監控系統 — 專案架構與開發計畫

> FastAPI + Streamlit + MariaDB + Docker 的全端即時資料分析與監控系統。

---

## 0. 交付文件清單（必繳，10/26 20:30 前回傳連結）

以下為題目要求的交付項目，本專案必須全部產出：

| # | 交付項目 | 對應檔案/位置 | 狀態 |
|---|----------|--------------|:----:|
| 1 | **完整的專案代碼（上傳至 GitHub）** | 整個 `Q2_Realtime_Monitoring_System/` 專案 repo | ☑ |
| 2 | **README.md**（內容見下方子項） | `README.md` | ☑ |
| 3 | **.env.example 文件** | `.env.example` | ☑ |
| 4 | **至少一個測試資料的 CSV 範例** | `docs/sample_data.csv`（批量導入用範例） | ☑ |
| 5 | **系統架構圖** | `docs/architecture.md` | ☑ |

### README.md 必須包含（但不限於）
- [ ] **專案介紹** — 系統目標、功能概述、五大模組摘要
- [ ] **技術棧說明** — FastAPI、Streamlit、MariaDB 11.7、SQLAlchemy ORM、Docker 等
- [ ] **本地運行步驟** — 不使用 Docker 的本地開發啟動（後端、前端、DB、Alembic 遷移）
- [ ] **Docker 部署指令** — `docker-compose up --build` 等完整容器化部署步驟
- [ ] **API 文件連結** — Swagger UI：`http://localhost:8000/docs`
- [ ] **測試帳號資訊** — 預設種子帳號（Admin / User / Viewer 各一組含密碼）

> 種子測試帳號由 `app/db/init_db.py` 建立，README 需列出帳號、密碼與對應角色。

---

## 1. 系統總覽

一個容器化的即時資料分析與監控系統，提供：
- 後端 **FastAPI**：RESTful API + WebSocket 即時推送
- 前端 **Streamlit**：資料可視化與互動介面
- 資料庫 **MariaDB 11.7**：以 **SQLAlchemy ORM**（禁止原生 SQL）持久化
- **Docker / Docker Compose**：多容器容器化部署
- JWT 認證、角色權限、即時監控、資料分析、系統管理

---

## 2. 技術棧

| 層 | 技術 | 關鍵點 |
|----|------|--------|
| 後端 | FastAPI, Uvicorn | 異步、RESTful CRUD、WebSocket、Swagger 自動文件 |
| 認證 | python-jose (JWT), passlib[bcrypt] | JWT Token、角色權限 (Admin/User/Viewer) |
| 驗證 | Pydantic v2 | 請求/回應 schema 驗證 |
| ORM | SQLAlchemy 2.0 (async) | **全程 ORM，禁止原生 SQL** |
| DB 驅動 | asyncmy | MariaDB 異步連線 |
| 遷移 | Alembic | schema 版本管理 |
| 資料庫 | MariaDB 11.7 | 連接池、Volume 持久化 |
| 前端 | Streamlit | 多頁面、Session 狀態、即時圖表 |
| 圖表 | Plotly / Altair | 折線圖、柱狀圖、趨勢圖 |
| 匯出 | openpyxl / pandas | Excel 下載 |
| 部署 | Docker, Docker Compose | 多階段構建、容器網路、Volume、環境變數 |
| 日誌 | logging / loguru | 錯誤處理與系統日誌 |
| 測試 | pytest, httpx | API 單元/整合測試 |

---

## 3. 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose 網路                      │
│                                                               │
│  ┌───────────────┐   HTTP/REST   ┌──────────────────────┐    │
│  │  Streamlit    │ ────────────► │     FastAPI 後端      │    │
│  │  前端 (8501)  │ ◄──WebSocket─ │       (8000)          │    │
│  │  多頁面/Session│               │  REST + WS + JWT      │    │
│  └───────────────┘               │  SQLAlchemy(async)ORM │    │
│                                   └───────────┬──────────┘    │
│                                               │ asyncmy       │
│                                   ┌───────────▼──────────┐    │
│                                   │   MariaDB 11.7        │    │
│                                   │   (3306) + Volume     │    │
│                                   └──────────────────────┘    │
│                                                               │
│  背景任務：即時資料生成器（每秒）→ WS 推送 + 批次寫入 DB       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 功能模組對照

### 4.1 使用者管理模組
- 使用者註冊
- 登入（JWT Token 發放）
- 角色：Admin / User / Viewer
- 權限控制（不同角色不同操作權限）

### 4.2 資料管理模組
- 建立資料記錄（標題、數值、分類、時間戳…）
- 讀取（分頁、篩選、排序）
- 更新（僅創建者或 Admin）
- 刪除（僅創建者或 Admin）
- 批量導入（CSV / JSON）

### 4.3 即時監控模組
- 模擬即時資料生成器（每秒隨機資料）
- WebSocket 推送即時資料
- 前端即時圖表更新（折線圖、柱狀圖）
- 資料異常告警（數值超過閾值標記）

### 4.4 資料分析模組
- 統計分析（總計、平均、最大、最小）
- 時間範圍查詢
- 分類資料聚合
- 資料趨勢圖表
- 可下載 Excel

### 4.5 系統管理模組（Admin 專用）
- 查看所有使用者列表
- 使用者權限管理
- 系統日誌查詢
- 資料庫狀態監控
- 即時資料的歷史資料查詢

---

## 5. 權限矩陣 (RBAC)

| 操作 | Admin | User | Viewer |
|------|:-----:|:----:|:------:|
| 瀏覽資料 | ✅ | ✅ | ✅ |
| 建立資料 | ✅ | ✅ | ❌ |
| 更新/刪除自己的資料 | ✅ | ✅ | ❌ |
| 更新/刪除他人資料 | ✅ | ❌ | ❌ |
| 批量導入 | ✅ | ✅ | ❌ |
| 查看使用者列表/權限管理 | ✅ | ❌ | ❌ |
| 系統日誌/DB 狀態 | ✅ | ❌ | ❌ |
| 即時監控/分析圖表 | ✅ | ✅ | ✅ |

---

## 6. 資料模型（SQLAlchemy ORM）

```
User
  id (PK), username (uniq), email (uniq), hashed_password,
  role (Enum: admin/user/viewer), is_active, created_at

DataRecord
  id (PK), title, value (float), category (index),
  timestamp (index), owner_id (FK→User.id), created_at, updated_at

RealtimeData        # 即時資料生成器批次寫入
  id (PK), value (float), category, is_anomaly (bool),
  generated_at (index)

SystemLog
  id (PK), level, message, user_id (FK, nullable),
  endpoint, created_at (index)
```

---

## 7. API 設計（RESTful + WebSocket）

```
Auth
  POST   /api/auth/register         註冊
  POST   /api/auth/login            登入 → JWT
  GET    /api/auth/me               目前使用者

Data (CRUD)
  GET    /api/data                  列表（分頁/篩選/排序）
  POST   /api/data                  建立
  GET    /api/data/{id}             取得單筆
  PUT    /api/data/{id}             更新（創建者/Admin）
  DELETE /api/data/{id}             刪除（創建者/Admin）
  POST   /api/data/import           批量導入（CSV/JSON）

Analytics
  GET    /api/analytics/stats       統計（總計/平均/最大/最小）
  GET    /api/analytics/aggregate   分類聚合
  GET    /api/analytics/trend       趨勢
  GET    /api/analytics/export      匯出 Excel

Realtime
  WS     /ws/realtime               即時資料推送
  GET    /api/realtime/history      歷史即時資料查詢

Admin
  GET    /api/admin/users           使用者列表
  PUT    /api/admin/users/{id}/role 權限管理
  GET    /api/admin/logs            系統日誌
  GET    /api/admin/db-status       資料庫狀態

System
  GET    /health                    健康檢查
  GET    /docs                      Swagger UI
```

---

## 8. 專案資料夾結構

```
Q2_Realtime_Monitoring_System/
├── README.md
├── PROJECT_PLAN.md                 # 本文件
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── architecture.md            # 系統架構圖
│   └── sample_data.csv             # 測試資料 CSV 範例
├── backend/
│   ├── Dockerfile                  # 多階段構建
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                    # 遷移腳本
│   └── app/
│       ├── main.py                 # FastAPI 入口
│       ├── core/
│       │   ├── config.py           # 設定（Pydantic Settings）
│       │   ├── security.py         # JWT / 密碼雜湊
│       │   └── logging.py
│       ├── db/
│       │   ├── base.py             # Declarative Base
│       │   ├── session.py          # async engine + 連接池
│       │   └── init_db.py          # 種子資料（測試帳號）
│       ├── models/                 # SQLAlchemy ORM models
│       │   ├── user.py
│       │   ├── data_record.py
│       │   ├── realtime_data.py
│       │   └── system_log.py
│       ├── schemas/                # Pydantic schemas
│       ├── api/
│       │   ├── deps.py             # 依賴注入（current_user/權限）
│       │   └── routers/
│       │       ├── auth.py
│       │       ├── data.py
│       │       ├── analytics.py
│       │       ├── realtime.py     # WebSocket
│       │       └── admin.py
│       ├── services/
│       │   ├── generator.py        # 即時資料生成器（背景任務）
│       │   └── batch_writer.py     # 批次寫入 DB
│       └── tests/
│           ├── test_auth.py
│           ├── test_data.py
│           └── test_analytics.py
└── frontend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── Home.py                 # Streamlit 入口（登入）
        ├── api_client.py           # 串接後端 API
        ├── state.py                # Session 狀態管理
        └── pages/
            ├── 1_📊_即時監控.py
            ├── 2_📋_資料管理.py
            ├── 3_📈_資料分析.py
            └── 4_⚙️_系統管理.py
```

---

## 9. 即時資料流程

```
背景任務 generator.py（每秒）
   │ 產生隨機資料 (value, category)
   │ 判斷 is_anomaly = value > threshold
   ├──► WebSocket 廣播給所有連線前端（即時圖表更新）
   └──► 緩衝區累積 → batch_writer.py 定期/條件觸發批次寫入 MariaDB
                                   │
前端 Streamlit WS 客戶端 ◄─────────┘
   折線圖/柱狀圖即時更新 + 異常標記
```

---

## 10. Docker 部署

- **3 個服務**：`backend`（FastAPI）、`frontend`（Streamlit）、`db`（MariaDB 11.7）
- **多階段 Dockerfile**：builder 階段裝依賴，runtime 階段精簡映像
- **容器網路**：Compose 預設 network，服務間以服務名互連
- **Volume**：MariaDB 資料持久化（`db_data`）
- **環境變數**：以 `.env` 管理（DB 連線、JWT secret、閾值等）
- **啟動順序**：`db` healthcheck → `backend`（跑 Alembic 遷移 + 種子）→ `frontend`

```
docker-compose up --build
# 前端 http://localhost:8501
# 後端 Swagger http://localhost:8000/docs
```

---

## 11. 開發計畫（里程碑）

| 階段 | 工作項目 | 產出 | 預估 |
|------|----------|------|------|
| M1 骨架 | 專案結構、Compose、MariaDB、.env | 可啟動空殼 | 0.5 天 |
| M2 DB/ORM | models、session、Alembic 遷移、種子 | ORM + 測試帳號 | 0.5 天 |
| M3 認證 | 註冊/登入/JWT、角色權限、deps | auth 模組 | 0.5 天 |
| M4 CRUD | 資料 CRUD + 分頁/篩選/排序 + 權限 | data 模組 | 0.5 天 |
| M5 匯入/分析 | CSV/JSON 導入、統計/聚合/趨勢、Excel | analytics 模組 | 0.5 天 |
| M6 即時 | 生成器、WebSocket、批次寫入 | realtime 模組 | 1 天 |
| M7 Admin | 使用者/日誌/DB 狀態/歷史查詢 | admin 模組 | 0.5 天 |
| M8 前端 | Streamlit 多頁面、登入、即時圖表、分析 | frontend | 1.5 天 |
| M9 交付 | README、架構圖、CSV 範例、測試、整合驗證 | 完整交付物 | 1 天 |

---

## 12. 交付物對照（題目要求）

| 題目要求 | 對應產出 |
|---------|---------|
| GitHub 完整代碼 | 整個 `Q2_*` 專案 |
| README.md | 介紹/技術棧/本地運行/Docker 指令/API 文件連結/測試帳號 |
| .env.example | `.env.example` |
| 測試資料 CSV 範例 | `docs/sample_data.csv` |
| 系統架構圖 | `docs/architecture.md` |
| Swagger 文件 | `http://localhost:8000/docs` |
| JWT 認證 | `core/security.py` + `api/routers/auth.py` |
| SQLAlchemy ORM（禁原生 SQL） | `models/` + `db/session.py`（全程 ORM） |
| WebSocket 即時推送 | `api/routers/realtime.py` + `services/generator.py` |

---

## 13. 重點合規檢查（題目硬性要求）

- [x] FastAPI 框架、異步處理
- [x] JWT 認證機制
- [x] RESTful API 設計（CRUD）
- [x] WebSocket 即時推送
- [x] **SQLAlchemy ORM 操作，禁止原生 SQL**
- [x] Pydantic 資料驗證
- [x] Swagger 文件
- [x] 錯誤處理與日誌記錄
- [x] MariaDB 11.7 + Alembic + 連接池 + asyncmy 異步
- [x] 定期/條件觸發批次寫入
- [x] Streamlit 多頁面、登入/登出、Session、即時圖表
- [x] 多階段 Dockerfile + Compose + 容器網路 + Volume + 環境變數
- [x] 三種角色與權限控制
- [x] 可下載 Excel
