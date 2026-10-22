"""資料分析 Pydantic schema。"""
from datetime import datetime

from pydantic import BaseModel


class StatsOut(BaseModel):
    count: int
    sum: float
    avg: float
    min: float
    max: float


class AggregateItem(BaseModel):
    category: str
    count: int
    sum: float
    avg: float


class TrendItem(BaseModel):
    bucket: datetime
    avg: float
    count: int
