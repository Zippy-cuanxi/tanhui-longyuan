"""用户域模型：users / user_profiles / user_addresses。

【安全】password_hash 仅服务端保存 Argon2id 哈希，任何响应 schema 不得包含。
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin
from app.core.types import GUID, UTCDatetime
from sqlalchemy import ForeignKey


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    # Argon2id 哈希（不对外输出）
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # 管理员 MFA（消费者/商家默认关闭）
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64))  # TOTP base32
    banned_until: Mapped[datetime | None] = mapped_column(UTCDatetime())
    ban_reason: Mapped[str | None] = mapped_column(String(255))


class UserProfile(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), unique=True, index=True
    )
    nickname: Mapped[str | None] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    gender: Mapped[str | None] = mapped_column(String(16))
    birthday: Mapped[date | None] = mapped_column(Date)
    bio: Mapped[str | None] = mapped_column(String(255))


class UserAddress(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "user_addresses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True
    )
    receiver: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(32))
    province: Mapped[str] = mapped_column(String(32))
    city: Mapped[str] = mapped_column(String(32))
    district: Mapped[str | None] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(String(255))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("user_id", "receiver", "phone", "detail", name="uq_user_addr"),
    )
