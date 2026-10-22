"""FastAPI 應用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.session import engine, wait_for_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("服務啟動中…")
    await wait_for_db()
    # 啟動即時資料生成器背景任務
    try:
        from app.services.generator import generator
        await generator.start()
    except Exception as exc:
        logger.error(f"背景任務啟動失敗：{exc}")
    # 啟動保留清理背景任務
    try:
        from app.services.retention import retention_cleaner
        await retention_cleaner.start()
    except Exception as exc:
        logger.error(f"保留清理啟動失敗：{exc}")
    yield
    try:
        from app.services.generator import generator
        await generator.stop()
    except Exception:
        pass
    try:
        from app.services.retention import retention_cleaner
        await retention_cleaner.stop()
    except Exception:
        pass
    await engine.dispose()
    logger.info("服務已關閉")


app = FastAPI(
    title="即時資料分析與監控系統",
    description="FastAPI + WebSocket 即時監控後端（SQLAlchemy async ORM）",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 系統日誌中介層（記錄變更類請求供 Admin 稽核）
from app.core.middleware import SystemLogMiddleware  # noqa: E402

app.add_middleware(SystemLogMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """避免向終端使用者外洩內部堆疊。"""
    logger.exception(f"未處理例外於 {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "伺服器內部錯誤"},
    )


@app.get("/health", tags=["system"])
async def health() -> dict:
    """健康檢查：含輕量 DB 探測，DB 異常時降級但不崩潰。"""
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "degraded"
    return {"status": "ok", "db": db_status}


# === 路由掛載（各階段逐步加入）===
def _register_routers() -> None:
    try:
        from app.api.routers import auth
        app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    except ImportError:
        pass

    try:
        from app.api.routers import data
        app.include_router(data.router, prefix="/api/data", tags=["data"])
    except ImportError:
        pass
    try:
        from app.api.routers import analytics
        app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    except ImportError:
        pass
    try:
        from app.api.routers import realtime
        app.include_router(realtime.router, tags=["realtime"])
    except ImportError:
        pass
    try:
        from app.api.routers import admin
        app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
    except ImportError:
        pass


_register_routers()
