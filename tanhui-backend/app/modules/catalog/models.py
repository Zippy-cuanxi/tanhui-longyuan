"""商品域模型：categories / products / product_skus / product_images / product_audit_records。

商品状态机：
- draft → pending_review（商家提交审核）
- pending_review → approved / rejected（管理员审核）
- approved：is_listed 控制上下架（商家可自主切换）
- approved（任意上下架状态）→ removed（平台强制下架）
- rejected → pending_review（修改后重新提交）
"""
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, UTCDatetime, Amount

PRODUCT_STATUSES = ("draft", "pending_review", "approved", "rejected", "removed")


class Category(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("categories.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    icon_url: Mapped[str | None] = mapped_column(String(512))
    sort: Mapped[int] = mapped_column(default=0, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class Product(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "products"

    store_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("stores.id"), index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("categories.id"), index=True
    )
    # 可选关联助农项目（aid 域）
    aid_project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    title: Mapped[str] = mapped_column(String(128), index=True)
    subtitle: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    # 商家自主上下架：审核通过后默认未上架，需商家显式上架
    is_listed: Mapped[bool] = mapped_column(default=False)
    audit_reason: Mapped[str | None] = mapped_column(String(255))
    audited_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    audited_at: Mapped[datetime | None] = mapped_column(UTCDatetime())


class ProductSku(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "product_skus"

    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("products.id"), index=True
    )
    spec: Mapped[str] = mapped_column(String(128))  # 如 "500g*2袋"
    code: Mapped[str | None] = mapped_column(String(64))  # 商家自定义编码
    # 价格为服务端权威，下单时与 expected_unit_price 比对防篡改
    price: Mapped[Decimal] = mapped_column(Amount())
    is_active: Mapped[bool] = mapped_column(default=True)


class ProductImage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("products.id"), index=True
    )
    url: Mapped[str] = mapped_column(String(512))
    sort: Mapped[int] = mapped_column(Amount(), default=0)


class ProductAuditRecord(UUIDPKMixin, Base):
    __tablename__ = "product_audit_records"

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    action: Mapped[str] = mapped_column(String(32))  # submit/approve/reject/remove/relist
    reason: Mapped[str | None] = mapped_column(String(255))
    operator_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)
