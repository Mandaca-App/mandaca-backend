from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AutoApplyTarget(str, Enum):
    ENTERPRISE = "enterprise"
    MENU_ITEM = "menu_item"


class AutoApplyRequest(BaseModel):
    enterprise_id: UUID
    target: AutoApplyTarget
    menu_item_id: UUID | None = None
    campo_para_alterar: str = Field(min_length=1, max_length=50)
    novo_valor: str = Field(min_length=1, max_length=500)

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
    mensagem: str  # texto exibível gerado pelo LLM junto com a sugestão
    target: AutoApplyTarget
    menu_item_id: UUID | None = None
    campo_para_alterar: str = Field(min_length=1, max_length=50)
    novo_valor: str = Field(min_length=1, max_length=500)


class AutoApplySuggestionResult(BaseModel):
    sugestao: AutoApplySuggestion
    status: SuggestionStatus
    erro: str | None = None


class ReportAutoApplyResponse(BaseModel):
    report_id: UUID
    total: int
    aplicadas: int
    rejeitadas: int
    ignorados: int = 0  # itens com pode_auto_aplicar=True mas JSON malformado no banco
    resultados: list[AutoApplySuggestionResult]
