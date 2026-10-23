"""資料記錄 Pydantic schema。"""
import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_finite(v: float | None) -> float | None:
    """拒絕 NaN / Infinity（H4）：非有限數會污染統計與 Excel 匯出。"""
    if v is not None and not math.isfinite(v):
        raise ValueError("value 必須為有限數（不接受 NaN 或 Infinity）")
    return v


class DataRecordCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    value: float
    category: str = Field(min_length=1, max_length=100)
    timestamp: datetime | None = None

    @field_validator("value")
    @classmethod
    def _value_finite(cls, v: float) -> float:
        return _validate_finite(v)


class DataRecordUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    value: float | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    timestamp: datetime | None = None

    @field_validator("value")
    @classmethod
    def _value_finite(cls, v: float | None) -> float | None:
        return _validate_finite(v)


class DataRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    value: float
    category: str
    timestamp: datetime
    owner_id: int
    created_at: datetime
    updated_at: datetime


class DataRecordPage(BaseModel):
    items: list[DataRecordOut]
    total: int
    page: int
    page_size: int
