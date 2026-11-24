"""RBAC 域模型：roles / permissions / role_permissions / user_roles / data_scopes。

设计：
- 全局角色（管理员侧）：通过 user_roles 授予，权限来自 role_permissions；
- 店铺内角色（商家侧）：store_members.role，权限映射见 core/deps.py；
- is_super 的角色（超级管理员）拥有全部权限（通配）。
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin
from app.core.types import GUID, UTCDatetime


class Role(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    # super_admin / ops_admin / product_auditor / finance_admin / cs_admin
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16), default="admin")  # admin / system
    is_super: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(String(255))


class Permission(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    # 如 product:approve / order:read / finance:manage
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    resource: Mapped[str] = mapped_column(String(32))


class RolePermission(UUIDPKMixin, Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("roles.id"), index=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("permissions.id"), index=True
    )

    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_perm"),)


class UserRole(UUIDPKMixin, Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("roles.id"), index=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    granted_at: Mapped[datetime] = mapped_column(UTCDatetime())

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


class DataScope(UUIDPKMixin, TimestampMixin, Base):
    """数据范围字典：global(全平台) / store(本店铺)。"""

    __tablename__ = "data_scopes"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(String(255))
