import json
from uuid import UUID

from google import genai
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AIReportGenerationError,
    AIReportNotFoundError,
)
from app.models.business_context import BusinessContext
from app.models.report import AIReport
from app.services.business_context_service import BusinessContextService
from app.services.context_validation_service import (
    ContextValidationResult,
    ContextValidationService,
)

_SYSTEM_PROMPT = (
    "Você é um analista de negócios especializado em gastronomia e turismo no Nordeste do Brasil. "
    "Analise o contexto do negócio fornecido e gere um relatório estruturado em JSON com três "
    "seções: pontos_positivos, melhorias e recomendacoes. "
    "Cada seção deve ter duas versões: resumo (até 100 palavras) e detalhado (até 400 palavras). "
    "Escreva em português brasileiro. Seja objetivo, construtivo e específico para o negócio.\n\n"
    "DIRETRIZES PARA SUGESTÕES ACIONÁVEIS:\n"
    "Sempre que possível, traga sugestões CONCRETAS com valores específicos a partir do contexto:\n"
    "- Ao sugerir alteração de preço de um item, indique uma faixa de valor recomendada "
    "(ex: 'reduzir o preço de R$ 89,99 para algo entre R$ 6,00 e R$ 9,00').\n"
    "- Ao sugerir mudança de horário, proponha um intervalo concreto "
    "(ex: 'abrir às 06:30 para atender o público do café da manhã').\n"
    "- Ao sugerir nova história ou descrição de item, proponha um texto curto inspirador "
    "que o estabelecimento poderia adotar.\n"
    "Para dados que não podem ser inventados (telefone real, endereço físico real), "
    "indique apenas que precisam ser corrigidos pelo usuário, sem propor valor.\n\n"
    "Retorne somente JSON compatível com o schema fornecido."
)


class _AIReportLLMOutput(BaseModel):
    pontos_positivos_resumo: str
    pontos_positivos_detalhado: str
    melhorias_resumo: str
    melhorias_detalhado: str
    recomendacoes_resumo: str
    recomendacoes_detalhado: str


class ReportService:
    def __init__(
        self,
        gemini_client: genai.Client | None = None,
        context_service: BusinessContextService | None = None,
        context_validation_service: ContextValidationService | None = None,
    ) -> None:
        self._gemini_client = gemini_client or genai.Client(api_key=settings.gemini_api_key)
        self._context_service = context_service or BusinessContextService()
        self._context_validation_service = context_validation_service or ContextValidationService(
            context_service=self._context_service
        )

    def generate_report(self, empresa_id: UUID, db: Session) -> AIReport:
        validation = self._context_validation_service.validate_for_report(empresa_id, db)
        if not validation.context_changed and validation.reusable_report is not None:
            return validation.reusable_report

        contexto, dados_contexto = self._resolve_context(validation, empresa_id, db)
        parsed = self._invoke_llm(dados_contexto)

        report = AIReport(
            empresa_id=empresa_id,
            contexto_id=contexto.id_contexto,
            pontos_positivos_resumo=parsed.pontos_positivos_resumo,
            pontos_positivos_detalhado=parsed.pontos_positivos_detalhado,
            melhorias_resumo=parsed.melhorias_resumo,
            melhorias_detalhado=parsed.melhorias_detalhado,
            recomendacoes_resumo=parsed.recomendacoes_resumo,
            recomendacoes_detalhado=parsed.recomendacoes_detalhado,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def _resolve_context(
        self, validation: ContextValidationResult, empresa_id: UUID, db: Session
    ) -> tuple[BusinessContext, dict]:
        if not validation.context_changed:
            if validation.saved_context is None:
                raise AIReportGenerationError("contexto salvo ausente para contexto inalterado")
            return validation.saved_context, validation.saved_context.dados_contexto

        contexto = self._context_service.create_from_snapshot(
            empresa_id,
            validation.current_context_data,
            validation.current_context_hash,
            db,
        )
        return contexto, validation.current_context_data

    def _invoke_llm(self, dados_contexto: dict) -> _AIReportLLMOutput:
        context_str = json.dumps(dados_contexto, ensure_ascii=False)

        try:
            response = self._gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Contexto do negócio:\n{context_str}",
                config={
                    "system_instruction": _SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_json_schema": _AIReportLLMOutput.model_json_schema(),
                    "temperature": 0.2,
                },
            )
            return _AIReportLLMOutput.model_validate_json(response.text)
        except Exception as exc:
            raise AIReportGenerationError(str(exc)) from exc

    def get_by_id(self, report_id: UUID, db: Session) -> AIReport:
        report = db.get(AIReport, report_id)
        if not report:
            raise AIReportNotFoundError(report_id)
        return report

    def list_by_enterprise(self, empresa_id: UUID, db: Session) -> list[AIReport]:
        return list(
            db.execute(
                select(AIReport)
                .where(AIReport.empresa_id == empresa_id)
                .order_by(AIReport.criado_em.desc())
            )
            .scalars()
            .all()
        )
