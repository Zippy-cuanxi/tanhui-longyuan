"""财务管理端接口：结算单生成/确认/打款、平台台账。"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.errors import AppError
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.finance import service
from app.modules.finance.models import MerchantSettlement, PlatformLedger
from app.modules.stores.models import Store

router = APIRouter(prefix="/admin/finance", tags=["admin-finance"])


class GenerateIn(BaseModel):
    store_id: uuid.UUID
    period_start: datetime
    period_end: datetime


@router.post(
    "/settlements/generate", response_model=ApiResponse[dict], summary="生成结算单（仿真佣金规则）"
)
def generate(
    payload: GenerateIn,
    admin=Depends(require_permissions("finance:manage")),
    db: Session = Depends(get_db),
):
    if db.get(Store, payload.store_id) is None:
        raise AppError("NOT_FOUND", "店铺不存在")
    s = service.generate_settlement(
        db, payload.store_id, payload.period_start, payload.period_end, admin.id
    )
    return ApiResponse(
        data={
            "id": str(s.id),
            "store_id": str(s.store_id),
            "status": s.status,
            "orders_total": str(s.orders_total),
            "commission_total": str(s.commission_total),
            "payable_total": str(s.payable_total),
        }
    )


@router.get("/settlements", response_model=ApiResponse[PageOut[dict]], summary="结算单列表")
def list_settlements(
    status: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("finance:read")),
    db: Session = Depends(get_db),
):
    stmt = select(MerchantSettlement).order_by(MerchantSettlement.created_at.desc())
    if status:
        stmt = stmt.where(MerchantSettlement.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(
            items=[
                {
                    "id": str(i.id),
                    "store_id": str(i.store_id),
                    "period_start": i.period_start,
                    "period_end": i.period_end,
                    "status": i.status,
                    "orders_total": str(i.orders_total),
                    "commission_total": str(i.commission_total),
                    "payable_total": str(i.payable_total),
                }
                for i in items
            ],
            pagination=pagination,
        )
    )


@router.post(
    "/settlements/{settlement_id}/confirm", response_model=ApiResponse[dict], summary="确认结算单"
)
def confirm(
    settlement_id: uuid.UUID,
    admin=Depends(require_permissions("finance:manage")),
    db: Session = Depends(get_db),
):
    s = service.confirm_settlement(db, settlement_id, admin.id)
    return ApiResponse(data={"id": str(s.id), "status": s.status})


@router.post(
    "/settlements/{settlement_id}/mark-paid",
    response_model=ApiResponse[dict],
    summary="标记打款（仿真，无真实资金流）",
)
def mark_paid(
    settlement_id: uuid.UUID,
    admin=Depends(require_permissions("finance:manage")),
    db: Session = Depends(get_db),
):
    s = service.mark_settlement_paid(db, settlement_id, admin.id)
    return ApiResponse(data={"id": str(s.id), "status": s.status})


@router.get("/ledger", response_model=ApiResponse[PageOut[dict]], summary="平台台账流水")
def ledger(
    entry_type: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("finance:read")),
    db: Session = Depends(get_db),
):
    stmt = select(PlatformLedger).order_by(PlatformLedger.created_at.desc())
    if entry_type:
        stmt = stmt.where(PlatformLedger.entry_type == entry_type)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(
            items=[
                {
                    "id": str(i.id),
                    "entry_type": i.entry_type,
                    "ref_type": i.ref_type,
                    "order_id": str(i.order_id) if i.order_id else None,
                    "amount": str(i.amount),
                    "note": i.note,
                    "created_at": i.created_at,
                }
                for i in items
            ],
            pagination=pagination,
        )
    )
