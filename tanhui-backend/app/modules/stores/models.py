"""店铺域模型：stores / store_members。

多店铺规则（业务已确认）：一个用户可以加入多个店铺，
但每次成员关系独立授权（owner/manager/staff/viewer），权限按店铺隔离。
"""
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin
from app.core.types import GUID

STORE_STATUSES = ("active", "suspended", "closed")
STORE_MEMBER_ROLES = ("owner", "manager", "staff", "viewer")


class Store(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "stores"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(64), unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(String(1024))
    region: Mapped[str | None] = mapped_column(String(64))
    # active 正常 / suspended 平台暂停 / closed 关闭
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    is_closed_temporarily: Mapped[bool] = mapped_column(default=False)  # 商家临时歇业


class StoreMember(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "store_members"

    store_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("stores.id"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="staff")  # owner/manager/staff/viewer
    invited_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    status: Mapped[str] = mapped_column(String(16), default="active")

    __table_args__ = (UniqueConstraint("store_id", "user_id", name="uq_store_member"),)
