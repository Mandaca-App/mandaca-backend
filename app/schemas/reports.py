from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.auto_apply import AutoApplySuggestion


class ReportItem(BaseModel):
    titulo: str
    resumo: str
    descricao: str
    pode_auto_aplicar: bool
    sugestao: AutoApplySuggestion | None = None

    @model_validator(mode="after")
    def _sugestao_required_when_auto_apply(self) -> "ReportItem":
        if self.pode_auto_aplicar and self.sugestao is None:
            raise ValueError("sugestao e obrigatoria quando pode_auto_aplicar=True")
        return self


class AIReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_relatorio: UUID
    empresa_id: UUID
    contexto_id: UUID
    pontos_positivos: list[ReportItem]
    melhorias: list[ReportItem]
    recomendacoes: list[ReportItem]
    criado_em: datetime
