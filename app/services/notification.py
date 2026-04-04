from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import Notification


def get_notifications(db: Session, usuario_id: UUID) -> list[Notification]:
    return db.query(Notification).filter(Notification.usuario_id == usuario_id).all()


def count_unread(db: Session, usuario_id: UUID) -> int:
    return (
        db.query(Notification)
        .filter(Notification.usuario_id == usuario_id, Notification.lida.is_(False))
        .count()
    )


def mark_as_read(db: Session, notification_id: UUID, usuario_id: UUID) -> Notification | None:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.usuario_id == usuario_id)
        .first()
    )
    if not notification:
        return None
    notification.lida = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_as_read(db: Session, usuario_id: UUID) -> int:
    updated = (
        db.query(Notification)
        .filter(Notification.usuario_id == usuario_id, Notification.lida.is_(False))
        .all()
    )
    for notification in updated:
        notification.lida = True
    db.commit()
    return len(updated)
