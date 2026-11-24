"""订单服务：服务端计价、多商家拆单、库存预占、状态机、幂等。

核心原则：
- 价格/运费/积分抵扣全部服务端计算，客户端仅可传 expected_unit_price 用于比对；
- 库存预占失败则整单回滚（全有或全无）；
- 状态迁移必须走 _transition()，非法迁移抛 ORDER_STATE_INVALID 并记录日志表。
"""
import hashlib
import json
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.base import gen_order_no, utcnow
from app.core.config import settings
from app.core.errors import AppError
from app.core.types import q2
from app.modules.catalog.models import Product, ProductImage, ProductSku
from app.modules.inventory import service as inventory_service
from app.modules.notifications import service as notify_service
from app.modules.orders.models import (
    ORDER_TRANSITIONS,
    Order,
    OrderItem,
    OrderStatusLog,
    StoreOrder,
)
from app.modules.orders.schemas import CreateOrderIn, PreviewIn, PreviewOut, PreviewStoreOut
from app.modules.points import service as points_service
from app.modules.stores.models import Store
from app.modules.users.models import UserAddress


# ---------------- 计价（preview 与 create 共用，保证一致）----------------
def _load_lines(db: Session, payload_items) -> list[dict]:
    """加载并校验下单条目：商品可购、SKU 有效、价格比对。"""
    lines = []
    for it in payload_items:
        sku = db.get(ProductSku, it.sku_id)
        if sku is None or not sku.is_active:
            raise AppError("NOT_FOUND", f"SKU {it.sku_id} 不存在或已停用")
        product = db.get(Product, sku.product_id)
        if product is None or product.status != "approved" or not product.is_listed:
            raise AppError("PRODUCT_NOT_PURCHASABLE", f"商品「{product.title if product else it.sku_id}」不可购买")
        store = db.get(Store, product.store_id)
        if store is None or store.status != "active":
            raise AppError("PRODUCT_NOT_PURCHASABLE", f"商品「{product.title}」所属店铺已停业")
        if it.expected_unit_price is not None:
            if q2(Decimal(it.expected_unit_price)) != q2(sku.price):
                raise AppError(
                    "PRICE_CHANGED",
                    f"商品「{product.title}」价格已变化，请重新确认",
                    data={"sku_id": str(sku.id), "current_price": f"{q2(sku.price):.2f}"},
                )
        stock = inventory_service.available_of(db, sku.id)
        if stock < it.quantity:
            raise AppError(
                "INSUFFICIENT_STOCK",
                f"商品「{product.title}」库存不足（剩余 {stock}）",
                data={"sku_id": str(sku.id), "available": stock},
            )
        image = db.execute(
            select(ProductImage.url)
            .where(ProductImage.product_id == product.id)
            .order_by(ProductImage.sort)
            .limit(1)
        ).scalar_one_or_none()
        lines.append(
            {
                "sku": sku,
                "product": product,
                "store": store,
                "quantity": it.quantity,
                "unit_price": q2(sku.price),
                "subtotal": q2(sku.price * it.quantity),
                "image_url": image,
            }
        )
    return lines


def _group_by_store(lines: list[dict]) -> dict[uuid.UUID, list[dict]]:
    grouped: dict[uuid.UUID, list[dict]] = {}
    for line in lines:
        grouped.setdefault(line["store"].id, []).append(line)
    return grouped


def _shipping_fee(subtotal: Decimal) -> Decimal:
    """单店运费【仿真规则】：满 SHIPPING_FREE_THRESHOLD 包邮，否则收基础运费。

    业务规则确认后直接修改 settings 中对应参数，或在此扩展按重量/地区计费。
    """
    if subtotal >= settings.decimal("SHIPPING_FREE_THRESHOLD"):
        return Decimal("0.00")
    return q2(settings.decimal("SHIPPING_FLAT_FEE"))


def _points_plan(db: Session, user_id: uuid.UUID, base: Decimal, use_points: bool) -> tuple[Decimal, int]:
    """绿豆抵扣【仿真规则】：最多抵扣商品金额的 POINTS_DEDUCT_MAX_PERCENT。"""
    if not use_points or not settings.POINTS_DEDUCTION_ENABLED:
        return Decimal("0.00"), 0
    rate = settings.decimal("POINTS_DEDUCT_RATE")  # N 绿豆 = 1 元
    if rate <= 0:
        return Decimal("0.00"), 0
    cap = base * settings.decimal("POINTS_DEDUCT_MAX_PERCENT")
    max_points = int((cap * rate).to_integral_value(rounding="ROUND_DOWN"))
    balance = points_service.get_balance(db, user_id)
    usable = min(balance, max_points)
    if usable <= 0:
        return Decimal("0.00"), 0
    return q2(Decimal(usable) / rate), usable


def preview(db: Session, user_id: uuid.UUID, payload: PreviewIn) -> PreviewOut:
    lines = _load_lines(db, payload.items)
    grouped = _group_by_store(lines)
    items_total = q2(sum((l["subtotal"] for l in lines), Decimal("0")))
    shipping = q2(sum((_shipping_fee(q2(sum(l["subtotal"] for l in g))) for g in grouped.values()), Decimal("0")))
    deduct, points_used = _points_plan(db, user_id, items_total, payload.use_points)
    pay = q2(items_total + shipping - deduct)
    stores_out = []
    for store_id, g in grouped.items():
        sub = q2(sum(l["subtotal"] for l in g))
        stores_out.append(
            PreviewStoreOut(
                store_id=store_id,
                store_name=g[0]["store"].name,
                items_total=sub,
                shipping_fee=_shipping_fee(sub),
                items=[
                    {
                        "sku_id": str(l["sku"].id),
                        "title": l["product"].title,
                        "spec": l["sku"].spec,
                        "unit_price": f"{l['unit_price']:.2f}",
                        "quantity": l["quantity"],
                        "subtotal": f"{l['subtotal']:.2f}",
                    }
                    for l in g
                ],
            )
        )
    return PreviewOut(
        items_total=items_total,
        shipping_fee=shipping,
        points_deduct=deduct,
        points_used=points_used,
        pay_amount=pay,
        stores=stores_out,
    )


# ---------------- 下单 ----------------
def _payload_hash(payload: CreateOrderIn) -> str:
    body = {
        "address_id": str(payload.address_id),
        "use_points": payload.use_points,
        "items": sorted(
            [
                {"sku_id": str(i.sku_id), "quantity": i.quantity, "price": i.expected_unit_price}
                for i in payload.items
            ],
            key=lambda x: x["sku_id"],
        ),
    }
    return hashlib.sha256(json.dumps(body, ensure_ascii=False).encode()).hexdigest()


def create_order(db: Session, user_id: uuid.UUID, payload: CreateOrderIn) -> Order:
    # 1) 幂等：同 key 同内容返回原订单；同 key 不同内容报冲突
    if payload.idempotency_key:
        existing = db.execute(
            select(Order).where(
                Order.user_id == user_id, Order.idempotency_key == payload.idempotency_key
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.idempotency_payload_hash != _payload_hash(payload):
                raise AppError("IDEMPOTENCY_CONFLICT", "幂等键已用于不同请求")
            return existing

    # 2) 收货地址校验（归属当前用户）
    address = db.get(UserAddress, payload.address_id)
    if address is None or address.user_id != user_id:
        raise AppError("NOT_FOUND", "收货地址不存在")

    # 3) 服务端计价（含价格比对、库存预检）
    lines = _load_lines(db, payload.items)
    grouped = _group_by_store(lines)
    items_total = q2(sum((l["subtotal"] for l in lines), Decimal("0")))
    shipping = q2(
        sum(
            (_shipping_fee(q2(sum(l["subtotal"] for l in g))) for g in grouped.values()),
            Decimal("0"),
        )
    )
    deduct, points_used = _points_plan(db, user_id, items_total, payload.use_points)
    pay_amount = q2(items_total + shipping - deduct)
    if pay_amount < 0:
        pay_amount = Decimal("0.00")

    # 4) 扣减绿豆（若使用）
    if points_used > 0:
        points_service.spend_for_order(
            db, user_id, points_used,
            idempotency_key=None,  # 订单尚未创建，取消时全额返还
            note="下单抵扣",
        )

    # 5) 创建父订单 + 子订单 + 条目快照
    order = Order(
        order_no=gen_order_no("TH"),
        user_id=user_id,
        receiver_name=address.receiver,
        receiver_phone=address.phone,
        address=f"{address.province}{address.city or ''}{address.district or ''}{address.detail}",
        items_total=items_total,
        shipping_fee=shipping,
        points_deduct=deduct,
        points_used=points_used,
        pay_amount=pay_amount,
        remark=payload.remark,
        idempotency_key=payload.idempotency_key,
        idempotency_payload_hash=_payload_hash(payload),
    )
    db.add(order)
    db.flush()

    from datetime import timedelta

    reserve_until = utcnow() + timedelta(minutes=settings.ORDER_PAY_EXPIRE_MINUTES)
    try:
        for store_id, g in grouped.items():
            sub = q2(sum(l["subtotal"] for l in g))
            fee = _shipping_fee(sub)
            so = StoreOrder(
                store_order_no=gen_order_no("TS"),
                order_id=order.id,
                store_id=store_id,
                items_total=sub,
                shipping_fee=fee,
                pay_amount=q2(sub + fee),
            )
            db.add(so)
            db.flush()
            for l in g:
                db.add(
                    OrderItem(
                        store_order_id=so.id,
                        sku_id=l["sku"].id,
                        product_id=l["product"].id,
                        title=l["product"].title,
                        spec=l["sku"].spec,
                        image_url=l["image_url"],
                        unit_price=l["unit_price"],
                        quantity=l["quantity"],
                        subtotal=l["subtotal"],
                    )
                )
                # 6) 库存预占（条件 UPDATE，失败抛 INSUFFICIENT_STOCK → 整单回滚）
                inventory_service.reserve(db, l["sku"].id, l["quantity"], so.id)
            _transition(db, order, so, "pending_payment", action="create")
        _transition(db, order, None, "pending_payment", action="create")
    except AppError:
        raise  # 触发依赖层 rollback，前面 spend 的绿豆一并回滚
    db.flush()

    # 7) 生成待支付支付单
    from app.modules.payments import service as payment_service

    payment_service.create_payment(db, order)
    notify_service.notify(
        db, user_id, "order_created",
        f"订单已创建 {order.order_no}",
        f"订单 {order.order_no} 已创建，请在 {settings.ORDER_PAY_EXPIRE_MINUTES} 分钟内完成支付，应付 ¥{pay_amount:.2f}。",
    )
    return order


# ---------------- 状态机 ----------------
def _transition(
    db: Session,
    order: Order,
    store_order: StoreOrder | None,
    to_status: str,
    action: str,
    operator_id: uuid.UUID | None = None,
    note: str | None = None,
) -> None:
    """强制走合法迁移表；非法迁移直接抛错并写日志。"""
    target = store_order or order
    allowed = ORDER_TRANSITIONS.get(target.status, set())
    if to_status not in allowed and target.status != to_status:
        raise AppError(
            "ORDER_STATE_INVALID",
            f"订单状态 {target.status} 不允许迁移到 {to_status}",
        )
    if to_status == target.status:
        return  # 幂等：已处于目标状态
    from_status = target.status
    target.status = to_status
    db.add(
        OrderStatusLog(
            order_id=order.id,
            store_order_id=store_order.id if store_order else None,
            from_status=from_status,
            to_status=to_status,
            action=action,
            operator_id=operator_id,
            note=note,
        )
    )
    db.flush()


def mark_paid(db: Session, order: Order) -> None:
    """支付成功回调（payments 服务调用，幂等）。"""
    if order.status == "paid":
        return
    _transition(db, order, None, "paid", action="payment_success", note=order.order_no)
    order.paid_at = utcnow()
    for so in _children(db, order.id):
        _transition(db, order, so, "paid", action="payment_success")
    notify_service.notify(
        db, order.user_id, "order_paid",
        f"支付成功 {order.order_no}",
        f"订单 {order.order_no} 已支付 ¥{order.pay_amount:.2f}，商家将尽快为您发货。",
    )


def _children(db: Session, order_id: uuid.UUID) -> list[StoreOrder]:
    return list(
        db.execute(select(StoreOrder).where(StoreOrder.order_id == order_id)).scalars()
    )


def cancel_by_user(db: Session, user_id: uuid.UUID, order_id: uuid.UUID, reason: str | None) -> Order:
    order = _get_owned(db, user_id, order_id)
    if order.status != "pending_payment":
        raise AppError("ORDER_STATE_INVALID", "仅待支付订单可取消")
    _do_cancel(db, order, reason=reason or "买家取消", operator_id=user_id)
    # 已扣绿豆返还
    if order.points_used > 0:
        points_service.compensate(db, order.user_id, order.points_used, note="订单取消返还绿色积分")
    notify_service.notify(
        db, order.user_id, "order_cancelled",
        f"订单已取消 {order.order_no}", f"订单 {order.order_no} 已取消。"
    )
    return order


def _do_cancel(db: Session, order: Order, reason: str, operator_id: uuid.UUID | None) -> None:
    for so in _children(db, order.id):
        if so.status == "pending_payment":
            inventory_service.release_for_store_order(db, so.id)
            _transition(db, order, so, "cancelled", action="cancel", operator_id=operator_id, note=reason)
    _transition(db, order, None, "cancelled", action="cancel", operator_id=operator_id, note=reason)
    order.cancelled_at = utcnow()
    order.cancel_reason = reason
    # 关闭未支付支付单
    from app.modules.payments import service as payment_service

    payment_service.close_pending_payments(db, order.id)


def confirm_receipt(db: Session, user_id: uuid.UUID, order_id: uuid.UUID) -> Order:
    order = _get_owned(db, user_id, order_id)
    children = _children(db, order.id)
    active = [so for so in children if so.status != "cancelled"]
    if order.status != "shipped" or any(so.status != "shipped" for so in active):
        raise AppError("ORDER_STATE_INVALID", "订单未全部发货，无法确认收货")
    now = utcnow()
    for so in active:
        _transition(db, order, so, "completed", action="confirm_receipt", operator_id=user_id)
        so.completed_at = now
    _transition(db, order, None, "completed", action="confirm_receipt", operator_id=user_id)
    order.completed_at = now
    db.flush()
    # 发放绿豆【仿真规则：按实付金额 × POINTS_EARN_RATE 向下取整】
    points_service.award_for_order(db, order)
    notify_service.notify(
        db, order.user_id, "order_completed",
        f"订单已完成 {order.order_no}",
        f"订单 {order.order_no} 已确认收货，感谢购买。",
    )
    return order


def ship(
    db: Session,
    store_id: uuid.UUID,
    store_order_id: uuid.UUID,
    carrier: str,
    tracking_no: str,
    operator_id: uuid.UUID,
) -> StoreOrder:
    """商家发货：出库消耗预占库存 + 创建物流单 + 状态迁移。"""
    so = db.get(StoreOrder, store_order_id)
    if so is None or so.store_id != store_id:  # 越权防护
        raise AppError("NOT_FOUND", "店铺订单不存在")
    order = db.get(Order, so.order_id)
    if so.status != "paid":
        raise AppError("ORDER_STATE_INVALID", "仅已支付订单可发货")
    from app.modules.logistics import service as logistics_service

    logistics_service.create_shipment(db, so, carrier, tracking_no, operator_id)
    inventory_service.consume_for_store_order(db, so.id)
    _transition(db, order, so, "shipped", action="ship", operator_id=operator_id)
    so.shipped_at = utcnow()
    _recompute_parent(db, order)
    notify_service.notify(
        db, order.user_id, "order_shipped",
        f"订单已发货 {order.order_no}",
        f"您的订单 {order.order_no}（{so.store_order_no}）已由 {carrier} 发出，运单号 {tracking_no}。",
    )
    return so


def _recompute_parent(db: Session, order: Order) -> None:
    """父订单状态 = 子订单聚合（部分发货保持 paid，规则待业务确认）。"""
    children = _children(db, order.id)
    active = [so for so in children if so.status != "cancelled"]
    if not active:
        target = "cancelled"
    elif all(so.status == "refunded" for so in active):
        target = "refunded"
    elif any(so.status == "refunding" for so in active):
        target = "refunding"
    elif any(so.refund_amount > 0 or so.status == "partially_refunded" for so in active):
        target = "partially_refunded"
    elif all(so.status == "completed" for so in active):
        target = "completed"
    elif all(so.status == "shipped" for so in active):
        target = "shipped"
    elif any(so.status == "shipped" for so in active):
        target = "paid"  # 部分发货（业务确认前按已支付展示）
    elif all(so.status in ("paid", "shipped", "completed") for so in active):
        target = "paid"
    else:
        return
    if target != order.status:
        _transition(db, order, None, target, action="recompute")
        db.flush()


def on_refund_executed(db: Session, store_order: StoreOrder) -> None:
    """退款执行完成后（payments 服务调用）：刷新子单与父单状态。"""
    order = db.get(Order, store_order.order_id)
    fully = store_order.refund_amount >= store_order.pay_amount
    _transition(
        db, order, store_order,
        "refunded" if fully else "partially_refunded",
        action="refund_executed",
    )
    _recompute_parent(db, order)


def close_expired(db: Session) -> int:
    """超时未支付订单关闭（Celery 定时任务调用）。"""
    from datetime import timedelta

    horizon = utcnow() - timedelta(minutes=settings.ORDER_PAY_EXPIRE_MINUTES)
    count = 0
    for order in db.execute(
        select(Order).where(Order.status == "pending_payment", Order.created_at < horizon)
    ).scalars():
        _do_cancel(db, order, reason="支付超时自动关闭", operator_id=None)
        if order.points_used > 0:
            points_service.compensate(db, order.user_id, order.points_used, note="超时关闭返还绿色积分")
        count += 1
    if count:
        db.commit()
    return count


# ---------------- 查询 ----------------
def _get_owned(db: Session, user_id: uuid.UUID, order_id: uuid.UUID) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.user_id != user_id:
        raise AppError("NOT_FOUND", "订单不存在")
    return order


def build_order_out(db: Session, order: Order):
    """组装父子订单 + 条目快照详情。"""
    from app.modules.orders.schemas import OrderItemOut, OrderOut, StoreOrderOut

    out = OrderOut.model_validate(order)
    out.store_orders = []
    for so in _children(db, order.id):
        so_out = StoreOrderOut.model_validate(so)
        so_out.items = [
            OrderItemOut.model_validate(i)
            for i in db.execute(
                select(OrderItem).where(OrderItem.store_order_id == so.id)
            ).scalars()
        ]
        out.store_orders.append(so_out)
    return out

