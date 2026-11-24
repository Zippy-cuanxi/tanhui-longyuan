"""通知服务：站内通知写入（业务事件后调用）。"""
import uuid

from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.modules.notifications.models import Notification


def notify(db: Session, user_id: uuid.UUID, type_: str, title: str, content: str) -> None:
    db.add(Notification(user_id=user_id, type=type_, title=title, content=content))
    db.flush()


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user_id:
        from app.core.errors import AppError

        raise AppError("NOT_FOUND", "通知不存在")
    if n.read_at is None:
        n.read_at = utcnow()
        db.flush()


def mark_all_read(db: Session, user_id: uuid.UUID) -> None:
    from sqlalchemy import select

    for n in db.execute(
        select(Notification).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
    ).scalars():
        n.read_at = utcnow()
    db.flush()
