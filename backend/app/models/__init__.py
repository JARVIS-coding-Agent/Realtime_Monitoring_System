"""集中匯入所有 ORM 模型，確保 SQLAlchemy mapper registry 完整。

任何使用 ORM 的模組應確保這些模型已被載入（例如透過 `import app.models`），
以避免 relationship 以字串名稱（如 "DataRecord"）解析時找不到類別。
"""
from app.models.data_record import DataRecord
from app.models.realtime_data import RealtimeData
from app.models.system_log import SystemLog
from app.models.user import User

__all__ = ["User", "DataRecord", "RealtimeData", "SystemLog"]
