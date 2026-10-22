"""系統管理路由（僅 Admin）：使用者列表、角色管理、日誌、DB 狀態。"""
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_role
from app.core.logging import logger
from app.db.session import engine
from app.models.enums import Role
from app.models.system_log import SystemLog
from app.models.user import User
from app.schemas.admin import DbStatusOut, SystemLogPage, UserRoleUpdate
from app.schemas.user import UserOut

router = APIRouter()


@router.get("/users", response_model=list[UserOut])
async def list_users(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_role(Role.admin)),
) -> list[User]:
    rows = (await session.scalars(select(User).order_by(User.id))).all()
    return list(rows)


@router.put("/users/{user_id}/role", response_model=UserOut)
async def update_role(
    user_id: int,
    payload: UserRoleUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_role(Role.admin)),
) -> User:
    """變更角色。禁止降級／停用最後一位啟用中的 Admin。"""
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="使用者不存在")

    # 若此人目前是 admin 且被降級，檢查是否為最後一位啟用中的 admin
    if user.role == Role.admin and payload.role != Role.admin:
        active_admins = await session.scalar(
            select(func.count(User.id)).where(
                User.role == Role.admin, User.is_active.is_(True)
            )
        )
        if (active_admins or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="無法降級最後一位啟用中的管理員",
            )

    user.role = payload.role
    await session.commit()
    await session.refresh(user)
    logger.info(f"管理員變更使用者 {user.username} 角色為 {payload.role.value}")
    return user


@router.get("/logs", response_model=SystemLogPage)
async def list_logs(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_role(Role.admin)),
    level: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    endpoint: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> SystemLogPage:
    base = select(SystemLog)
    count_q = select(func.count()).select_from(SystemLog)
    conds = []
    if level:
        conds.append(SystemLog.level == level)
    if start:
        conds.append(SystemLog.created_at >= start)
    if end:
        conds.append(SystemLog.created_at <= end)
    if endpoint:
        conds.append(SystemLog.endpoint == endpoint)
    for c in conds:
        base = base.where(c)
        count_q = count_q.where(c)
    total = await session.scalar(count_q) or 0
    rows = (
        await session.scalars(
            base.order_by(SystemLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return SystemLogPage(items=list(rows), total=total)


@router.get("/db-status", response_model=DbStatusOut)
async def db_status(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_role(Role.admin)),
) -> DbStatusOut:
    start = time.monotonic()
    connected = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        connected = False
    latency_ms = round((time.monotonic() - start) * 1000, 2)
    pool = engine.pool
    return DbStatusOut(
        connected=connected,
        pool_size=getattr(pool, "size", lambda: 0)() if hasattr(pool, "size") else 0,
        checked_out=getattr(pool, "checkedout", lambda: 0)() if hasattr(pool, "checkedout") else 0,
        latency_ms=latency_ms,
    )
