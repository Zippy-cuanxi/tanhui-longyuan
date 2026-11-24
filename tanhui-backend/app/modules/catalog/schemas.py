"""商品域 Schema。"""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.responses import MoneyOut


class SkuIn(BaseModel):
    spec: str = Field(..., max_length=128)
    code: str | None = Field(None, max_length=64)
    price: Decimal = Field(..., gt=0)
    initial_stock: int = Field(0, ge=0, description="初始库存（创建时写入库存域）")

    @field_validator("price")
    @classmethod
    def two_decimals(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:
            raise ValueError("价格最多两位小数")
        return v


class SkuOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    product_id: uuid.UUID
    spec: str
    code: str | None = None
    price: MoneyOut
    is_active: bool


class ProductCreateIn(BaseModel):
    title: str = Field(..., max_length=128)
    subtitle: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=10000)
    category_id: uuid.UUID | None = None
    aid_project_id: uuid.UUID | None = None
    skus: list[SkuIn] = Field(..., min_length=1)


class ProductUpdateIn(BaseModel):
    title: str | None = Field(None, max_length=128)
    subtitle: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=10000)
    category_id: uuid.UUID | None = None
    aid_project_id: uuid.UUID | None = None


class ProductImageOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    url: str
    sort: int


class ProductOut(BaseModel):
    """商品列表项（消费者视角，仅含审核通过且上架的商品）。"""

    class Config:
        from_attributes = True

    id: uuid.UUID
    store_id: uuid.UUID
    category_id: uuid.UUID | None = None
    aid_project_id: uuid.UUID | None = None
    title: str
    subtitle: str | None = None
    is_listed: bool
    created_at: datetime
    min_price: MoneyOut | None = None
    cover_url: str | None = None
    store_name: str | None = None


class ProductDetailOut(ProductOut):
    description: str | None = None
    status: str
    audit_reason: str | None = None
    audited_at: datetime | None = None
    skus: list[SkuOut] = []
    images: list[ProductImageOut] = []


class AuditIn(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|remove)$")
    reason: str | None = Field(None, max_length=255)


class ProductAuditRecordOut(BaseModel):
    class Config:
        from_attributes = True

    id: uuid.UUID
    product_id: uuid.UUID
    action: str
    reason: str | None = None
    operator_id: uuid.UUID | None = None
    created_at: datetime
