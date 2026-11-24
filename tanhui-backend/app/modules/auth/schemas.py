"""认证域 Schema。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    nickname: str | None = Field(None, max_length=64)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    mfa_code: str | None = Field(None, min_length=4, max_length=8)


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # access token 有效期（秒）


class RefreshIn(BaseModel):
    refresh_token: str


class SessionOut(BaseModel):
    id: uuid.UUID
    user_agent: str | None = None
    ip: str | None = None
    created_at: datetime
    expires_at: datetime
    revoked: bool


class MfaBindIn(BaseModel):
    secret: str = Field(..., min_length=8, max_length=64)  # TOTP base32
