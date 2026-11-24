"""管理员订单/退款接口。"""
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.orders import service as order_service
from app.modules.orders.models import Order
from app.modules.payments import service
from app.modules.payments.models import Refund

router = APIRouter(prefix="/admin", tags=["admin-orders"])


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
    requested_by: uuid.UUID
    handled_by: uuid.UUID | None = None
    handled_at: datetime | None = None
    result_note: str | None = None
    created_at: datetime


@router.get("/orders", response_model=ApiResponse[PageOut[dict]], summary="全部订单列表")
def list_orders(
    status: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("order:read")),
    db: Session = Depends(get_db),
):
    stmt = select(Order).order_by(Order.created_at.desc())
    if status:
        stmt = stmt.where(Order.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(
            items=[
                {
                    "id": str(o.id),
                    "order_no": o.order_no,
                    "status": o.status,
                    "user_id": str(o.user_id),
                    "pay_amount": str(o.pay_amount),
                    "created_at": o.created_at,
                }
                for o in items
            ],
            pagination=pagination,
        )
    )


@router.get("/orders/{order_id}", response_model=ApiResponse[dict], summary="订单详情")
def order_detail(
    order_id: uuid.UUID,
    _admin=Depends(require_permissions("order:read")),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        from app.core.errors import AppError

        raise AppError("NOT_FOUND", "订单不存在")
    out = order_service.build_order_out(db, order)
    return ApiResponse(data=out.model_dump(mode="json"))


@router.get("/refunds", response_model=ApiResponse[PageOut[RefundOut]], summary="退款单列表")
def list_refunds(
    status: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("order:read")),
    db: Session = Depends(get_db),
):
    stmt = select(Refund).order_by(Refund.created_at.desc())
    if status:
        stmt = stmt.where(Refund.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(items=[RefundOut.model_validate(i) for i in items], pagination=pagination)
    )


class RefundHandleIn(BaseModel):
    action: str  # approve / reject
    note: str | None = None


@router.post(
    "/refunds/{refund_id}/handle", response_model=ApiResponse[RefundOut], summary="处理退款（approve=Mock原路退回）"
)
def handle_refund(
    refund_id: uuid.UUID,
    payload: RefundHandleIn,
    request: Request,
    admin=Depends(require_permissions("refund:approve")),
    db: Session = Depends(get_db),
):
    refund = service.handle_refund(
        db, refund_id, payload.action, payload.note, admin.id, request
    )
    return ApiResponse(data=RefundOut.model_validate(refund))
