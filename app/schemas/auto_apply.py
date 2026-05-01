from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class AutoApplyTarget(str, Enum):
    ENTERPRISE = "enterprise"
    MENU_ITEM = "menu_item"


class AutoApplySuggestion(BaseModel):
    mensagem: str
    target: AutoApplyTarget
    menu_item_id: UUID | None = None
    campo_para_alterar: str
    novo_valor: str
