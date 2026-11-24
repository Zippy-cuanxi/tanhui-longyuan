"""消费者物流接口：按父订单查询发货单与轨迹。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.responses import ApiResponse
from app.modules.logistics import service
from app.modules.orders.models import Order, StoreOrder
from app.modules.users.models import User

router = APIRouter(prefix="/logistics", tags=["logistics"])


@router.get("/{order_id}", response_model=ApiResponse[list], summary="订单物流（发货单+轨迹）")
def order_logistics(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise AppError("NOT_FOUND", "订单不存在")
    so_ids = [
        so.id
        for so in db.query(StoreOrder).filter(StoreOrder.order_id == order_id).all()
    ]
    return ApiResponse(data=service.get_shipments_for_order(db, so_ids))
