"""
SQLAlchemy 模型。统一从本包导出，便于 db.create_all() 与迁移扫描。
"""
from .user import User

__all__ = ["User"]
