"""商家域模型：merchants（入驻主体与审核状态机）/ merchant_users。"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin
from app.core.types import GUID, UTCDatetime

# 入驻状态机：pending_review → approved / rejected；approved → frozen → approved
MERCHANT_STATUSES = ("pending_review", "approved", "rejected", "frozen")


class Merchant(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "merchants"

    status: Mapped[str] = mapped_column(String(32), default="pending_review", index=True)
    company_name: Mapped[str] = mapped_column(String(128), unique=True)
    license_no: Mapped[str] = mapped_column(String(64))  # 统一社会信用代码【以业务要求为准】
    license_url: Mapped[str | None] = mapped_column(String(512))
    legal_person: Mapped[str] = mapped_column(String(64))
    contact_phone: Mapped[str] = mapped_column(String(32))
    region: Mapped[str | None] = mapped_column(String(64))
    # 入驻申请时填写的初始店铺名，审核通过后据此自动创建默认店铺
    initial_store_name: Mapped[str | None] = mapped_column(String(64))
    reject_reason: Mapped[str | None] = mapped_column(String(255))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDatetime())


class MerchantUser(UUIDPKMixin, TimestampMixin, Base):
    """商家与用户的从属关系（owner 为入驻申请人）。"""

    __tablename__ = "merchant_users"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="owner")  # owner / manager

    __table_args__ = (UniqueConstraint("merchant_id", "user_id", name="uq_merchant_user"),)
