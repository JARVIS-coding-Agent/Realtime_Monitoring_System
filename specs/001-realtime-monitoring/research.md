# Phase 0 研究：技術決策與最佳實務

**功能**：即時資料分析與監控系統 | **日期**：2026-10-22

本文件解析所有技術選型與關鍵實作模式。規格（spec.md）層級已無 NEEDS CLARIFICATION；以下為規劃階段延後處理的實作設定細節決策。

---

## 1. 非同步 ORM 存取（MariaDB）

- **Decision**：SQLAlchemy 2.0 async API + `asyncmy` 驅動，連線字串 `mysql+asyncmy://`。全程 `AsyncSession`，查詢以 `select()`、聚合以 `func.count/sum/avg/max/min`，皆為 ORM，不出現原生 SQL 字串。
- **Rationale**：Constitution 硬性要求 ORM 且禁原生 SQL；asyncmy 是 MariaDB/MySQL 效能較佳的純異步驅動，與 FastAPI 的 async 模型一致，滿足 P95 ≤ 300 ms 目標。
- **Alternatives considered**：aiomysql（較舊、維護較少）；同步 PyMySQL（阻塞事件迴圈，違反 async 需求）；原生 SQL（被 constitution 禁止）。

## 2. 連接池與 DB 中斷降級

- **Decision**：`create_async_engine` 設定 `pool_size`、`max_overflow`、`pool_pre_ping=True`、`pool_recycle`。對暫時性連線錯誤採指數退避重試（上限次數），逾限回傳 503 而非讓服務崩潰。健康檢查 `/health` 嘗試輕量 DB 探測。
- **Rationale**：對應 FR-028、SC-009（DB 短暫中斷不崩潰）；`pool_pre_ping` 可自動汰除失效連線。
- **Alternatives considered**：無重試（違反降級要求）；無限重試（可能拖垮服務）。

## 3. JWT 認證與密碼雜湊

- **Decision**：`python-jose[cryptography]` 簽發 HS256 JWT，payload 含 `sub`（user id）、`role`、`exp`；預設有效期 60 分鐘，由環境變數 `ACCESS_TOKEN_EXPIRE_MINUTES` 設定。密碼以 `passlib[bcrypt]` 雜湊。登入失敗回傳統一訊息不區分帳號/密碼錯誤。
- **Rationale**：對應 FR-002/FR-003 與 constitution 安全約束；HS256 對單體後端足夠，密鑰由 `JWT_SECRET` 環境變數提供。
- **Alternatives considered**：RS256（需金鑰對管理，單服務無必要）；session cookie（與 Streamlit 跨服務串接較不直接）。

## 4. 角色權限（RBAC）

- **Decision**：以 FastAPI 依賴注入實作 `get_current_user` 與 `require_role(*roles)`；資源層級的「擁有者或 Admin」檢查於 router 內比對 `owner_id`。角色為 Enum（admin/user/viewer）。
- **Rationale**：對應 FR-004/FR-008 與權限矩陣；依賴注入讓授權集中、可單元測試。
- **Alternatives considered**：中介層硬編碼路徑權限（較難表達「擁有者」語意）。

## 5. 即時資料生成、WebSocket 廣播與批次寫入

- **Decision**：
  - 生成器以 `asyncio` 背景任務（FastAPI `lifespan` 啟動）每秒產生一筆 `(value, category)`，`is_anomaly = value > ANOMALY_THRESHOLD`（環境變數）。
  - `ws_manager` 維護連線集合，將每筆資料 JSON 廣播給所有連線；斷線自動移除。
  - `batch_writer` 將資料推入記憶體緩衝區，依「筆數門檻或時間間隔（可設定）」觸發一次批次 `add_all` + `commit`。
- **Rationale**：對應 FR-011~FR-015、SC-002（≤ 1 s）、SC-004（≥ 50 連線）、Performance 原則（批次而非逐筆）。緩衝批次大幅降低 DB 寫入壓力。
- **Alternatives considered**：每筆即時 INSERT（違反批次要求、DB 壓力大）；外部訊息佇列如 Redis/Kafka（對本題規模過度設計）。

## 6. 資料分析與 Excel 匯出

- **Decision**：統計/聚合/趨勢以 ORM 聚合函式查詢（`func.*`、`group_by`、時間範圍 `where`）。匯出以 pandas DataFrame → `openpyxl` 產生 `.xlsx`，經 `StreamingResponse` 下載，內容對應畫面資料。
- **Rationale**：對應 FR-016~FR-019、SC-008（匯出與畫面一致）；ORM 聚合維持「禁原生 SQL」。
- **Alternatives considered**：於應用層以 Python 迴圈計算（資料量大時較慢，應優先交給 DB 聚合）。

## 7. 批量導入（CSV/JSON）

- **Decision**：以 `UploadFile` 接收，先檢查大小上限（10 MB）與筆數上限（10,000）；以 pandas 解析，逐列以 Pydantic schema 驗證；正確列批次寫入、錯誤列收集 `{row, error}` 回報。Viewer 一律拒絕。
- **Rationale**：對應 FR-010、US5、SC-006（1,000 筆 ≤ 10 s）。
- **Alternatives considered**：全有或全無（部分錯誤即整批失敗，體驗差且不符驗收情境 2）。

## 8. 前端（Streamlit）與即時更新

- **Decision**：多頁面（`pages/` 自動路由）；`st.session_state` 保存 token 與 role；`api_client` 以 httpx 帶 Bearer token 呼叫 REST；即時監控頁以 `ws_client`（websocket-client）接收推送並以 plotly 折線圖/柱狀圖更新，異常點以紅色標記。過期 token 觸發導回登入。
- **Rationale**：對應 FR-014/FR-027、UX Consistency 原則（一致圖表、時區、異常視覺提示）。
- **Alternatives considered**：純輪詢 REST（延遲較高，不符 ≤ 1 s 即時性）。

## 9. 資料保留與清理

- **Decision**：以可設定保留天數（即時資料 30 天、日誌 90 天）提供清理機制（背景任務定期或 Admin 觸發），以 ORM 刪除逾期資料。
- **Rationale**：對應 FR-029 與 clarify 決議，控制資料量與儲存成本。
- **Alternatives considered**：永不清理（資料無限成長）。

## 10. 容器化部署

- **Decision**：三服務 Compose（backend/frontend/db）；多階段 Dockerfile（builder 裝依賴、runtime 精簡）；`db` 具 healthcheck，backend `depends_on` healthy 後先跑 Alembic 遷移 + 種子再啟動；MariaDB 掛 `db_data` volume；所有機密與參數經 `.env`（提供不含真值的 `.env.example`）。
- **Rationale**：對應 constitution 容器化約束與交付物要求；啟動順序確保 schema 就緒。
- **Alternatives considered**：單容器塞三服務（違反容器化與可維運性）。

## 11. 測試策略

- **Decision**：pytest + pytest-asyncio；REST 以 `httpx.AsyncClient` + `ASGITransport` 免網路測試；整合測試對獨立的可丟棄 MariaDB 測試資料庫走 ORM（統一採 MariaDB 而非 SQLite，避免方言與枚舉/聚合行為差異造成誤判）；每個 bug-fix 先寫重現測試；auth 與 data/analytics 覆蓋率 ≥ 80%。
- **Rationale**：對應 Testing Standards 原則。
- **Alternatives considered**：僅手動測試（不符交付與憲章要求）。

---

**結論**：所有技術選型已與 spec 需求、clarify 決議、constitution 約束對齊，無殘留 NEEDS CLARIFICATION，可進入 Phase 1 設計。
