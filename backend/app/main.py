"""FastAPI 應用入口。"""
from contextlib import asynccontextmanager

import math
import os

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings, validate_secrets
from app.core.logging import logger, setup_logging
from app.db.session import engine, wait_for_db

# 載入所有 ORM 模型以註冊 mapper（確保 relationship 字串名稱可解析）
import app.models  # noqa: F401, E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("服務啟動中…")
    # 啟動前置安全檢查：secret 未設定或仍為佔位值則拒絕啟動
    validate_secrets()
    await wait_for_db()
    # 啟動批次寫入器的獨立 flush loop（須在 generator 之前備妥）。
    # batch writer 是資料完整性的核心：若 timer flush loop 起不來，時間觸發會失效、
    # 退化回 issue #3 的資料遺失狀態。因此啟動失敗直接中斷服務，不靜默繼續。
    from app.services.batch_writer import batch_writer
    try:
        await batch_writer.start()
    except Exception as exc:
        logger.error(f"批次寫入器啟動失敗，拒絕啟動服務（避免資料靜默遺失）：{exc}")
        raise
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
    # generator 停止後才關閉批次寫入器（確保最終資料落地）
    try:
        from app.services.batch_writer import batch_writer
        await batch_writer.stop()
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
    # 關閉預設的 CDN 版 Swagger；改用本地靜態資源自訂（見下方 /docs）。
    # ReDoc 非題目需求且與離線資源相容性不佳，故停用（redoc_url=None）。
    docs_url=None,
    redoc_url=None,
)

# 本地靜態資源：讓 Swagger UI 不依賴外部 CDN（離線/擋 CDN 環境也能開）
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
# 僅在本地靜態資源「實際存在」時才用本地；否則回退 FastAPI 預設（CDN），
# 兼顧 Docker（已下載靜態檔→本地）與本機非 Docker 開發（無靜態檔→CDN）。
# 必須 JS 與 CSS 皆存在才算完整；任一缺少（例如 build 時 CSS 下載失敗）
# 就整組回退 CDN，避免 /docs 引用到 404 的本地資源造成破版。
_HAS_SWAGGER_ASSETS = os.path.isfile(
    os.path.join(_STATIC_DIR, "swagger-ui-bundle.js")
) and os.path.isfile(os.path.join(_STATIC_DIR, "swagger-ui.css"))

if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    if _HAS_SWAGGER_ASSETS:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )
    # fallback：無本地資源時用 FastAPI 預設 CDN 版
    return get_swagger_ui_html(openapi_url=app.openapi_url, title=f"{app.title} - Swagger UI")


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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """清洗驗證錯誤明細中的非有限 float，避免回 422 時噴 500。

    starlette 底層 json 解析預設接受非標準字面值 NaN/Infinity，這類輸入會通過
    parse 進到 Pydantic 並被 value validator 擋下。但 Pydantic 會把原始 input
    （float('nan') 等）放進錯誤明細，而 JSONResponse 以 allow_nan=False 序列化，
    直接 dump 會丟 ValueError 使 422 退化成 500。此處遞迴把非有限 float 轉成字串
    表示，確保回出乾淨、可序列化的 422。
    """
    def _sanitize(obj):
        if isinstance(obj, float) and not math.isfinite(obj):
            return str(obj)  # "nan" / "inf" / "-inf"
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_sanitize(v) for v in obj]
        return obj

    # 先用 jsonable_encoder 把 ctx.error 等不可序列化物件轉成可序列化型別，
    # 但它會原樣保留 float('nan')（即原始 500 的來源），故再跑一次 _sanitize。
    encoded = jsonable_encoder(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": _sanitize(encoded)},
    )


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
