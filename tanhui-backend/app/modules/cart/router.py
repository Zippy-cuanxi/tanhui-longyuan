"""消费者购物车接口。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ApiResponse
from app.modules.cart import service
from app.modules.cart.schemas import CartItemAddIn, CartItemOut, CartItemUpdateIn, CartOut
from app.modules.users.models import User

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=ApiResponse[CartOut], summary="我的购物车（价格/库存实时）")
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ApiResponse(data=service.get_cart(db, user.id))


@router.post("/items", response_model=ApiResponse[CartItemOut], summary="加入购物车")
def add_item(
    payload: CartItemAddIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service.add_item(db, user.id, payload)
    cart = service.get_cart(db, user.id)
    target = next(i for i in cart.items if i.sku_id == payload.sku_id)
    return ApiResponse(data=target)


@router.patch("/items/{item_id}", response_model=ApiResponse[CartItemOut], summary="修改数量/勾选")
def update_item(
    item_id: uuid.UUID,
    payload: CartItemUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service.update_item(db, user.id, item_id, payload.quantity, payload.checked)
    cart = service.get_cart(db, user.id)
    target = next((i for i in cart.items if i.id == item_id), None)
    return ApiResponse(data=target)


@router.delete("/items/{item_id}", response_model=ApiResponse[None], summary="删除购物车条目")
def remove_item(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service.remove_item(db, user.id, item_id)
    return ApiResponse(message="已删除")
