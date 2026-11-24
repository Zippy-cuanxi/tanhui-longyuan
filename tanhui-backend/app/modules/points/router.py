"""积分接口：账户、流水、兑换。"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, page_params
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.points import service
from app.modules.points.models import PointTransaction
from app.modules.users.models import User

router = APIRouter(prefix="/points", tags=["points"])


class AccountOut(BaseModel):
    balance: int


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    amount: int
    balance_after: int
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    note: str | None = None
    created_at: datetime


class RedeemIn(BaseModel):
    reward_code: str


class RedeemOut(BaseModel):
    reward_code: str
    reward_name: str
    points_spent: int
    voucher_code: str
    mock: bool


@router.get("/account", response_model=ApiResponse[AccountOut], summary="我的绿豆账户")
def my_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ApiResponse(data=AccountOut(balance=service.get_balance(db, user.id)))


@router.get("/transactions", response_model=ApiResponse[PageOut[TransactionOut]], summary="绿豆流水")
def my_transactions(
    type_: str | None = None,
    page_size_pair: tuple[int, int] = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(PointTransaction)
        .where(PointTransaction.user_id == user.id)
        .order_by(PointTransaction.created_at.desc())
    )
    if type_:
        stmt = stmt.where(PointTransaction.type == type_)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(
        data=PageOut(items=[TransactionOut.model_validate(i) for i in items], pagination=pagination)
    )


@router.get("/redemption-catalog", response_model=ApiResponse[list], summary="可兑换权益目录（Mock）")
def catalog(user: User = Depends(get_current_user)):
    return ApiResponse(
        data=[
            {"reward_code": code, "name": r["name"], "points": r["points"], "mock": True}
            for code, r in service.REDEMPTION_CATALOG.items()
        ]
    )


@router.post("/redemptions", response_model=ApiResponse[RedeemOut], summary="绿豆兑换（Mock 权益）")
def redeem(
    payload: RedeemIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = service.redeem(db, user.id, payload.reward_code)
    return ApiResponse(data=RedeemOut(**result))
