from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EnterpriseFromAudioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_empresa: UUID
    usuario_id: UUID
    nome: str
    especialidade: str | None = None
    endereco: str | None = None
    historia: str | None = None
    telefone: str | None = None
