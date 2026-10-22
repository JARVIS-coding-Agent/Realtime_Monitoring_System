"""系統日誌中介層：將非 GET 的 API 請求結果記錄到 SystemLog。"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import logger
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.models.system_log import SystemLog


class SystemLogMiddleware(BaseHTTPMiddleware):
    """記錄變更類請求（POST/PUT/DELETE）至 system_logs，供 Admin 稽核。"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method in {"POST", "PUT", "DELETE"} and request.url.path.startswith("/api"):
            try:
                user_id = None
                auth = request.headers.get("authorization", "")
                if auth.lower().startswith("bearer "):
                    payload = decode_access_token(auth[7:])
                    if payload and payload.get("sub"):
                        user_id = int(payload["sub"])
                level = "INFO" if response.status_code < 400 else "WARNING"
                async with AsyncSessionLocal() as session:
                    session.add(
                        SystemLog(
                            level=level,
                            message=f"{request.method} {request.url.path} -> {response.status_code}",
                            user_id=user_id,
                            endpoint=request.url.path,
                        )
                    )
                    await session.commit()
            except Exception as exc:
                logger.debug(f"系統日誌中介層寫入失敗（略過）：{exc}")

        return response
