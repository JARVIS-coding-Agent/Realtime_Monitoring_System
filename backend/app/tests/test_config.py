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


def test_empty_db_password_fails():
    with pytest.raises(RuntimeError, match="DB_PASSWORD"):
        validate_secrets(_settings(db_password=""))


def test_empty_jwt_secret_reports_single_error():
    # 空值不應同時觸發「未設定」與「長度過短」兩條重複訊息
    with pytest.raises(RuntimeError) as exc:
        validate_secrets(_settings(jwt_secret=""))
    assert exc.value.args[0].count("JWT_SECRET") == 1


def test_defaults_have_no_usable_secret():
    # issue #1：原始碼不得帶入可用的 hardcoded secret 預設值
    fields = Settings.model_fields
    assert fields["jwt_secret"].default == ""
    assert fields["db_password"].default == ""
