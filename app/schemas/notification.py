from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.notification import Notification


class NotificationResponse(BaseModel):
    id: UUID
    usuario_id: UUID
    titulo: str
    mensagem: str
    lida: bool
    data_criacao: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_notificaiton(cls, notification: Notification):
        return cls(
            id=notification.id,
            usuario_id=notification.usuario_id,
            titulo=notification.titulo,
            mensagem=notification.mensagem,
            lida=notification.lida,
            data_criacao=notification.data_criacao,
        )

class UnreadCountResponse(BaseModel):
    unread_count: int

class MessageResponse(BaseModel):
    message: str