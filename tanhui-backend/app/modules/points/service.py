"""积分服务：账户、幂等流水、规则版本、订单发放/退款冲正、管理员调整、兑换。

【仿真规则】所有比例/开关默认值见 app/core/config.py，业务确认后：
- 临时调整：直接改 .env / config 默认值；
- 正式调整：调用 admin 接口创建新的规则版本（流水会引用版本，可追溯）。
"""
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.config import settings
from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.points.models import (
    PointAccount,
    PointRule,
    PointRuleVersion,
    PointTransaction,
)

# 兑换目录【仿真数据】：业务确认兑换权益后替换或接入真实权益系统
REDEMPTION_CATALOG: dict[str, dict] = {
    "coupon_5": {"name": "5元无门槛优惠券(Mock)", "points": 500},
    "coupon_6": {"name": "6元优惠券·满59可用(Mock)", "points": 600},
    "coupon_10": {"name": "10元无门槛优惠券(Mock)", "points": 900},
    "coupon_30": {"name": "30元优惠券·满199可用(Mock)", "points": 1800},
    "coupon_50": {"name": "50元优惠券·满299可用(Mock)", "points": 2500},
    "green_donation": {"name": "绿色积分捐助助农项目(Mock)", "points": 100},
}


def get_or_create_account(db: Session, user_id: uuid.UUID) -> PointAccount:
    acct = db.execute(
        select(PointAccount).where(PointAccount.user_id == user_id)
    ).scalar_one_or_none()
    if acct is None:
        acct = PointAccount(user_id=user_id)
        db.add(acct)
        db.flush()
    return acct


def get_balance(db: Session, user_id: uuid.UUID) -> int:
    return get_or_create_account(db, user_id).balance


def estimate_for_order(db: Session, order) -> int:
    """按当前规则预估订单可获得的绿色积分（用于支付/订单页展示）。"""
    config, _ = get_rule_config(db, "order_earn")
    if not config.get("enabled", False):
        return 0
    rate = Decimal(str(config.get("rate", "1")))
    amount = int(
        (Decimal(str(order.pay_amount)) * rate).to_integral_value(rounding="ROUND_DOWN")
    )
    return max(0, amount)


def earned_for_order(db: Session, order) -> int:
    """查询订单实际已发放的绿色积分（订单完成后才有值）。"""
    txn = db.execute(
        select(PointTransaction).where(
            PointTransaction.user_id == order.user_id,
            PointTransaction.source_type == "order_completion",
            PointTransaction.source_id == order.id,
        )
    ).scalar_one_or_none()
    return txn.amount if txn is not None and txn.amount > 0 else 0


def _apply(
    db: Session,
    account: PointAccount,
    *,
    type_: str,
    amount: int,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
    rule_version_id: uuid.UUID | None = None,
    note: str | None = None,
    operator_id: uuid.UUID | None = None,
) -> PointTransaction:
    """底层入账（正负皆可）。幂等：同 key 已存在则直接返回原流水。"""
    if idempotency_key:
        exists = db.execute(
            select(PointTransaction).where(
                PointTransaction.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()
        if exists is not None:
            return exists
    if account.balance + amount < 0:
        raise AppError("POINTS_INSUFFICIENT")
    account.balance += amount
    txn = PointTransaction(
        account_id=account.id,
        user_id=account.user_id,
        type=type_,
        amount=amount,
        balance_after=account.balance,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        rule_version_id=rule_version_id,
        note=note,
        operator_id=operator_id,
    )
    db.add(txn)
    db.flush()
    return txn


# ---------------- 规则 ----------------
def ensure_rules_seeded(db: Session) -> None:
    """幂等初始化积分规则（从 settings 读默认值【仿真】）。"""
    defaults = {
        "order_earn": {
            "name": "订单完成发放绿色积分",
            "config": {
                "enabled": settings.POINTS_EARN_ENABLED,
                "rate": settings.POINTS_EARN_RATE,  # 每消费 1 元发 N 绿豆
            },
        },
        "deduct": {
            "name": "下单绿色积分抵扣",
            "config": {
                "enabled": settings.POINTS_DEDUCTION_ENABLED,
                "rate": settings.POINTS_DEDUCT_RATE,  # N 绿豆 = 1 元
                "max_percent": settings.POINTS_DEDUCT_MAX_PERCENT,
            },
        },
        "refund_reverse": {
            "name": "退款冲正绿色积分",
            "config": {
                "enabled": settings.POINTS_REFUND_REVERSE_ENABLED,
                "proportional": True,  # 按退款金额比例冲正
            },
        },
    }
    for code, spec in defaults.items():
        rule = db.execute(select(PointRule).where(PointRule.code == code)).scalar_one_or_none()
        if rule is None:
            rule = PointRule(code=code, name=spec["name"])
            db.add(rule)
            db.flush()
        if rule.current_version_id is None:
            version = PointRuleVersion(rule_id=rule.id, version=1, config=spec["config"])
            db.add(version)
            db.flush()
            rule.current_version_id = version.id
    db.flush()


def get_rule_config(db: Session, code: str) -> tuple[dict, uuid.UUID | None]:
    """读取规则当前版本配置；未初始化时回退 settings【仿真兜底】。"""
    rule = db.execute(select(PointRule).where(PointRule.code == code)).scalar_one_or_none()
    if rule is not None and rule.current_version_id is not None:
        version = db.get(PointRuleVersion, rule.current_version_id)
        if version is not None:
            return version.config, version.id
    # 兜底（未 seed 的环境）
    fallback = {
        "order_earn": {"enabled": settings.POINTS_EARN_ENABLED, "rate": settings.POINTS_EARN_RATE},
        "deduct": {
            "enabled": settings.POINTS_DEDUCTION_ENABLED,
            "rate": settings.POINTS_DEDUCT_RATE,
            "max_percent": settings.POINTS_DEDUCT_MAX_PERCENT,
        },
        "refund_reverse": {"enabled": settings.POINTS_REFUND_REVERSE_ENABLED, "proportional": True},
    }
    return fallback.get(code, {}), None


def update_rule(db: Session, code: str, config: dict, operator_id: uuid.UUID) -> PointRule:
    """创建新版本（旧版本保留，可追溯）。"""
    rule = db.execute(select(PointRule).where(PointRule.code == code)).scalar_one_or_none()
    if rule is None:
        raise AppError("NOT_FOUND", "规则不存在")
    latest = db.get(PointRuleVersion, rule.current_version_id) if rule.current_version_id else None
    version_no = (latest.version + 1) if latest else 1
    version = PointRuleVersion(
        rule_id=rule.id, version=version_no, config=config, created_by=operator_id
    )
    db.add(version)
    db.flush()
    rule.current_version_id = version.id
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="points.rule_update",
        resource="point_rule", resource_id=str(rule.id),
        detail={"code": code, "version": version_no, "config": config},
    )
    return rule


# ---------------- 业务操作 ----------------
def award_for_order(db: Session, order) -> PointTransaction | None:
    """订单支付成功发放绿色积分（幂等：order_complete:{order_id}）。

    确认收货会再次调用，但同一幂等键只入账一次。
    """
    config, rule_version_id = get_rule_config(db, "order_earn")
    if not config.get("enabled", False):
        return None
    rate = Decimal(str(config.get("rate", "1")))
    amount = int((Decimal(str(order.pay_amount)) * rate).to_integral_value(rounding="ROUND_DOWN"))
    if amount <= 0:
        return None
    account = get_or_create_account(db, order.user_id)
    return _apply(
        db, account,
        type_="earn", amount=amount,
        source_type="order_completion", source_id=order.id,
        idempotency_key=f"order_complete:{order.id}",
        rule_version_id=rule_version_id,
        note=f"订单 {order.order_no} 支付成功发放",
    )


def award_for_donation(
    db: Session, user_id: uuid.UUID, donation_id: uuid.UUID, amount: Decimal
) -> PointTransaction | None:
    """助农资助发放绿色积分（1 元 = POINTS_DONATION_RATE 积分，幂等）。"""
    rate = Decimal(str(settings.POINTS_DONATION_RATE))
    points = int((Decimal(str(amount)) * rate).to_integral_value(rounding="ROUND_DOWN"))
    if points <= 0:
        return None
    account = get_or_create_account(db, user_id)
    return _apply(
        db,
        account,
        type_="earn",
        amount=points,
        source_type="aid_donation",
        source_id=donation_id,
        idempotency_key=f"aid_donation:{donation_id}",
        note=f"资助助农项目获得 {points} 绿色积分",
    )


def spend_for_order(
    db: Session, user_id: uuid.UUID, amount: int, *, idempotency_key: str | None, note: str
) -> PointTransaction:
    account = get_or_create_account(db, user_id)
    return _apply(
        db, account,
        type_="spend", amount=-amount,
        source_type="order_deduction",
        idempotency_key=idempotency_key,
        note=note,
    )


def compensate(db: Session, user_id: uuid.UUID, amount: int, *, note: str) -> PointTransaction:
    """订单取消/超时返还绿豆。"""
    account = get_or_create_account(db, user_id)
    return _apply(db, account, type_="adjust", amount=amount, source_type="order_cancel", note=note)


def reverse_for_refund(db: Session, order, refund_amount: Decimal, refund_id: uuid.UUID) -> PointTransaction | None:
    """退款冲正：按退款金额占实付比例冲回已发放绿豆（幂等：refund:{refund_id}）。"""
    config, rule_version_id = get_rule_config(db, "refund_reverse")
    if not config.get("enabled", False):
        return None
    # 计算该订单实际发放的绿豆
    earned = db.execute(
        select(PointTransaction).where(
            PointTransaction.user_id == order.user_id,
            PointTransaction.source_type == "order_completion",
            PointTransaction.source_id == order.id,
        )
    ).scalar_one_or_none()
    if earned is None or earned.amount <= 0 or order.pay_amount <= 0:
        return None
    if config.get("proportional", True):
        reverse = int(
            (
                Decimal(str(earned.amount))
                * (Decimal(str(refund_amount)) / Decimal(str(order.pay_amount)))
            ).to_integral_value(rounding="ROUND_DOWN")
        )
    else:
        reverse = earned.amount
    if reverse <= 0:
        return None
    account = get_or_create_account(db, order.user_id)
    return _apply(
        db, account,
        type_="reverse", amount=-reverse,
        source_type="refund_reversal", source_id=refund_id,
        idempotency_key=f"refund:{refund_id}",
        rule_version_id=rule_version_id,
        note=f"订单 {order.order_no} 退款冲正",
    )


def admin_adjust(
    db: Session, user_id: uuid.UUID, delta: int, reason: str, operator_id: uuid.UUID
) -> PointTransaction:
    if delta == 0:
        raise AppError("VALIDATION_ERROR", "调整值不能为 0")
    account = get_or_create_account(db, user_id)
    txn = _apply(
        db, account,
        type_="adjust", amount=delta,
        source_type="admin_adjust",
        note=reason, operator_id=operator_id,
    )
    audit_service.log_operation(
        db, operator_id=operator_id, action="points.admin_adjust",
        resource="point_account", resource_id=str(user_id),
        detail={"delta": delta, "reason": reason},
    )
    return txn


def redeem(db: Session, user_id: uuid.UUID, reward_code: str) -> dict:
    """兑换权益【仿真】：按目录扣减绿豆并生成 Mock 凭证码。"""
    reward = REDEMPTION_CATALOG.get(reward_code)
    if reward is None:
        raise AppError("NOT_FOUND", "兑换项不存在")
    account = get_or_create_account(db, user_id)
    import secrets

    voucher = f"MOCK-{secrets.token_hex(4).upper()}"  # Mock 凭证码，不代表真实权益
    _apply(
        db, account,
        type_="spend", amount=-reward["points"],
        source_type="redemption",
        note=f"兑换「{reward['name']}」 凭证码 {voucher}",
    )
    return {
        "reward_code": reward_code,
        "reward_name": reward["name"],
        "points_spent": reward["points"],
        "voucher_code": voucher,
        "mock": True,  # 【仿真标记】
    }
