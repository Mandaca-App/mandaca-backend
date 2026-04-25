from enum import Enum
from uuid import UUID

from pydantic import BaseModel, model_validator


class AutoApplyTarget(str, Enum):
    ENTERPRISE = "enterprise"
    MENU_ITEM = "menu_item"


class AutoApplyRequest(BaseModel):
    enterprise_id: UUID
    target: AutoApplyTarget
    menu_item_id: UUID | None = None
    campo_para_alterar: str
    novo_valor: str

    @model_validator(mode="after")
    def _menu_item_id_required_when_menu(self) -> "AutoApplyRequest":
        if self.target == AutoApplyTarget.MENU_ITEM and self.menu_item_id is None:
            raise ValueError("menu_item_id é obrigatório quando target=menu_item")
        return self


class SuggestionStatus(str, Enum):
    APPLIED = "aplicado"
    REJECTED = "rejeitado"


class AutoApplyResponse(BaseModel):
    campo_alterado: str
    status: SuggestionStatus = SuggestionStatus.APPLIED


class AutoApplySuggestion(BaseModel):
    target: AutoApplyTarget
    menu_item_id: UUID | None = None
    campo_para_alterar: str
    novo_valor: str


class AutoApplySuggestionResult(BaseModel):
    sugestao: AutoApplySuggestion
    status: SuggestionStatus
    erro: str | None = None


class ReportAutoApplyResponse(BaseModel):
    report_id: UUID
    total: int
    aplicadas: int
    rejeitadas: int
    resultados: list[AutoApplySuggestionResult]
