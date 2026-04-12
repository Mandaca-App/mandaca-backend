from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.menu import CategoriaCardapio


class MenuCreate(BaseModel):
    descricao: Annotated[Optional[str], StringConstraints(max_length=255)] = None
    historia: Annotated[Optional[str], StringConstraints(max_length=500)] = None
    preco: Decimal
    categoria: CategoriaCardapio
    status: bool
    empresa_id: UUID


class MenuUpdate(BaseModel):
    descricao: Annotated[Optional[str], StringConstraints(max_length=255)] = None
    historia: Annotated[Optional[str], StringConstraints(max_length=500)] = None
    preco: Optional[Decimal] = None
    categoria: Optional[CategoriaCardapio] = None
    status: Optional[bool] = None
    empresa_id: Optional[UUID] = None


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_cardapio: UUID
    descricao: Optional[str] = None
    historia: Optional[str] = None
    preco: Decimal = Field(..., json_schema_extra={"example": Decimal("8.50")})
    categoria: CategoriaCardapio
    status: bool
    empresa_id: UUID
