"""資料分析服務：以 SQLAlchemy ORM 聚合函式計算統計、分類聚合與趨勢。"""
from datetime import datetime

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_record import DataRecord


def _apply_range(stmt, start: datetime | None, end: datetime | None, category: str | None):
    if start:
        stmt = stmt.where(DataRecord.timestamp >= start)
    if end:
        stmt = stmt.where(DataRecord.timestamp <= end)
    if category:
        stmt = stmt.where(DataRecord.category == category)
    return stmt


async def compute_stats(
    session: AsyncSession,
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
) -> dict:
    """總計/平均/最大/最小/筆數。"""
    stmt = select(
        func.count(DataRecord.id),
        func.coalesce(func.sum(DataRecord.value), 0.0),
        func.coalesce(func.avg(cast(DataRecord.value, Float)), 0.0),
        func.coalesce(func.min(DataRecord.value), 0.0),
        func.coalesce(func.max(DataRecord.value), 0.0),
    )
    stmt = _apply_range(stmt, start, end, category)
    row = (await session.execute(stmt)).one()
    return {
        "count": int(row[0]),
        "sum": float(row[1]),
        "avg": float(row[2]),
        "min": float(row[3]),
        "max": float(row[4]),
    }


async def compute_aggregate(
    session: AsyncSession,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    """依分類聚合。"""
    stmt = select(
        DataRecord.category,
        func.count(DataRecord.id),
        func.coalesce(func.sum(DataRecord.value), 0.0),
        func.coalesce(func.avg(cast(DataRecord.value, Float)), 0.0),
    ).group_by(DataRecord.category)
    stmt = _apply_range(stmt, start, end, None)
    rows = (await session.execute(stmt)).all()
    return [
        {"category": r[0], "count": int(r[1]), "sum": float(r[2]), "avg": float(r[3])}
        for r in rows
    ]


async def compute_trend(
    session: AsyncSession,
    start: datetime | None = None,
    end: datetime | None = None,
    interval: str = "day",
) -> list[dict]:
    """趨勢分桶（day 或 hour），以 DB 聚合。"""
    fmt = "%Y-%m-%d %H:00:00" if interval == "hour" else "%Y-%m-%d"
    bucket = func.date_format(DataRecord.timestamp, fmt).label("bucket")
    stmt = select(
        bucket,
        func.coalesce(func.avg(cast(DataRecord.value, Float)), 0.0),
        func.count(DataRecord.id),
    ).group_by(bucket).order_by(bucket)
    stmt = _apply_range(stmt, start, end, None)
    rows = (await session.execute(stmt)).all()
    result = []
    for r in rows:
        bucket_str = r[0]
        parsed = datetime.strptime(
            bucket_str, "%Y-%m-%d %H:%M:%S" if interval == "hour" else "%Y-%m-%d"
        )
        result.append({"bucket": parsed, "avg": float(r[1]), "count": int(r[2])})
    return result
