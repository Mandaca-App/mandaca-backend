import json
from uuid import UUID

from google import genai
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AIReportGenerationError, AIReportNotFoundError
from app.models.report import AIReport
from app.schemas.reports import _AIReportLLMOutput
from app.services.business_context_service import BusinessContextService

_SYSTEM_PROMPT = (
    "Você é um analista de negócios especializado em gastronomia e turismo no Nordeste do Brasil. "
    "Analise o contexto do negócio fornecido e gere um relatório estruturado em JSON com três "
    "seções: pontos_positivos, melhorias e recomendacoes. "
    "Cada seção deve ter duas versões: resumo (até 100 palavras) e detalhado (até 400 palavras). "
    "Escreva em português brasileiro. Seja objetivo, construtivo e específico para o negócio. "
    "Retorne somente JSON compatível com o schema fornecido."
)


class ReportService:
    def __init__(
        self,
        gemini_client: genai.Client | None = None,
        context_service: BusinessContextService | None = None,
    ) -> None:
        self._gemini_client = gemini_client
        self._context_service = context_service or BusinessContextService()

    def _get_gemini_client(self) -> genai.Client:
        if self._gemini_client is not None:
            return self._gemini_client
        return genai.Client(api_key=settings.gemini_api_key)

    def generate_report(self, empresa_id: UUID, db: Session) -> AIReport:
        contextos = self._context_service.list_by_enterprise(empresa_id, db)
        if not contextos:
            raise AIReportNotFoundError(
                f"Nenhum contexto de negócio encontrado para a empresa: {empresa_id}"
            )

        contexto = contextos[0]
        context_str = json.dumps(contexto.dados_contexto, ensure_ascii=False)

        client = self._get_gemini_client()
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Contexto do negócio:\n{context_str}",
                config={
                    "system_instruction": _SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_json_schema": _AIReportLLMOutput.model_json_schema(),
                    "temperature": 0.2,
                },
            )
            parsed = _AIReportLLMOutput.model_validate_json(response.text)
        except Exception as exc:
            raise AIReportGenerationError(str(exc)) from exc

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
