"""管理员同步日志查询：支持按商品、结果、触发场景筛选，用于审计追溯。"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.catalog.schemas import ProductSyncLogOut
from app.modules.catalog.sync_models import ProductSyncLog

router = APIRouter(prefix="/admin/product-sync-logs", tags=["admin-catalog-sync"])


@router.get(
    "",
    response_model=ApiResponse[PageOut[ProductSyncLogOut]],
    summary="商品同步日志列表（审计追溯）",
)
def list_sync_logs(
    product_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None, pattern="^(success|failed)$"),
    trigger_type: str | None = Query(None, max_length=32),
    operator_id: uuid.UUID | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("product:read")),
    db: Session = Depends(get_db),
):
    stmt: Select = select(ProductSyncLog).order_by(ProductSyncLog.created_at.desc())
    if product_id is not None:
        stmt = stmt.where(ProductSyncLog.product_id == product_id)
    if status is not None:
        stmt = stmt.where(ProductSyncLog.status == status)
    if trigger_type is not None:
        stmt = stmt.where(ProductSyncLog.trigger_type == trigger_type)
    if operator_id is not None:
        stmt = stmt.where(ProductSyncLog.operator_id == operator_id)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(
            items=[ProductSyncLogOut.model_validate(item) for item in items],
            pagination=pagination,
        )
    )
