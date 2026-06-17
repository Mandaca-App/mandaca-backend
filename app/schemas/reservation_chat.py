from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.reservation_message import TipoRemetente


class ReservationMessageCreate(BaseModel):
    remetente_id: UUID
    conteudo: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]


class ReservationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_mensagem: UUID
    reserva_id: UUID
    remetente_id: UUID
    tipo_remetente: TipoRemetente
    conteudo: str
    criado_em: datetime
