# API 契約：即時監控（Realtime）

## WS /ws/realtime — 即時資料推送

- **權限**：已登入（連線時以 query 或 header 帶 token）
- **伺服器推送訊息**（每秒）：
  ```json
  { "value": 0.0, "category": "cpu", "is_anomaly": false, "generated_at": "2026-10-22T13:00:00Z" }
  ```
- 多連線同步接收同一份資料（FR-012）；異常點 `is_anomaly=true`（FR-013）
- 斷線後前端重連可恢復後續推送（US3 情境 4）
- 端到端延遲 P95 ≤ 1 s（SC-002）；支援 ≥ 50 連線（SC-004）

## GET /api/realtime/history — 歷史即時資料

- **權限**：Admin（系統管理）/ 亦可供監控頁查詢（依實作）
- **Query**：`start`?, `end`?, `category`?, `only_anomaly`?(bool), `page`, `page_size`
- **200**：`{ "items": [RealtimeData...], "total": int }`（FR-024）

**對應驗收**：US3 情境 1–4、US6 情境 4。
