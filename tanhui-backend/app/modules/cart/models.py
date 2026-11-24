"""购物车模型：carts / cart_items（一人一车）。"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin
from app.core.types import GUID


class Cart(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "carts"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), unique=True)


class CartItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"

    cart_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("carts.id"), index=True)
    sku_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("product_skus.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    checked: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("cart_id", "sku_id", name="uq_cart_sku"),)
