"""商品服务：商家 CRUD 与状态机、管理员审核、消费者查询。"""
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.catalog.models import (
    Category,
    Product,
    ProductAuditRecord,
    ProductImage,
    ProductSku,
)
from app.modules.catalog.schemas import ProductCreateIn, ProductUpdateIn, SkuIn
from app.modules.inventory import service as inventory_service


# ---------------- 商家侧 ----------------
def create_product(db: Session, store_id: uuid.UUID, payload: ProductCreateIn) -> Product:
    product = Product(
        store_id=store_id,
        category_id=payload.category_id,
        aid_project_id=payload.aid_project_id,
        title=payload.title,
        subtitle=payload.subtitle,
        description=payload.description,
        status="draft",
    )
    db.add(product)
    db.flush()
    for sku_in in payload.skus:
        sku = ProductSku(
            product_id=product.id, spec=sku_in.spec, code=sku_in.code, price=sku_in.price
        )
        db.add(sku)
        db.flush()
        # 初始库存写入库存域（0 也建记录，统一由 inventory 域管理）
        inventory_service.ensure_inventory(db, sku.id, sku_in.initial_stock)
    db.flush()
    return product


def update_product(
    db: Session, store_id: uuid.UUID, product_id: uuid.UUID, payload: ProductUpdateIn
) -> Product:
    product = _get_owned(db, store_id, product_id)
    if product.status == "removed":
        raise AppError("CONFLICT", "平台下架商品不可修改")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.flush()
    return product


def add_sku(db: Session, store_id: uuid.UUID, product_id: uuid.UUID, sku_in: SkuIn) -> ProductSku:
    product = _get_owned(db, store_id, product_id)
    if product.status in ("approved", "removed"):
        # 已上架商品新增/改价 SKU 需重新审核（保守策略【仿真参数：业务可调整】）
        product.status = "pending_review"
        _audit_record(db, product.id, "submit", "新增SKU触发重新审核")
    sku = ProductSku(product_id=product.id, spec=sku_in.spec, code=sku_in.code, price=sku_in.price)
    db.add(sku)
    db.flush()
    inventory_service.ensure_inventory(db, sku.id, sku_in.initial_stock)
    return sku


def update_sku_price(
    db: Session, store_id: uuid.UUID, sku_id: uuid.UUID, price: Decimal
) -> ProductSku:
    sku = db.get(ProductSku, sku_id)
    if sku is None:
        raise AppError("NOT_FOUND", "SKU 不存在")
    product = _get_owned(db, store_id, sku.product_id)
    if sku.price != price and product.status == "approved":
        product.status = "pending_review"  # 改价需重新审核【仿真策略：业务可调整】
        _audit_record(db, product.id, "submit", "价格变更触发重新审核")
    sku.price = price
    db.flush()
    return sku


def submit_for_review(db: Session, store_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    product = _get_owned(db, store_id, product_id)
    if product.status not in ("draft", "rejected"):
        raise AppError("CONFLICT", "当前状态不可提交审核")
    product.status = "pending_review"
    _audit_record(db, product.id, "submit")
    db.flush()
    return product


def toggle_listing(
    db: Session, store_id: uuid.UUID, product_id: uuid.UUID, listed: bool
) -> Product:
    product = _get_owned(db, store_id, product_id)
    if product.status != "approved":
        raise AppError("CONFLICT", "仅审核通过的商品可上下架")
    product.is_listed = listed
    _audit_record(db, product.id, "relist" if listed else "delist")
    db.flush()
    return product


def delete_product(db: Session, store_id: uuid.UUID, product_id: uuid.UUID) -> None:
    """商家删除：仅草稿/驳回状态可物理删除，其余仅允许下架。"""
    product = _get_owned(db, store_id, product_id)
    if product.status not in ("draft", "rejected"):
        raise AppError("CONFLICT", "已进入审核流程的商品只能下架，不能删除")
    db.delete(product)
    db.flush()


def add_image(db: Session, store_id: uuid.UUID, product_id: uuid.UUID, url: str) -> ProductImage:
    _get_owned(db, store_id, product_id)
    count = db.execute(
        select(func.count()).select_from(ProductImage).where(ProductImage.product_id == product_id)
    ).scalar_one()
    img = ProductImage(product_id=product_id, url=url, sort=count)
    db.add(img)
    db.flush()
    return img


def delete_image(db: Session, store_id: uuid.UUID, image_id: uuid.UUID) -> None:
    img = db.get(ProductImage, image_id)
    if img is None:
        raise AppError("NOT_FOUND", "图片不存在")
    _get_owned(db, store_id, img.product_id)
    db.delete(img)
    db.flush()


# ---------------- 管理员侧 ----------------
def audit_product(
    db: Session, product_id: uuid.UUID, action: str, reason: str | None, operator_id: uuid.UUID
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise AppError("NOT_FOUND", "商品不存在")
    if action == "approve":
        if product.status != "pending_review":
            raise AppError("CONFLICT", "仅待审核商品可通过")
        product.status = "approved"
    elif action == "reject":
        if product.status != "pending_review":
            raise AppError("CONFLICT", "仅待审核商品可驳回")
        product.status = "rejected"
        product.audit_reason = reason or "不符合规范"
    elif action == "remove":
        if product.status in ("draft",):
            raise AppError("CONFLICT", "草稿商品无需平台下架")
        product.status = "removed"
        product.audit_reason = reason
    else:
        raise AppError("VALIDATION_ERROR", "未知操作")
    from app.core.base import utcnow

    product.audited_by = operator_id
    product.audited_at = utcnow()
    _audit_record(db, product.id, action, reason, operator_id)
    audit_service.log_operation(
        db, operator_id=operator_id, action=f"product.{action}",
        resource="product", resource_id=str(product_id), detail={"reason": reason},
    )
    db.flush()
    return product


# ---------------- 消费者侧 ----------------
def list_consumer_products(
    db: Session,
    *,
    category_id: uuid.UUID | None = None,
    store_id: uuid.UUID | None = None,
    keyword: str | None = None,
    sort: str = "created_desc",
):
    stmt = (
        select(Product)
        .where(Product.status == "approved", Product.is_listed == True)  # noqa: E712
        .order_by(Product.created_at.desc())
    )
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if store_id:
        stmt = stmt.where(Product.store_id == store_id)
    if keyword:
        stmt = stmt.where(Product.title.like(f"%{keyword}%"))
    if sort == "price_asc":
        # 简化排序：按最低 SKU 价（用子查询近似）
        stmt = stmt.order_by(
            select(func.min(ProductSku.price))
            .where(ProductSku.product_id == Product.id)
            .correlate(Product)
            .scalar_subquery()
            .asc()
        )
    return stmt


def get_consumer_product(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.status != "approved" or not product.is_listed:
        raise AppError("NOT_FOUND", "商品不存在或未上架")
    return product


def list_categories(db: Session) -> list[Category]:
    return list(
        db.execute(select(Category).where(Category.is_active == True).order_by(Category.sort)).scalars()  # noqa: E712
    )


# ---------------- 内部 ----------------
def _get_owned(db: Session, store_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    """越权防护：商品必须属于当前店铺。"""
    product = db.get(Product, product_id)
    if product is None or product.store_id != store_id:
        raise AppError("NOT_FOUND", "商品不存在")
    return product


def _audit_record(
    db: Session,
    product_id: uuid.UUID,
    action: str,
    reason: str | None = None,
    operator_id: uuid.UUID | None = None,
) -> None:
    db.add(
        ProductAuditRecord(
            product_id=product_id, action=action, reason=reason, operator_id=operator_id
        )
    )


def create_category(
    db: Session,
    name: str,
    parent_id: uuid.UUID | None = None,
    icon_url: str | None = None,
    sort: int = 0,
) -> Category:
    """创建商品分类（幂等：同名同级直接返回已有分类）。"""
    stmt = select(Category).where(Category.name == name)
    if parent_id is not None:
        stmt = stmt.where(Category.parent_id == parent_id)
    else:
        stmt = stmt.where(Category.parent_id.is_(None))
    exists = db.execute(stmt).scalar_one_or_none()
    if exists is not None:
        return exists
    cat = Category(parent_id=parent_id, name=name, icon_url=icon_url, sort=sort)
    db.add(cat)
    db.flush()
    return cat
