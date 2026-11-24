"""绿豆积分域模型：point_accounts / point_transactions / point_rules / point_rule_versions。

设计要点：
- 独立账户、余额快照流水（balance_after）；
- 规则版本化：每次修改生成新版本，流水引用当时的版本（可追溯）；
- 所有关键操作以 idempotency_key 幂等（唯一约束兜底）。
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, JSONBType, UTCDatetime


class PointAccount(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "point_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), unique=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)


class PointTransaction(UUIDPKMixin, Base):
    __tablename__ = "point_transactions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_point_txn_idem"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    # earn 发放 / spend 消费 / reverse 冲正 / adjust 管理员调整
    type: Mapped[str] = mapped_column(String(16), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # 正数增加，负数减少
    balance_after: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str | None] = mapped_column(String(32))
    source_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    rule_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    note: Mapped[str | None] = mapped_column(Text)
    operator_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow, index=True)


class PointRule(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "point_rules"

    code: Mapped[str] = mapped_column(String(32), unique=True)  # order_earn / deduct / refund_reverse
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(String(255))
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID())


class PointRuleVersion(UUIDPKMixin, Base):
    __tablename__ = "point_rule_versions"
    __table_args__ = (UniqueConstraint("rule_id", "version", name="uq_rule_version"),)

    rule_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("point_rules.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(JSONBType())  # {"rate": "1", "enabled": true}
    effective_from: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)
