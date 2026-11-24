"""审计服务：登录日志、操作日志、安全事件。"""
import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit.models import LoginLog, OperationLog, SecurityEvent


def _client_meta(request: Request | None) -> dict:
    if request is None:
        return {"ip": None, "user_agent": None}
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent", "")[:255],
    }


def log_operation(
    db: Session,
    *,
    operator_id: uuid.UUID | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    detail: dict | None = None,
    request: Request | None = None,
) -> None:
    meta = _client_meta(request)
    db.add(
        OperationLog(
            user_id=operator_id,
            action=action,
            resource=resource,
            resource_id=str(resource_id) if resource_id else None,
            detail=detail,
            ip=meta["ip"],
            user_agent=meta["user_agent"],
        )
    )
    db.flush()


def log_login(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    email: str,
    success: bool,
    message: str | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        LoginLog(
            user_id=user_id,
            email=email,
            success=success,
            message=message,
            ip=ip,
            user_agent=user_agent,
        )
    )
    db.flush()


def log_security_event(
    db: Session,
    *,
    kind: str,
    user_id: uuid.UUID | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    db.add(SecurityEvent(kind=kind, user_id=user_id, detail=detail, ip=ip))
    db.flush()
