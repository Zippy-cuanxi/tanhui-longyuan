"""购物车服务：加购/改量/删除/查询（价格与库存实时取服务端权威值）。"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.cart.models import Cart, CartItem
from app.modules.cart.schemas import CartItemAddIn, CartItemOut, CartOut
from app.modules.catalog.models import Product, ProductImage, ProductSku
from app.modules.inventory import service as inventory_service
from app.modules.stores.models import Store


def _get_cart(db: Session, user_id: uuid.UUID) -> Cart:
    cart = db.execute(select(Cart).where(Cart.user_id == user_id)).scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()
    return cart


def add_item(db: Session, user_id: uuid.UUID, payload: CartItemAddIn) -> CartItem:
    cart = _get_cart(db, user_id)
    sku = db.get(ProductSku, payload.sku_id)
    if sku is None or not sku.is_active:
        raise AppError("NOT_FOUND", "SKU 不存在或已停用")
    product = db.get(Product, sku.product_id)
    if product is None or product.status != "approved" or not product.is_listed:
        raise AppError("PRODUCT_NOT_PURCHASABLE", "商品不可购买")
    existing = db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.sku_id == sku.id)
    ).scalar_one_or_none()
    if existing:
        existing.quantity += payload.quantity
        existing.checked = True
        db.flush()
        return existing
    item = CartItem(cart_id=cart.id, sku_id=sku.id, quantity=payload.quantity, checked=True)
    db.add(item)
    db.flush()
    return item


def update_item(
    db: Session, user_id: uuid.UUID, item_id: uuid.UUID, quantity: int | None, checked: bool | None
) -> CartItem:
    item = _owned_item(db, user_id, item_id)
    if quantity is not None:
        item.quantity = quantity
    if checked is not None:
        item.checked = checked
    db.flush()
    return item


def remove_item(db: Session, user_id: uuid.UUID, item_id: uuid.UUID) -> None:
    item = _owned_item(db, user_id, item_id)
    db.delete(item)
    db.flush()


def _owned_item(db: Session, user_id: uuid.UUID, item_id: uuid.UUID) -> CartItem:
    cart = _get_cart(db, user_id)
    item = db.get(CartItem, item_id)
    if item is None or item.cart_id != cart.id:
        raise AppError("NOT_FOUND", "购物车条目不存在")
    return item


def get_cart(db: Session, user_id: uuid.UUID) -> CartOut:
    cart = _get_cart(db, user_id)
    rows = db.execute(
        select(CartItem, ProductSku, Product, Store)
        .join(ProductSku, ProductSku.id == CartItem.sku_id)
        .join(Product, Product.id == ProductSku.product_id)
        .join(Store, Store.id == Product.store_id)
        .where(CartItem.cart_id == cart.id)
        .order_by(CartItem.created_at.desc())
    ).all()
    items, subtotal, total_qty = [], 0, 0
    from decimal import Decimal

    checked_sum = Decimal("0.00")
    for item, sku, product, store in rows:
        image = db.execute(
            select(ProductImage.url)
            .where(ProductImage.product_id == product.id)
            .order_by(ProductImage.sort)
            .limit(1)
        ).scalar_one_or_none()
        stock = inventory_service.available_of(db, sku.id)
        items.append(
            CartItemOut(
                id=item.id,
                sku_id=sku.id,
                product_id=product.id,
                product_title=product.title,
                spec=sku.spec,
                image_url=image,
                current_price=sku.price,
                quantity=item.quantity,
                checked=item.checked,
                stock_available=stock,
                store_id=store.id,
                store_name=store.name,
            )
        )
        total_qty += item.quantity
        if item.checked:
            checked_sum += sku.price * item.quantity
    return CartOut(items=items, total_quantity=total_qty, checked_subtotal=checked_sum)
