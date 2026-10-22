"""初始化資料庫：建立種子測試帳號（Admin/User/Viewer）。"""
import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models import User  # 透過套件載入全部模型，確保 mapper registry 完整
from app.models.enums import Role


async def _seed_user(session, username: str, email: str, password: str, role: Role) -> None:
    existing = await session.scalar(select(User).where(User.username == username))
    if existing is not None:
        return
    session.add(
        User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
    )
    logger.info(f"建立種子帳號：{username}（{role.value}）")


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        await _seed_user(
            session, settings.seed_admin_username, settings.seed_admin_email,
            settings.seed_admin_password, Role.admin,
        )
        await _seed_user(
            session, settings.seed_user_username, settings.seed_user_email,
            settings.seed_user_password, Role.user,
        )
        await _seed_user(
            session, settings.seed_viewer_username, settings.seed_viewer_email,
            settings.seed_viewer_password, Role.viewer,
        )
        await session.commit()


def main() -> None:
    setup_logging()
    asyncio.run(seed())


if __name__ == "__main__":
    main()
