"""RBAC 服务：权限目录、管理员角色、角色授予（幂等种子初始化）。

权限目录与管理员角色为系统内置【仿真配置】：
- 业务确认后可直接修改下方 PERMISSION_CATALOG / ADMIN_ROLES 再重新 seed；
- seed_role_data() 幂等，可重复执行（已存在则跳过）。
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.rbac.models import (
    DataScope,
    Permission,
    Role,
    RolePermission,
    UserRole,
)

# ---------------- 权限目录（code, 名称, 资源域）----------------
PERMISSION_CATALOG: list[tuple[str, str, str]] = [
    ("user:read", "查看用户", "user"),
    ("user:ban", "封禁/解封用户", "user"),
    ("merchant:read", "查看商家", "merchant"),
    ("merchant:review", "商家入驻审核", "merchant"),
    ("store:read", "查看店铺", "store"),
    ("store:manage", "店铺管理(停业等)", "store"),
    ("product:read", "查看商品", "product"),
    ("product:approve", "商品审核", "product"),
    ("product:remove", "平台下架商品", "product"),
    ("order:read", "查看订单", "order"),
    ("refund:approve", "退款审核", "refund"),
    ("finance:read", "查看财务", "finance"),
    ("finance:manage", "财务管理/生成结算", "finance"),
    ("points:manage", "积分规则与人工调整", "points"),
    ("cms:manage", "CMS 内容管理", "cms"),
    ("aid:manage", "助农项目管理", "aid"),
    ("green:review", "绿色资料审核", "green"),
    ("audit:read", "查看审计日志", "audit"),
    ("rbac:manage", "角色与授权管理", "rbac"),
    ("settings:manage", "系统设置", "settings"),
]

# ---------------- 管理员角色（code, 名称, 权限码列表）----------------
ADMIN_ROLES: dict[str, tuple[str, list[str]]] = {
    # 超级管理员：is_super，拥有全部权限
    "super_admin": ("超级管理员", []),
    "ops_admin": (
        "运营管理员",
        ["user:read", "user:ban", "merchant:read", "store:read", "order:read",
         "cms:manage", "aid:manage", "audit:read"],
    ),
    "product_auditor": (
        "商品审核员",
        ["product:read", "product:approve", "product:remove", "merchant:read",
         "green:review", "store:read"],
    ),
    "finance_admin": (
        "财务管理员",
        ["finance:read", "finance:manage", "order:read", "merchant:read", "refund:approve"],
    ),
    "cs_admin": (
        "客服管理员",
        ["order:read", "refund:approve", "user:read", "product:read"],
    ),
}


def seed_role_data(db: Session) -> None:
    """幂等初始化权限目录、管理员角色、数据范围字典。"""
    existing_perms = {p.code: p for p in db.execute(select(Permission)).scalars()}
    for code, name, resource in PERMISSION_CATALOG:
        if code not in existing_perms:
            db.add(Permission(code=code, name=name, resource=resource))
    db.flush()

    all_perms = {p.code: p for p in db.execute(select(Permission)).scalars()}
    existing_roles = {r.code: r for r in db.execute(select(Role)).scalars()}
    for code, (name, perm_codes) in ADMIN_ROLES.items():
        role = existing_roles.get(code)
        if role is None:
            role = Role(code=code, name=name, kind="admin", is_super=(code == "super_admin"))
            db.add(role)
            db.flush()
            existing_roles[code] = role
        if code == "super_admin":
            continue  # 超级管理员通过 is_super 通配，不逐条绑定
        have = {
            rp.permission_id
            for rp in db.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            ).scalars()
        }
        for pc in perm_codes:
            perm = all_perms.get(pc)
            if perm is not None and perm.id not in have:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    for code, name, desc in [
        ("global", "全平台数据范围", "平台管理员"),
        ("store", "本店铺数据范围", "商家店铺成员"),
    ]:
        if db.execute(select(DataScope).where(DataScope.code == code)).scalar_one_or_none() is None:
            db.add(DataScope(code=code, name=name, description=desc))
    db.flush()


def get_role_by_code(db: Session, code: str) -> Role:
    role = db.execute(select(Role).where(Role.code == code)).scalar_one_or_none()
    if role is None:
        raise AppError("NOT_FOUND", f"角色不存在: {code}")
    return role


def assign_role(
    db: Session, user_id: uuid.UUID, role_code: str, granted_by: uuid.UUID
) -> UserRole:
    """授予用户全局角色（管理员授权入口，写审计）。"""
    role = get_role_by_code(db, role_code)
    existing = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id)
    ).scalar_one_or_none()
    if existing:
        return existing
    from app.core.base import utcnow
    ur = UserRole(user_id=user_id, role_id=role.id, granted_by=granted_by, granted_at=utcnow())
    db.add(ur)
    db.flush()
    audit_service.log_operation(
        db, operator_id=granted_by, action="rbac.assign_role",
        resource="user", resource_id=str(user_id),
        detail={"role": role_code},
    )
    return ur


def remove_role(db: Session, user_id: uuid.UUID, role_code: str, operator_id: uuid.UUID) -> None:
    role = get_role_by_code(db, role_code)
    ur = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id)
    ).scalar_one_or_none()
    if ur is None:
        raise AppError("NOT_FOUND", "该用户未持有此角色")
    db.delete(ur)
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="rbac.remove_role",
        resource="user", resource_id=str(user_id),
        detail={"role": role_code},
    )


def list_user_role_codes(db: Session, user_id: uuid.UUID) -> list[str]:
    rows = db.execute(
        select(Role.code).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    ).scalars()
    return list(rows)
