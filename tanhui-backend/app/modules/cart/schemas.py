"""购物车 Schema。"""
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.responses import MoneyOut


class CartItemAddIn(BaseModel):
    sku_id: uuid.UUID
    quantity: int = Field(..., gt=0, le=999)


class CartItemUpdateIn(BaseModel):
    quantity: int | None = Field(None, gt=0, le=999)
    checked: bool | None = None


class CartItemOut(BaseModel):
    id: uuid.UUID
    sku_id: uuid.UUID
    product_id: uuid.UUID
    product_title: str
    spec: str
    image_url: str | None = None
    current_price: MoneyOut  # 服务端实时价（结算依据）
    quantity: int
    checked: bool
    stock_available: int
    store_id: uuid.UUID
    store_name: str


class CartOut(BaseModel):
    items: list[CartItemOut]
    total_quantity: int
    checked_subtotal: MoneyOut  # 勾选商品实时小计
