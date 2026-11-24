"""用户域 Pydantic Schema。"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    phone: str | None = None
    is_active: bool
    is_email_verified: bool
    mfa_enabled: bool
    created_at: datetime


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    nickname: str | None = None
    avatar_url: str | None = None
    gender: str | None = None
    birthday: date | None = None
    bio: str | None = None


class MeOut(BaseModel):
    user: UserOut
    profile: ProfileOut | None = None


class ProfileUpdateIn(BaseModel):
    nickname: str | None = Field(None, max_length=64)
    avatar_url: str | None = Field(None, max_length=512)
    gender: str | None = Field(None, max_length=16)
    birthday: date | None = None
    bio: str | None = Field(None, max_length=255)


class AddressIn(BaseModel):
    receiver: str = Field(..., max_length=64)
    phone: str = Field(..., max_length=32)
    province: str = Field(..., max_length=32)
    city: str = Field(..., max_length=32)
    district: str | None = Field(None, max_length=32)
    detail: str = Field(..., max_length=255)
    is_default: bool = False


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    receiver: str
    phone: str
    province: str
    city: str
    district: str | None = None
    detail: str
    is_default: bool
