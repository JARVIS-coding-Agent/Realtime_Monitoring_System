"""安全工具：密碼雜湊與 JWT 簽發/驗證。"""
from datetime import timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.db.base import utcnow

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """以 bcrypt 雜湊密碼。"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """驗證明文密碼與雜湊是否相符。"""
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str | int, role: str) -> str:
    """簽發 JWT（含 sub、role、exp）。"""
    expire = utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": str(subject), "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """解碼並驗證 JWT；無效或過期回傳 None。"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
