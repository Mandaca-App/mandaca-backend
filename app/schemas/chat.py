from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints


class ChatMessageCreate(BaseModel):
    empresa_id: UUID
    mensagem: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]


class ChatMessageResponse(BaseModel):
    reply: str


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_mensagem: UUID
    empresa_id: UUID
    conteudo_usuario: str
    conteudo_assistente: str
    criado_em: datetime


class ChatHistoryResponse(BaseModel):
    historico: list[ChatHistoryItem]
