"""非同步資料庫 engine、session 與連線重試。"""
import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import logger

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    pool_recycle=settings.db_pool_recycle,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依賴：提供一個 AsyncSession。"""
    async with AsyncSessionLocal() as session:
        yield session


async def wait_for_db(max_retries: int = 10, base_delay: float = 1.0) -> bool:
    """以指數退避等待資料庫可連線，避免啟動時因 DB 尚未就緒而崩潰。"""
    from sqlalchemy import text

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("資料庫連線成功")
            return True
        except OperationalError as exc:
            delay = min(base_delay * 2 ** (attempt - 1), 30.0)
            logger.warning(f"資料庫尚未就緒（第 {attempt}/{max_retries} 次），{delay:.1f}s 後重試：{exc}")
            await asyncio.sleep(delay)
    logger.error("資料庫重試逾限，放棄連線")
    return False
