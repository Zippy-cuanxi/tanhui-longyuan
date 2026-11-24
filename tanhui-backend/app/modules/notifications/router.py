"""站内通知接口。"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ApiResponse
from app.modules.notifications import service
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    content: str
    read_at: datetime | None = None
    created_at: datetime


@router.get("", response_model=ApiResponse[list[NotificationOut]], summary="我的通知（最近100条）")
def my_notifications(
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.modules.notifications.models import Notification

    stmt = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    items = list(db.execute(stmt).scalars())
    return ApiResponse(data=[NotificationOut.model_validate(i) for i in items])


@router.post("/{notification_id}/read", response_model=ApiResponse[None], summary="标记已读")
def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service.mark_read(db, user.id, notification_id)
    return ApiResponse(message="已读")


@router.post("/read-all", response_model=ApiResponse[None], summary="全部已读")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.mark_all_read(db, user.id)
    return ApiResponse(message="已全部标记为已读")
