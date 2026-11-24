"""订单域模型：orders(父) / store_orders(子) / order_items(快照) / order_status_logs。

多商家拆单：一次下单按店铺拆分为多个 store_orders，支付挂在父订单；
order_items 保存商品快照（标题/规格/单价），下单后不受商家改价影响。

订单状态机（父订单与子订单同构）：
  pending_payment → paid → shipped → completed
  pending_payment → cancelled（取消/超时）
  paid/shipped/completed → refunding → refunded / partially_refunded
"""
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, UTCDatetime, Amount

ORDER_STATUSES = (
    "pending_payment",
    "paid",
    "shipped",
    "completed",
    "cancelled",
    "refunding",
    "refunded",
    "partially_refunded",
)

# 合法状态迁移表（服务层强制校验）
ORDER_TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"paid", "cancelled"},
    "paid": {"shipped", "refunding"},
    "shipped": {"completed", "refunding"},
    "completed": {"refunding"},
    "refunding": {"refunded", "partially_refunded", "paid"},
    "refunded": set(),
    "partially_refunded": set(),
    "cancelled": set(),
}


class Order(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending_payment", index=True)
    # 收货信息快照（下单时冻结）
    receiver_name: Mapped[str] = mapped_column(String(64))
    receiver_phone: Mapped[str] = mapped_column(String(32))
    address: Mapped[str] = mapped_column(String(512))
    # 金额（全部服务端计算）
    items_total: Mapped[Decimal] = mapped_column(Amount())
    shipping_fee: Mapped[Decimal] = mapped_column(Amount())
    points_deduct: Mapped[Decimal] = mapped_column(Amount())
    points_used: Mapped[int] = mapped_column(Integer, default=0)
    pay_amount: Mapped[Decimal] = mapped_column(Amount())
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    remark: Mapped[str | None] = mapped_column(String(255))
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    paid_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    # 幂等键：同一用户同一 key 只会产生一笔订单（重复提交返回原订单）
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    idempotency_payload_hash: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_order_idem"),
    )


class StoreOrder(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "store_orders"

    store_order_no: Mapped[str] = mapped_column(String(32), unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("orders.id"), index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("stores.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending_payment", index=True)
    items_total: Mapped[Decimal] = mapped_column(Amount())
    shipping_fee: Mapped[Decimal] = mapped_column(Amount())
    pay_amount: Mapped[Decimal] = mapped_column(Amount())
    refund_amount: Mapped[Decimal] = mapped_column(Amount(), default=0)
    shipped_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDatetime())


class OrderItem(UUIDPKMixin, Base):
    __tablename__ = "order_items"

    store_order_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("store_orders.id"), index=True
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    # 商品快照：不随商品信息变化
    title: Mapped[str] = mapped_column(String(128))
    spec: Mapped[str] = mapped_column(String(128))
    image_url: Mapped[str | None] = mapped_column(String(512))
    unit_price: Mapped[Decimal] = mapped_column(Amount())
    quantity: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[Decimal] = mapped_column(Amount())


class OrderStatusLog(UUIDPKMixin, Base):
    __tablename__ = "order_status_logs"

    order_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    store_order_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(32))
    operator_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, index=True)

    __table_args__ = (Index("ix_order_status_order_created", "order_id", "created_at"),)
