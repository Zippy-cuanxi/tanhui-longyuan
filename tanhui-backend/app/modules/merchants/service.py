"""商家服务：入驻申请、审核（含自动创建默认店铺）、冻结/解冻。"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.merchants.models import Merchant, MerchantUser
from app.modules.stores.models import Store, StoreMember


def apply(db: Session, user_id: uuid.UUID, payload) -> tuple[Merchant, Store | None]:
    """提交入驻申请：创建 pending_review 商家 + owner 关系；店铺在审核通过后创建。"""
    dup = db.execute(
        select(Merchant.id).where(Merchant.company_name == payload.company_name)
    ).scalar_one_or_none()
    if dup:
        raise AppError("CONFLICT", "该公司名称已提交过入驻申请")
    merchant = Merchant(
        status="pending_review",
        company_name=payload.company_name,
        license_no=payload.license_no,
        license_url=payload.license_url,
        legal_person=payload.legal_person,
        contact_phone=payload.contact_phone,
        region=payload.region,
        initial_store_name=payload.store_name,
    )
    db.add(merchant)
    db.flush()
    db.add(MerchantUser(merchant_id=merchant.id, user_id=user_id, role="owner"))
    db.flush()
    return merchant


def review(
    db: Session, merchant_id: uuid.UUID, action: str, reason: str | None, operator_id: uuid.UUID
) -> Merchant:
    """管理员审核/冻结/解冻。approve 时自动创建默认店铺并绑定 owner。"""
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise AppError("NOT_FOUND", "商家不存在")

    if action == "approve":
        if merchant.status not in ("pending_review",):
            raise AppError("MERCHANT_STATE_INVALID", "当前状态不可通过")
        merchant.status = "approved"
        # 自动创建默认店铺 + 店主成员关系（店铺名取申请时填写的名称）
        store = Store(merchant_id=merchant.id, name=merchant.initial_store_name or merchant.company_name)
        db.add(store)
        db.flush()
        owner_user_id = db.execute(
            select(MerchantUser.user_id).where(
                MerchantUser.merchant_id == merchant.id, MerchantUser.role == "owner"
            )
        ).scalar_one_or_none()
        if owner_user_id:
            db.add(StoreMember(store_id=store.id, user_id=owner_user_id, role="owner"))
    elif action == "reject":
        if merchant.status != "pending_review":
            raise AppError("MERCHANT_STATE_INVALID", "当前状态不可驳回")
        merchant.status = "rejected"
        merchant.reject_reason = reason or "不符合入驻要求"
    elif action == "freeze":
        if merchant.status != "approved":
            raise AppError("MERCHANT_STATE_INVALID", "仅已通过商家可冻结")
        merchant.status = "frozen"
    elif action == "unfreeze":
        if merchant.status != "frozen":
            raise AppError("MERCHANT_STATE_INVALID", "仅冻结商家可解冻")
        merchant.status = "approved"
    else:
        raise AppError("VALIDATION_ERROR", "未知操作")

    merchant.reviewed_by = operator_id
    from app.core.base import utcnow

    merchant.reviewed_at = utcnow()
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action=f"merchant.{action}",
        resource="merchant", resource_id=str(merchant_id), detail={"reason": reason},
    )
    return merchant


def get_my_merchants(db: Session, user_id: uuid.UUID) -> list[Merchant]:
    mids = db.execute(
        select(MerchantUser.merchant_id).where(MerchantUser.user_id == user_id)
    ).scalars()
    return list(db.execute(select(Merchant).where(Merchant.id.in_(mids))).scalars())
