"""消费者订单接口：预览、创建（幂等）、取消、确认收货、退款申请。"""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, page_params
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.orders import service
from app.modules.orders.models import Order
from app.modules.orders.schemas import (
    CancelIn,
    CreateOrderIn,
    OrderOut,
    PreviewIn,
    PreviewOut,
    RefundRequestIn,
)
from app.modules.payments import service as payment_service
from app.modules.payments.schemas import RefundOut
from app.modules.users.models import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/preview", response_model=ApiResponse[PreviewOut], summary="订单预览（服务端计价）")
def preview(
    payload: PreviewIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApiResponse(data=service.preview(db, user.id, payload))


@router.post("", response_model=ApiResponse[OrderOut], summary="创建订单（多商家拆单+库存预占+幂等）")
def create_order(
    payload: CreateOrderIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = service.create_order(db, user.id, payload)
    return ApiResponse(data=service.build_order_out(db, order))


@router.get("", response_model=ApiResponse[PageOut[OrderOut]], summary="我的订单列表")
def my_orders(
    status: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    if status:
        stmt = stmt.where(Order.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(
            items=[service.build_order_out(db, o) for o in items], pagination=pagination
        )
    )


@router.get("/{order_id}", response_model=ApiResponse[OrderOut], summary="订单详情")
def order_detail(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = service._get_owned(db, user.id, order_id)
    return ApiResponse(data=service.build_order_out(db, order))


@router.post("/{order_id}/cancel", response_model=ApiResponse[OrderOut], summary="取消待支付订单")
def cancel_order(
    order_id: uuid.UUID,
    payload: CancelIn | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = service.cancel_by_user(
        db, user.id, order_id, payload.reason if payload else None
    )
    return ApiResponse(data=service.build_order_out(db, order))


@router.post(
    "/{order_id}/confirm-receipt", response_model=ApiResponse[OrderOut], summary="确认收货"
)
def confirm_receipt(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = service.confirm_receipt(db, user.id, order_id)
    return ApiResponse(data=service.build_order_out(db, order))


@router.post(
    "/{order_id}/refunds", response_model=ApiResponse[RefundOut], summary="申请退款（按店铺子单）"
)
def request_refund(
    order_id: uuid.UUID,
    payload: RefundRequestIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store_order_id = payload.store_order_id
    refund = payment_service.request_refund(
        db,
        user.id,
        order_id,
        store_order_id,
        payload.reason,
        Decimal(payload.amount) if payload.amount else None,
    )
    return ApiResponse(data=RefundOut.model_validate(refund))


@router.get("/{order_id}/refunds", response_model=ApiResponse[list[RefundOut]], summary="订单退款记录")
def order_refunds(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select as _select

    from app.modules.payments.models import Refund

    service._get_owned(db, user.id, order_id)
    refunds = db.execute(
        _select(Refund).where(Refund.order_id == order_id).order_by(Refund.created_at.desc())
    ).scalars()
    return ApiResponse(data=[RefundOut.model_validate(r) for r in refunds])
