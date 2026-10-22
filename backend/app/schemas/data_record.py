"""資料記錄 Pydantic schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DataRecordCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    value: float
    category: str = Field(min_length=1, max_length=100)
    timestamp: datetime | None = None


class DataRecordUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    value: float | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    timestamp: datetime | None = None


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
