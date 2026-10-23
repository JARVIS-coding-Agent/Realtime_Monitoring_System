"""pytest 共用 fixture。

測試資料庫（issue #4）：
- 預設使用 in-memory aiosqlite，供本機快速驗證邏輯層。
- 設定環境變數 `TEST_DATABASE_URL` 可對 MariaDB 測試資料庫執行（貼近 production 方言）；
  CI（.github/workflows/ci.yml）即以 MariaDB 跑完整套件。
- 多數測試已跨方言（含 analytics trend），兩種 DB 皆可執行；僅限 MariaDB 的測試
  可標記 `@pytest.mark.requires_mariadb`，非 MariaDB 環境會自動 skip。
"""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
_IS_MARIADB = TEST_DATABASE_URL.startswith(("mysql", "mariadb"))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_mariadb: 僅能在 MariaDB 測試資料庫執行的測試"
    )


def pytest_collection_modifyitems(config, items):
    if _IS_MARIADB:
        return
    skip = pytest.mark.skip(reason="需 MariaDB（設定 TEST_DATABASE_URL 後執行）")
    for item in items:
        if "requires_mariadb" in item.keywords:
            item.add_marker(skip)


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
