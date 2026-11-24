"""跨数据库兼容的列类型（UUID / JSONB / UTC 时间 / 金额）。"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CHAR, JSON, Numeric, DateTime, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID


class GUID(TypeDecorator):
    """UUID 类型：PostgreSQL 用原生 UUID，SQLite 用 CHAR(36)。"""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class JSONBType(TypeDecorator):
    """JSONB 类型：PostgreSQL 用原生 JSONB，SQLite 退化为 JSON。"""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class UTCDatetime(TypeDecorator):
    """统一 UTC 时间：SQLite 存取会丢失时区，此处读出时统一补 UTC。"""
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Amount(TypeDecorator):
    """金额类型：统一 NUMERIC(12,2) + Decimal，禁止浮点。"""
    impl = Numeric
    cache_ok = True

    def __init__(self):
        super().__init__(precision=12, scale=2, asdecimal=True)

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(Numeric(12, 2, asdecimal=True))


def q2(value: Decimal | int | str) -> Decimal:
    """金额统一保留两位小数。"""
    return Decimal(str(value)).quantize(Decimal("0.01"))
