from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.models.reservation import StatusReserva


class ReservationCreate(BaseModel):
    num_pessoas: int
    mensagem: Annotated[Optional[str], StringConstraints(max_length=120)] = None
    usuario_id: Optional[UUID] = None
    empresa_id: Optional[UUID] = None
    horario_reserva: datetime


class ReservationStatusUpdate(BaseModel):
    status: StatusReserva


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_reserva: UUID
    num_pessoas: int
    horario_reserva: datetime
    mensagem: Optional[str] = None
    status: StatusReserva
    usuario_id: Optional[UUID] = None
    empresa_id: Optional[UUID] = None
    usuario_nome: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def extrair_usuario_nome(cls, data):
        if hasattr(data, "usuario") and data.usuario:
            nome_usuario = getattr(data.usuario, "nome", None)
            if hasattr(data, "__dict__"):
                data.__dict__["usuario_nome"] = nome_usuario
            else:
                setattr(data, "usuario_nome", nome_usuario)

        elif isinstance(data, dict):
            usuario = data.get("usuario")
            if usuario:
                data["usuario_nome"] = (
                    usuario.get("nome")
                    if isinstance(usuario, dict)
                    else getattr(usuario, "nome", None)
                )

        return data
