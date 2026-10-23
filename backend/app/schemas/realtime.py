"""即時資料 Pydantic schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RealtimeMessage(BaseModel):
    """WebSocket 推送訊息格式。"""

    value: float
    category: str
    is_anomaly: bool
    generated_at: datetime


class RealtimeDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    value: float
    category: str
    is_anomaly: bool
    generated_at: datetime


class RealtimeHistoryPage(BaseModel):
    items: list[RealtimeDataOut]
    total: int
    page: int
    page_size: int
