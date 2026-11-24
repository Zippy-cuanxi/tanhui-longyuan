"""财务服务：平台台账、佣金计算、结算单生成/确认/打款。

【仿真说明】
- 佣金比例 COMMISSION_RATE 默认 5%（config.py 可改）；
- 结算口径：周期内"已完成"店铺子单，按订单实付（不含运费【口径待业务确认】）计佣金；
- "打款"仅为状态流转，未对接任何真实资金通道。
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.config import settings
from app.core.errors import AppError
from app.core.types import q2
from app.modules.audit import service as audit_service
from app.modules.finance.models import (
    MerchantSettlement,
    PlatformLedger,
    SettlementItem,
)
from app.modules.orders.models import Order, StoreOrder
from app.modules.payments.models import PaymentOrder, Refund


def _commission_of(amount) -> "Decimal":
    from decimal import Decimal

    rate = settings.decimal("COMMISSION_RATE")
    return q2(amount * rate)


def record_payment(db: Session, order: Order, payment: PaymentOrder) -> None:
    """支付成功：入账流水 + 佣金流水（按订单实付总额）。"""
    db.add(
        PlatformLedger(
            entry_type="payment",
            ref_type="payment_order",
            ref_id=payment.id,
            order_id=order.id,
            amount=q2(payment.amount),
            note=f"订单支付入账 {order.order_no}",
        )
    )
    commission = _commission_of(order.pay_amount)
    db.add(
        PlatformLedger(
            entry_type="commission",
            ref_type="payment_order",
            ref_id=payment.id,
            order_id=order.id,
            amount=commission,
            note=f"平台佣金({settings.COMMISSION_RATE}) {order.order_no}",
        )
    )
    db.flush()


def record_refund(db: Session, order: Order, refund: Refund) -> None:
    """退款成功：退款流水 + 佣金回退流水。"""
    db.add(
        PlatformLedger(
            entry_type="refund",
            ref_type="refund",
            ref_id=refund.id,
            order_id=order.id,
            amount=-q2(refund.amount),
            note=f"订单退款 {refund.refund_no}",
        )
    )
    db.add(
        PlatformLedger(
            entry_type="commission",
            ref_type="refund",
            ref_id=refund.id,
            order_id=order.id,
            amount=-_commission_of(refund.amount),
            note=f"退款佣金回退 {refund.refund_no}",
        )
    )
    db.flush()


def generate_settlement(
    db: Session,
    store_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
    operator_id: uuid.UUID,
) -> MerchantSettlement:
    """按周期生成结算单（幂等：同店同期只允许一张）。"""
    dup = db.execute(
        select(MerchantSettlement).where(
            MerchantSettlement.store_id == store_id,
            MerchantSettlement.period_start == period_start,
            MerchantSettlement.period_end == period_end,
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise AppError("CONFLICT", "该店铺此周期已生成结算单")

    # 已在其他结算单中出现的子单不再重复结算
    settled = (
        select(SettlementItem.store_order_id).join(
            MerchantSettlement,
            MerchantSettlement.id == SettlementItem.settlement_id,
        )
    ).scalar_subquery()
    stmt = select(StoreOrder).where(
        StoreOrder.store_id == store_id,
        StoreOrder.status.in_(("completed", "partially_refunded")),
        StoreOrder.completed_at >= period_start,
        StoreOrder.completed_at < period_end,
        StoreOrder.id.not_in(settled),
    )
    orders = list(db.execute(stmt).scalars())
    orders_total = q2(sum((so.items_total for so in orders), start=q2(0)))
    commission_total = q2(sum((_commission_of(so.items_total) for so in orders), start=q2(0)))
    settlement = MerchantSettlement(
        store_id=store_id,
        period_start=period_start,
        period_end=period_end,
        status="pending",
        orders_total=orders_total,
        commission_total=commission_total,
        payable_total=q2(orders_total - commission_total),
        generated_by=operator_id,
    )
    db.add(settlement)
    db.flush()
    for so in orders:
        db.add(
            SettlementItem(
                settlement_id=settlement.id,
                store_order_id=so.id,
                order_amount=so.items_total,
                commission_amount=_commission_of(so.items_total),
            )
        )
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="finance.generate_settlement",
        resource="settlement", resource_id=str(settlement.id),
        detail={"store_id": str(store_id), "orders": len(orders)},
    )
    return settlement


def confirm_settlement(db: Session, settlement_id: uuid.UUID, operator_id: uuid.UUID) -> MerchantSettlement:
    s = db.get(MerchantSettlement, settlement_id)
    if s is None:
        raise AppError("NOT_FOUND", "结算单不存在")
    if s.status != "pending":
        raise AppError("CONFLICT", "仅待确认结算单可确认")
    s.status = "confirmed"
    s.confirmed_at = utcnow()
    db.flush()
    return s


def mark_settlement_paid(db: Session, settlement_id: uuid.UUID, operator_id: uuid.UUID) -> MerchantSettlement:
    """标记打款【仿真：无真实资金流】。"""
    s = db.get(MerchantSettlement, settlement_id)
    if s is None:
        raise AppError("NOT_FOUND", "结算单不存在")
    if s.status != "confirmed":
        raise AppError("CONFLICT", "仅已确认结算单可标记打款")
    s.status = "paid"
    s.paid_at = utcnow()
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="finance.settlement_paid",
        resource="settlement", resource_id=str(settlement_id),
    )
    return s


def store_summary(db: Session, store_id: uuid.UUID) -> dict:
    """商家财务汇总（实时计算）。"""
    paid_total = db.execute(
        select(func.coalesce(func.sum(StoreOrder.items_total), 0)).where(
            StoreOrder.store_id == store_id,
            StoreOrder.status.notin_(("cancelled", "pending_payment")),
        )
    ).scalar_one()
    refund_total = db.execute(
        select(func.coalesce(func.sum(StoreOrder.refund_amount), 0)).where(
            StoreOrder.store_id == store_id
        )
    ).scalar_one()
    return {
        "store_id": str(store_id),
        "paid_items_total": str(q2(paid_total)),
        "refund_total": str(q2(refund_total)),
        "commission_rate": settings.COMMISSION_RATE,  # 【仿真参数】
        "settlement_period_days": settings.SETTLEMENT_PERIOD_DAYS,  # 【仿真参数】
    }
