"""支付域模型：payment_orders / payment_transactions / payment_callbacks / refunds。

【重要】当前支付渠道为 Mock 沙箱（provider=mock_sandbox），未接入真实渠道。
接入真实渠道：实现 providers/base.py 的 PaymentProvider 并在
providers/__init__.py 工厂中按 settings.PAYMENT_PROVIDER 返回。
"""
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, JSONBType, UTCDatetime, Amount


class PaymentOrder(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "payment_orders"

    pay_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("orders.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Amount())
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    # pending / success / failed / expired / closed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    provider: Mapped[str] = mapped_column(String(32), default="mock_sandbox")
    trade_no: Mapped[str | None] = mapped_column(String(64), unique=True)  # 渠道交易号
    expires_at: Mapped[datetime] = mapped_column(UTCDatetime())
    paid_at: Mapped[datetime | None] = mapped_column(UTCDatetime())


class PaymentTransaction(UUIDPKMixin, Base):
    __tablename__ = "payment_transactions"

    payment_order_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    provider_trade_no: Mapped[str] = mapped_column(String(64), unique=True)
    amount: Mapped[Decimal] = mapped_column(Amount())
    currency: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16))
    raw: Mapped[dict | None] = mapped_column(JSONBType())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)


class PaymentCallback(UUIDPKMixin, Base):
    __tablename__ = "payment_callbacks"

    pay_no: Mapped[str] = mapped_column(String(32), index=True)
    provider_trade_no: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSONBType())
    signature: Mapped[str | None] = mapped_column(String(256))
    # processed 首次处理 / duplicate 重复回调(幂等跳过) / invalid 校验失败
    status: Mapped[str] = mapped_column(String(16), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)


class Refund(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "refunds"

    refund_no: Mapped[str] = mapped_column(String(32), unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("orders.id"), index=True)
    store_order_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    amount: Mapped[Decimal] = mapped_column(Amount())
    reason: Mapped[str] = mapped_column(String(255))
    # requested → processing → approved → refunded / rejected
    status: Mapped[str] = mapped_column(String(16), default="requested", index=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(GUID())
    handled_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    handled_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    result_note: Mapped[str | None] = mapped_column(Text)
