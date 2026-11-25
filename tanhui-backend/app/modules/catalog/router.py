"""消费者商品接口：分类、商品列表、详情（仅审核通过且上架）。"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.catalog import service
from app.modules.catalog.schemas import (
    ProductDetailOut,
    ProductImageOut,
    ProductOut,
    SkuOut,
)
from app.modules.catalog.sync_models import (
    ConsumerProduct,
    ConsumerProductImage,
    ConsumerProductSku,
)
from app.modules.stores.models import Store

router = APIRouter(tags=["catalog"])


def _decorate(db: Session, products: list[ConsumerProduct]) -> list[ProductOut]:
    """补充列表展示字段：最低 SKU 价、封面图、店铺名（避免 N+1 用批量查询）。"""
    if not products:
        return []
    ids = [p.id for p in products]
    min_prices = dict(
        db.execute(
            select(ConsumerProductSku.product_id, func.min(ConsumerProductSku.price))
            .where(
                ConsumerProductSku.product_id.in_(ids),
                ConsumerProductSku.is_active == True,  # noqa: E712
            )
            .group_by(ConsumerProductSku.product_id)
        ).all()
    )
    covers = dict(
        db.execute(
            select(ConsumerProductImage.product_id, func.min(ConsumerProductImage.url))
            .where(ConsumerProductImage.product_id.in_(ids))
            .group_by(ConsumerProductImage.product_id)
        ).all()
    )
    store_ids = {p.store_id for p in products}
    store_names = dict(
        db.execute(
            select(Store.id, Store.name).where(Store.id.in_(store_ids))
        ).all()
    )
    out = []
    for p in products:
        item = ProductOut.model_validate(p)
        item.min_price = min_prices.get(p.id)
        item.cover_url = covers.get(p.id)
        item.store_name = store_names.get(p.store_id)
        out.append(item)
    return out


@router.get(
    "/catalog/version",
    response_model=ApiResponse[dict],
    summary="消费者商品目录版本（前端实时刷新）",
)
def catalog_version(db: Session = Depends(get_db)):
    """返回可见商品（已通过且已上架）的轻量指纹，供消费者端轮询感知变更。"""
    count, last_synced, sync_version = db.execute(
        select(
            func.count(ConsumerProduct.id),
            func.max(ConsumerProduct.synced_at),
            func.max(ConsumerProduct.sync_version),
        ).where(
            ConsumerProduct.status == "approved",
            ConsumerProduct.is_listed == True,  # noqa: E712
        )
    ).one()
    stamp = last_synced.isoformat() if last_synced is not None else "-"
    total = int(count or 0)
    return ApiResponse(
        data={
            "version": f"{total}:{stamp}:{int(sync_version or 0)}",
            "count": total,
            "updated_at": last_synced,
        }
    )


@router.get(
    "/products", response_model=ApiResponse[PageOut[ProductOut]], summary="商品列表（分页/筛选/排序）"
)
def list_products(
    category_id: uuid.UUID | None = Query(None),
    store_id: uuid.UUID | None = Query(None),
    keyword: str | None = Query(None, max_length=64),
    sort: str = Query("created_desc", pattern="^(created_desc|price_asc)$"),
    page_size_pair: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
):
    stmt = service.list_consumer_products(
        db, category_id=category_id, store_id=store_id, keyword=keyword, sort=sort
    )
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(data=PageOut(items=_decorate(db, items), pagination=pagination))


@router.get(
    "/products/{product_id}", response_model=ApiResponse[ProductDetailOut], summary="商品详情（含 SKU）"
)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product = service.get_consumer_product(db, product_id)
    detail = ProductDetailOut.model_validate(product)
    detail.skus = [
        SkuOut.model_validate(s)
        for s in db.execute(
            select(ConsumerProductSku).where(
                ConsumerProductSku.product_id == product.id,
                ConsumerProductSku.is_active == True,  # noqa: E712
            )
        ).scalars()
    ]
    detail.images = [
        ProductImageOut.model_validate(i)
        for i in db.execute(
            select(ConsumerProductImage)
            .where(ConsumerProductImage.product_id == product.id)
            .order_by(ConsumerProductImage.sort)
        ).scalars()
    ]
    detail.store_name = db.get(Store, product.store_id).name if db.get(Store, product.store_id) else None
    return ApiResponse(data=detail)


@router.get("/categories", response_model=ApiResponse[list], summary="商品分类（树形/列表）")
def list_categories(db: Session = Depends(get_db)):
    from datetime import datetime as _dt

    cats = service.list_categories(db)
    return ApiResponse(
        data=[
            {
                "id": str(c.id),
                "parent_id": str(c.parent_id) if c.parent_id else None,
                "name": c.name,
                "icon_url": c.icon_url,
                "sort": c.sort,
                "created_at": c.created_at,
            }
            for c in cats
        ]
    )
