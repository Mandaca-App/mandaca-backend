from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

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
    usuario_nome: Optional[str] = None
    empresa_id: UUID
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _extract_usuario_nome(cls, data):
        # Quando a entrada e um objeto ORM com relationship "usuario" carregada,
        # promove o nome para usuario_nome. Itera sobre model_fields para nao
        # quebrar se novos campos forem adicionados ao schema.
        if isinstance(data, dict):
            return data
        usuario = getattr(data, "usuario", None)
        if usuario is None:
            return data
        fields = {name: getattr(data, name, None) for name in cls.model_fields}
        fields["usuario_nome"] = getattr(usuario, "nome", None)
        return fields


class AssessmentPaginatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int
    items: list[AssessmentResponse]
    has_more: bool
