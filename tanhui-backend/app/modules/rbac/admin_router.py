"""RBAC 管理端接口：角色列表、用户角色授予/移除（需 rbac:manage 权限）。"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permissions
from app.core.responses import ApiResponse, PageOut, build_pagination, paginate
from app.modules.rbac import service
from app.modules.rbac.models import Permission, Role, UserRole
from app.modules.users.models import User

router = APIRouter(prefix="/admin/rbac", tags=["admin-rbac"])


class RoleOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    code: str
    name: str
    kind: str
    is_super: bool
    description: str | None = None


class UserBriefOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    email: str


class UserRoleOut(BaseModel):
    user: UserBriefOut
    role: RoleOut


class AssignRoleIn(BaseModel):
    role_code: str = Field(..., max_length=64)


@router.get("/roles", response_model=ApiResponse[list[RoleOut]], summary="角色列表")
def list_roles(
    _op=Depends(require_permissions("rbac:manage")), db: Session = Depends(get_db)
):
    roles = list(db.execute(select(Role).order_by(Role.code)).scalars())
    return ApiResponse(data=[RoleOut.model_validate(r) for r in roles])


@router.get("/permissions", response_model=ApiResponse[list[dict]], summary="权限目录")
def list_permissions(
    _op=Depends(require_permissions("rbac:manage")), db: Session = Depends(get_db)
):
    perms = list(db.execute(select(Permission).order_by(Permission.code)).scalars())
    return ApiResponse(
        data=[{"code": p.code, "name": p.name, "resource": p.resource} for p in perms]
    )


@router.get(
    "/user-roles", response_model=ApiResponse[PageOut[UserRoleOut]], summary="用户角色列表(分页)"
)
def list_user_roles(
    email: str | None = None,
    page: int = 1,
    page_size: int = 20,
    _op=Depends(require_permissions("rbac:manage")),
    db: Session = Depends(get_db),
):
    stmt = (
        select(User, Role)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .order_by(UserRole.granted_at.desc())
    )
    if email:
        stmt = stmt.where(User.email.contains(email))
    rows, paging = paginate(db, stmt, page, page_size)
    items = [
        UserRoleOut(user=UserBriefOut.model_validate(u), role=RoleOut.model_validate(r))
        for u, r in rows
    ]
    return ApiResponse(data=PageOut(items=items, pagination=paging))


@router.post(
    "/users/{user_id}/roles", response_model=ApiResponse[UserRoleOut], summary="授予用户角色"
)
def assign_role(
    user_id: uuid.UUID,
    payload: AssignRoleIn,
    operator=Depends(require_permissions("rbac:manage")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        from app.core.errors import AppError

        raise AppError("NOT_FOUND", "用户不存在")
    service.assign_role(db, user_id, payload.role_code, operator.id)
    role = service.get_role_by_code(db, payload.role_code)
    return ApiResponse(
        data=UserRoleOut(user=UserBriefOut.model_validate(user), role=RoleOut.model_validate(role))
    )


@router.delete(
    "/users/{user_id}/roles/{role_code}", response_model=ApiResponse[None], summary="移除用户角色"
)
def remove_role(
    user_id: uuid.UUID,
    role_code: str,
    operator=Depends(require_permissions("rbac:manage")),
    db: Session = Depends(get_db),
):
    service.remove_role(db, user_id, role_code, operator.id)
    return ApiResponse(message="已移除")
