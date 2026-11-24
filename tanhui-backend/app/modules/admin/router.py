"""管理员聚合接口：仪表盘统计、系统设置、用户列表与封禁。"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.errors import AppError
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.admin.models import SystemSetting
from app.modules.audit import service as audit_service
from app.modules.auth import service as auth_service
from app.modules.merchants.models import Merchant
from app.modules.orders.models import Order, StoreOrder
from app.modules.users.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------- 仪表盘 ----------------
@router.get("/dashboard/stats", response_model=ApiResponse[dict], summary="运营概览统计")
def dashboard(
    _admin=Depends(require_permissions("order:read", "user:read")), db: Session = Depends(get_db)
):
    now = utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    return ApiResponse(
        data={
            "users_total": db.execute(select(func.count()).select_from(User)).scalar_one(),
            "merchants_total": db.execute(
                select(func.count()).select_from(Merchant).where(Merchant.status == "approved")
            ).scalar_one(),
            "orders_today": db.execute(
                select(func.count()).select_from(Order).where(Order.created_at >= day_ago)
            ).scalar_one(),
            "gmv_week": str(
                db.execute(
                    select(func.coalesce(func.sum(Order.pay_amount), 0)).where(
                        Order.status.notin_(("pending_payment", "cancelled")),
                        Order.created_at >= week_ago,
                    )
                ).scalar_one()
            ),
            "pending_product_audits": 0,  # 由各域接口查询，仪表盘不做跨域聚合（保持解耦）
            "mock": False,
        }
    )


# ---------------- 系统设置 ----------------
class SettingIn(BaseModel):
    key: str
    value: dict
    description: str | None = None


@router.get("/system-settings", response_model=ApiResponse[list], summary="系统设置列表")
def list_settings(
    _admin=Depends(require_permissions("settings:manage")), db: Session = Depends(get_db)
):
    items = db.execute(select(SystemSetting).order_by(SystemSetting.key)).scalars()
    return ApiResponse(
        data=[{"key": s.key, "value": s.value, "description": s.description} for s in items]
    )


@router.put("/system-settings", response_model=ApiResponse[dict], summary="写入系统设置（记审计）")
def put_setting(
    payload: SettingIn,
    admin=Depends(require_permissions("settings:manage")),
    db: Session = Depends(get_db),
):
    s = db.execute(
        select(SystemSetting).where(SystemSetting.key == payload.key)
    ).scalar_one_or_none()
    if s is None:
        s = SystemSetting(key=payload.key, value=payload.value, description=payload.description)
        db.add(s)
    else:
        s.value = payload.value
        s.description = payload.description or s.description
    s.updated_by = admin.id
    db.flush()
    audit_service.log_operation(
        db, operator_id=admin.id, action="settings.put",
        resource="system_setting", resource_id=payload.key,
        detail={"value": payload.value},
    )
    return ApiResponse(data={"key": s.key, "value": s.value})


# ---------------- 用户管理 ----------------
class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    mfa_enabled: bool
    created_at: datetime


@router.get("/users", response_model=ApiResponse[PageOut[AdminUserOut]], summary="用户列表")
def list_users(
    email: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("user:read")),
    db: Session = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc())
    if email:
        stmt = stmt.where(User.email.contains(email))
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(items=[AdminUserOut.model_validate(i) for i in items], pagination=pagination)
    )


class BanIn(BaseModel):
    reason: str


@router.post("/users/{user_id}/ban", response_model=ApiResponse[dict], summary="封禁用户（撤销全部会话）")
def ban_user(
    user_id: uuid.UUID,
    payload: BanIn,
    request: Request,
    admin=Depends(require_permissions("user:ban")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise AppError("NOT_FOUND", "用户不存在")
    user.is_active = False
    user.ban_reason = payload.reason
    revoked = auth_service.revoke_all_sessions(db, user_id)
    db.flush()
    audit_service.log_operation(
        db, operator_id=admin.id, action="user.ban",
        resource="user", resource_id=str(user_id), detail={"reason": payload.reason},
        request=request,
    )
    return ApiResponse(data={"user_id": str(user_id), "sessions_revoked": revoked})


@router.post("/users/{user_id}/unban", response_model=ApiResponse[dict], summary="解封用户")
def unban_user(
    user_id: uuid.UUID,
    admin=Depends(require_permissions("user:ban")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise AppError("NOT_FOUND", "用户不存在")
    user.is_active = True
    user.ban_reason = None
    db.flush()
    audit_service.log_operation(
        db, operator_id=admin.id, action="user.unban",
        resource="user", resource_id=str(user_id),
    )
    return ApiResponse(data={"user_id": str(user_id), "is_active": True})
