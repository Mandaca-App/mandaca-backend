from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints


class ContactCreate(BaseModel):
    telefone: Annotated[Optional[str], StringConstraints(max_length=20)] = None
    email: Annotated[Optional[str], StringConstraints(max_length=255)] = None
    whatsapp: Annotated[Optional[str], StringConstraints(max_length=20)] = None


class ContactUpdate(BaseModel):
    telefone: Annotated[Optional[str], StringConstraints(max_length=20)] = None
    email: Annotated[Optional[str], StringConstraints(max_length=255)] = None
    whatsapp: Annotated[Optional[str], StringConstraints(max_length=20)] = None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_contato: UUID
    telefone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
