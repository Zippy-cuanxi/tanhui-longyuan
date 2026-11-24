"""财务域模型：merchant_settlements / settlement_items / platform_ledger。

【仿真参数】佣金比例与结算周期见 config.py（COMMISSION_RATE / SETTLEMENT_PERIOD_DAYS），
业务确认后直接修改配置即可，无需改代码。
"""
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, UTCDatetime, Amount


class MerchantSettlement(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "merchant_settlements"
    __table_args__ = (
        UniqueConstraint("store_id", "period_start", "period_end", name="uq_settlement_period"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    period_start: Mapped[datetime] = mapped_column(UTCDatetime())
    period_end: Mapped[datetime] = mapped_column(UTCDatetime())
    # pending → confirmed → paid
    status: Mapped[str] = mapped_column(String(16), default="pending")
    orders_total: Mapped[Decimal] = mapped_column(Amount())
    commission_total: Mapped[Decimal] = mapped_column(Amount())
    payable_total: Mapped[Decimal] = mapped_column(Amount())
    generated_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    paid_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    note: Mapped[str | None] = mapped_column(Text)


class SettlementItem(UUIDPKMixin, Base):
    __tablename__ = "settlement_items"

    settlement_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    store_order_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    order_amount: Mapped[Decimal] = mapped_column(Amount())
    commission_amount: Mapped[Decimal] = mapped_column(Amount())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)


class PlatformLedger(UUIDPKMixin, Base):
    """平台台账（只追加，不更新不删除）。"""

    __tablename__ = "platform_ledger"

    # payment 支付入账 / commission 佣金 / refund 退款 / adjustment 调整
    entry_type: Mapped[str] = mapped_column(String(16), index=True)
    ref_type: Mapped[str] = mapped_column(String(32))
    ref_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    store_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    amount: Mapped[Decimal] = mapped_column(Amount())  # 正=平台收入, 负=平台支出
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, index=True)
