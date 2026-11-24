"""商家店铺接口：店铺资料、员工管理、工作台统计。

数据范围：store_id 一律通过 resolve_store_ctx 校验成员身份后使用，
绝不信任客户端直接操作他店资源。
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, resolve_store_ctx
from app.core.responses import ApiResponse
from app.modules.stores import service
from app.modules.stores.schemas import (
    EmployeeIn,
    EmployeeOut,
    EmployeeUpdateIn,
    StoreOut,
    StoreUpdateIn,
)
from app.modules.users.models import User

router = APIRouter(prefix="/merchant", tags=["merchant-stores"])


@router.get("/stores", response_model=ApiResponse[list[StoreOut]], summary="我的店铺列表")
def my_stores(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from app.modules.stores.models import Store, StoreMember

    stores = list(
        db.execute(
            select(Store)
            .join(StoreMember, StoreMember.store_id == Store.id)
            .where(StoreMember.user_id == user.id)
        ).scalars()
    )
    return ApiResponse(data=[StoreOut.model_validate(s) for s in stores])


@router.patch(
    "/stores/{store_id}", response_model=ApiResponse[StoreOut], summary="更新店铺资料（owner/manager）"
)
def update_store(
    store_id: uuid.UUID,
    payload: StoreUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolve_store_ctx(db, user, store_id, "store:read")
    store = service.update_store(db, store_id, payload, user.id)
    return ApiResponse(data=StoreOut.model_validate(store))


@router.get(
    "/stores/{store_id}/employees", response_model=ApiResponse[list[EmployeeOut]], summary="员工列表"
)
def list_employees(
    store_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolve_store_ctx(db, user, store_id, "employee:manage")
    return ApiResponse(data=[EmployeeOut(**e) for e in service.list_employees(db, store_id)])


@router.post(
    "/stores/{store_id}/employees", response_model=ApiResponse[EmployeeOut], summary="添加员工"
)
def add_employee(
    store_id: uuid.UUID,
    payload: EmployeeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolve_store_ctx(db, user, store_id, "employee:manage")
    member = service.add_employee(db, store_id, payload.email, payload.role, user.id)
    return ApiResponse(data=EmployeeOut.model_validate(member))


@router.patch(
    "/stores/{store_id}/employees/{member_id}", response_model=ApiResponse[EmployeeOut], summary="调整员工角色"
)
def update_employee(
    store_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: EmployeeUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolve_store_ctx(db, user, store_id, "employee:manage")
    member = service.update_employee_role(db, store_id, member_id, payload.role, user.id)
    return ApiResponse(data=EmployeeOut.model_validate(member))


@router.delete(
    "/stores/{store_id}/employees/{member_id}", response_model=ApiResponse[None], summary="移除员工"
)
def remove_employee(
    store_id: uuid.UUID,
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolve_store_ctx(db, user, store_id, "employee:manage")
    service.remove_employee(db, store_id, member_id, user.id)
    return ApiResponse(message="已移除")


@router.get(
    "/stores/{store_id}/dashboard", response_model=ApiResponse[dict], summary="商家工作台统计"
)
def store_dashboard(
    store_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolve_store_ctx(db, user, store_id, "store:read")
    return ApiResponse(data=service.dashboard(db, store_id))
