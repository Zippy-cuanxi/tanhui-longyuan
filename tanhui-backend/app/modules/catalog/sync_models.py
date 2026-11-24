"""消费者端商品镜像模型与同步日志。

设计说明：
- 管理端商品库使用 `categories/products/product_skus/product_images`（审核与运营的权威源）；
- 消费者端使用 `consumer_*` 镜像表，由同步服务在商品审核通过后写入；
- 镜像表沿用源实体的 UUID 主键，既保证两端一一对应，也避免破坏购物车/订单对 SKU 的引用；
- `product_sync_logs` 完整记录每次同步的触发人、目标分类、结果、重试次数与耗时，供审计追溯。
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, Amount, UTCDatetime


class ConsumerCategory(UUIDPKMixin, TimestampMixin, Base):
    """消费者端商品分类镜像：层级、排序、图标与管理端完全一致。"""

    __tablename__ = "consumer_categories"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    name: Mapped[str] = mapped_column(String(64))
    icon_url: Mapped[str | None] = mapped_column(String(512))
    sort: Mapped[int] = mapped_column(default=0, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    synced_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)


class ConsumerProduct(UUIDPKMixin, TimestampMixin, Base):
    """消费者端商品镜像（全量字段）。"""

    __tablename__ = "consumer_products"

    store_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    aid_project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    title: Mapped[str] = mapped_column(String(128), index=True)
    subtitle: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="approved", index=True)
    is_listed: Mapped[bool] = mapped_column(default=False, index=True)
    audit_reason: Mapped[str | None] = mapped_column(String(255))
    audited_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    audited_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    # 同步元数据
    sync_version: Mapped[int] = mapped_column(default=1)
    source_hash: Mapped[str | None] = mapped_column(String(64))
    synced_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)


class ConsumerProductSku(UUIDPKMixin, Base):
    __tablename__ = "consumer_product_skus"

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    spec: Mapped[str] = mapped_column(String(128))
    code: Mapped[str | None] = mapped_column(String(64))
    price: Mapped[Decimal] = mapped_column(Amount())
    is_active: Mapped[bool] = mapped_column(default=True)
    # 审核通过时的可售库存快照（库存实时权威仍在 inventory 域，此处用于消费者端展示）
    stock: Mapped[int] = mapped_column(default=0)


class ConsumerProductImage(UUIDPKMixin, Base):
    __tablename__ = "consumer_product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    url: Mapped[str] = mapped_column(String(512))
    sort: Mapped[int] = mapped_column(Amount(), default=0)


class ProductSyncLog(UUIDPKMixin, Base):
    """商品同步审计日志：每次同步（含失败重试）一条记录。"""

    __tablename__ = "product_sync_logs"
    __table_args__ = (Index("ix_product_sync_logs_product_created", "product_id", "created_at"),)

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    operator_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    trigger_type: Mapped[str] = mapped_column(String(32), index=True)
    target_category_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    status: Mapped[str] = mapped_column(String(16), index=True)  # success / failed
    attempts: Mapped[int] = mapped_column(default=1)
    max_attempts: Mapped[int] = mapped_column(default=3)
    duration_ms: Mapped[int] = mapped_column(default=0)
    source_hash: Mapped[str | None] = mapped_column(String(64))
    target_hash: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, index=True)
