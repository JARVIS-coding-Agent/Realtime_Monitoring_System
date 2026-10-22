"""日誌設定（loguru）。"""
import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """設定統一的 loguru 日誌格式與等級。"""
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "{message}"
        ),
        backtrace=False,
        diagnose=False,
    )


__all__ = ["logger", "setup_logging"]
