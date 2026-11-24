"""用户域服务：注册、资料、收货地址。"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.modules.users.models import User, UserAddress, UserProfile
from app.modules.users.schemas import AddressIn, ProfileUpdateIn


def register_user(db: Session, email: str, password: str, nickname: str | None) -> User:
    """注册消费者账号（商家/管理员角色由后续流程授予）。"""
    exists = db.execute(
        select(User.id).where(User.email == email)
    ).scalar_one_or_none()
    if exists:
        raise AppError("EMAIL_TAKEN")
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, nickname=nickname or email.split("@")[0]))
    db.flush()
    return user


def get_profile(db: Session, user_id: uuid.UUID) -> UserProfile | None:
    return db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).scalar_one_or_none()


def update_profile(db: Session, user_id: uuid.UUID, payload: ProfileUpdateIn) -> UserProfile:
    profile = get_profile(db, user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.flush()
    return profile


def list_addresses(db: Session, user_id: uuid.UUID) -> list[UserAddress]:
    return list(
        db.execute(
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
        ).scalars()
    )


def _check_owner(db: Session, user_id: uuid.UUID, address_id: uuid.UUID) -> UserAddress:
    addr = db.get(UserAddress, address_id)
    if addr is None or addr.user_id != user_id:  # 归属校验，防 IDOR
        raise AppError("NOT_FOUND", "收货地址不存在")
    return addr


def create_address(db: Session, user_id: uuid.UUID, payload: AddressIn) -> UserAddress:
    if payload.is_default:
        _clear_default(db, user_id)
    addr = UserAddress(user_id=user_id, **payload.model_dump())
    db.add(addr)
    db.flush()
    return addr


def update_address(
    db: Session, user_id: uuid.UUID, address_id: uuid.UUID, payload: AddressIn
) -> UserAddress:
    addr = _check_owner(db, user_id, address_id)
    if payload.is_default:
        _clear_default(db, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(addr, field, value)
    db.flush()
    return addr


def delete_address(db: Session, user_id: uuid.UUID, address_id: uuid.UUID) -> None:
    addr = _check_owner(db, user_id, address_id)
    db.delete(addr)
    db.flush()


def _clear_default(db: Session, user_id: uuid.UUID) -> None:
    for addr in list(
        db.execute(select(UserAddress).where(UserAddress.user_id == user_id)).scalars()
    ):
        addr.is_default = False
