"""#1 啟動前置安全檢查測試：validate_secrets fail-fast。"""
import pytest

from app.core.config import Settings, validate_secrets


def _settings(**overrides) -> Settings:
    base = dict(
        jwt_secret="a" * 32,
        db_password="a-real-password",
    )
    base.update(overrides)
    return Settings(**base)


def test_valid_secrets_pass():
    # 安全值不應拋錯
    validate_secrets(_settings())


def test_placeholder_jwt_secret_fails():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_secrets(_settings(jwt_secret="change-me-to-a-long-random-secret"))


def test_placeholder_db_password_fails():
    with pytest.raises(RuntimeError, match="DB_PASSWORD"):
        validate_secrets(_settings(db_password="change-me-db-password"))


def test_short_jwt_secret_fails():
    with pytest.raises(RuntimeError, match="長度過短"):
        validate_secrets(_settings(jwt_secret="short"))


def test_empty_jwt_secret_fails():
    with pytest.raises(RuntimeError):
        validate_secrets(_settings(jwt_secret=""))
