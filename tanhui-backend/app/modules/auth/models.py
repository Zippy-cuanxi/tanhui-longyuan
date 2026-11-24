"""认证域模型：sessions（刷新令牌会话，只存哈希，支持轮换与撤销）。"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, UUIDPKMixin, utcnow
from app.core.types import GUID, UTCDatetime


class AuthSession(UUIDPKMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True
    )
    # refresh token 的 SHA-256 哈希（轮换检测：不匹配说明旧令牌被复用）
    refresh_token_hash: Mapped[str] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDatetime())
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    # 轮换链：本次会话由哪个旧会话轮换而来
    rotated_from_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)
