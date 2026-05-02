import json
from typing import Any
from uuid import UUID

from google import genai
from pydantic import BaseModel, field_validator, model_validator
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

# ---------------------------------------------------------------------------
# Structured output models (private - Gemini response only)
# ---------------------------------------------------------------------------


class _ParsedSuggestion(BaseModel):
    mensagem: str
    target: str
    menu_item_id: str | None = None
    campo_para_alterar: str
    novo_valor: str

    @field_validator("target", mode="before")
    @classmethod
    def _coerce_invalid_target(cls, v: str) -> str:
        if v not in ("enterprise", "menu_item"):
            return "enterprise"
        return v

    @field_validator("menu_item_id", mode="before")
    @classmethod
    def _coerce_invalid_uuid(cls, v: str | None) -> str | None:
        if v is None:
            return None
        try:
            UUID(str(v))
            return str(v)
        except (ValueError, AttributeError):
            return None


class _ParsedReportItem(BaseModel):
    titulo: str
    resumo: str
    descricao: str
    pode_auto_aplicar: bool
    sugestao: _ParsedSuggestion | None = None

    @model_validator(mode="after")
    def _validate_sugestao(self) -> "_ParsedReportItem":
        if self.pode_auto_aplicar and self.sugestao is None:
            raise ValueError("sugestao obrigatoria quando pode_auto_aplicar=True")
        return self


class _ParsedReport(BaseModel):
    pontos_positivos: list[_ParsedReportItem]
    melhorias: list[_ParsedReportItem]
    recomendacoes: list[_ParsedReportItem]


_PARSED_REPORT_SCHEMA: dict[str, Any] = _ParsedReport.model_json_schema()


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
Voce e um consultor especializado em avaliar negocios gastronomicos do
interior de Pernambuco. Analise o contexto do negocio fornecido (perfil,
avaliacoes de clientes e cardapio) e gere um relatorio estruturado em tres
categorias: pontos_positivos, melhorias e recomendacoes.

Para cada item, defina pode_auto_aplicar e sugestao conforme as regras abaixo.

## Campos editaveis no aplicativo

Empresa (target=enterprise): historia, telefone, endereco, hora_abrir (HH:MM), hora_fechar (HH:MM)
Cardapio por item (target=menu_item): descricao, preco (valor decimal positivo)

O contexto lista os itens de cardapio com seus respectivos "id" (UUID).
Quando a sugestao envolver um item de cardapio especifico, use exatamente o "id"
desse item no campo menu_item_id. Nunca invente ou modifique um UUID.

## Regras de pode_auto_aplicar

- pode_auto_aplicar=true: o aspecto corresponde a um campo editavel listado acima
  e e possivel sugerir um valor concreto para substituicao.
  Preencha sugestao com: mensagem, target, campo_para_alterar e novo_valor.
  Para target=menu_item: preencha menu_item_id com o UUID exato do item do contexto.
  Para target=enterprise: deixe menu_item_id como null.

- pode_auto_aplicar=false: o aspecto nao pode ser resolvido editando um campo do app
  (ex: higiene, atendimento, ambiente, logistica). Sugestao DEVE ser null.

## Exemplos

Aspecto "historia da empresa nao contada": pode_auto_aplicar=true,
  target=enterprise, campo_para_alterar=historia, novo_valor=<texto sugerido>,
  menu_item_id=null

Aspecto "descricao do prato X esta vazia": pode_auto_aplicar=true,
  target=menu_item, campo_para_alterar=descricao, novo_valor=<descricao sugerida>,
  menu_item_id=<id exato do item no contexto>

Aspecto "higiene dos talheres precisa melhorar": pode_auto_aplicar=false, sugestao=null

Aspecto "atendimento simpatico": pode_auto_aplicar=false, sugestao=null

Retorne JSON valido que siga exatamente o schema fornecido.
""".strip()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


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

        # LLM chamado antes de persistir o contexto: falha na API nao deixa contexto orfao
        parsed = self._invoke_llm(validation.current_context_data)
        contexto = self._resolve_context(validation, empresa_id, db)

        existing = (
            db.execute(select(AIReport).where(AIReport.empresa_id == empresa_id)).scalars().first()
        )
        if existing is not None:
            db.delete(existing)
            db.flush()

        report = AIReport(
            empresa_id=empresa_id,
            contexto_id=contexto.id_contexto,
            pontos_positivos=[i.model_dump() for i in parsed.pontos_positivos],
            melhorias=[i.model_dump() for i in parsed.melhorias],
            recomendacoes=[i.model_dump() for i in parsed.recomendacoes],
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def _resolve_context(
        self, validation: ContextValidationResult, empresa_id: UUID, db: Session
    ) -> BusinessContext:
        if not validation.context_changed:
            if validation.saved_context is None:
                raise AIReportGenerationError("contexto salvo ausente para contexto inalterado")
            return validation.saved_context

        return self._context_service.create_from_snapshot(
            empresa_id,
            validation.current_context_data,
            validation.current_context_hash,
            db,
        )

    def _invoke_llm(self, context_data: dict[str, Any]) -> _ParsedReport:
        try:
            response = self._gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=json.dumps(context_data, ensure_ascii=False),
                config={
                    "system_instruction": _SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_json_schema": _PARSED_REPORT_SCHEMA,
                    "temperature": 0,
                    "http_options": {"timeout": 30000},
                },
            )
            return _ParsedReport.model_validate_json(response.text)
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
