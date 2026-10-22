# Implementation Plan：即時資料分析與監控系統

**Branch**: `001-realtime-monitoring` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-realtime-monitoring/spec.md`

## Summary

建置一套容器化的即時資料分析與監控系統。後端以 **FastAPI**（非同步）提供 RESTful CRUD、JWT 認證、三角色 RBAC、資料分析與 WebSocket 即時推送；資料層以 **SQLAlchemy 2.0 async ORM**（禁止原生 SQL）搭配 **asyncmy** 連線 **MariaDB 11.7**，schema 以 **Alembic** 管理。背景任務每秒產生模擬資料，透過 WebSocket 廣播給所有連線前端，並以定期／條件觸發的批次方式寫入資料庫。前端以 **Streamlit** 多頁面呈現登入、即時監控、資料管理、分析與系統管理。整個系統以 **Docker Compose**（backend／frontend／db 三服務、多階段 Dockerfile、持久化 volume、環境變數）部署。

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**:
- 後端：FastAPI、Uvicorn、Pydantic v2、pydantic-settings、SQLAlchemy 2.0（async）、asyncmy、Alembic、python-jose[cryptography]（JWT）、passlib[bcrypt]（密碼雜湊）、python-multipart（檔案上傳）、pandas、openpyxl（Excel 匯出）、loguru（日誌）
- 前端：Streamlit、httpx（REST 串接）、websocket-client（WS 串接）、plotly（圖表）、pandas

**Storage**: MariaDB 11.7，僅透過 SQLAlchemy async ORM 存取（禁止原生 SQL），Alembic 管理遷移，bounded 連接池，資料以具名 volume 持久化

**Testing**: pytest、pytest-asyncio、httpx.AsyncClient + ASGITransport（REST 整合測試免啟網路）、獨立 MariaDB 測試資料庫（整合測試用，走 ORM；統一採 MariaDB 而非 SQLite，避免方言與枚舉/聚合行為差異導致誤判）

**Target Platform**: Linux 容器（Docker Compose 多容器網路），桌面瀏覽器操作前端

**Project Type**: Web application（backend FastAPI + frontend Streamlit，前後端分離）

**Performance Goals**:
- 一般 REST 讀取端點 P95 ≤ 300 ms（不含冷啟動）
- 即時資料端到端延遲 P95 ≤ 1 秒
- 支援 ≥ 50 位使用者同時連線即時監控
- 即時資料以批次寫入，非逐筆 INSERT

**Constraints**:
- 全程 ORM，原生 SQL 字串一律禁止
- 密碼必須雜湊保存，JWT 密鑰與 DB 憑證僅由環境變數提供，不得進版控
- JWT 預設有效期 60 分鐘（可設定）
- 批量導入單檔上限 10,000 筆 / 10 MB
- 資料保留：即時資料 30 天、系統日誌 90 天（可設定）
- 預設時區 Asia/Taipei，時間戳 ISO 8601
- DB 短暫中斷需優雅降級（重試退避）而非崩潰

**Scale/Scope**: 3 種角色、4 個資料實體、約 20+ REST 端點 + 1 WebSocket、前端 5 個頁面（1 入口 + 4 子頁）、交付含 README／.env.example／範例 CSV／架構圖

## Constitution Check

*GATE：Phase 0 前須通過；Phase 1 設計後再檢查一次。*

| 原則 | 本計畫如何符合 | 判定 |
|------|----------------|:----:|
| I. Code Quality | 單一職責模組（auth／data／analytics／realtime／admin）；所有 DB 存取走 ORM，無原生 SQL；所有公開 API 以 Pydantic schema 定義並經 Swagger 呈現；相依版本釘選 | PASS |
| II. Testing Standards | 核心邏輯（JWT、RBAC、CRUD 擁有者規則、分析聚合、異常閾值）單元測試涵蓋授權／未授權／邊界；REST／WS／批次寫入／匯入整合測試走可丟棄測試 DB；auth 與 data/analytics 覆蓋率 ≥ 80% | PASS |
| III. UX Consistency | Streamlit 各頁一致用語／版面；session 統一管理登入狀態與過期憑證處理；圖表一致軸／單位／時區（Asia/Taipei）／ISO 8601；異常一致視覺提示；錯誤不外洩堆疊 | PASS |
| IV. Performance | REST P95 ≤ 300 ms、即時延遲 ≤ 1 s；即時資料批次寫入且策略可設定；asyncmy + bounded pool；DB 中斷重試退避；每項目標有對應指標／日誌 | PASS |
| V. Language & Documentation | spec／plan／tasks／README／UI 文案／API 描述皆為繁體中文（zh-TW）；constitution 維持英文；README 含專案介紹／技術棧／本地運行／Docker／Swagger 連結／種子帳號 | PASS |

**額外約束檢查**：MariaDB 11.7 + ORM + Alembic ✅；JWT + 三角色 RBAC（擁有者/Admin 限制）✅；密碼雜湊 + 環境變數機密 + `.env.example` ✅；Docker Compose 多階段 + 網路 + volume + 環境變數 ✅；錯誤處理 + 日誌 + Admin 可查日誌/DB 狀態/即時歷史 ✅；交付物（代碼/README/.env.example/範例 CSV/架構圖）✅

**Gate 結果**：PASS，無違規，`Complexity Tracking` 不需填寫。

## Project Structure

### Documentation (this feature)

```text
specs/001-realtime-monitoring/
├── plan.md              # 本檔（/speckit.plan 輸出）
├── research.md          # Phase 0 輸出
├── data-model.md        # Phase 1 輸出
├── quickstart.md        # Phase 1 輸出
├── contracts/           # Phase 1 輸出（API 契約）
│   ├── auth.md
│   ├── data.md
│   ├── analytics.md
│   ├── realtime.md
│   └── admin.md
├── checklists/
│   └── requirements.md  # /speckit.specify 已產出
└── tasks.md             # /speckit.tasks 產出（本指令不建立）
```

### Source Code (repository root)

```text
backend/
├── Dockerfile                  # 多階段構建
├── requirements.txt
├── alembic.ini
├── alembic/                    # 遷移腳本
│   ├── env.py
│   └── versions/
└── app/
    ├── main.py                 # FastAPI 入口、路由掛載、lifespan（啟動背景任務）
    ├── core/
    │   ├── config.py           # Pydantic Settings（環境變數）
    │   ├── security.py         # JWT 簽發/驗證、密碼雜湊
    │   └── logging.py          # loguru 設定
    ├── db/
    │   ├── base.py             # Declarative Base
    │   ├── session.py          # async engine + bounded pool + session 依賴
    │   └── init_db.py          # 種子資料（Admin/User/Viewer 測試帳號）
    ├── models/                 # SQLAlchemy ORM models
    │   ├── user.py
    │   ├── data_record.py
    │   ├── realtime_data.py
    │   └── system_log.py
    ├── schemas/                # Pydantic schemas（請求/回應）
    │   ├── user.py
    │   ├── auth.py
    │   ├── data_record.py
    │   ├── analytics.py
    │   ├── realtime.py
    │   └── admin.py
    ├── api/
    │   ├── deps.py             # current_user / require_role 依賴注入
    │   └── routers/
    │       ├── auth.py
    │       ├── data.py
    │       ├── analytics.py
    │       ├── realtime.py     # WebSocket + 歷史查詢
    │       └── admin.py
    ├── services/
    │   ├── generator.py        # 即時資料生成器（背景任務，每秒）
    │   ├── batch_writer.py     # 緩衝區 + 批次寫入 DB
    │   ├── ws_manager.py       # WebSocket 連線管理與廣播
    │   ├── analytics_service.py# 統計/聚合/趨勢（ORM 聚合）
    │   └── import_service.py   # CSV/JSON 批量導入驗證
    └── tests/
        ├── conftest.py
        ├── test_auth.py
        ├── test_data.py
        ├── test_analytics.py
        ├── test_realtime.py
        └── test_admin.py

frontend/
├── Dockerfile
├── requirements.txt
└── app/
    ├── Home.py                 # Streamlit 入口（登入/登出）
    ├── api_client.py           # 串接後端 REST
    ├── ws_client.py            # WebSocket 客戶端
    ├── state.py                # Session 狀態（token/role）
    └── pages/
        ├── 1_📊_即時監控.py
        ├── 2_📋_資料管理.py
        ├── 3_📈_資料分析.py
        └── 4_⚙️_系統管理.py

docs/
├── architecture.png            # 系統架構圖
└── sample_data.csv             # 測試資料 CSV 範例

docker-compose.yml
.env.example
README.md
```

**Structure Decision**: 採「Web application（前後端分離）」結構。後端與前端各自獨立容器與相依，透過 Compose 網路以服務名互連；資料庫為第三個服務並掛載持久化 volume。此結構對應 spec 的五大模組與 constitution 的單一職責要求，並讓測試（後端 pytest）與部署（三服務 Compose）邊界清晰。

## Complexity Tracking

> 無 Constitution 違規，本節不適用。
