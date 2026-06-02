from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.chatbot_ajuda import ChatbotKind, KnowledgeModuleType

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
TopicText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ChatbotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: ChatbotKind
    nome: ShortText
    descricao: Annotated[str | None, StringConstraints(max_length=500)] = None
    ativo: bool = True


class ChatbotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: ShortText | None = None
    descricao: Annotated[str | None, StringConstraints(max_length=500)] = None
    ativo: bool | None = None


class KnowledgeModuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topico: TopicText
    tipo: KnowledgeModuleType = KnowledgeModuleType.GERAL
    conteudo: Annotated[str | None, StringConstraints(max_length=4000)] = None
    referencia: Annotated[str | None, StringConstraints(max_length=500)] = None
    ordem: int = 0
    ativo: bool = True


class KnowledgeModuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topico: TopicText | None = None
    tipo: KnowledgeModuleType | None = None
    conteudo: Annotated[str | None, StringConstraints(max_length=4000)] = None
    referencia: Annotated[str | None, StringConstraints(max_length=500)] = None
    ordem: int | None = None
    ativo: bool | None = None


class ChatbotMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empresa_id: UUID | None = None
    usuario_id: UUID | None = None
    mensagem: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]
    topicos: list[TopicText] = Field(default_factory=list, max_length=10)


class KnowledgeModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_modulo: UUID
    chatbot_id: UUID
    topico: str
    tipo: KnowledgeModuleType
    conteudo: str | None = None
    referencia: str | None = None
    ordem: int
    ativo: bool
    created_at: datetime
    updated_at: datetime


class ChatbotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_chatbot: UUID
    tipo: ChatbotKind
    nome: str
    descricao: str | None = None
    ativo: bool
    created_at: datetime
    updated_at: datetime
