import json
from uuid import UUID

from google import genai
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AIReportNotFoundError,
    EnterpriseNotFoundError,
    MandacaError,
    SuggestionExtractionError,
)
from app.models.enterprise import Enterprise
from app.models.menu import Menu
from app.models.report import AIReport
from app.schemas.auto_apply import (
    AutoApplyRequest,
    AutoApplySuggestion,
    AutoApplySuggestionResult,
    ReportAutoApplyResponse,
    SuggestionStatus,
)
from app.services.auto_apply_service import AutoApplyService

_SYSTEM_PROMPT = (
    "Você analisa um relatório de melhorias de um restaurante e extrai mudanças "
    "concretas e acionáveis para campos específicos da base de dados. "
    "Você recebe o relatório E o estado atual dos dados (telefone, endereço, "
    "horário, história, itens do cardápio com preço). Use o estado atual como "
    "ponto de partida para INTERPRETAR sugestões vagas em valores concretos.\n\n"
    "REGRAS DE INTERPRETAÇÃO (seja proativo quando o relatório indicar direção):\n"
    "- Se o relatório disser 'reduzir um pouco o preço', sugira uma redução de "
    "10% a 20% sobre o preço atual e devolva o valor calculado.\n"
    "- Se disser 'aumentar levemente', sugira aumento de 5% a 15%.\n"
    "- Se disser 'preço irrealista' ou 'muito alto/baixo' SEM faixa explícita, "
    "use bom senso de mercado para itens similares no Nordeste.\n"
    "- Se disser 'abrir mais cedo', sugira 30 a 60 minutos antes do hora_abrir "
    "atual. 'Fechar mais tarde' equivalente.\n"
    "- Se disser 'reescrever história' ou 'descrição mais convidativa', "
    "proponha um texto curto (até 250 chars) baseado na especialidade da empresa.\n"
    "- Se disser 'mudar nome do item', proponha um nome mais atrativo a partir "
    "da descrição existente.\n\n"
    "REGRAS RÍGIDAS DE NÃO-INVENÇÃO (se violar, descarte a sugestão):\n"
    "- Telefone: SÓ inclua se o relatório trouxer um número específico literal. "
    "Caso contrário NÃO sugira esse campo.\n"
    "- Endereço: idem — só com endereço real explícito no texto.\n\n"
    "Whitelist de campos permitidos:\n"
    "- target=enterprise: 'historia', 'telefone', 'endereco', "
    "'horario_funcionamento' (formato HH:MM-HH:MM)\n"
    "- target=menu_item: 'nome' (nome exibido do item), "
    "'descricao' (texto descritivo longo do item), "
    "'preco' (string com decimal, ex: '32.50')\n\n"
    "Para sugestões em itens de cardápio, use APENAS os IDs (menu_item_id) "
    "fornecidos no contexto. Nunca invente IDs.\n"
    "Retorne APENAS JSON conforme o schema fornecido."
)


class _SuggestionsLLMOutput(BaseModel):
    sugestoes: list[AutoApplySuggestion]


class ReportAutoApplyService:
    def __init__(
        self,
        gemini_client: genai.Client | None = None,
        auto_apply_service: AutoApplyService | None = None,
    ) -> None:
        self._gemini_client = gemini_client or genai.Client(api_key=settings.gemini_api_key)
        self._auto_apply_service = auto_apply_service or AutoApplyService()

    def apply_from_report(self, report_id: UUID, db: Session) -> ReportAutoApplyResponse:
        report = self._load_report(report_id, db)
        enterprise = self._load_enterprise(report.empresa_id, db)
        menu_items = self._load_menu_items(report.empresa_id, db)
        sugestoes = self._extract_suggestions(report, enterprise, menu_items)

        resultados = [self._apply_one(report.empresa_id, s, db) for s in sugestoes]
        aplicadas = sum(1 for r in resultados if r.status == SuggestionStatus.APPLIED)

        if aplicadas > 0:
            db.commit()

        return ReportAutoApplyResponse(
            report_id=report_id,
            total=len(resultados),
            aplicadas=aplicadas,
            rejeitadas=len(resultados) - aplicadas,
            resultados=resultados,
        )

    def _load_report(self, report_id: UUID, db: Session) -> AIReport:
        report = db.get(AIReport, report_id)
        if not report:
            raise AIReportNotFoundError(report_id)
        return report

    def _load_enterprise(self, empresa_id: UUID, db: Session) -> Enterprise:
        enterprise = db.get(Enterprise, empresa_id)
        if not enterprise:
            raise EnterpriseNotFoundError(empresa_id)
        return enterprise

    def _load_menu_items(self, empresa_id: UUID, db: Session) -> list[Menu]:
        return list(
            db.execute(
                select(Menu).where(
                    Menu.empresa_id == empresa_id,
                    Menu.status.is_(True),
                )
            )
            .scalars()
            .all()
        )

    def _extract_suggestions(
        self,
        report: AIReport,
        enterprise: Enterprise,
        menu_items: list[Menu],
    ) -> list[AutoApplySuggestion]:
        contexto = {
            "relatorio": {
                "melhorias_resumo": report.melhorias_resumo,
                "melhorias_detalhado": report.melhorias_detalhado,
                "recomendacoes_resumo": report.recomendacoes_resumo,
                "recomendacoes_detalhado": report.recomendacoes_detalhado,
            },
            "estado_atual_empresa": {
                "nome": enterprise.nome,
                "especialidade": enterprise.especialidade,
                "historia": enterprise.historia,
                "telefone": enterprise.telefone,
                "endereco": enterprise.endereco,
                "hora_abrir": (
                    enterprise.hora_abrir.isoformat() if enterprise.hora_abrir else None
                ),
                "hora_fechar": (
                    enterprise.hora_fechar.isoformat() if enterprise.hora_fechar else None
                ),
            },
            "itens_cardapio": [
                {
                    "menu_item_id": str(m.id_cardapio),
                    "nome_atual": m.descricao,
                    "descricao_atual": m.historia,
                    "preco_atual": str(m.preco),
                    "categoria": m.categoria.value if m.categoria else None,
                }
                for m in menu_items
            ],
        }

        try:
            response = self._gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=json.dumps(contexto, ensure_ascii=False),
                config={
                    "system_instruction": _SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_json_schema": _SuggestionsLLMOutput.model_json_schema(),
                    "temperature": 0.2,
                },
            )
            parsed = _SuggestionsLLMOutput.model_validate_json(response.text)
            return parsed.sugestoes
        except Exception as exc:
            raise SuggestionExtractionError(str(exc)) from exc

    def _apply_one(
        self,
        empresa_id: UUID,
        sugestao: AutoApplySuggestion,
        db: Session,
    ) -> AutoApplySuggestionResult:
        try:
            request = AutoApplyRequest(
                enterprise_id=empresa_id,
                target=sugestao.target,
                menu_item_id=sugestao.menu_item_id,
                campo_para_alterar=sugestao.campo_para_alterar,
                novo_valor=sugestao.novo_valor,
            )
            self._auto_apply_service.apply(request, db, commit=False)
            return AutoApplySuggestionResult(
                sugestao=sugestao,
                status=SuggestionStatus.APPLIED,
            )
        except (MandacaError, ValueError) as exc:
            return AutoApplySuggestionResult(
                sugestao=sugestao,
                status=SuggestionStatus.REJECTED,
                erro=str(exc),
            )
