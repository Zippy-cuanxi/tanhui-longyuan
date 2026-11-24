"""助农域：cooperatives / aid_projects / aid_records（项目内容为仿真数据）。"""
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, UTCDatetime, Amount


class Cooperative(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cooperatives"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    region: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    contact: Mapped[str | None] = mapped_column(String(64))


class AidProject(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "aid_projects"

    cooperative_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("cooperatives.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(128))
    cover_url: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    # 目标/已筹金额为仿真展示字段，资金流口径待业务确认
    goal_amount: Mapped[Decimal | None] = mapped_column(Amount())
    raised_amount: Mapped[Decimal] = mapped_column(Amount(), default=0)
    # draft / pending_review / published / offline
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    published_at: Mapped[datetime | None] = mapped_column(UTCDatetime())


class AidDonation(UUIDPKMixin, Base):
    """用户对助农项目的资助记录（仿真支付，积分按 1 元 = 3 积分发放）。"""

    __tablename__ = "aid_donations"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("aid_projects.id"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Amount())
    display_mode: Mapped[str] = mapped_column(String(16), default="anonymous")
    display_name: Mapped[str | None] = mapped_column(String(64))
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)


class AidRecord(UUIDPKMixin, Base):
    """助农参与记录（下单捐助/人工记录，仿真）。"""

    __tablename__ = "aid_records"

    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    amount: Mapped[Decimal] = mapped_column(Amount())
    kind: Mapped[str] = mapped_column(String(16), default="order")  # order / manual
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)
