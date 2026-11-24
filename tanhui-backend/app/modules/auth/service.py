"""认证服务：注册、登录（含管理员 MFA）、刷新轮换（含复用检测）、撤销。

安全设计：
- refresh token 只存 SHA-256 哈希；
- 刷新即轮换：旧会话立即作废；检测到已作废令牌被复用时撤销整条轮换链；
- 登录成功/失败写 login_logs；连续失败写 security_events。
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_token,
    decode_token,
    sha256_hex,
    verify_mfa,
    verify_password,
)
from app.modules.audit import service as audit_service
from app.modules.auth.models import AuthSession
from app.modules.users import service as users_service
from app.modules.users.models import User


def register(db: Session, payload) -> User:
    return users_service.register_user(db, payload.email, payload.password, payload.nickname)


def _client_meta(request: Request | None) -> dict:
    return {
        "ip": request.client.host if request and request.client else None,
        "user_agent": request.headers.get("User-Agent", "")[:255] if request else None,
    }


def _is_admin(db: Session, user_id: uuid.UUID) -> bool:
    from app.modules.rbac.models import Role, UserRole

    cnt = (
        db.execute(
            select(Role.id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.kind == "admin")
        )
        .first()
    )
    return cnt is not None


def login(db: Session, payload, request: Request | None = None) -> tuple[User, str, str]:
    """登录成功返回 (user, access_token, refresh_token)；需要 MFA 时抛 MFA_REQUIRED。"""
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    meta = _client_meta(request)
    if user is None or not verify_password(payload.password, user.password_hash):
        audit_service.log_login(
            db, user_id=user.id if user else None, email=payload.email,
            success=False, message="账号或密码错误", **meta,
        )
        raise AppError("BAD_CREDENTIALS")

    if not user.is_active or (user.banned_until and user.banned_until > utcnow()):
        audit_service.log_login(
            db, user_id=user.id, email=payload.email,
            success=False, message="账号已禁用", **meta,
        )
        raise AppError("ACCOUNT_DISABLED")

    # 管理员 MFA：用户开启 MFA 或全局强制管理员 MFA 时必须提供验证码
    need_mfa = user.mfa_enabled or (
        settings.MFA_REQUIRED_FOR_ADMIN_LOGIN and _is_admin(db, user.id)
    )
    if need_mfa:
        if not payload.mfa_code:
            raise AppError("MFA_REQUIRED", data={"mfa_required": True})
        if not verify_mfa(user, payload.mfa_code):
            audit_service.log_login(
                db, user_id=user.id, email=payload.email,
                success=False, message="MFA 校验失败", **meta,
            )
            raise AppError("MFA_INVALID", data={"mfa_required": True})

    access, refresh, _sid = _issue_session(db, user.id, meta)
    audit_service.log_login(
        db, user_id=user.id, email=payload.email, success=True, message="登录成功", **meta
    )
    return user, access, refresh


def _issue_session(
    db: Session, user_id: uuid.UUID, meta: dict, rotated_from_id: uuid.UUID | None = None
) -> tuple[str, str, uuid.UUID]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session = AuthSession(
        user_id=user_id,
        refresh_token_hash="pending",
        expires_at=expires_at,
        rotated_from_id=rotated_from_id,
        created_at=now,
        user_agent=meta.get("user_agent"),
        ip=meta.get("ip"),
    )
    db.add(session)
    db.flush()
    refresh = create_token(
        user_id, session.id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    session.refresh_token_hash = sha256_hex(refresh)
    access = create_token(
        user_id, session.id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    db.flush()
    return access, refresh, session.id


def refresh(db: Session, refresh_token: str) -> tuple[User, str, str]:
    """刷新令牌轮换。检测到已轮换/已撤销令牌被复用 → 撤销整条链。"""
    payload = decode_token(refresh_token, "refresh")
    sid = uuid.UUID(payload["sid"])
    session = db.get(AuthSession, sid)
    if session is None:
        raise AppError("REFRESH_TOKEN_INVALID")
    if session.revoked_at is not None:
        # 复用检测：撤销整条轮换链，要求重新登录
        _revoke_chain(db, session)
        audit_service.log_security_event(
            db, kind="refresh_token_reuse",
            user_id=session.user_id,
            detail={"session_id": str(sid), "chain_revoked": True},
        )
        # 【重要】先提交撤销再抛错，否则请求级回滚会撤销"链撤销"本身
        db.commit()
        raise AppError("REFRESH_TOKEN_INVALID", "检测到凭证复用，请重新登录")
    if session.refresh_token_hash != sha256_hex(refresh_token):
        raise AppError("REFRESH_TOKEN_INVALID")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise AppError("ACCOUNT_DISABLED")

    now = datetime.now(timezone.utc)
    session.revoked_at = now  # 旧会话立即作废（轮换）
    db.flush()
    access, new_refresh, _ = _issue_session(
        db, user.id, {"ip": session.ip, "user_agent": session.user_agent},
        rotated_from_id=session.id,
    )
    return user, access, new_refresh


def _revoke_chain(db: Session, session: AuthSession) -> None:
    current = session
    while current is not None:
        if current.revoked_at is None:
            current.revoked_at = datetime.now(timezone.utc)
        nxt = (
            db.execute(
                select(AuthSession).where(AuthSession.rotated_from_id == current.id)
            ).scalar_one_or_none()
        )
        current = nxt
    db.flush()


def logout(db: Session, access_payload: dict) -> None:
    """撤销当前会话。"""
    sid = uuid.UUID(access_payload["sid"])
    session = db.get(AuthSession, sid)
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.flush()


def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> int:
    """撤销用户全部会话（封禁/改密后调用）。"""
    count = 0
    for s in db.execute(select(AuthSession).where(AuthSession.user_id == user_id)).scalars():
        if s.revoked_at is None:
            s.revoked_at = datetime.now(timezone.utc)
            count += 1
    db.flush()
    return count


def decode_access(access_token: str) -> dict:
    return decode_token(access_token, "access")
