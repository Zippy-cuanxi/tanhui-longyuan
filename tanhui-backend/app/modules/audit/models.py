"""审计域模型：operation_logs / login_logs / security_events（敏感操作必审计）。"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, UUIDPKMixin, utcnow
from app.core.types import GUID, JSONBType, UTCDatetime


class OperationLog(UUIDPKMixin, Base):
    __tablename__ = "operation_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)  # 如 product.audit
    resource: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSONBType())
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, index=True)


class LoginLog(UUIDPKMixin, Base):
    __tablename__ = "login_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    email: Mapped[str] = mapped_column(String(255))
    success: Mapped[bool] = mapped_column(Boolean)
    message: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, index=True)


class SecurityEvent(UUIDPKMixin, Base):
    __tablename__ = "security_events"

    kind: Mapped[str] = mapped_column(String(64), index=True)  # refresh_token_reuse 等
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    detail: Mapped[dict | None] = mapped_column(JSONBType())
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, index=True)
