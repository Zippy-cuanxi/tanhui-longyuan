"""商家管理端接口：入驻审核 / 冻结（需 merchant:review 权限）。"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.merchants import service
from app.modules.merchants.schemas import MerchantOut, MerchantReviewIn
from app.modules.merchants.models import Merchant

router = APIRouter(prefix="/admin/merchants", tags=["admin-merchants"])


@router.get("", response_model=ApiResponse[PageOut[MerchantOut]], summary="商家列表（可按状态筛选）")
def list_merchants(
    status: str | None = Query(None, description="pending_review/approved/rejected/frozen"),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("merchant:read")),
    db: Session = Depends(get_db),
):
    stmt: Select = select(Merchant).order_by(Merchant.created_at.desc())
    if status:
        stmt = stmt.where(Merchant.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(items=[MerchantOut.model_validate(i) for i in items], pagination=pagination)
    )


@router.post(
    "/{merchant_id}/review", response_model=ApiResponse[MerchantOut], summary="审核/冻结/解冻商家"
)
def review_merchant(
    merchant_id: uuid.UUID,
    payload: MerchantReviewIn,
    admin=Depends(require_permissions("merchant:review")),
    db: Session = Depends(get_db),
):
    merchant = service.review(db, merchant_id, payload.action, payload.reason, admin.id)
    return ApiResponse(data=MerchantOut.model_validate(merchant))
