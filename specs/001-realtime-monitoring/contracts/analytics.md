# API 契約：資料分析（Analytics）

共通：需登入（Admin/User/Viewer 皆可檢視圖表）。聚合一律以 ORM 聚合函式查詢。

## GET /api/analytics/stats — 統計

- **Query**：`start`?, `end`?, `category`?
- **200**：`{ "count": int, "sum": float, "avg": float, "min": float, "max": float }`（FR-016）

## GET /api/analytics/aggregate — 分類聚合

- **Query**：`start`?, `end`?
- **200**：`[{ "category": str, "count": int, "sum": float, "avg": float }]`（FR-018）

## GET /api/analytics/trend — 趨勢

- **Query**：`start`, `end`, `interval`(hour|day，預設 day)
- **200**：`[{ "bucket": datetime, "avg": float, "count": int }]`（FR-017）
- 時間範圍無資料回空陣列（空狀態，非錯誤）

## GET /api/analytics/export — 匯出 Excel

- **Query**：同 stats/trend 篩選
- **200**：`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`（.xlsx 檔下載，內容與畫面一致）（FR-019, SC-008）

**對應驗收**：US4 情境 1–4。
