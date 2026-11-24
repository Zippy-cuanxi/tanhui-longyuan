"""商家订单接口：本店订单列表/详情、发货。"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, page_params, resolve_store_ctx
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.orders import service
from app.modules.orders.models import StoreOrder
from app.modules.orders.schemas import ShipIn
from app.modules.users.models import User

router = APIRouter(prefix="/merchant/orders", tags=["merchant-orders"])


@router.get("", response_model=ApiResponse[PageOut[dict]], summary="本店订单列表")
def list_store_orders(
    status: str | None = Query(None),
    store_id: uuid.UUID | None = Query(None, description="多店铺时必填"),
    page_size_pair: tuple[int, int] = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "store:read")
    stmt = (
        select(StoreOrder)
        .where(StoreOrder.store_id == ctx.store_id)
        .order_by(StoreOrder.created_at.desc())
    )
    if status:
        stmt = stmt.where(StoreOrder.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    out = []
    for so in items:
        order = db.get(service.Order, so.order_id) if hasattr(service, "Order") else None
        out.append(
            {
                "id": str(so.id),
                "store_order_no": so.store_order_no,
                "order_id": str(so.order_id),
                "status": so.status,
                "items_total": str(so.items_total),
                "shipping_fee": str(so.shipping_fee),
                "pay_amount": str(so.pay_amount),
                "refund_amount": str(so.refund_amount),
                "shipped_at": so.shipped_at,
                "completed_at": so.completed_at,
                "created_at": so.created_at,
            }
        )
    return ApiResponse(data=PageOut(items=out, pagination=pagination))


@router.get("/{store_order_id}", response_model=ApiResponse[dict], summary="本店订单详情")
def store_order_detail(
    store_order_id: uuid.UUID,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "store:read")
    so = db.get(StoreOrder, store_order_id)
    if so is None or so.store_id != ctx.store_id:  # 越权防护
        from app.core.errors import AppError

        raise AppError("NOT_FOUND", "订单不存在")
    from app.modules.orders.models import OrderItem

    items = [
        {
            "title": i.title,
            "spec": i.spec,
            "unit_price": str(i.unit_price),
            "quantity": i.quantity,
            "subtotal": str(i.subtotal),
        }
        for i in db.execute(
            select(OrderItem).where(OrderItem.store_order_id == so.id)
        ).scalars()
    ]
    order = db.get(service.Order, so.order_id) if hasattr(service, "Order") else None
    return ApiResponse(
        data={
            "id": str(so.id),
            "store_order_no": so.store_order_no,
            "order_no": order.order_no if order else None,
            "status": so.status,
            "receiver_name": order.receiver_name if order else None,
            "receiver_phone": order.receiver_phone if order else None,
            "address": order.address if order else None,
            "remark": order.remark if order else None,
            "items_total": str(so.items_total),
            "shipping_fee": str(so.shipping_fee),
            "pay_amount": str(so.pay_amount),
            "refund_amount": str(so.refund_amount),
            "items": items,
            "shipped_at": so.shipped_at,
            "completed_at": so.completed_at,
            "created_at": so.created_at,
        }
    )


@router.post(
    "/{store_order_id}/ship", response_model=ApiResponse[dict], summary="发货（出库+物流单）"
)
def ship_order(
    store_order_id: uuid.UUID,
    payload: ShipIn,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "order:manage")
    so = service.ship(
        db, ctx.store_id, store_order_id, payload.carrier, payload.tracking_no, user.id
    )
    return ApiResponse(
        data={
            "id": str(so.id),
            "status": so.status,
            "store_order_no": so.store_order_no,
        }
    )


# ---------------- 商家售后（退款）视图 ----------------
@router.get(
    "/aftersales/all",
    response_model=ApiResponse[PageOut[dict]],
    summary="本店售后/退款列表（只读，处理由平台客服完成）",
)
def store_aftersales(
    status: str | None = Query(None),
    store_id: uuid.UUID | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.modules.payments.models import Refund

    ctx = resolve_store_ctx(db, user, store_id, "aftersale:manage")
    so_ids = [
        so.id
        for so in db.execute(
            select(StoreOrder.id).where(StoreOrder.store_id == ctx.store_id)
        ).scalars()
    ]
    stmt = select(Refund).where(Refund.store_order_id.in_(so_ids)).order_by(Refund.created_at.desc())
    if status:
        stmt = stmt.where(Refund.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(
            items=[
                {
                    "id": str(r.id),
                    "refund_no": r.refund_no,
                    "store_order_id": str(r.store_order_id),
                    "amount": str(r.amount),
                    "reason": r.reason,
                    "status": r.status,
                    "created_at": r.created_at,
                }
                for r in items
            ],
            pagination=pagination,
        )
    )
