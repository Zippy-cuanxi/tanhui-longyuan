"""支付服务：支付单生命周期、Mock 回调处理（验签/金额核对/幂等）、退款流程。"""
import uuid
from datetime import timedelta
from decimal import Decimal

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.base import gen_order_no, utcnow
from app.core.config import settings
from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.notifications import service as notify_service
from app.modules.orders import service as order_service
from app.modules.orders.models import Order, StoreOrder
from app.modules.payments.models import (
    PaymentCallback,
    PaymentOrder,
    PaymentTransaction,
    Refund,
)
from app.modules.payments.providers import MockSandboxProvider, get_provider
from app.modules.points import service as points_service


def create_payment(db: Session, order: Order) -> PaymentOrder:
    """为订单创建待支付支付单（同订单可多次尝试，仅一笔可成功）。"""
    pay = PaymentOrder(
        pay_no=gen_order_no("PAY"),
        order_id=order.id,
        amount=order.pay_amount,
        currency=order.currency,
        status="pending",
        provider=settings.PAYMENT_PROVIDER,
        expires_at=utcnow() + timedelta(minutes=settings.ORDER_PAY_EXPIRE_MINUTES),
    )
    db.add(pay)
    db.flush()
    return pay


def get_or_create_active_payment(db: Session, order: Order) -> PaymentOrder:
    """取当前 pending 且未过期的支付单，否则新建。"""
    pay = db.execute(
        select(PaymentOrder)
        .where(
            PaymentOrder.order_id == order.id,
            PaymentOrder.status == "pending",
            PaymentOrder.expires_at > utcnow(),
        )
        .order_by(PaymentOrder.created_at.desc())
    ).scalar_one_or_none()
    return pay if pay is not None else create_payment(db, order)


def get_payment_for_user(db: Session, user_id: uuid.UUID, pay_no: str) -> PaymentOrder:
    pay = db.execute(
        select(PaymentOrder).where(PaymentOrder.pay_no == pay_no)
    ).scalar_one_or_none()
    if pay is None:
        raise AppError("NOT_FOUND", "支付单不存在")
    order = db.get(Order, pay.order_id)
    if order is None or order.user_id != user_id:  # 越权防护
        raise AppError("NOT_FOUND", "支付单不存在")
    return pay


def close_pending_payments(db: Session, order_id: uuid.UUID) -> None:
    for pay in db.execute(
        select(PaymentOrder).where(
            PaymentOrder.order_id == order_id, PaymentOrder.status == "pending"
        )
    ).scalars():
        pay.status = "closed"
    db.flush()


# ---------------- Mock 沙箱工具（SANDBOX ONLY）----------------
def mock_pay(db: Session, user_id: uuid.UUID, pay_no: str) -> dict:
    """【仿真】模拟用户在沙箱收银台完成支付：生成已签名回调并内部投递。"""
    pay = get_payment_for_user(db, user_id, pay_no)
    if pay.status != "pending":
        raise AppError("CONFLICT", f"支付单状态为 {pay.status}，无需支付")
    provider = MockSandboxProvider()
    payload = {
        "pay_no": pay.pay_no,
        "merchant_no": settings.MOCK_PAYMENT_MERCHANT_NO,
        "trade_no": provider.generate_trade_no(),
        "amount": f"{pay.amount:.2f}",
        "currency": pay.currency,
        "status": "SUCCESS",
        "timestamp": str(int(utcnow().timestamp())),
    }
    signature = provider.sign(payload)
    result = process_callback(db, payload, signature)
    db.commit()
    return result


# ---------------- 回调处理 ----------------
def process_callback(db: Session, payload: dict, signature: str | None) -> dict:
    """渠道回调统一处理：验签 → 商户号/金额/币种核对 → 幂等入账。

    返回给渠道的应答体：{"return_code": "SUCCESS"|"FAIL", ...}
    幂等：重复回调不重复入账，直接返回成功应答。
    """
    provider = get_provider()
    trade_no = str(payload.get("trade_no", ""))
    pay_no = str(payload.get("pay_no", ""))

    def _record(status: str, message: str) -> dict:
        db.add(
            PaymentCallback(
                pay_no=pay_no,
                provider_trade_no=trade_no,
                payload=payload,
                signature=signature,
                status=status,
                message=message,
            )
        )
        db.flush()

    # 1) 验签失败 → 抛统一错误码（HTTP 400）
    if not provider.verify_callback(payload, signature or ""):
        _record("invalid", "签名校验失败")
        db.commit()
        raise AppError("PAYMENT_SIGNATURE_INVALID")

    # 2) 商户号核对
    if payload.get("merchant_no") != settings.MOCK_PAYMENT_MERCHANT_NO:
        _record("invalid", "商户号不符")
        db.commit()
        raise AppError("PAYMENT_MERCHANT_MISMATCH")

    pay = db.execute(
        select(PaymentOrder).where(PaymentOrder.pay_no == pay_no)
    ).scalar_one_or_none()
    if pay is None:
        _record("invalid", "支付单不存在")
        db.commit()
        return {"return_code": "FAIL", "reason": "PAY_NOT_FOUND"}

    # 3) 金额/币种核对（先于幂等短路：已入账单据金额不符同样视为异常）
    if Decimal(str(payload.get("amount", "0"))) != pay.amount:
        _record("invalid", f"金额不符: {payload.get('amount')} != {pay.amount}")
        db.commit()
        raise AppError("PAYMENT_AMOUNT_MISMATCH")
    if payload.get("currency") != pay.currency:
        _record("invalid", "币种不符")
        db.commit()
        raise AppError("PAYMENT_AMOUNT_MISMATCH", "币种不符")

    # 4) 幂等：已成功直接应答成功
    if pay.status == "success":
        _record("duplicate", "重复回调，幂等跳过")
        db.commit()
        return {"return_code": "SUCCESS", "result": "duplicate"}

    order = db.get(Order, pay.order_id)
    if order is None:
        _record("invalid", "订单不存在")
        db.commit()
        return {"return_code": "FAIL", "reason": "ORDER_NOT_FOUND"}
    if order.status != "pending_payment":
        # 订单已取消/关闭：接受回调但不入账
        _record("invalid", f"订单状态 {order.status}，不允许入账")
        pay.status = "failed"
        db.commit()
        return {"return_code": "FAIL", "reason": "ORDER_STATE_INVALID"}

    # 5) 入账：支付单成功 + 渠道流水 + 订单状态机 + 台账 + 绿色积分发放
    # 积分在支付成功即发放（幂等键 order_complete:{id}），确认收货重复调用不会重复发放；
    # 退款时由 reverse_for_refund 按比例冲正。
    pay.status = "success"
    pay.trade_no = trade_no
    pay.paid_at = utcnow()
    db.add(
        PaymentTransaction(
            payment_order_id=pay.id,
            provider_trade_no=trade_no,
            amount=pay.amount,
            currency=pay.currency,
            status="success",
            raw=payload,
        )
    )
    order_service.mark_paid(db, order)
    points_service.award_for_order(db, order)

    # 平台账流水【仿真佣金比例见 settings.COMMISSION_RATE】
    from app.modules.finance import service as finance_service

    finance_service.record_payment(db, order, pay)

    _record("processed", "入账成功")
    db.commit()
    return {"return_code": "SUCCESS", "result": "processed"}


# ---------------- 退款 ----------------
def request_refund(
    db: Session,
    user_id: uuid.UUID,
    order_id: uuid.UUID,
    store_order_id: uuid.UUID | None,
    reason: str,
    amount: Decimal | None,
) -> Refund:
    """消费者发起退款申请（默认整单可退余额）。"""
    order = db.get(Order, order_id)
    if order is None or order.user_id != user_id:
        raise AppError("NOT_FOUND", "订单不存在")
    if order.status not in ("paid", "shipped", "completed", "partially_refunded"):
        raise AppError("REFUND_NOT_ALLOWED", "当前订单状态不支持退款申请")
    children = order_service._children(db, order.id)
    if store_order_id is not None:
        targets = [so for so in children if so.id == store_order_id]
        if not targets:
            raise AppError("NOT_FOUND", "店铺订单不存在")
    else:
        targets = [so for so in children if so.status in ("paid", "shipped", "completed", "partially_refunded")]
        if len(targets) != 1:
            raise AppError(
                "REFUND_NOT_ALLOWED",
                "多店铺订单请指定 store_order_id（当前仅支持按店铺子单退款）",
            )
    so = targets[0]
    refundable = so.pay_amount - so.refund_amount
    if refundable <= 0:
        raise AppError("REFUND_NOT_ALLOWED", "该子单已无可退金额")
    final_amount = amount if amount is not None else refundable
    if final_amount <= 0 or final_amount > refundable:
        raise AppError("REFUND_EXCEED_LIMIT", f"可退金额 {refundable:.2f}")

    refund = Refund(
        refund_no=gen_order_no("RF"),
        order_id=order.id,
        store_order_id=so.id,
        amount=final_amount,
        reason=reason,
        status="requested",
        requested_by=user_id,
    )
    db.add(refund)
    db.flush()
    # 子单进入退款中
    order_service._transition(db, order, so, "refunding", action="refund_request", operator_id=user_id, note=reason)
    order_service._recompute_parent(db, order)
    notify_service.notify(
        db, user_id, "refund_requested",
        f"退款申请已提交 {refund.refund_no}",
        f"退款申请 {refund.refund_no} 已提交，金额 ¥{final_amount:.2f}，请等待平台处理。",
    )
    return refund


def handle_refund(
    db: Session,
    refund_id: uuid.UUID,
    action: str,  # approve / reject
    note: str | None,
    admin_id: uuid.UUID,
    request: Request | None = None,
) -> Refund:
    """管理员处理退款：approve → Mock 渠道立即原路退回【仿真】。"""
    refund = db.get(Refund, refund_id)
    if refund is None:
        raise AppError("NOT_FOUND", "退款单不存在")
    if refund.status != "requested":
        raise AppError("CONFLICT", f"退款单状态为 {refund.status}，不可处理")
    refund.handled_by = admin_id
    refund.handled_at = utcnow()
    refund.result_note = note

    if action == "reject":
        refund.status = "rejected"
        so = db.get(StoreOrder, refund.store_order_id)
        order = db.get(Order, refund.order_id)
        if so.status == "refunding":
            # 回到退款前状态（按是否已发货判断）
            prev = "shipped" if so.shipped_at else ("completed" if so.completed_at else "paid")
            order_service._transition(db, order, so, prev, action="refund_rejected", operator_id=admin_id, note=note)
            order_service._recompute_parent(db, order)
        db.flush()
        audit_service.log_operation(
            db, operator_id=admin_id, action="refund.reject",
            resource="refund", resource_id=str(refund_id), detail={"note": note}, request=request,
        )
        notify_service.notify(
            db, refund.requested_by, "refund_rejected",
            f"退款被驳回 {refund.refund_no}", f"退款申请 {refund.refund_no} 被驳回：{note or '无'}",
        )
        return refund

    # ---- approve：Mock 执行退款 ----
    refund.status = "refunded"
    so = db.get(StoreOrder, refund.store_order_id)
    order = db.get(Order, refund.order_id)
    so.refund_amount += refund.amount
    db.flush()
    # 台账 + 绿豆冲正
    from app.modules.finance import service as finance_service

    finance_service.record_refund(db, order, refund)
    points_service.reverse_for_refund(db, order, refund.amount, refund.id)
    # 子单/父单状态推进
    order_service.on_refund_executed(db, so)
    audit_service.log_operation(
        db, operator_id=admin_id, action="refund.approve",
        resource="refund", resource_id=str(refund_id),
        detail={"amount": str(refund.amount), "note": note}, request=request,
    )
    notify_service.notify(
        db, refund.requested_by, "refund_done",
        f"退款完成 {refund.refund_no}",
        f"退款 {refund.refund_no} 已原路退回 ¥{refund.amount:.2f}（Mock 渠道，仿真）。",
    )
    return refund
