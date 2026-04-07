from datetime import time
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints


class EnterpriseCreate(BaseModel):
    nome: Annotated[str, StringConstraints(max_length=255)]
    especialidade: Annotated[Optional[str], StringConstraints(max_length=100)] = None
    endereco: Annotated[Optional[str], StringConstraints(max_length=255)] = None
    historia: Annotated[Optional[str], StringConstraints(max_length=500)] = None
    hora_abrir: Optional[time] = None
    hora_fechar: Optional[time] = None
    telefone: Annotated[Optional[str], StringConstraints(max_length=20)] = None
    usuario_id: UUID


class EnterpriseUpdate(BaseModel):
    nome: Annotated[Optional[str], StringConstraints(max_length=255)] = None
    especialidade: Annotated[Optional[str], StringConstraints(max_length=100)] = None
    endereco: Annotated[Optional[str], StringConstraints(max_length=255)] = None
    historia: Annotated[Optional[str], StringConstraints(max_length=500)] = None
    hora_abrir: Optional[time] = None
    hora_fechar: Optional[time] = None
    telefone: Annotated[Optional[str], StringConstraints(max_length=20)] = None
    usuario_id: Optional[UUID] = None


class EnterpriseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_empresa: UUID
    nome: str
    especialidade: Optional[str] = None
    endereco: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    historia: Optional[str] = None
    hora_abrir: Optional[time] = None
    hora_fechar: Optional[time] = None
    telefone: Optional[str] = None
    usuario_id: UUID


class EnterprisePercentageResponse(BaseModel):
    id_empresa: UUID
    nome: str
    porcentagem: float
    campos_preenchidos: list[str]
    campos_faltando: list[str]


class PhotoOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url_foto_empresa: Optional[str] = None


class EnterpriseOverviewResponse(BaseModel):
    id_empresa: UUID
    endereco: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    historia: Optional[str] = None
    fotos: list[PhotoOverviewResponse]
