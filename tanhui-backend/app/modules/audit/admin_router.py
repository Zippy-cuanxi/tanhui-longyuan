"""审计管理端接口：操作日志 / 登录日志 / 安全事件（需 audit:read 权限）。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.audit.models import LoginLog, OperationLog, SecurityEvent

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


class OperationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None = None
    action: str
    resource: str
    resource_id: str | None = None
    detail: dict | None = None
    ip: str | None = None
    created_at: datetime


class LoginLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None = None
    email: str
    success: bool
    message: str | None = None
    ip: str | None = None
    created_at: datetime


class SecurityEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    user_id: str | None = None
    detail: dict | None = None
    created_at: datetime


def _to_out(model, row) -> BaseModel:
    data = OperationLogOut if model is OperationLog else LoginLogOut if model is LoginLog else SecurityEventOut
    obj = data.model_validate(row)
    obj.id = str(row.id)
    if getattr(row, "user_id", None):
        obj.user_id = str(row.user_id)
    return obj


@router.get("/operation-logs", response_model=ApiResponse[PageOut[OperationLogOut]], summary="操作日志")
def list_operation_logs(
    action: str | None = Query(None),
    resource: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
):
    stmt: Select = select(OperationLog).order_by(OperationLog.created_at.desc())
    if action:
        stmt = stmt.where(OperationLog.action == action)
    if resource:
        stmt = stmt.where(OperationLog.resource == resource)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(data=PageOut(items=[_to_out(OperationLog, i) for i in items], pagination=pagination))


@router.get("/login-logs", response_model=ApiResponse[PageOut[LoginLogOut]], summary="登录日志")
def list_login_logs(
    email: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
):
    stmt = select(LoginLog).order_by(LoginLog.created_at.desc())
    if email:
        stmt = stmt.where(LoginLog.email == email)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(data=PageOut(items=[_to_out(LoginLog, i) for i in items], pagination=pagination))


@router.get("/security-events", response_model=ApiResponse[PageOut[SecurityEventOut]], summary="安全事件")
def list_security_events(
    kind: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
):
    stmt = select(SecurityEvent).order_by(SecurityEvent.created_at.desc())
    if kind:
        stmt = stmt.where(SecurityEvent.kind == kind)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(data=PageOut(items=[_to_out(SecurityEvent, i) for i in items], pagination=pagination))
