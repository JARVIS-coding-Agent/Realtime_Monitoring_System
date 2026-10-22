"""資料分析路由：統計、分類聚合、趨勢、Excel 匯出。"""
import io
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.analytics import AggregateItem, StatsOut, TrendItem
from app.services import analytics_service

router = APIRouter()

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/stats", response_model=StatsOut)
async def stats(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
) -> StatsOut:
    data = await analytics_service.compute_stats(session, start, end, category)
    return StatsOut(**data)


@router.get("/aggregate", response_model=list[AggregateItem])
async def aggregate(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[AggregateItem]:
    data = await analytics_service.compute_aggregate(session, start, end)
    return [AggregateItem(**d) for d in data]


@router.get("/trend", response_model=list[TrendItem])
async def trend(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
    start: datetime | None = None,
    end: datetime | None = None,
    interval: str = Query("day", pattern="^(day|hour)$"),
) -> list[TrendItem]:
    data = await analytics_service.compute_trend(session, start, end, interval)
    return [TrendItem(**d) for d in data]


@router.get("/export")
async def export(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
) -> StreamingResponse:
    """匯出統計與分類聚合為 Excel（內容與畫面一致）。"""
    stats_data = await analytics_service.compute_stats(session, start, end, category)
    agg_data = await analytics_service.compute_aggregate(session, start, end)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([stats_data]).to_excel(writer, sheet_name="統計", index=False)
        pd.DataFrame(agg_data or [{"category": "", "count": 0, "sum": 0.0, "avg": 0.0}]).to_excel(
            writer, sheet_name="分類聚合", index=False
        )
    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=analytics_export.xlsx"}
    return StreamingResponse(buffer, media_type=_XLSX_MEDIA, headers=headers)
