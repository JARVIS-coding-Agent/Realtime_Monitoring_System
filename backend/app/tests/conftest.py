"""pytest 共用 fixture。

整合測試預設對獨立 MariaDB 測試資料庫執行（見 TEST_DATABASE_URL）；
若未提供，退回使用 in-memory aiosqlite 以便本機快速驗證邏輯層。
"""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    # 匯入所有模型以建立 metadata
    import app.models.user  # noqa: F401
    try:
        import app.models.data_record  # noqa: F401
    except ImportError:
        pass
    try:
        import app.models.realtime_data  # noqa: F401
    except ImportError:
        pass
    try:
        import app.models.system_log  # noqa: F401
    except ImportError:
        pass
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_factory):
    from app.api.deps import get_session
    from app.main import app

    async def _override_get_session():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
