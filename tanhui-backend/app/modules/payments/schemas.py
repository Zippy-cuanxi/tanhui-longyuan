"""支付域 Schema（含消费者侧退款视图）。"""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class RefundOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    refund_no: str
    order_id: uuid.UUID
    store_order_id: uuid.UUID
    amount: Decimal
    reason: str
    status: str
    result_note: str | None = None
    created_at: datetime
    handled_at: datetime | None = None
