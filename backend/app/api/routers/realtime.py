"""即時監控路由：WebSocket 推送 + 歷史資料查詢。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.core.security import decode_access_token
from app.models.realtime_data import RealtimeData
from app.models.user import User
from app.schemas.realtime import RealtimeHistoryPage
from app.services.ws_manager import ws_manager

router = APIRouter()


@router.websocket("/ws/realtime")
async def ws_realtime(websocket: WebSocket, token: str = Query(default="")) -> None:
    """即時資料推送。連線時以 query 參數 token 驗證。"""
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=1008)  # policy violation
        return
    await ws_manager.connect(websocket)
    try:
        while True:
            # 伺服器單向推送；接收以偵測斷線
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


@router.get("/api/realtime/history", response_model=RealtimeHistoryPage)
async def history(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
    only_anomaly: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> RealtimeHistoryPage:
    """歷史即時資料查詢（分頁/篩選）。"""
    base = select(RealtimeData)
    count_q = select(func.count()).select_from(RealtimeData)
    conditions = []
    if start:
        conditions.append(RealtimeData.generated_at >= start)
    if end:
        conditions.append(RealtimeData.generated_at <= end)
    if category:
        conditions.append(RealtimeData.category == category)
    if only_anomaly:
        conditions.append(RealtimeData.is_anomaly.is_(True))
    for c in conditions:
        base = base.where(c)
        count_q = count_q.where(c)

    total = await session.scalar(count_q) or 0
    rows = (
        await session.scalars(
            base.order_by(RealtimeData.generated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return RealtimeHistoryPage(items=list(rows), total=total, page=page, page_size=page_size)
