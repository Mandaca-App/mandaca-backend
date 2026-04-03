from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.session import get_db
from app.models.notification import Notification
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/", response_model=List[NotificationResponse])
def listar_notificacoes(user_id: UUID, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    notificacoes = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read.is_(False)
    ).offset(skip).limit(limit).all()
    return notificacoes

@router.get("/count")
def contar_notificacoes(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    total = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read.is_(False)
    ).count()
    return {"unread_count": total}

@router.patch("/{notification_id}/read")
def marcar_como_lida(
    notification_id: int,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    notificacao = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")

    notificacao.is_read = True
    db.commit()
    db.refresh(notificacao)
    return notificacao

@router.patch("/read-all")
def marcar_todas_como_lidas(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return {"detail": "Todas as notificações marcadas como lidas"}