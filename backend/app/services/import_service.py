"""批量導入服務：解析 CSV/JSON、驗證、批次寫入，回報成功與失敗。"""
import io
import json
from app.db.base import utcnow

import pandas as pd
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.data_record import DataRecord
from app.schemas.data_record import DataRecordCreate

_REQUIRED = {"title", "value", "category"}


class ImportValidationError(Exception):
    """導入前置檢查錯誤（大小/格式）。"""


def _parse(content: bytes, filename: str) -> list[dict]:
    """依副檔名解析 CSV 或 JSON 為 dict 清單。"""
    name = (filename or "").lower()
    if name.endswith(".json"):
        data = json.loads(content.decode("utf-8"))
        if not isinstance(data, list):
            raise ImportValidationError("JSON 須為物件陣列")
        return data
    # 預設視為 CSV
    df = pd.read_csv(io.BytesIO(content))
    return df.to_dict(orient="records")


async def import_records(
    session: AsyncSession, content: bytes, filename: str, owner_id: int
) -> dict:
    """執行導入。回傳 {success_count, failed_count, errors:[{row,error}]}。"""
    if len(content) > settings.import_max_bytes:
        raise ImportValidationError(f"檔案超過大小上限（{settings.import_max_bytes} bytes）")
    if not content.strip():
        raise ImportValidationError("檔案為空")

    try:
        rows = _parse(content, filename)
    except ImportValidationError:
        raise
    except Exception as exc:
        raise ImportValidationError(f"檔案格式錯誤：{exc}")

    if len(rows) > settings.import_max_rows:
        raise ImportValidationError(f"筆數超過上限（{settings.import_max_rows}）")

    success: list[DataRecord] = []
    errors: list[dict] = []
    for idx, raw in enumerate(rows, start=1):
        try:
            payload = DataRecordCreate(
                title=str(raw.get("title", "")),
                value=float(raw.get("value")),
                category=str(raw.get("category", "")),
                timestamp=raw.get("timestamp") or None,
            )
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append({"row": idx, "error": str(exc)})
            continue
        success.append(
            DataRecord(
                title=payload.title,
                value=payload.value,
                category=payload.category,
                timestamp=payload.timestamp or utcnow(),
                owner_id=owner_id,
            )
        )

    if success:
        session.add_all(success)
        await session.commit()

    return {
        "success_count": len(success),
        "failed_count": len(errors),
        "errors": errors,
    }
