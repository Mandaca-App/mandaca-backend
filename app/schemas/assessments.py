from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.assessment import TipoAvaliacao


class AssessmentCreate(BaseModel):
    texto: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    usuario_id: UUID
    empresa_id: UUID


class AssessmentUpdate(BaseModel):
    texto: Annotated[Optional[str], StringConstraints(max_length=500)] = None
    usuario_id: Optional[UUID] = None
    empresa_id: Optional[UUID] = None


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_avaliacao: UUID
    texto: str
    tipo_avaliacao: TipoAvaliacao  # serializado como inteiro (0-4)
    usuario_id: UUID
    empresa_id: UUID
    created_at: datetime
