from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

from app.models.tutorial import CategoriaTutorial


class TutorialIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: CategoriaTutorial
    titulo: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    descricao: Annotated[str | None, StringConstraints(max_length=500)] = None
    url: HttpUrl
    ordem: int = 0
    ativo: bool = True


class TutorialUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: CategoriaTutorial | None = None
    titulo: Annotated[str | None, StringConstraints(min_length=1, max_length=120)] = None
    descricao: Annotated[str | None, StringConstraints(max_length=500)] = None
    url: HttpUrl | None = None
    ordem: int | None = None
    ativo: bool | None = None


class TutorialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    categoria: CategoriaTutorial
    titulo: str
    descricao: str | None = None
    url: str
    ordem: int = Field(default=0)
    ativo: bool
    created_at: datetime
    updated_at: datetime
