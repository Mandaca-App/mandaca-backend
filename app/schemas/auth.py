import re
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.models.user import TipoUsuario

EmailText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]


class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailText
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    tipo_usuario: TipoUsuario = TipoUsuario.TURISTA
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    cpf: Annotated[str, StringConstraints(strip_whitespace=True, min_length=11, max_length=11)]

    @field_validator("password")
    @classmethod
    def validate_strong_password(cls, value: str) -> str:
        rules = (
            re.search(r"[a-z]", value),
            re.search(r"[A-Z]", value),
            re.search(r"\d", value),
            re.search(r"[^A-Za-z0-9]", value),
        )
        if not all(rules):
            raise ValueError(
                "A senha deve conter letra maiuscula, letra minuscula, numero e simbolo."
            )
        return value


class UserRegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: UUID
    auth_user_id: UUID
    email: str
    tipo_usuario: TipoUsuario
    nome: str
    cpf: str
