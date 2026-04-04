from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.notification import MessageResponse, NotificationResponse, UnreadCountResponse
from app.services import notification as notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationResponse])
def list_notifications(usuario_id: UUID, db: Session = Depends(get_db)):
    notifications = notification_service.get_notifications(db, usuario_id)
    return [NotificationResponse.from_notification(n) for n in notifications]


@router.get("/count", response_model=UnreadCountResponse)
def count_unread(usuario_id: UUID, db: Session = Depends(get_db)):
    count = notification_service.count_unread(db, usuario_id)
    return UnreadCountResponse(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(notification_id: UUID, usuario_id: UUID, db: Session = Depends(get_db)):
    notification = notification_service.mark_as_read(db, notification_id, usuario_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificação não encontrada",
        )
    return NotificationResponse.from_notification(notification)


@router.patch("/read-all", response_model=MessageResponse)
def mark_all_as_read(usuario_id: UUID, db: Session = Depends(get_db)):
    count = notification_service.mark_all_as_read(db, usuario_id)
    return MessageResponse(message=f"{count} notificações marcadas como lidas")
