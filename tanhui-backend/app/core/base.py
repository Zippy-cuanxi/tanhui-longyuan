"""ORM 基类与通用 Mixin。

规范：
- 所有表主键统一为 UUID（防枚举、便于分布式生成）；
- created_at / updated_at 统一 UTC；
- 金额列统一 Amount()（NUMERIC(12,2) + Decimal）。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.types import GUID, UTCDatetime


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDatetime(), default=utcnow, onupdate=utcnow, nullable=False
    )


def gen_order_no(prefix: str) -> str:
    """生成人类可读业务单号：前缀 + yyyyMMddHHmmss + 6 位随机。"""
    now = datetime.now(timezone.utc)
    return f"{prefix}{now:%Y%m%d%H%M%S}{uuid.uuid4().hex[:6].upper()}"
