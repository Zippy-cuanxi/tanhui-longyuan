"""支付接口：支付单查询/发起、Mock 沙箱支付工具、渠道回调接收。"""
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.responses import ApiResponse
from app.modules.orders import service as order_service
from app.modules.orders.models import Order
from app.modules.payments import service
from app.modules.payments.models import PaymentOrder
from app.modules.payments.providers import MockSandboxProvider, get_provider
from app.modules.users.models import User

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    pay_no: str
    order_id: uuid.UUID
    amount: Decimal
    currency: str
    status: str
    provider: str
    expires_at: datetime
    paid_at: datetime | None = None
    pay_url: str | None = None


class InitPayIn(BaseModel):
    order_id: str = Field(..., description="订单 ID（UUID）")


@router.get("/{pay_no}", response_model=ApiResponse[PaymentOut], summary="查询支付单状态")
def get_payment(
    pay_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pay = service.get_payment_for_user(db, user.id, pay_no)
    out = PaymentOut.model_validate(pay)
    if pay.status == "pending":
        out.pay_url = get_provider().create_payment_url(pay.pay_no, pay.amount, pay.currency)
    return ApiResponse(data=out)


@router.post(
    "/{order_id}/init", response_model=ApiResponse[PaymentOut], summary="发起/重新发起支付"
)
def init_payment(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import uuid as _uuid

    try:
        oid = _uuid.UUID(order_id)
    except ValueError:
        raise AppError("VALIDATION_ERROR", "订单 ID 格式错误")
    order = db.get(Order, oid)
    if order is None or order.user_id != user.id:
        raise AppError("NOT_FOUND", "订单不存在")
    if order.status != "pending_payment":
        raise AppError("ORDER_STATE_INVALID", "当前订单状态无需支付")
    pay = service.get_or_create_active_payment(db, order)
    out = PaymentOut.model_validate(pay)
    out.pay_url = get_provider().create_payment_url(pay.pay_no, pay.amount, pay.currency)
    return ApiResponse(data=out)


class MockPayIn(BaseModel):
    pay_no: str


@router.post(
    "/mock/pay",
    response_model=ApiResponse[dict],
    summary="【SANDBOX 仿真】模拟用户完成支付并触发签名回调",
    description="仅沙箱环境可用：模拟渠道收银台支付成功，生成 HMAC-SHA256 签名回调并走真实回调处理链路。",
)
def mock_pay(
    payload: MockPayIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.config import settings as _s

    if _s.ENV == "prod":
        raise AppError("FORBIDDEN", "生产环境禁用沙箱支付工具")
    result = service.mock_pay(db, user.id, payload.pay_no)
    return ApiResponse(data=result)


class CallbackIn(BaseModel):
    """渠道回调载荷（Mock 沙箱格式，与真实渠道字段对齐）。"""

    pay_no: str
    merchant_no: str
    trade_no: str
    amount: str
    currency: str
    status: str
    timestamp: str
    sign: str


@router.post(
    "/callback/mock",
    response_model=dict,
    summary="【SANDBOX】Mock 渠道支付回调（验签+金额核对+幂等）",
    include_in_schema=True,
)
def payment_callback(payload: CallbackIn, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"sign"})
    result = service.process_callback(db, data, payload.sign)
    return result
