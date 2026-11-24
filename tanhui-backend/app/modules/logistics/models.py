"""物流域模型：shipments / shipment_tracks（轨迹为仿真数据）。"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, UTCDatetime


class Shipment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "shipments"

    store_order_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("store_orders.id"), unique=True, index=True
    )
    carrier: Mapped[str] = mapped_column(String(64))
    tracking_no: Mapped[str] = mapped_column(String(64), index=True)
    # shipped / delivered / exception
    status: Mapped[str] = mapped_column(String(16), default="shipped")
    shipped_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    shipped_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDatetime())


class ShipmentTrack(UUIDPKMixin, Base):
    __tablename__ = "shipment_tracks"

    shipment_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    status: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)
