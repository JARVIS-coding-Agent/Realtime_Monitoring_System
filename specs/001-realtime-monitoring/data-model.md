# Phase 1 資料模型

**功能**：即時資料分析與監控系統 | **日期**：2026-10-22

以 SQLAlchemy 2.0 ORM 定義（禁止原生 SQL），Alembic 管理遷移。時間一律以 UTC 儲存，呈現時換算 Asia/Taipei 並以 ISO 8601 格式輸出。

---

## 實體總覽

| 實體 | 說明 | 對應需求 |
|------|------|----------|
| User | 系統操作者與角色 | FR-001~005, FR-020~021 |
| DataRecord | 使用者建立的業務資料 | FR-006~010 |
| RealtimeData | 生成器產生的即時資料點 | FR-011~015, FR-024 |
| SystemLog | 系統活動與錯誤記錄 | FR-022, FR-025 |

---

## User（使用者）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | int | PK, autoincrement | 主鍵 |
| username | str(50) | unique, not null, index | 登入帳號 |
| email | str(255) | unique, not null, index | 電子郵件 |
| hashed_password | str(255) | not null | bcrypt 雜湊，不存明文 |
| role | Enum(admin/user/viewer) | not null, default=user | 角色 |
| is_active | bool | not null, default=true | 是否啟用 |
| created_at | datetime(UTC) | not null, default=now | 建立時間 |

**驗證規則**：
- username/email 唯一；重複註冊回傳 409（FR-001）。
- password 於註冊時以 bcrypt 雜湊；驗證失敗回傳統一訊息（FR-003）。
- 不得降級／停用最後一位 `is_active=true` 的 admin（FR-021）。

**關聯**：`data_records = relationship(DataRecord, back_populates="owner")`。

## DataRecord（資料記錄）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | int | PK | 主鍵 |
| title | str(200) | not null | 標題 |
| value | float | not null | 數值 |
| category | str(100) | not null, index | 分類 |
| timestamp | datetime(UTC) | not null, index | 業務時間戳 |
| owner_id | int | FK→user.id, not null, index | 建立者 |
| created_at | datetime(UTC) | not null, default=now | 建立時間 |
| updated_at | datetime(UTC) | not null, default=now, onupdate=now | 最後更新時間 |

**驗證規則**：
- 建立者或 Admin 方可更新/刪除（FR-008）；Viewer 不可建立/改/刪（權限矩陣）。
- 並發更新採最後寫入者勝出（Clarifications）。
- 分頁（limit/offset）、依 category 篩選、依 timestamp/created_at 排序（FR-007）。

## RealtimeData（即時資料）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | int | PK | 主鍵 |
| value | float | not null | 數值 |
| category | str(100) | not null | 分類 |
| is_anomaly | bool | not null, default=false | 是否超過閾值 |
| generated_at | datetime(UTC) | not null, index | 產生時間 |

**驗證規則**：
- 生成器每秒產生（FR-011）；`is_anomaly = value > ANOMALY_THRESHOLD`（FR-013）。
- 批次寫入（非逐筆）（FR-015）。
- 保留 30 天，逾期清理（FR-029）。

## SystemLog（系統日誌）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | int | PK | 主鍵 |
| level | str(20) | not null, index | 等級（INFO/WARNING/ERROR…） |
| message | text | not null | 訊息 |
| user_id | int | FK→user.id, nullable, index | 相關使用者（可空） |
| endpoint | str(255) | nullable | 相關端點 |
| created_at | datetime(UTC) | not null, default=now, index | 時間 |

**驗證規則**：
- Admin 可依時間與條件（level/endpoint）篩選查詢（FR-022）。
- 保留 90 天，逾期清理（FR-029）。
- 不對終端使用者外洩堆疊；僅 Admin 可查（FR-025）。

---

## 關聯圖（文字）

```
User (1) ──< (N) DataRecord        [owner_id]
User (1) ──< (N) SystemLog         [user_id, nullable]
RealtimeData                       [獨立，無外鍵]
```

## 種子資料（init_db）

| username | role | 用途 |
|----------|------|------|
| admin | admin | 系統管理展示 |
| user | user | 一般操作展示 |
| viewer | viewer | 唯讀展示 |

密碼由環境變數提供預設值，README 需列出帳號/密碼/角色。
