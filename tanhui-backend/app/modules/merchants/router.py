"""商家端接口：入驻申请、我的商家身份。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ApiResponse
from app.modules.merchants import service
from app.modules.merchants.schemas import MerchantApplyIn, MerchantOut
from app.modules.users.models import User

router = APIRouter(prefix="/merchant", tags=["merchant"])


@router.post(
    "/apply", response_model=ApiResponse[MerchantOut], summary="提交入驻申请（任意登录用户）"
)
def apply(
    payload: MerchantApplyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merchant = service.apply(db, user.id, payload)
    return ApiResponse(data=MerchantOut.model_validate(merchant))


@router.get(
    "/merchants/me", response_model=ApiResponse[list[MerchantOut]], summary="我所属的商家主体"
)
def my_merchants(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return ApiResponse(
        data=[MerchantOut.model_validate(m) for m in service.get_my_merchants(db, user.id)]
    )
