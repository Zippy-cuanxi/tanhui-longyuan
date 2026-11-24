"""商家商品接口：CRUD、提交审核、上下架、SKU 管理、图片上传。"""
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, page_params, resolve_store_ctx
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.catalog import service
from app.modules.catalog import storage
from app.modules.catalog.models import Product
from app.modules.catalog.schemas import (
    ProductCreateIn,
    ProductDetailOut,
    ProductImageOut,
    ProductUpdateIn,
    SkuIn,
    SkuOut,
)
from app.modules.users.models import User

router = APIRouter(prefix="/merchant/products", tags=["merchant-catalog"])


@router.get("", response_model=ApiResponse[PageOut[ProductDetailOut]], summary="本店商品列表")
def list_my_products(
    status: str | None = Query(None),
    store_id: uuid.UUID | None = Query(None, description="多店铺时必填"),
    page_size_pair: tuple[int, int] = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:read")
    stmt = select(Product).where(Product.store_id == ctx.store_id).order_by(Product.created_at.desc())
    if status:
        stmt = stmt.where(Product.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(items=[ProductDetailOut.model_validate(p) for p in items], pagination=pagination)
    )


@router.post("", response_model=ApiResponse[ProductDetailOut], summary="新建商品（草稿）")
def create_product(
    payload: ProductCreateIn,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    product = service.create_product(db, ctx.store_id, payload)
    return ApiResponse(data=ProductDetailOut.model_validate(product))


@router.get("/{product_id}", response_model=ApiResponse[ProductDetailOut], summary="本店商品详情")
def get_my_product(
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:read")
    service._get_owned(db, ctx.store_id, product_id)
    product = db.get(Product, product_id)
    return ApiResponse(data=ProductDetailOut.model_validate(product))


@router.patch("/{product_id}", response_model=ApiResponse[ProductDetailOut], summary="修改商品信息")
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdateIn,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    product = service.update_product(db, ctx.store_id, product_id, payload)
    return ApiResponse(data=ProductDetailOut.model_validate(product))


@router.delete("/{product_id}", response_model=ApiResponse[None], summary="删除商品（仅草稿/驳回）")
def delete_product(
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    service.delete_product(db, ctx.store_id, product_id)
    return ApiResponse(message="已删除")


@router.post("/{product_id}/submit", response_model=ApiResponse[ProductDetailOut], summary="提交审核")
def submit_product(
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    product = service.submit_for_review(db, ctx.store_id, product_id)
    return ApiResponse(data=ProductDetailOut.model_validate(product))


@router.post("/{product_id}/list", response_model=ApiResponse[ProductDetailOut], summary="上架")
def list_product(
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    product = service.toggle_listing(db, ctx.store_id, product_id, True)
    return ApiResponse(data=ProductDetailOut.model_validate(product))


@router.post("/{product_id}/delist", response_model=ApiResponse[ProductDetailOut], summary="下架")
def delist_product(
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    product = service.toggle_listing(db, ctx.store_id, product_id, False)
    return ApiResponse(data=ProductDetailOut.model_validate(product))


@router.post("/{product_id}/skus", response_model=ApiResponse[SkuOut], summary="新增 SKU")
def add_sku(
    product_id: uuid.UUID,
    payload: SkuIn,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    sku = service.add_sku(db, ctx.store_id, product_id, payload)
    return ApiResponse(data=SkuOut.model_validate(sku))


@router.patch("/skus/{sku_id}/price", response_model=ApiResponse[SkuOut], summary="修改 SKU 价格（触发重新审核）")
def update_sku_price(
    sku_id: uuid.UUID,
    payload: dict,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from decimal import Decimal
    from pydantic import BaseModel, Field

    class PriceIn(BaseModel):
        price: Decimal = Field(..., gt=0)

    parsed = PriceIn(**payload)
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    sku = service.update_sku_price(db, ctx.store_id, sku_id, parsed.price)
    return ApiResponse(data=SkuOut.model_validate(sku))


@router.post(
    "/{product_id}/images", response_model=ApiResponse[ProductImageOut], summary="上传商品图片"
)
async def upload_image(
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = Query(None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    data, filename = await storage.validate_and_read(file)
    url = storage.get_storage().save(data, filename)
    img = service.add_image(db, ctx.store_id, product_id, url)
    return ApiResponse(data=ProductImageOut.model_validate(img))


@router.delete("/images/{image_id}", response_model=ApiResponse[None], summary="删除商品图片")
def delete_image(
    image_id: uuid.UUID,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = resolve_store_ctx(db, user, store_id, "product:manage")
    service.delete_image(db, ctx.store_id, image_id)
    return ApiResponse(message="已删除")
