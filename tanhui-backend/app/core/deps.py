"""通用依赖：当前用户、全局 RBAC 权限、商家店铺范围解析、分页参数。

安全要点：
- 商家端数据范围 100% 由服务端 store_members 推导，客户端传入的 store_id
  仅用于"选择"，必须校验成员身份，防止越权（IDOR）；
- 一个用户允许加入多个店铺（业务已确认），但每个店铺的角色权限独立受限。
"""
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """解析 Bearer Access Token → 校验会话未撤销 → 返回活跃用户。"""
    from app.modules.auth.models import AuthSession
    from app.modules.users.models import User

    if creds is None or not creds.credentials:
        raise AppError("UNAUTHENTICATED")
    payload = decode_token(creds.credentials, "access")
    session = db.get(AuthSession, uuid.UUID(payload["sid"]))
    if session is None or session.revoked_at is not None:
        raise AppError("UNAUTHENTICATED")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise AppError("ACCOUNT_DISABLED")
    return user


def get_user_permission_codes(db: Session, user_id: uuid.UUID) -> set[str]:
    """全局权限（管理员侧）：user_roles → role_permissions → permissions。

    is_super 角色（超级管理员）返回 {"*"} 通配全部权限。
    注意：超管判定独立于权限行（超管可以没有任何 role_permissions 记录）。
    """
    from app.modules.rbac.models import Permission, Role, RolePermission, UserRole

    roles = list(
        db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        ).scalars()
    )
    if any(r.is_super for r in roles):
        return {"*"}
    codes: set[str] = set()
    if not roles:
        return codes
    perms = db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id.in_([r.id for r in roles]))
    ).scalars()
    codes.update(perms)
    return codes


def has_admin_role(db: Session, user_id: uuid.UUID) -> bool:
    from app.modules.rbac.models import Role, UserRole

    cnt = db.execute(
        select(func.count())
        .select_from(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id, Role.kind == "admin")
    ).scalar_one()
    return cnt > 0


def require_permissions(*perm_codes: str):
    """管理员接口权限依赖；超级管理员自动放行。"""

    def dependency(
        user=Depends(get_current_user), db: Session = Depends(get_db)
    ):
        perms = get_user_permission_codes(db, user.id)
        if "*" in perms:
            return user
        missing = [p for p in perm_codes if p not in perms]
        if missing:
            raise AppError("FORBIDDEN", f"缺少权限: {', '.join(missing)}")
        return user

    return dependency


def require_mfa_code(
    x_mfa_code: str = Header("", alias="X-MFA-Code"),
    user=Depends(get_current_user),
):
    """高风险管理操作的二次验证【仿真模式：默认关闭，见 MFA_STRICT_HIGH_RISK】。"""
    from app.core.security import verify_mfa

    if settings.MFA_STRICT_HIGH_RISK and not verify_mfa(user, x_mfa_code):
        raise AppError("MFA_REQUIRED")
    return user


# ==================== 商家店铺范围 ====================

# 店铺内角色 → 权限映射【仿真配置：业务确认后可调整】
# owner=店主  manager=店长  staff=店员  viewer=只读
STORE_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        "store:read", "store:manage", "product:read", "product:manage",
        "inventory:manage", "order:read", "order:manage", "aftersale:manage",
        "finance:read", "employee:manage", "green:submit",
    },
    "manager": {
        "store:read", "product:read", "product:manage", "inventory:manage",
        "order:read", "order:manage", "aftersale:manage", "finance:read",
        "green:submit",
    },
    "staff": {
        "store:read", "product:read", "inventory:manage",
        "order:read", "order:manage", "green:submit",
    },
    "viewer": {"store:read", "product:read", "order:read", "finance:read"},
}


@dataclass
class StoreCtx:
    """商家端请求上下文：店铺范围由服务端成员表推导。"""

    user_id: uuid.UUID
    store_id: uuid.UUID
    role: str
    permissions: set[str]


def resolve_store_ctx(
    db: Session, user, store_id: uuid.UUID | None, *required_perms: str
) -> StoreCtx:
    """解析当前用户的店铺上下文（允许多店身份，按店铺角色限权）。

    - 无任何店铺成员身份 → 403；
    - 指定 store_id 但不是该店成员 → 403（防 IDOR）；
    - 属于多个店铺且未指定 → 400 STORE_REQUIRED。
    """
    from app.modules.stores.models import StoreMember

    memberships = list(
        db.execute(select(StoreMember).where(StoreMember.user_id == user.id)).scalars()
    )
    if not memberships:
        raise AppError("FORBIDDEN", "当前账号没有任何店铺权限")
    if store_id is not None:
        member = next((m for m in memberships if m.store_id == store_id), None)
        if member is None:
            raise AppError("FORBIDDEN", "不是该店铺的成员，禁止访问")
    elif len(memberships) == 1:
        member = memberships[0]
    else:
        raise AppError("STORE_REQUIRED")
    perms = STORE_ROLE_PERMISSIONS.get(member.role, set())
    missing = [p for p in required_perms if p not in perms]
    if missing:
        raise AppError(
            "FORBIDDEN", f"店铺角色({member.role})缺少权限: {', '.join(missing)}"
        )
    return StoreCtx(
        user_id=user.id, store_id=member.store_id, role=member.role, permissions=perms
    )


def page_params(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> tuple[int, int]:
    return page, page_size
