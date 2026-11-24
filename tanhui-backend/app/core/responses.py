"""统一成功响应结构与分页工具。"""
from decimal import Decimal
from typing import Annotated, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, PlainSerializer
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_request_id

T = TypeVar("T")

# 金额输出统一为两位小数字符串（如 "12.00"），避免浮点误差
MoneyOut = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str)]


class ApiResponse(BaseModel, Generic[T]):
    """统一成功响应：{code, message, data, request_id}。"""

    code: str = "OK"
    message: str = "success"
    data: Optional[T] = None
    request_id: Optional[str] = Field(default_factory=get_request_id)


class PaginationOut(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PageOut(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationOut


def build_pagination(total: int, page: int, page_size: int) -> PaginationOut:
    return PaginationOut(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size if page_size else 0,
    )


def paginate(db: Session, stmt: Select, page: int | None, page_size: int | None):
    """对查询语句执行统一分页，返回 (items, PaginationOut)。"""
    page = max(page or 1, 1)
    page_size = min(max(page_size or settings.DEFAULT_PAGE_SIZE, 1), settings.MAX_PAGE_SIZE)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = list(
        db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars()
    )
    return items, build_pagination(total, page, page_size)
