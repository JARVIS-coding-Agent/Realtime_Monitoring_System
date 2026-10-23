"""資料管理路由：CRUD + 分頁/篩選/排序，擁有者或 Admin 方可改刪。"""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow

from app.api.deps import get_current_user, get_session, require_role
from app.core.logging import logger
from app.models.data_record import DataRecord
from app.models.enums import Role
from app.models.user import User
from app.schemas.data_record import (
    DataRecordCreate,
    DataRecordOut,
    DataRecordPage,
    DataRecordUpdate,
)
from app.services import import_service

router = APIRouter()

_SORT_COLUMNS = {
    "timestamp": DataRecord.timestamp,
    "created_at": DataRecord.created_at,
    "value": DataRecord.value,
}


def _can_modify(record: DataRecord, user: User) -> bool:
    return record.owner_id == user.id or user.role == Role.admin


@router.get("", response_model=DataRecordPage)
async def list_records(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    sort_by: str = Query("timestamp"),
    order: str = Query("desc"),
) -> DataRecordPage:
    """列表：所有角色可瀏覽；支援分類篩選、排序與分頁。"""
    column = _SORT_COLUMNS.get(sort_by, DataRecord.timestamp)
    order_by = column.asc() if order == "asc" else column.desc()

    base = select(DataRecord)
    count_q = select(func.count()).select_from(DataRecord)
    if category:
        base = base.where(DataRecord.category == category)
        count_q = count_q.where(DataRecord.category == category)

    total = await session.scalar(count_q) or 0
    rows = (
        await session.scalars(
            base.order_by(order_by).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    return DataRecordPage(items=list(rows), total=total, page=page, page_size=page_size)


@router.post("", response_model=DataRecordOut, status_code=status.HTTP_201_CREATED)
async def create_record(
    payload: DataRecordCreate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(require_role(Role.admin, Role.user)),
) -> DataRecord:
    """建立資料記錄（Admin/User；Viewer 由 require_role 擋下回 403）。"""
    record = DataRecord(
        title=payload.title,
        value=payload.value,
        category=payload.category,
        timestamp=payload.timestamp or utcnow(),
        owner_id=current.id,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    logger.info(f"使用者 {current.username} 建立資料 {record.id}")
    return record


@router.post("/import")
async def import_data(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current: User = Depends(require_role(Role.admin, Role.user)),
) -> dict:
    """批量導入 CSV/JSON（Admin/User；Viewer 403）。回報成功/失敗筆數與每列原因。"""
    content = await file.read()
    try:
        result = await import_service.import_records(
            session, content, file.filename or "", current.id
        )
    except import_service.ImportError_ as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.info(
        f"使用者 {current.username} 批量導入：成功 {result['success_count']} 失敗 {result['failed_count']}"
    )
    return result


@router.get("/{record_id}", response_model=DataRecordOut)
async def get_record(
    record_id: int,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> DataRecord:
    # 設計決策（issue #2）：資料記錄採「團隊共享」可見性，所有登入者皆可讀取
    # 任一筆（與列表行為一致）；僅寫入限 owner/Admin。故此處刻意不做 owner 檢查。
    record = await session.get(DataRecord, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="資料不存在")
    return record


@router.put("/{record_id}", response_model=DataRecordOut)
async def update_record(
    record_id: int,
    payload: DataRecordUpdate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> DataRecord:
    """更新：僅擁有者或 Admin；最後寫入者勝出。"""
    record = await session.get(DataRecord, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="資料不存在")
    if not _can_modify(record, current):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")
    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(record, field, val)
    await session.commit()
    await session.refresh(record)
    logger.info(f"使用者 {current.username} 更新資料 {record.id}")
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: int,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> None:
    """刪除：僅擁有者或 Admin。"""
    record = await session.get(DataRecord, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="資料不存在")
    if not _can_modify(record, current):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")
    await session.delete(record)
    await session.commit()
    logger.info(f"使用者 {current.username} 刪除資料 {record_id}")
