"""系統管理 Pydantic schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Role


class UserRoleUpdate(BaseModel):
    role: Role


class SystemLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: str
    message: str
    user_id: int | None
    endpoint: str | None
    created_at: datetime


class SystemLogPage(BaseModel):
    items: list[SystemLogOut]
    total: int


class DbStatusOut(BaseModel):
    connected: bool
    pool_size: int
    checked_out: int
    latency_ms: float
