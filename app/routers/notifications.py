from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.schemas.notification import (
    MessageResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    usuario_id: UUID,
    service: NotificationService = Depends(get_notification_service),
):
    notifications = await service.get_notifications(usuario_id)
    return [NotificationResponse.from_notification(n) for n in notifications]


@router.get("/count", response_model=UnreadCountResponse)
async def count_unread(
    usuario_id: UUID,
    service: NotificationService = Depends(get_notification_service),
):
    count = await service.count_unread(usuario_id)
    return UnreadCountResponse(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: UUID,
    usuario_id: UUID,
    service: NotificationService = Depends(get_notification_service),
):
    notification = await service.mark_as_read(notification_id, usuario_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificação não encontrada",
        )
    return NotificationResponse.from_notification(notification)


@router.patch("/read-all", response_model=MessageResponse)
async def mark_all_as_read(
    usuario_id: UUID,
    service: NotificationService = Depends(get_notification_service),
):
    count = await service.mark_all_as_read(usuario_id)
    return MessageResponse(message=f"{count} notificações marcadas como lidas")
