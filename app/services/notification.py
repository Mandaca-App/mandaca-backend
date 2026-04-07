from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def get_notifications(db: Session, usuario_id: UUID) -> list[Notification]:
    stmt = select(Notification).where(
        Notification.usuario_id == usuario_id, Notification.deleted_at.is_(None)
    )
    return list(db.execute(stmt).scalars().all())


def count_unread(db: Session, usuario_id: UUID) -> int:
    stmt = select(Notification).where(
        Notification.usuario_id == usuario_id,
        Notification.lida.is_(False),
        Notification.deleted_at.is_(None),
    )
    return len(db.execute(stmt).scalars().all())


def mark_as_read(db: Session, notification_id: UUID, usuario_id: UUID) -> Notification | None:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.usuario_id == usuario_id,
        Notification.deleted_at.is_(None),
    )
    notification = db.execute(stmt).scalars().first()
    if not notification:
        return None
    notification.lida = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_as_read(db: Session, usuario_id: UUID) -> int:
    stmt = select(Notification).where(
        Notification.usuario_id == usuario_id,
        Notification.lida.is_(False),
        Notification.deleted_at.is_(None),
    )
    updated = list(db.execute(stmt).scalars().all())
    for notification in updated:
        notification.lida = True
    db.commit()
    return len(updated)
