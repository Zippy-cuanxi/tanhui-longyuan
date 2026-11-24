"""库存服务：条件 UPDATE 防超卖、预占/释放/出库、流水、商家调整。"""
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.config import settings
from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.inventory.models import Inventory, InventoryLog, InventoryReservation


def get_or_create(db: Session, sku_id: uuid.UUID, initial: int = 0) -> Inventory:
    inv = db.execute(select(Inventory).where(Inventory.sku_id == sku_id)).scalar_one_or_none()
    if inv is None:
        inv = Inventory(sku_id=sku_id, quantity_total=initial)
        db.add(inv)
        db.flush()
        if initial > 0:
            _log(db, sku_id, "adjust_add", delta_total=initial,
                 ref_type="sku_init", reason="SKU 创建初始化库存")
    return inv


def available_of(db: Session, sku_id: uuid.UUID) -> int:
    inv = db.execute(select(Inventory).where(Inventory.sku_id == sku_id)).scalar_one_or_none()
    if inv is None:
        return 0
    return inv.quantity_total - inv.quantity_reserved


def _log(
    db: Session,
    sku_id: uuid.UUID,
    change_type: str,
    delta_total: int = 0,
    delta_reserved: int = 0,
    ref_type: str | None = None,
    ref_id: uuid.UUID | None = None,
    reason: str | None = None,
    operator_id: uuid.UUID | None = None,
) -> None:
    db.add(
        InventoryLog(
            sku_id=sku_id,
            change_type=change_type,
            delta_total=delta_total,
            delta_reserved=delta_reserved,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
            operator_id=operator_id,
        )
    )


def adjust(
    db: Session,
    sku_id: uuid.UUID,
    delta: int,
    reason: str,
    operator_id: uuid.UUID,
) -> Inventory:
    """商家手工调整库存（正数入库 / 负数出库），必须填原因。"""
    inv = get_or_create(db, sku_id)
    new_total = inv.quantity_total + delta
    if new_total < inv.quantity_reserved:
        raise AppError("CONFLICT", "调整后总库存小于已预占数量，拒绝操作")
    inv.quantity_total = new_total
    db.flush()
    _log(db, sku_id, "adjust_add" if delta >= 0 else "adjust_remove",
         delta_total=delta, reason=reason, operator_id=operator_id)
    audit_service.log_operation(
        db, operator_id=operator_id, action="inventory.adjust",
        resource="sku", resource_id=str(sku_id), detail={"delta": delta, "reason": reason},
    )
    return inv


def reserve(
    db: Session,
    sku_id: uuid.UUID,
    quantity: int,
    store_order_id: uuid.UUID,
) -> InventoryReservation:
    """下单预占：条件 UPDATE 原子扣减，防止并发超卖。"""
    result = db.execute(
        update(Inventory)
        .where(
            Inventory.sku_id == sku_id,
            Inventory.quantity_total - Inventory.quantity_reserved >= quantity,
        )
        .values(quantity_reserved=Inventory.quantity_reserved + quantity)
    )
    if result.rowcount == 0:
        raise AppError("INSUFFICIENT_STOCK", f"SKU {sku_id} 库存不足")
    reservation = InventoryReservation(
        sku_id=sku_id,
        store_order_id=store_order_id,
        quantity=quantity,
        status="held",
        expires_at=utcnow() + timedelta(minutes=settings.ORDER_PAY_EXPIRE_MINUTES),
    )
    db.add(reservation)
    db.flush()
    _log(db, sku_id, "reserve", delta_reserved=quantity,
         ref_type="store_order", ref_id=store_order_id)
    return reservation


def release_reservation(db: Session, reservation: InventoryReservation, expired: bool = False) -> None:
    """释放预占（取消/超时）。"""
    inv = db.execute(select(Inventory).where(Inventory.sku_id == reservation.sku_id)).scalar_one()
    inv.quantity_reserved -= reservation.quantity
    reservation.status = "expired" if expired else "released"
    reservation.released_at = utcnow()
    db.flush()
    _log(db, reservation.sku_id, "expire" if expired else "release",
         delta_reserved=-reservation.quantity,
         ref_type="store_order", ref_id=reservation.store_order_id)


def consume_reservations(db: Session, store_order_id: uuid.UUID) -> int:
    """发货出库：预占转实际扣减（total 与 reserved 同减）。"""
    count = 0
    for r in db.execute(
        select(InventoryReservation).where(
            InventoryReservation.store_order_id == store_order_id,
            InventoryReservation.status == "held",
        )
    ).scalars():
        inv = db.execute(select(Inventory).where(Inventory.sku_id == r.sku_id)).scalar_one()
        inv.quantity_total -= r.quantity
        inv.quantity_reserved -= r.quantity
        r.status = "consumed"
        count += 1
        _log(db, r.sku_id, "consume", delta_total=-r.quantity, delta_reserved=-r.quantity,
             ref_type="store_order", ref_id=store_order_id)
    db.flush()
    return count


def release_expired(db: Session) -> int:
    """释放所有超时未支付预占（Celery 定时任务调用，见 app/worker/tasks.py）。"""
    count = 0
    now = utcnow()
    for r in db.execute(
        select(InventoryReservation).where(
            InventoryReservation.status == "held",
            InventoryReservation.expires_at < now,
        )
    ).scalars():
        release_reservation(db, r, expired=True)
        count += 1
    if count:
        db.commit()
    return count


# catalog 域使用的别名（初始化 SKU 库存）
ensure_inventory = get_or_create


def release_for_store_order(db: Session, store_order_id: uuid.UUID) -> int:
    """取消/超时订单：释放该店铺子单全部预占。"""
    count = 0
    for r in db.execute(
        select(InventoryReservation).where(
            InventoryReservation.store_order_id == store_order_id,
            InventoryReservation.status == "held",
        )
    ).scalars():
        release_reservation(db, r, expired=False)
        count += 1
    db.flush()
    return count


# 订单域使用的别名
consume_for_store_order = consume_reservations
