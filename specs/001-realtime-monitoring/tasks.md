# Tasks：即時資料分析與監控系統

**Input**: 設計文件來自 `specs/001-realtime-monitoring/`

**Prerequisites**: plan.md、spec.md（必要）；research.md、data-model.md、contracts/、quickstart.md（已存在）

**Tests**: 本專案 constitution（Testing Standards 原則）將測試列為交付要求，故包含測試任務（auth 與 data/analytics 覆蓋率 ≥ 80%）。

**Organization**: 任務依使用者故事分組，每個故事可獨立實作與測試。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行（不同檔案、無未完成相依）
- **[Story]**：所屬使用者故事（US1~US6）
- 路徑依 plan.md 的 Web application 結構（`backend/`、`frontend/`）

---

## Phase 1: Setup（共用基礎設施）

**目的**：專案初始化與基本結構

- [X] T001 建立專案資料夾結構（`backend/app/{core,db,models,schemas,api/routers,services,tests}`、`frontend/app/pages`、`docs/`）per plan.md
- [X] T002 建立 `backend/requirements.txt`（釘選版本：fastapi, uvicorn[standard], pydantic>=2, pydantic-settings, sqlalchemy[asyncio]>=2, asyncmy, alembic, python-jose[cryptography], passlib[bcrypt], python-multipart, pandas, openpyxl, loguru, pytest, pytest-asyncio, httpx）
- [X] T003 [P] 建立 `frontend/requirements.txt`（釘選版本：streamlit, httpx, websocket-client, plotly, pandas）
- [X] T004 [P] 建立 `.env.example`（DB 連線、JWT_SECRET、ACCESS_TOKEN_EXPIRE_MINUTES=60、ANOMALY_THRESHOLD、BATCH_SIZE、BATCH_INTERVAL_SECONDS、REALTIME_RETENTION_DAYS=30、LOG_RETENTION_DAYS=90、種子帳號密碼；不含真實機密）
- [X] T005 [P] 建立 `backend/Dockerfile`（多階段：builder 裝依賴 + runtime 精簡）
- [X] T006 [P] 建立 `frontend/Dockerfile`（多階段）
- [X] T007 建立 `docker-compose.yml`（三服務 backend/frontend/db；db healthcheck；backend depends_on db healthy；MariaDB 11.7 + `db_data` volume；環境變數由 .env 注入；啟動時 backend 先跑 Alembic 遷移 + 種子）

---

## Phase 2: Foundational（阻塞性前置，所有故事開始前必須完成）

**⚠️ CRITICAL**：此階段完成前，任何使用者故事皆不可開始

- [X] T008 [P] 實作 `backend/app/core/config.py`（Pydantic Settings，從環境變數讀取所有設定，含時區 Asia/Taipei）
- [X] T009 [P] 實作 `backend/app/core/logging.py`（loguru 設定，統一日誌格式）
- [X] T010 實作 `backend/app/db/base.py`（SQLAlchemy Declarative Base）
- [X] T011 實作 `backend/app/db/session.py`（`create_async_engine` with bounded pool：pool_size/max_overflow/pool_pre_ping=True/pool_recycle；`AsyncSession` 依賴；暫時性連線錯誤指數退避重試）per research.md §2
- [X] T012 實作 `backend/app/main.py`（FastAPI app、掛載路由佔位、CORS、全域例外處理器不外洩堆疊、lifespan 佔位）
- [X] T013 實作 `backend/app/core/security.py`（bcrypt 密碼雜湊/驗證；JWT 簽發 HS256 含 sub/role/exp，有效期 60 分鐘可設定；JWT 解碼驗證）per contracts/auth.md
- [X] T014 初始化 Alembic（`backend/alembic.ini`、`backend/alembic/env.py` 綁定 async engine 與 Base metadata）
- [X] T015 實作 `backend/app/api/deps.py`（`get_db`、`get_current_user` 解析 Bearer token、`require_role(*roles)` 依賴）per plan.md
- [X] T016 設定 `GET /health` 於 main.py（回傳 `{status, db}`，db 輕量探測，降級回 degraded 不崩潰）per contracts/admin.md、SC-009

**Checkpoint**：基礎就緒，使用者故事可開始

---

## Phase 3: User Story 1 — 安全登入與角色授權 (Priority: P1) 🎯 MVP

**Goal**：使用者可註冊/登入取得 JWT，依角色（Admin/User/Viewer）強制授權。

**Independent Test**：建立帳號→登入取得 token→`/me` 回傳角色→Viewer 建立資料被拒→過期/無效 token 被拒。

### Tests for User Story 1 ⚠️（先寫、先失敗）

- [X] T017 [P] [US1] 契約測試 auth 端點於 `backend/app/tests/test_auth.py`（register 409 重複、login 401 統一訊息、me 401 無效 token）per contracts/auth.md
- [X] T018 [P] [US1] 單元測試 security（密碼雜湊/驗證、JWT 簽發/過期驗證）於 `backend/app/tests/test_auth.py`

### Implementation for User Story 1

- [X] T019 [US1] 實作 `backend/app/models/user.py`（User ORM：id PK；username str(50) unique not null index；email str(255) unique not null index；hashed_password str(255) not null；role Enum(admin/user/viewer) not null default=user；is_active bool not null default=true；created_at datetime(UTC) not null default=now）per data-model.md
- [X] T020 [US1] 建立 Alembic 遷移（users 資料表）`backend/alembic/versions/`
- [X] T021 [P] [US1] 實作 `backend/app/schemas/auth.py`（LoginRequest、TokenResponse{access_token,token_type,role}）per contracts/auth.md
- [X] T022 [P] [US1] 實作 `backend/app/schemas/user.py`（UserCreate{username,email,password>=8}、UserOut{id,username,email,role,is_active,created_at}）
- [X] T023 [US1] 實作 `backend/app/api/routers/auth.py`（POST /api/auth/register 409 重複〔FR-001〕；POST /api/auth/login 401 統一訊息〔FR-002〕；GET /api/auth/me 回傳目前使用者〔FR-005〕）掛載至 main.py per contracts/auth.md
- [X] T024 [US1] 實作 `backend/app/db/init_db.py`（種子三帳號 admin/user/viewer，密碼由環境變數，雜湊保存）per data-model.md
- [X] T025 [US1] 為 auth 操作加入系統日誌與錯誤處理（登入成功/失敗記錄，不外洩細節）

**Checkpoint**：US1 可獨立運作——登入授權為後續所有故事之基礎（MVP）

---

## Phase 4: User Story 2 — 資料記錄的建立與管理 (Priority: P1)

**Goal**：Admin/User 可對 DataRecord 進行 CRUD（分頁/篩選/排序），擁有者或 Admin 方可改刪；Viewer 唯讀。

**Independent Test**：建立數筆→分頁/篩選/排序查詢→非擁有者改刪被拒→擁有者/Admin 改刪成功→Viewer 寫入被拒。

### Tests for User Story 2 ⚠️

- [X] T026 [P] [US2] 契約測試 data CRUD 於 `backend/app/tests/test_data.py`（建立 201、Viewer 建立 403、列表分頁/篩選/排序、非擁有者 PUT/DELETE 403、擁有者/Admin 200）per contracts/data.md
- [X] T027 [P] [US2] 單元測試擁有者權限規則於 `backend/app/tests/test_data.py`

### Implementation for User Story 2

- [X] T028 [US2] 實作 `backend/app/models/data_record.py`（DataRecord ORM：id PK；title str(200) not null；value float not null；category str(100) not null index；timestamp datetime(UTC) not null index；owner_id FK→user.id not null index；created_at not null default=now；updated_at not null default=now onupdate=now）per data-model.md
- [X] T029 [US2] 建立 Alembic 遷移（data_records 資料表）
- [X] T030 [P] [US2] 實作 `backend/app/schemas/data_record.py`（DataRecordCreate、DataRecordUpdate、DataRecordOut、分頁回應 {items,total,page,page_size}）per contracts/data.md
- [X] T031 [US2] 實作 `backend/app/api/routers/data.py`（GET /api/data 分頁/篩選/排序；POST 201 Viewer 403；GET/{id}；PUT/{id} 擁有者或 Admin 否則 403，最後寫入者勝出；DELETE/{id} 204）掛載至 main.py per contracts/data.md、FR-007/008
- [X] T032 [US2] 加入 data 操作的驗證、錯誤處理與系統日誌

**Checkpoint**：US1 + US2 皆可獨立運作

---

## Phase 5: User Story 3 — 即時資料監控與異常告警 (Priority: P1)

**Goal**：每秒產生模擬資料，WebSocket 廣播給所有連線，前端即時圖表更新並標記異常；批次寫入 DB。

**Independent Test**：開啟監控頁觀察每秒更新（≤1s）；注入超閾值資料驗證異常標記；多連線同步；批次寫入 DB。

### Tests for User Story 3 ⚠️

- [X] T033 [P] [US3] 整合測試 WS 推送與批次寫入於 `backend/app/tests/test_realtime.py`（連線收到每秒資料、is_anomaly 正確、批次寫入後可由 history 查得）per contracts/realtime.md
- [X] T034 [P] [US3] 單元測試異常閾值判斷於 `backend/app/tests/test_realtime.py`

### Implementation for User Story 3

- [X] T035 [US3] 實作 `backend/app/models/realtime_data.py`（RealtimeData ORM：id PK；value float not null；category str(100) not null；is_anomaly bool not null default=false；generated_at datetime(UTC) not null index）per data-model.md
- [X] T036 [US3] 建立 Alembic 遷移（realtime_data 資料表）
- [X] T037 [P] [US3] 實作 `backend/app/schemas/realtime.py`（RealtimeMessage{value,category,is_anomaly,generated_at}、歷史查詢回應）
- [X] T038 [P] [US3] 實作 `backend/app/services/ws_manager.py`（連線集合管理、廣播、斷線移除）per research.md §5
- [X] T039 [US3] 實作 `backend/app/services/batch_writer.py`（記憶體緩衝 + 依 BATCH_SIZE 或 BATCH_INTERVAL 觸發批次 add_all+commit）per research.md §5、FR-015
- [X] T040 [US3] 實作 `backend/app/services/generator.py`（asyncio 每秒產生 value/category，is_anomaly=value>ANOMALY_THRESHOLD，推送 ws_manager + 送入 batch_writer）per FR-011/013
- [X] T041 [US3] 於 main.py lifespan 啟動 generator 背景任務；實作 `WS /ws/realtime`（連線驗證 token）與 `GET /api/realtime/history`（分頁/篩選）於 `backend/app/api/routers/realtime.py` per contracts/realtime.md

**Checkpoint**：US1 + US2 + US3（三個 P1）皆可獨立運作——核心後端完成

---

## Phase 6: User Story 4 — 資料統計分析與匯出 (Priority: P2)

**Goal**：統計/分類聚合/趨勢查詢（ORM 聚合），結果可匯出與畫面一致的 Excel。

**Independent Test**：請求 stats/aggregate/trend 驗證數字；時間範圍無資料回空；匯出 .xlsx 與畫面一致。

### Tests for User Story 4 ⚠️

- [ ] T042 [P] [US4] 契約/整合測試 analytics 於 `backend/app/tests/test_analytics.py`（stats 正確、aggregate 分類、trend 範圍與空狀態、export 回傳 xlsx）per contracts/analytics.md

### Implementation for User Story 4

- [ ] T043 [P] [US4] 實作 `backend/app/schemas/analytics.py`（StatsOut、AggregateItem、TrendItem）per contracts/analytics.md
- [ ] T044 [US4] 實作 `backend/app/services/analytics_service.py`（以 ORM func.count/sum/avg/min/max、group_by、時間範圍 where；趨勢分桶）per research.md §6、FR-016/017/018
- [ ] T045 [US4] 實作 `backend/app/api/routers/analytics.py`（GET /stats /aggregate /trend /export；export 以 pandas+openpyxl 產生 xlsx StreamingResponse）掛載至 main.py per contracts/analytics.md、FR-019

**Checkpoint**：US1–US4 皆可獨立運作

---

## Phase 7: User Story 5 — 批量資料導入 (Priority: P2)

**Goal**：Admin/User 上傳 CSV/JSON 批量導入（上限 10,000 筆/10 MB），回報成功/失敗筆數與每列原因；Viewer 拒絕。

**Independent Test**：上傳正確檔回報成功數；含錯誤列檔正確列導入、錯誤列回報 {row,error}；Viewer 403。

### Tests for User Story 5 ⚠️

- [ ] T046 [P] [US5] 整合測試 import 於 `backend/app/tests/test_data.py`（正確檔成功數、部分錯誤回報、超過上限 400、Viewer 403）per contracts/data.md

### Implementation for User Story 5

- [ ] T047 [US5] 實作 `backend/app/services/import_service.py`（檢查 10 MB/10,000 筆上限；pandas 解析 CSV/JSON；逐列 Pydantic 驗證；正確列批次寫入、錯誤列收集）per research.md §7、FR-010
- [ ] T048 [US5] 於 `backend/app/api/routers/data.py` 新增 POST /api/data/import（multipart；回報 {success_count,failed_count,errors}；Viewer 403）per contracts/data.md
- [ ] T049 [P] [US5] 建立 `docs/sample_data.csv`（含標題/數值/分類/時間戳的測試資料範例，供導入與交付用）

**Checkpoint**：US1–US5 皆可獨立運作

---

## Phase 8: User Story 6 — 系統管理與稽核 (Priority: P3)

**Goal**：Admin 可查使用者列表、變更角色（禁降級最後一位 Admin）、查日誌、查 DB 狀態、查即時歷史。

**Independent Test**：Admin 查使用者/變更角色；降級最後 Admin 被拒（409）；非 Admin 存取 403；查日誌/DB 狀態/歷史可篩選。

### Tests for User Story 6 ⚠️

- [ ] T050 [P] [US6] 契約/整合測試 admin 於 `backend/app/tests/test_admin.py`（users 列表、變更角色生效、最後 Admin 409、非 Admin 403、logs/db-status 查詢）per contracts/admin.md

### Implementation for User Story 6

- [ ] T051 [US6] 實作 `backend/app/models/system_log.py`（SystemLog ORM：id PK；level str(20) not null index；message text not null；user_id FK→user.id nullable index；endpoint str(255) nullable；created_at datetime(UTC) not null default=now index）per data-model.md
- [ ] T052 [US6] 建立 Alembic 遷移（system_logs 資料表）
- [ ] T053 [P] [US6] 實作 `backend/app/schemas/admin.py`（UserRoleUpdate、SystemLogOut、DbStatusOut）per contracts/admin.md
- [ ] T054 [US6] 實作 `backend/app/api/routers/admin.py`（GET /users；PUT /users/{id}/role 禁降級/停用最後一位啟用 Admin 回 409；GET /logs 篩選；GET /db-status 連接池指標）掛載至 main.py，全端點 require_role admin per contracts/admin.md、FR-020~024
- [ ] T055 [US6] 導入中介層/依賴記錄系統日誌（endpoint、user、level）供 Admin 查詢 per FR-025

**Checkpoint**：所有六個使用者故事皆可獨立運作（後端完成）

---

## Phase 9: 前端（Streamlit）— 跨故事使用者介面

**Purpose**：對應 US1–US6 的前端呈現（FR-014/027、UX Consistency）

- [ ] T056 [P] 實作 `frontend/app/state.py`（session_state 管理 token/role/登入狀態）per research.md §8
- [ ] T057 實作 `frontend/app/api_client.py`（httpx 帶 Bearer token 呼叫 REST；處理 401 導回登入）
- [ ] T058 [P] 實作 `frontend/app/ws_client.py`（websocket-client 連線 /ws/realtime 接收推送）
- [ ] T059 實作 `frontend/app/Home.py`（登入/登出頁，寫入 session，過期處理）對應 US1
- [ ] T060 [P] 實作 `frontend/app/pages/2_📋_資料管理.py`（CRUD、分頁/篩選/排序、批量導入 UI）對應 US2/US5
- [ ] T061 [P] 實作 `frontend/app/pages/1_📊_即時監控.py`（WS 即時 plotly 折線/柱狀圖，異常紅色標記，時區 Asia/Taipei，ISO 8601）對應 US3
- [ ] T062 [P] 實作 `frontend/app/pages/3_📈_資料分析.py`（stats/aggregate/trend 圖表 + Excel 下載）對應 US4
- [ ] T063 [P] 實作 `frontend/app/pages/4_⚙️_系統管理.py`（使用者列表/角色管理/日誌/DB 狀態/即時歷史，僅 Admin 可見）對應 US6

**Checkpoint**：前端五頁對應全部故事，端到端可操作

---

## Phase 10: Polish & 跨領域關注

- [ ] T064 [P] 實作資料保留清理背景任務（即時資料 30 天、日誌 90 天，ORM 刪除逾期）per FR-029
- [ ] T065 [P] 撰寫 `README.md`（繁中：專案介紹、技術棧、本地運行步驟、Docker 部署指令、Swagger 連結、種子測試帳號含密碼與角色）per constitution 語言/文件原則
- [ ] T066 [P] 建立 `docs/architecture.png`（系統架構圖）
- [ ] T067 確認 auth 與 data/analytics 測試覆蓋率 ≥ 80%（補足缺口）per constitution Testing Standards
- [ ] T068 執行 `quickstart.md` 全部驗證情境（US1–US6 + 成功標準對照 SC-002~009）
- [ ] T069 [P] 靜態檢查（linter/formatter/type）全綠、移除死碼與除錯輸出 per constitution Code Quality
- [ ] T070 [P] 新增 REST 讀取端點壓測腳本於 `backend/app/tests/perf/test_rest_latency.py`（量測 GET /api/data P95，驗證 ≤ 300 ms）per SC-003、Performance 原則
- [ ] T071 [P] 新增 WebSocket 負載測試腳本於 `backend/app/tests/perf/test_ws_load.py`（模擬 ≥ 50 並發連線，驗證推送不中斷且端到端延遲 P95 ≤ 1 s）per SC-002/SC-004

---

## Dependencies & Execution Order

### Phase 相依

- **Setup (P1)**：無相依，可立即開始
- **Foundational (P2)**：依賴 Setup 完成 — 阻塞所有使用者故事
- **User Stories (P3–P8)**：皆依賴 Foundational 完成
  - US2/US3 依賴 US1 的 User 模型（T019）
  - US5 依賴 US2 的 DataRecord（T028）
  - US6 依賴 User 模型（T019）
- **Frontend (P9)**：依賴對應後端故事端點完成
- **Polish (P10)**：依賴所有目標故事完成

### User Story 相依

- **US1 (P1)**：Foundational 後即可開始，為其他故事之基礎
- **US2 (P1)**：需 User 模型（T019）；其餘獨立
- **US3 (P1)**：需 Foundational；獨立於 US2
- **US4 (P2)**：需 DataRecord（T028）
- **US5 (P2)**：需 DataRecord（T028）
- **US6 (P3)**：需 User 模型（T019）

### 各故事內部

- 測試先寫、先失敗 → 模型 → schema → service → 端點 → 整合/日誌

### 平行機會

- Setup 中 T003–T006 可平行
- Foundational 中 T008/T009 可平行
- 各故事內標 [P] 的測試/schema/model（不同檔）可平行
- US3（即時）與 US2（資料）在 US1 模型完成後可由不同人平行
- 前端各頁面（T060–T063）可平行

---

## Parallel Example: User Story 1

```text
# 測試先行（平行）：
Task: T017 契約測試 auth 於 backend/app/tests/test_auth.py
Task: T018 單元測試 security 於 backend/app/tests/test_auth.py

# schema 平行：
Task: T021 schemas/auth.py
Task: T022 schemas/user.py
```

---

## Implementation Strategy

### MVP First（僅 US1）

1. 完成 Phase 1 Setup
2. 完成 Phase 2 Foundational（關鍵，阻塞全部）
3. 完成 Phase 3 US1（登入授權）
4. **STOP 驗證**：獨立測試 US1
5. 可展示登入與授權基礎

### 增量交付

1. Setup + Foundational → 基礎就緒
2. US1（登入授權）→ 測試 → MVP
3. US2（資料管理）、US3（即時監控）→ 測試 → 展示（核心後端）
4. US4（分析）、US5（導入）→ 測試 → 展示
5. US6（系統管理）→ 測試 → 展示
6. 前端（P9）串接各故事 → Polish（P10）交付

### 平行團隊策略

1. 團隊共同完成 Setup + Foundational
2. 之後：開發者 A 做 US1→US2；B 做 US3（即時）；C 待 US1 模型後做 US6
3. 前端開發者依後端端點完成進度逐頁串接

---

## Notes

- [P] = 不同檔案、無相依
- [Story] 標籤對應使用者故事以利追溯
- 每個故事可獨立完成與測試
- 實作前先確認測試失敗（TDD）
- 每個任務或邏輯群組後提交
- 可於任一 checkpoint 停下獨立驗證
- 避免：模糊任務、同檔衝突、破壞獨立性的跨故事相依
