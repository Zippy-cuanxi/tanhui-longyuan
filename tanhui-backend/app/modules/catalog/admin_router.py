"""管理员商品接口：待审核列表、审核通过/驳回、平台强制下架。"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.catalog import service
from app.modules.catalog.models import Product
from app.modules.catalog.schemas import AuditIn, ProductAuditRecordOut, ProductDetailOut

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
    return ApiResponse(data=ProductDetailOut.model_validate(product))
