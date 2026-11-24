"""店铺服务：员工管理、店铺资料、商家工作台统计。"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.stores.models import Store, StoreMember
from app.modules.users.models import User


def update_store(
    db: Session, store_id: uuid.UUID, payload, operator_id: uuid.UUID
) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise AppError("NOT_FOUND", "店铺不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="store.update",
        resource="store", resource_id=str(store_id),
    )
    return store


def add_employee(
    db: Session, store_id: uuid.UUID, email: str, role: str, operator_id: uuid.UUID
) -> StoreMember:
    """添加店铺成员（允许多店身份：同一用户可在多个店铺各有一条成员记录）。"""
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        raise AppError("NOT_FOUND", "该邮箱尚未注册，无法添加为员工")
    exists = db.execute(
        select(StoreMember).where(
            StoreMember.store_id == store_id, StoreMember.user_id == user.id
        )
    ).scalar_one_or_none()
    if exists:
        raise AppError("CONFLICT", "该用户已是本店成员")
    member = StoreMember(store_id=store_id, user_id=user.id, role=role, invited_by=operator_id)
    db.add(member)
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="store.add_employee",
        resource="store", resource_id=str(store_id), detail={"email": email, "role": role},
    )
    return member


def update_employee_role(
    db: Session, store_id: uuid.UUID, member_id: uuid.UUID, role: str, operator_id: uuid.UUID
) -> StoreMember:
    member = db.get(StoreMember, member_id)
    if member is None or member.store_id != store_id:
        raise AppError("NOT_FOUND", "成员不存在")
    if member.role == "owner":
        raise AppError("FORBIDDEN", "不能修改店主角色")
    member.role = role
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="store.update_employee",
        resource="store", resource_id=str(store_id),
        detail={"member_id": str(member_id), "role": role},
    )
    return member


def remove_employee(
    db: Session, store_id: uuid.UUID, member_id: uuid.UUID, operator_id: uuid.UUID
) -> None:
    member = db.get(StoreMember, member_id)
    if member is None or member.store_id != store_id:
        raise AppError("NOT_FOUND", "成员不存在")
    if member.role == "owner":
        raise AppError("FORBIDDEN", "不能移除店主")
    db.delete(member)
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="store.remove_employee",
        resource="store", resource_id=str(store_id), detail={"member_id": str(member_id)},
    )


def list_employees(db: Session, store_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(StoreMember, User.email)
        .join(User, User.id == StoreMember.user_id)
        .where(StoreMember.store_id == store_id)
        .order_by(StoreMember.created_at)
    ).all()
    result = []
    for member, email in rows:
        out = {
            "id": member.id,
            "store_id": member.store_id,
            "user_id": member.user_id,
            "role": member.role,
            "status": member.status,
            "created_at": member.created_at,
            "email": email,
        }
        result.append(out)
    return result


def dashboard(db: Session, store_id: uuid.UUID) -> dict:
    """商家工作台统计【仿真数据来源为本库实时统计】。"""
    from app.modules.orders.models import OrderItem, StoreOrder
    from app.modules.payments.models import PaymentOrder

    paid_sub = (
        select(func.coalesce(func.sum(StoreOrder.items_total), 0))
        .where(StoreOrder.store_id == store_id)
        .where(StoreOrder.status.notin_(("cancelled", "pending_payment")))
    )
    total_sales = db.execute(paid_sub).scalar_one()
    order_counts = dict(
        db.execute(
            select(StoreOrder.status, func.count())
            .where(StoreOrder.store_id == store_id)
            .group_by(StoreOrder.status)
        ).all()
    )
    sku_count = 0
    from app.modules.catalog.models import Product, ProductSku

    products = list(
        db.execute(select(Product.id).where(Product.store_id == store_id)).scalars()
    )
    if products:
        sku_count = db.execute(
            select(func.count())
            .select_from(ProductSku)
            .where(ProductSku.product_id.in_(products))
        ).scalar_one()
    return {
        "store_id": str(store_id),
        "total_sales": str(total_sales),
        "orders_by_status": {k: v for k, v in order_counts.items()},
        "product_count": len(products),
        "sku_count": sku_count,
    }
