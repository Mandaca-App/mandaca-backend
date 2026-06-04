from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.reservation import StatusReserva


class ReservationCreate(BaseModel):
    num_mesas: int
    num_pessoas: int
    mensagem: Annotated[Optional[str], StringConstraints(max_length=120)] = None
    usuario_id: Optional[UUID] = None
    empresa_id: Optional[UUID] = None


class ReservationStatusUpdate(BaseModel):
    status: StatusReserva


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_reserva: UUID
    num_mesas: int
    num_pessoas: int
    mensagem: Optional[str] = None
    status: StatusReserva
    usuario_id: Optional[UUID] = None
    empresa_id: Optional[UUID] = None
