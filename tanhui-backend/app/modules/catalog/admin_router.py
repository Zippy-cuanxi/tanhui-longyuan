"""管理员商品接口：待审核列表、审核通过/驳回、平台强制下架、同步状态与日志。"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.errors import AppError
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.catalog import service, sync_service
from app.modules.catalog.models import Product
from app.modules.catalog.schemas import (
    AuditIn,
    ProductAuditRecordOut,
    ProductDetailOut,
    ProductSyncLogOut,
)
from app.modules.catalog.sync_models import ConsumerProduct, ProductSyncLog

router = APIRouter(prefix="/admin/products", tags=["admin-catalog"])


@router.get("", response_model=ApiResponse[PageOut[ProductDetailOut]], summary="全部商品列表（可按状态筛选）")
def list_products(
    status: str | None = Query(None),
    store_id: uuid.UUID | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("product:read")),
    db: Session = Depends(get_db),
):
    stmt: Select = select(Product).order_by(Product.created_at.desc())
    if status:
        stmt = stmt.where(Product.status == status)
    if store_id:
        stmt = stmt.where(Product.store_id == store_id)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(items=[ProductDetailOut.model_validate(p) for p in items], pagination=pagination)
    )


@router.get("/{product_id}/audit-records", response_model=ApiResponse[list[ProductAuditRecordOut]], summary="商品审核历史")
def audit_records(
    product_id: uuid.UUID,
    _admin=Depends(require_permissions("product:read")),
    db: Session = Depends(get_db),
):
    from app.modules.catalog.models import ProductAuditRecord

    records = db.execute(
        select(ProductAuditRecord)
        .where(ProductAuditRecord.product_id == product_id)
        .order_by(ProductAuditRecord.created_at.desc())
    ).scalars()
    return ApiResponse(data=[ProductAuditRecordOut.model_validate(r) for r in records])


@router.post("/{product_id}/audit", response_model=ApiResponse[ProductDetailOut], summary="审核商品（通过/驳回/平台下架）")
def audit(
    product_id: uuid.UUID,
    payload: AuditIn,
    admin=Depends(require_permissions("product:approve", "product:remove")),
    db: Session = Depends(get_db),
):
    product = service.audit_product(db, product_id, payload.action, payload.reason, admin.id)
    data = ProductDetailOut.model_validate(product)
    outcome = getattr(product, "sync_outcome", None)
    if outcome is not None:
        data.sync_status = "success" if outcome.success else "failed"
        data.sync_attempts = outcome.attempts
        data.sync_error = outcome.error
        data.sync_message = outcome.message
        data.sync_log_id = outcome.log_id
        data.source_hash = outcome.source_hash
        data.consumer_hash = outcome.target_hash
        mirror = db.get(ConsumerProduct, product.id)
        data.synced_at = mirror.synced_at if mirror is not None else None
    return ApiResponse(data=data)


@router.post("/{product_id}/sync", response_model=ApiResponse[dict], summary="手动重同步商品到消费者端")
def resync_product(
    product_id: uuid.UUID,
    admin=Depends(require_permissions("product:approve")),
    db: Session = Depends(get_db),
):
    """支持两端数据漂移后的修复；失败返回 409 并附带重试与哈希信息。"""
    outcome = sync_service.sync_product(db, product_id, admin.id, "manual_resync")
    if not outcome.success:
        # 先提交失败日志，再抛业务异常（get_db 会回滚异常事务，不能吞掉审计记录）
        db.commit()
        raise AppError("CONFLICT", outcome.message, data=outcome.as_dict())
    return ApiResponse(data=outcome.as_dict(), message=outcome.message)


@router.get("/{product_id}/sync-status", response_model=ApiResponse[dict], summary="校验两端商品数据一致性")
def sync_status(
    product_id: uuid.UUID,
    _admin=Depends(require_permissions("product:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse(data=sync_service.consistency_report(db, product_id))


@router.get(
    "/{product_id}/sync-logs",
    response_model=ApiResponse[PageOut[ProductSyncLogOut]],
    summary="商品同步日志",
)
def sync_logs(
    product_id: uuid.UUID,
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("product:read")),
    db: Session = Depends(get_db),
):
    stmt: Select = (
        select(ProductSyncLog)
        .where(ProductSyncLog.product_id == product_id)
        .order_by(ProductSyncLog.created_at.desc())
    )
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(
            items=[ProductSyncLogOut.model_validate(item) for item in items],
            pagination=pagination,
        )
    )
