"""消费者侧用户接口：GET/PATCH /users/me、收货地址管理。"""
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ApiResponse
from app.modules.catalog import storage
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import (
    AddressIn,
    AddressOut,
    MeOut,
    ProfileOut,
    ProfileUpdateIn,
    UserOut,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=ApiResponse[MeOut], summary="当前登录用户信息")
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = service.get_profile(db, user.id)
    return ApiResponse(
        data=MeOut(user=UserOut.model_validate(user), profile=ProfileOut.model_validate(profile) if profile else None)
    )


@router.patch("/me", response_model=ApiResponse[ProfileOut], summary="更新个人资料")
def update_me(
    payload: ProfileUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = service.update_profile(db, user.id, payload)
    return ApiResponse(data=ProfileOut.model_validate(profile))


@router.post("/me/avatar", response_model=ApiResponse[ProfileOut], summary="上传个人头像")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data, filename = await storage.validate_and_read(file)
    url = storage.get_storage().save(data, filename)
    profile = service.update_profile(db, user.id, ProfileUpdateIn(avatar_url=url))
    return ApiResponse(data=ProfileOut.model_validate(profile))


@router.get(
    "/me/addresses", response_model=ApiResponse[list[AddressOut]], summary="收货地址列表"
)
def list_my_addresses(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    items = service.list_addresses(db, user.id)
    return ApiResponse(data=[AddressOut.model_validate(a) for a in items])


@router.post(
    "/me/addresses", response_model=ApiResponse[AddressOut], summary="新增收货地址"
)
def create_address(
    payload: AddressIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    addr = service.create_address(db, user.id, payload)
    return ApiResponse(data=AddressOut.model_validate(addr))


@router.put(
    "/me/addresses/{address_id}", response_model=ApiResponse[AddressOut], summary="修改收货地址"
)
def update_address(
    address_id: uuid.UUID,
    payload: AddressIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    addr = service.update_address(db, user.id, address_id, payload)
    return ApiResponse(data=AddressOut.model_validate(addr))


@router.delete(
    "/me/addresses/{address_id}", response_model=ApiResponse[None], summary="删除收货地址"
)
def delete_address(
    address_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service.delete_address(db, user.id, address_id)
    return ApiResponse(message="已删除")
