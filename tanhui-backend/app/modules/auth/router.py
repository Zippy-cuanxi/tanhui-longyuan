"""认证接口：注册 / 登录 / 刷新 / 登出 / 会话列表 / MFA 绑定。"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ApiResponse
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginIn,
    MfaBindIn,
    RefreshIn,
    RegisterIn,
    SessionOut,
    TokenPairOut,
)
from app.modules.users.schemas import UserOut
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[UserOut], summary="注册消费者账号")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    user = service.register(db, payload)
    return ApiResponse(data=UserOut.model_validate(user))


@router.post("/login", response_model=ApiResponse[TokenPairOut], summary="登录（管理员可能要求 MFA）")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    user, access, refresh = service.login(db, payload, request)
    from app.core.config import settings

    return ApiResponse(
        data=TokenPairOut(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    )


@router.post("/refresh", response_model=ApiResponse[TokenPairOut], summary="刷新令牌（轮换，旧令牌作废）")
def refresh_tokens(payload: RefreshIn, db: Session = Depends(get_db)):
    user, access, refresh = service.refresh(db, payload.refresh_token)
    from app.core.config import settings

    return ApiResponse(
        data=TokenPairOut(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    )


@router.post("/logout", response_model=ApiResponse[None], summary="登出（撤销当前会话）")
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    payload = service.decode_access(token)
    service.logout(db, payload)
    return ApiResponse(message="已登出")


@router.get("/sessions", response_model=ApiResponse[list[SessionOut]], summary="我的登录会话列表")
def my_sessions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from app.modules.auth.models import AuthSession

    sessions = list(
        db.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user.id)
            .order_by(AuthSession.created_at.desc())
        ).scalars()
    )
    return ApiResponse(
        data=[
            SessionOut(
                id=s.id,
                user_agent=s.user_agent,
                ip=s.ip,
                created_at=s.created_at,
                expires_at=s.expires_at,
                revoked=s.revoked_at is not None,
            )
            for s in sessions
        ]
    )


@router.post(
    "/sessions/revoke-all", response_model=ApiResponse[None], summary="撤销我的全部会话"
)
def revoke_all(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    count = service.revoke_all_sessions(db, user.id)
    return ApiResponse(message=f"已撤销 {count} 个会话")


@router.post(
    "/mfa/bind", response_model=ApiResponse[None], summary="绑定 TOTP MFA（仿真：任意有效 secret）"
)
def bind_mfa(
    payload: MfaBindIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.mfa_secret = payload.secret
    user.mfa_enabled = True
    db.flush()
    return ApiResponse(message="MFA 已绑定")
