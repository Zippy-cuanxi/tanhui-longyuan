"""商家财务接口：本店结算单与财务汇总。"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, page_params, resolve_store_ctx
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.finance import service
from app.modules.finance.models import MerchantSettlement
from app.modules.users.models import User

router = APIRouter(prefix="/merchant/finance", tags=["merchant-finance"])


@router.get("/summary", response_model=ApiResponse[dict], summary="本店财务汇总")
def summary(
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "finance:read")
    return ApiResponse(data=service.store_summary(db, ctx.store_id))


@router.get("/settlements", response_model=ApiResponse[PageOut[dict]], summary="本店结算单")
def my_settlements(
    store_id: uuid.UUID | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "finance:read")
    stmt = (
        select(MerchantSettlement)
        .where(MerchantSettlement.store_id == ctx.store_id)
        .order_by(MerchantSettlement.created_at.desc())
    )
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(
            items=[
                {
                    "id": str(i.id),
                    "period_start": i.period_start,
                    "period_end": i.period_end,
                    "status": i.status,
                    "orders_total": str(i.orders_total),
                    "commission_total": str(i.commission_total),
                    "payable_total": str(i.payable_total),
                    "paid_at": i.paid_at,
                }
                for i in items
            ],
            pagination=pagination,
        )
    )
