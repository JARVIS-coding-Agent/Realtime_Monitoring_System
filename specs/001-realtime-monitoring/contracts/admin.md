# API 契約：系統管理（Admin）

共通：需登入且 `role=admin`，否則一律 403（FR-020~024, US6 情境 3）。

## GET /api/admin/users — 使用者列表

- **200**：`[{ "id", "username", "email", "role", "is_active", "created_at" }]`（FR-020）

## PUT /api/admin/users/{id}/role — 變更角色

- **Request**：`{ "role": "admin|user|viewer" }`
- **200**：更新後使用者；變更即時生效於後續授權（FR-021）
- **409**：嘗試降級/停用最後一位啟用中的 Admin → 拒絕並回報原因（FR-021, US6 邊界）
- **404**：使用者不存在

## GET /api/admin/logs — 系統日誌

- **Query**：`level`?, `start`?, `end`?, `endpoint`?, `page`, `page_size`
- **200**：`{ "items": [SystemLog...], "total": int }`（FR-022）

## GET /api/admin/db-status — 資料庫狀態

- **200**：`{ "connected": bool, "pool_size": int, "checked_out": int, "latency_ms": float }`（FR-023）

**對應驗收**：US6 情境 1–4。

---

## 其他系統端點

## GET /health — 健康檢查

- **權限**：公開
- **200**：`{ "status": "ok", "db": "ok|degraded" }`（FR-026, SC-009）

## GET /docs — Swagger UI（自動產生，FR 對應 Swagger 文件需求）
