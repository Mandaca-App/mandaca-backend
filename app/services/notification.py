from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def get_notifications(self, usuario_id: UUID) -> list[Notification]:
        stmt = select(Notification).where(
            Notification.usuario_id == usuario_id, Notification.deleted_at.is_(None)
        )
        return list(self.db.execute(stmt).scalars().all())

    async def count_unread(self, usuario_id: UUID) -> int:
        stmt = select(func.count()).where(
            Notification.usuario_id == usuario_id,
            Notification.lida.is_(False),
            Notification.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one()

    async def mark_as_read(self, notification_id: UUID, usuario_id: UUID) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.usuario_id == usuario_id,
            Notification.deleted_at.is_(None),
        )
        notification = self.db.execute(stmt).scalars().first()
        if not notification:
            return None
        notification.lida = True
        self.db.commit()
        self.db.refresh(notification)
        return notification

    async def mark_all_as_read(self, usuario_id: UUID) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.usuario_id == usuario_id,
                Notification.lida.is_(False),
                Notification.deleted_at.is_(None),
            )
            .values(lida=True)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount
