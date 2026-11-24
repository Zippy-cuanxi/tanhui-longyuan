"""店铺域 Schema。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class StoreOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    logo_url: str | None = None
    description: str | None = None
    region: str | None = None
    status: str
    is_closed_temporarily: bool
    created_at: datetime


class StoreUpdateIn(BaseModel):
    name: str | None = Field(None, max_length=64)
    logo_url: str | None = Field(None, max_length=512)
    description: str | None = Field(None, max_length=1024)
    region: str | None = Field(None, max_length=64)
    is_closed_temporarily: bool | None = None


class EmployeeIn(BaseModel):
    email: EmailStr = Field(..., description="要添加的成员账号邮箱（须已注册）")
    role: str = Field("staff", pattern="^(manager|staff|viewer)$")


class EmployeeUpdateIn(BaseModel):
    role: str = Field(..., pattern="^(manager|staff|viewer)$")


class EmployeeOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    store_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    status: str
    created_at: datetime
    email: str | None = None
