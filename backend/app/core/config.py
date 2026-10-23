"""應用設定：從環境變數載入（Pydantic Settings）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# 不得於 production 使用的範本佔位值（啟動時偵測到即 fail-fast）
_PLACEHOLDER_VALUES = {
    "change-me-db-password",
    "change-me-to-a-long-random-secret",
    "change-me-root-password",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 資料庫
    db_host: str = "db"
    db_port: int = 3306
    db_name: str = "monitoring"
    db_user: str = "monitor"
    db_password: str = "change-me-db-password"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800

    # JWT / 安全
    jwt_secret: str = "change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # 即時資料生成器
    generator_interval_seconds: float = 1.0
    anomaly_threshold: float = 80.0
    generator_categories: str = "cpu,memory,disk,network"

    # 批次寫入
    batch_size: int = 50
    batch_interval_seconds: float = 5.0

    # 資料保留
    realtime_retention_days: int = 30
    log_retention_days: int = 90
    retention_cleanup_interval_hours: int = 24

    # 批量導入上限
    import_max_rows: int = 10000
    import_max_bytes: int = 10 * 1024 * 1024

    # 種子帳號
    seed_admin_username: str = "admin"
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "Admin@12345"
    seed_user_username: str = "user"
    seed_user_email: str = "user@example.com"
    seed_user_password: str = "User@12345"
    seed_viewer_username: str = "viewer"
    seed_viewer_email: str = "viewer@example.com"
    seed_viewer_password: str = "Viewer@12345"

    # 一般
    timezone: str = "Asia/Taipei"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:8501"

    @property
    def database_url(self) -> str:
        """SQLAlchemy async 連線字串（asyncmy 驅動）。"""
        return (
            f"mysql+asyncmy://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def category_list(self) -> list[str]:
        return [c.strip() for c in self.generator_categories.split(",") if c.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [c.strip() for c in self.cors_origins.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_secrets(s: "Settings | None" = None) -> None:
    """啟動時驗證敏感設定：未設定或仍為範本佔位值則 fail-fast。

    於服務實際啟動時呼叫（main.py lifespan），避免影響測試 import。
    """
    s = s or get_settings()
    errors: list[str] = []

    if not s.jwt_secret or s.jwt_secret in _PLACEHOLDER_VALUES:
        errors.append("JWT_SECRET 未設定或仍為範本佔位值，請以 `openssl rand -hex 32` 產生安全值")
    if len(s.jwt_secret) < 16:
        errors.append("JWT_SECRET 長度過短（至少 16 字元）")
    if not s.db_password or s.db_password in _PLACEHOLDER_VALUES:
        errors.append("DB_PASSWORD 未設定或仍為範本佔位值")

    if errors:
        raise RuntimeError(
            "啟動前置安全檢查失敗，服務拒絕啟動：\n  - " + "\n  - ".join(errors)
        )


settings = get_settings()
