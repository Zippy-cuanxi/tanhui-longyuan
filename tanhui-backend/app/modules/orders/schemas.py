"""订单域 Schema。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.responses import MoneyOut


class OrderItemIn(BaseModel):
    sku_id: uuid.UUID
    quantity: int = Field(..., gt=0, le=999)
    expected_unit_price: str | None = Field(
        None, description="预览返回的单价；不一致时报 PRICE_CHANGED"
    )


class PreviewIn(BaseModel):
    items: list[OrderItemIn] = Field(..., min_length=1)
    use_points: bool = False
    address_id: uuid.UUID | None = None


class PreviewStoreOut(BaseModel):
    store_id: uuid.UUID
    store_name: str
    items_total: MoneyOut
    shipping_fee: MoneyOut
    items: list[dict]


class PreviewOut(BaseModel):
    items_total: MoneyOut
    shipping_fee: MoneyOut
    points_deduct: MoneyOut
    points_used: int
    pay_amount: MoneyOut
    stores: list[PreviewStoreOut]


class CreateOrderIn(BaseModel):
    address_id: uuid.UUID
    items: list[OrderItemIn] = Field(..., min_length=1)
    use_points: bool = False
    remark: str | None = Field(None, max_length=255)
    idempotency_key: str | None = Field(None, max_length=64)


class OrderItemOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    sku_id: uuid.UUID
    product_id: uuid.UUID
    title: str
    spec: str
    image_url: str | None = None
    unit_price: MoneyOut
    quantity: int
    subtotal: MoneyOut


class StoreOrderOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    store_order_no: str
    store_id: uuid.UUID
    status: str
    items_total: MoneyOut
    shipping_fee: MoneyOut
    pay_amount: MoneyOut
    refund_amount: MoneyOut
    shipped_at: datetime | None = None
    completed_at: datetime | None = None
    items: list[OrderItemOut] = []


class OrderOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    order_no: str
    status: str
    receiver_name: str
    receiver_phone: str
    address: str
    items_total: MoneyOut
    shipping_fee: MoneyOut
    points_deduct: MoneyOut
    points_used: int
    pay_amount: MoneyOut
    currency: str
    remark: str | None = None
    cancel_reason: str | None = None
    paid_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    store_orders: list[StoreOrderOut] = []


class ShipIn(BaseModel):
    carrier: str = Field(..., max_length=64)
    tracking_no: str = Field(..., max_length=64)


class CancelIn(BaseModel):
    reason: str | None = Field(None, max_length=255)


class RefundRequestIn(BaseModel):
    reason: str = Field(..., max_length=255)
    amount: str | None = Field(None, description="默认整单可退余额")
    store_order_id: uuid.UUID | None = Field(
        None, description="指定店铺子单；缺省=全部可退子单"
    )
