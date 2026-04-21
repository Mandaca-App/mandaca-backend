from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BusinessContextCreate(BaseModel):
    dados_contexto: dict[str, Any]  # objeto JSON direto, sem escapar
    empresa_id: UUID


class BusinessContextUpdate(BaseModel):
    dados_contexto: Optional[dict[str, Any]] = None  # objeto JSON direto


class BusinessContextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_contexto: UUID
    empresa_id: UUID
    hash_contexto: str
    dados_contexto: Any
    criado_em: datetime
