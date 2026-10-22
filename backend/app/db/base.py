"""SQLAlchemy Declarative Base。"""
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """回傳 timezone-aware 的 UTC 現在時間。"""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """所有 ORM 模型的共用基底。"""

    pass
