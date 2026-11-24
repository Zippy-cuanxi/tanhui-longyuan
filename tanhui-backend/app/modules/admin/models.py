"""管理员聚合域：system_settings 表（仪表盘与用户管理无独立表）。"""
import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin
from app.core.types import GUID, JSONBType


class SystemSetting(UUIDPKMixin, TimestampMixin, Base):
    """平台运行时配置（key-value），如维护公告、首页提示等。"""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), unique=True)
    value: Mapped[dict] = mapped_column(JSONBType())
    description: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
