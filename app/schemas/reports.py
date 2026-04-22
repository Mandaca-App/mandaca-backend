from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AIReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_relatorio: UUID
    empresa_id: UUID
    contexto_id: UUID
    pontos_positivos_resumo: str
    melhorias_resumo: str
    recomendacoes_resumo: str
    criado_em: datetime


class AIReportDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_relatorio: UUID
    empresa_id: UUID
    contexto_id: UUID
    pontos_positivos_resumo: str
    pontos_positivos_detalhado: str
    melhorias_resumo: str
    melhorias_detalhado: str
    recomendacoes_resumo: str
    recomendacoes_detalhado: str
    criado_em: datetime
