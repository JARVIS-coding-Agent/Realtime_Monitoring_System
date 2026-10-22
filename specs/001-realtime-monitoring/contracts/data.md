# API 契約：資料管理（Data）

共通：需 `Authorization: Bearer <token>`。權限依 RBAC 矩陣。

## GET /api/data — 列表（分頁/篩選/排序）

- **權限**：Admin/User/Viewer（皆可瀏覽）
- **Query**：`page`(預設1), `page_size`(預設20,≤100), `category`?, `sort_by`(timestamp|created_at|value), `order`(asc|desc)
- **200**：`{ "items": [DataRecord...], "total": int, "page": int, "page_size": int }`（FR-007）

## POST /api/data — 建立

- **權限**：Admin/User（Viewer 拒絕）
- **Request**：`{ "title": str, "value": float, "category": str, "timestamp": datetime? }`
- **201**：建立的 DataRecord（含 owner_id=目前使用者）（FR-006）
- **403**：Viewer

## GET /api/data/{id} — 取得單筆

- **權限**：Admin/User/Viewer
- **200**：DataRecord；**404**：不存在

## PUT /api/data/{id} — 更新

- **權限**：建立者或 Admin（FR-008）
- **Request**：可更新 `title/value/category/timestamp`
- **200**：更新後 DataRecord（`updated_at` 更新）；**403**：非擁有者且非 Admin；**404**：不存在
- 並發：最後寫入者勝出

## DELETE /api/data/{id} — 刪除

- **權限**：建立者或 Admin（FR-008）
- **204**：成功；**403**：非擁有者且非 Admin；**404**：不存在

## POST /api/data/import — 批量導入

- **權限**：Admin/User（Viewer 拒絕）
- **Request**：`multipart/form-data`，檔案 CSV 或 JSON（上限 10,000 筆 / 10 MB）（FR-010）
- **200**：`{ "success_count": int, "failed_count": int, "errors": [{ "row": int, "error": str }] }`
- **400**：空檔/格式完全錯誤/超過上限；**403**：Viewer

**對應驗收**：US2 情境 1–5、US5 情境 1–3。
