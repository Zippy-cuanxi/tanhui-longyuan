"""商家域 Schema。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MerchantApplyIn(BaseModel):
    company_name: str = Field(..., max_length=128)
    license_no: str = Field(..., max_length=64)
    license_url: str | None = Field(None, max_length=512)
    legal_person: str = Field(..., max_length=64)
    contact_phone: str = Field(..., max_length=32)
    region: str | None = Field(None, max_length=64)
    # 初始店铺名称（审核通过后自动创建默认店铺）
    store_name: str = Field(..., max_length=64)


class MerchantOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    status: str
    company_name: str
    license_no: str
    license_url: str | None = None
    legal_person: str
    contact_phone: str
    region: str | None = None
    reject_reason: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class MerchantReviewIn(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|freeze|unfreeze)$")
    reason: str | None = Field(None, max_length=255)
