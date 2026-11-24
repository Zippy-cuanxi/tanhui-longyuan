"""绿色资料域：product_green_profiles / carbon_assessments / verification_records。

【重要】碳评估数据默认 verified=false（未核验），对外输出必须显式携带核验状态，
避免把估算值当作已核验数据展示。
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin
from app.core.types import GUID, JSONBType, UTCDatetime


class ProductGreenProfile(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "product_green_profiles"

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), unique=True, index=True)
    origin: Mapped[str] = mapped_column(String(128))  # 产地（如 甘肃定西）
    planting_mode: Mapped[str | None] = mapped_column(String(128))  # 种植方式（有机/绿色/地理标志）
    certifications: Mapped[list | None] = mapped_column(JSONBType())  # [{name, issuer, valid_until}]
    description: Mapped[str | None] = mapped_column(Text)
    # draft / pending_review / approved / rejected
    status: Mapped[str] = mapped_column(String(16), default="draft")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID())


class CarbonAssessment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "carbon_assessments"

    product_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    co2e_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 4))  # kg CO2e/件（估算）
    unit: Mapped[str] = mapped_column(String(16), default="kg")
    methodology: Mapped[str | None] = mapped_column(String(255))  # 评估方法说明
    # 【未核验标记】仅平台核验后才为 true
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verifier_id: Mapped[uuid.UUID | None] = mapped_column(GUID())


class VerificationRecord(UUIDPKMixin, Base):
    __tablename__ = "verification_records"

    assessment_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    result: Mapped[str] = mapped_column(String(16))  # pass / fail
    notes: Mapped[str | None] = mapped_column(Text)
    verifier_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime())
