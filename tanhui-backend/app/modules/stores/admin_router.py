"""店铺管理端接口：店铺列表 / 停业 / 恢复 / 关闭（需 store:manage 权限）。"""
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import page_params, require_permissions
from app.core.errors import AppError
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.audit import service as audit_service
from app.modules.stores.models import Store
from app.modules.stores.schemas import StoreOut

router = APIRouter(prefix="/admin/stores", tags=["admin-stores"])


class StoreActionIn(BaseModel):
    action: str  # suspend / activate / close


@router.get("", response_model=ApiResponse[PageOut[StoreOut]], summary="店铺列表")
def list_stores(
    status: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("store:read")),
    db: Session = Depends(get_db),
):
    stmt: Select = select(Store).order_by(Store.created_at.desc())
    if status:
        stmt = stmt.where(Store.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(items=[StoreOut.model_validate(i) for i in items], pagination=pagination)
    )


@router.post("/{store_id}/status", response_model=ApiResponse[StoreOut], summary="变更店铺状态")
def change_store_status(
    store_id: uuid.UUID,
    payload: StoreActionIn,
    admin=Depends(require_permissions("store:manage")),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if store is None:
        raise AppError("NOT_FOUND", "店铺不存在")
    mapping = {"suspend": "suspended", "activate": "active", "close": "closed"}
    if payload.action not in mapping:
        raise AppError("VALIDATION_ERROR", "未知操作")
    if store.status == "closed":
        raise AppError("CONFLICT", "已关闭店铺不可再变更")
    store.status = mapping[payload.action]
    db.flush()
    audit_service.log_operation(
        db, operator_id=admin.id, action=f"store.{payload.action}",
        resource="store", resource_id=str(store_id),
    )
    return ApiResponse(data=StoreOut.model_validate(store))
