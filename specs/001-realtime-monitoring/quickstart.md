# Quickstart 驗證指南

**功能**：即時資料分析與監控系統 | **日期**：2026-10-22

本文件說明如何啟動系統並端到端驗證各使用者故事。實作細節見 `data-model.md` 與 `contracts/`，不在此重複程式碼。

---

## 前置需求

- Docker 與 Docker Compose
- 已由 `.env.example` 複製出 `.env` 並填入值（JWT 密鑰、DB 憑證、異常閾值、批次策略、保留天數、種子帳號密碼）

## 啟動（Docker）

```bash
docker-compose up --build
```

啟動順序：`db`（healthcheck 通過）→ `backend`（跑 Alembic 遷移 + 種子資料）→ `frontend`。

- 前端：http://localhost:8501
- 後端 Swagger：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

## 本地啟動（不使用 Docker，開發用）

1. 啟動 MariaDB 11.7（本機或容器），設定 `.env` 的 DB 連線。
2. 後端：安裝 `backend/requirements.txt` → `alembic upgrade head` → 執行種子 → `uvicorn app.main:app --reload`。
3. 前端：安裝 `frontend/requirements.txt` → `streamlit run app/Home.py`。

## 種子測試帳號

| 帳號 | 角色 | 用途 |
|------|------|------|
| admin | Admin | 完整管理權限 |
| user | User | 建立/管理自己的資料 |
| viewer | Viewer | 僅瀏覽 |

（密碼見 `.env` / README）

---

## 驗證情境（對應使用者故事）

### US1 登入與授權
1. 以 viewer 登入（`POST /api/auth/login`）取得 token。
2. 以該 token `GET /api/auth/me` → 回傳 role=viewer。
3. 以 viewer token `POST /api/data` → 預期 **403**（Viewer 不可建立）。
4. 等待逾時或使用無效 token 存取受保護端點 → 預期 **401** 並於前端引導重新登入。

### US2 資料管理
1. 以 user 登入 `POST /api/data` 建立數筆 → **201**，owner 為該 user。
2. `GET /api/data?category=X&sort_by=timestamp&order=desc&page=2` → 正確篩選/排序/分頁與 total。
3. 以另一 user `PUT/DELETE` 他人資料 → **403**；以擁有者或 admin 更新 → **200**，`updated_at` 更新。

### US3 即時監控
1. 前端開啟「即時監控」頁，觀察 plotly 圖表每秒更新（延遲 ≤ 1 s）。
2. 將 `ANOMALY_THRESHOLD` 設低，觀察異常點以紅色標記（`is_anomaly=true`）。
3. 開兩個瀏覽器分頁，確認同步收到同一份資料。
4. 中斷網路再恢復，確認前端重連後續推送。

### US4 分析與匯出
1. `GET /api/analytics/stats` → 正確 count/sum/avg/min/max。
2. `GET /api/analytics/trend?start&end&interval=day` → 僅回傳範圍內資料；無資料回空陣列。
3. `GET /api/analytics/aggregate` → 每分類彙總。
4. `GET /api/analytics/export` → 下載 .xlsx，內容與畫面一致。

### US5 批量導入
1. 以 `docs/sample_data.csv` `POST /api/data/import` → 回報成功筆數。
2. 上傳含錯誤列的檔 → 正確列導入、錯誤列回報 `{row, error}`。
3. 以 viewer 導入 → **403**。

### US6 系統管理
1. 以 admin `GET /api/admin/users` → 全部使用者。
2. `PUT /api/admin/users/{id}/role` 變更角色 → 生效；嘗試降級最後一位 admin → **409**。
3. 以非 admin 存取任一 `/api/admin/*` → **403**。
4. `GET /api/admin/logs`、`GET /api/admin/db-status`、`GET /api/realtime/history` → 可查詢並篩選。

---

## 自動化測試

```bash
cd backend
pytest -q
```

- 單元：JWT、RBAC、CRUD 擁有者規則、分析聚合、異常閾值
- 整合：REST（AsyncClient）、WS 推送、批次寫入、CSV/JSON 匯入
- 覆蓋率：auth 與 data/analytics ≥ 80%

## 成功標準對照

| 成功標準 | 驗證方式 |
|----------|----------|
| SC-002 即時延遲 ≤ 1 s | 觀察前端更新 / WS 時間戳差 |
| SC-003 REST P95 ≤ 300 ms | 壓測讀取端點 |
| SC-004 ≥ 50 連線 | 多連線模擬 |
| SC-005 權限 100% | 整合測試未授權路徑全拒 |
| SC-006 1000 筆 ≤ 10 s | 以範例檔計時導入 |
| SC-009 DB 中斷不崩潰 | 暫停 db 容器觀察 /health 降級後恢復 |
