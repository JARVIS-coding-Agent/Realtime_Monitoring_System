"""共用列舉。"""
import enum


class Role(str, enum.Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"
