# API 契約：認證（Auth）

所有回應為 JSON。錯誤統一格式：`{ "detail": "<訊息>" }`，不含內部堆疊。

## POST /api/auth/register — 註冊

- **權限**：公開
- **Request**：`{ "username": str, "email": str(email), "password": str(>=8) }`
- **201**：`{ "id", "username", "email", "role", "is_active", "created_at" }`
- **409**：帳號或電子郵件已存在（FR-001）
- **422**：欄位驗證失敗

## POST /api/auth/login — 登入

- **權限**：公開
- **Request**：`{ "username": str, "password": str }`（或 OAuth2 form）
- **200**：`{ "access_token": str, "token_type": "bearer", "role": str }`
- **401**：帳號或密碼錯誤（統一訊息，不區分）（FR-003）
- 憑證預設有效 60 分鐘（可設定）（FR-002）

## GET /api/auth/me — 目前使用者

- **權限**：已登入
- **200**：`{ "id", "username", "email", "role", "is_active", "created_at" }`
- **401**：未提供/無效/過期憑證（FR-002）

**對應驗收**：US1 情境 1–4。
