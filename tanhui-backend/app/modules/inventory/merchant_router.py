"""商家库存接口：库存查询、手工调整（记流水+审计）、流水查询。"""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, page_params, resolve_store_ctx
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.catalog.models import Product, ProductSku
from app.modules.inventory import service
from app.modules.inventory.models import Inventory, InventoryLog
from app.modules.users.models import User

router = APIRouter(prefix="/merchant/inventory", tags=["merchant-inventory"])


class InventoryItemOut(BaseModel):
    sku_id: uuid.UUID
    product_id: uuid.UUID
    product_title: str
    spec: str
    quantity_total: int
    quantity_reserved: int
    quantity_available: int


class AdjustIn(BaseModel):
    sku_id: uuid.UUID
    delta: int  # 正数入库 / 负数出库
    reason: str = Field(..., min_length=2, max_length=255, description="调整原因（必填）")


class InventoryLogOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    sku_id: uuid.UUID
    change_type: str
    delta_total: int
    delta_reserved: int
    reason: str | None = None
    operator_id: uuid.UUID | None = None
    created_at: object


def _store_skus(db: Session, store_id: uuid.UUID):
    return (
        select(ProductSku, Product)
        .join(Product, Product.id == ProductSku.product_id)
        .where(Product.store_id == store_id)
    )


@router.get("", response_model=ApiResponse[list[InventoryItemOut]], summary="本店库存列表")
def list_inventory(
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "store:read")
    rows = db.execute(_store_skus(db, ctx.store_id)).all()
    invs = {
        i.sku_id: i
        for i in db.execute(
            select(Inventory).where(Inventory.sku_id.in_([sku.id for sku, _ in rows]))
        ).scalars()
    }
    out = []
    for sku, product in rows:
        inv = invs.get(sku.id)
        total = inv.quantity_total if inv else 0
        reserved = inv.quantity_reserved if inv else 0
        out.append(
            InventoryItemOut(
                sku_id=sku.id,
                product_id=product.id,
                product_title=product.title,
                spec=sku.spec,
                quantity_total=total,
                quantity_reserved=reserved,
                quantity_available=total - reserved,
            )
        )
    return ApiResponse(data=out)


@router.post("/adjust", response_model=ApiResponse[InventoryItemOut], summary="调整库存（记流水）")
def adjust_inventory(
    payload: AdjustIn,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "inventory:manage")
    # 越权防护：SKU 必须属于本店
    sku = db.execute(
        select(ProductSku)
        .join(Product, Product.id == ProductSku.product_id)
        .where(ProductSku.id == payload.sku_id, Product.store_id == ctx.store_id)
    ).scalar_one_or_none()
    if sku is None:
        from app.core.errors import AppError

        raise AppError("NOT_FOUND", "SKU 不存在或不属于本店")
    service.adjust(db, payload.sku_id, payload.delta, payload.reason, user.id)
    inv = service.get_or_create(db, payload.sku_id)
    product = db.get(Product, sku.product_id)
    return ApiResponse(
        data=InventoryItemOut(
            sku_id=sku.id,
            product_id=product.id,
            product_title=product.title,
            spec=sku.spec,
            quantity_total=inv.quantity_total,
            quantity_reserved=inv.quantity_reserved,
            quantity_available=inv.quantity_total - inv.quantity_reserved,
        )
    )


@router.get("/logs", response_model=ApiResponse[PageOut[InventoryLogOut]], summary="库存流水")
def list_logs(
    sku_id: uuid.UUID | None = Query(None),
    store_id: uuid.UUID | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "store:read")
    sku_ids = [s.id for s, _ in db.execute(_store_skus(db, ctx.store_id)).all()]
    stmt = select(InventoryLog).where(InventoryLog.sku_id.in_(sku_ids)).order_by(InventoryLog.created_at.desc())
    if sku_id:
        stmt = stmt.where(InventoryLog.sku_id == sku_id)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(items=[InventoryLogOut.model_validate(i) for i in items], pagination=pagination)
    )
