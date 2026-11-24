"""库存域模型：inventories / inventory_reservations / inventory_logs。

防超卖设计：
- 可售库存 = quantity_total - quantity_reserved（CHECK 约束保证非负且 reserved ≤ total）；
- 下单预占使用"条件 UPDATE"（UPDATE ... WHERE total - reserved >= n），
  数据库行级原子性保证并发下不超卖，不依赖应用层锁；
- 所有变更写 inventory_logs 流水（谁、为何、变了多少）。
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, UTCDatetime


class Inventory(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "inventories"
    __table_args__ = (
        CheckConstraint("quantity_reserved >= 0", name="ck_inv_reserved_nonneg"),
        CheckConstraint("quantity_total >= quantity_reserved", name="ck_inv_total_ge_reserved"),
    )

    sku_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("product_skus.id"), unique=True, index=True
    )
    quantity_total: Mapped[int] = mapped_column(default=0)
    quantity_reserved: Mapped[int] = mapped_column(default=0)


class InventoryReservation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "inventory_reservations"

    sku_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("product_skus.id"), index=True)
    store_order_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("store_orders.id"), index=True
    )
    quantity: Mapped[int] = mapped_column()
    # held 预占中 / consumed 已出库 / released 已释放(取消) / expired 超时过期
    status: Mapped[str] = mapped_column(String(16), default="held", index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDatetime())
    released_at: Mapped[datetime | None] = mapped_column(UTCDatetime())


class InventoryLog(UUIDPKMixin, Base):
    __tablename__ = "inventory_logs"

    sku_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    # adjust_add/adjust_remove/reserve/release/consume/expire
    change_type: Mapped[str] = mapped_column(String(32))
    delta_total: Mapped[int] = mapped_column(default=0)
    delta_reserved: Mapped[int] = mapped_column(default=0)
    ref_type: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    reason: Mapped[str | None] = mapped_column(Text)
    operator_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, index=True)
