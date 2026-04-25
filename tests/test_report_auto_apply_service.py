"""
Testes unitários para ReportAutoApplyService.

Foco: extração estruturada de sugestões via LLM e aplicação em lote
delegando ao AutoApplyService. Gemini e AutoApplyService são mockados.
"""

import json
import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    AIReportNotFoundError,
    EnterpriseNotFoundError,
    FieldNotAllowedError,
    SuggestionExtractionError,
)
from app.models.enterprise import Enterprise
from app.models.menu import CategoriaCardapio, Menu
from app.models.report import AIReport
from app.schemas.auto_apply import AutoApplyTarget, SuggestionStatus
from app.services.report_auto_apply_service import ReportAutoApplyService

FAKE_REPORT_ID = uuid.uuid4()
FAKE_ENTERPRISE_ID = uuid.uuid4()
FAKE_MENU_ID = uuid.uuid4()


def _make_report() -> AIReport:
    return AIReport(
        id_relatorio=FAKE_REPORT_ID,
        empresa_id=FAKE_ENTERPRISE_ID,
        contexto_id=uuid.uuid4(),
        pontos_positivos_resumo="ok",
        pontos_positivos_detalhado="ok",
        melhorias_resumo="aumentar telefone",
        melhorias_detalhado="incluir telefone novo",
        recomendacoes_resumo="ok",
        recomendacoes_detalhado="ok",
    )


def _make_menu() -> Menu:
    return Menu(
        id_cardapio=FAKE_MENU_ID,
        descricao="Frango grelhado",
        historia=None,
        preco=Decimal("20.00"),
        categoria=CategoriaCardapio.PRATO_PRINCIPAL,
        status=True,
        empresa_id=FAKE_ENTERPRISE_ID,
    )


def _make_enterprise() -> Enterprise:
    return Enterprise(
        id_empresa=FAKE_ENTERPRISE_ID,
        nome="Empresa Teste",
        usuario_id=uuid.uuid4(),
    )


def _mock_db(report=None, enterprise=None, menus=None) -> MagicMock:
    db = MagicMock()

    def _get(model, key):
        if model is AIReport:
            return report
        if model is Enterprise:
            return enterprise
        return None

    db.get.side_effect = _get
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = menus or []
    db.execute.return_value = execute_result
    return db


def _mock_gemini(sugestoes: list[dict]) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.text = json.dumps({"sugestoes": sugestoes})
    client.models.generate_content.return_value = response
    return client


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_given_report_with_valid_suggestions_when_applied_then_all_succeed() -> None:
    # GIVEN
    db = _mock_db(report=_make_report(), enterprise=_make_enterprise(), menus=[_make_menu()])
    gemini = _mock_gemini(
        [
            {
                "target": "enterprise",
                "menu_item_id": None,
                "campo_para_alterar": "telefone",
                "novo_valor": "81999990000",
            },
            {
                "target": "menu_item",
                "menu_item_id": str(FAKE_MENU_ID),
                "campo_para_alterar": "preco",
                "novo_valor": "25.00",
            },
        ]
    )
    auto_apply = MagicMock()
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 2
    assert response.aplicadas == 2
    assert response.rejeitadas == 0
    assert auto_apply.apply.call_count == 2
    assert all(r.status == SuggestionStatus.APPLIED for r in response.resultados)
    db.commit.assert_called_once()
    for call in auto_apply.apply.call_args_list:
        assert call.kwargs.get("commit") is False


def test_given_llm_returns_empty_list_when_applied_then_returns_zero_counters() -> None:
    # GIVEN
    db = _mock_db(report=_make_report(), enterprise=_make_enterprise(), menus=[])
    gemini = _mock_gemini([])
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=MagicMock())

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 0
    assert response.aplicadas == 0
    assert response.rejeitadas == 0
    assert response.resultados == []
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Falhas individuais não derrubam o lote
# ---------------------------------------------------------------------------


def test_given_invalid_field_when_applied_then_marks_rejected() -> None:
    # GIVEN
    db = _mock_db(report=_make_report(), enterprise=_make_enterprise(), menus=[])
    gemini = _mock_gemini(
        [
            {
                "target": "enterprise",
                "menu_item_id": None,
                "campo_para_alterar": "owner_id",
                "novo_valor": "x",
            },
        ]
    )
    auto_apply = MagicMock()
    auto_apply.apply.side_effect = FieldNotAllowedError("owner_id")
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 1
    assert response.aplicadas == 0
    assert response.rejeitadas == 1
    assert response.resultados[0].status == SuggestionStatus.REJECTED
    assert "owner_id" in response.resultados[0].erro


def test_given_unknown_menu_id_when_applied_then_marks_rejected() -> None:
    # GIVEN
    db = _mock_db(report=_make_report(), enterprise=_make_enterprise(), menus=[_make_menu()])
    gemini = _mock_gemini(
        [
            {
                "target": "menu_item",
                "menu_item_id": str(uuid.uuid4()),
                "campo_para_alterar": "preco",
                "novo_valor": "10.00",
            },
        ]
    )
    auto_apply = MagicMock()
    auto_apply.apply.side_effect = EnterpriseNotFoundError(FAKE_ENTERPRISE_ID)
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.rejeitadas == 1
    assert response.resultados[0].status == SuggestionStatus.REJECTED


def test_given_mixed_suggestions_when_applied_then_partial_results_returned() -> None:
    # GIVEN
    db = _mock_db(report=_make_report(), enterprise=_make_enterprise(), menus=[_make_menu()])
    gemini = _mock_gemini(
        [
            {
                "target": "enterprise",
                "menu_item_id": None,
                "campo_para_alterar": "historia",
                "novo_valor": "Nova",
            },
            {
                "target": "enterprise",
                "menu_item_id": None,
                "campo_para_alterar": "owner_id",
                "novo_valor": "x",
            },
        ]
    )
    auto_apply = MagicMock()
    auto_apply.apply.side_effect = [None, FieldNotAllowedError("owner_id")]
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 2
    assert response.aplicadas == 1
    assert response.rejeitadas == 1


# ---------------------------------------------------------------------------
# Erros bloqueantes
# ---------------------------------------------------------------------------


def test_given_missing_report_when_applied_then_raises_404() -> None:
    # GIVEN
    db = _mock_db(report=None)
    service = ReportAutoApplyService(
        gemini_client=MagicMock(),
        auto_apply_service=MagicMock(),
    )

    # WHEN / THEN
    with pytest.raises(AIReportNotFoundError):
        service.apply_from_report(FAKE_REPORT_ID, db)


def test_given_llm_failure_when_applied_then_raises_extraction_error() -> None:
    # GIVEN
    db = _mock_db(report=_make_report(), enterprise=_make_enterprise(), menus=[])
    gemini = MagicMock()
    gemini.models.generate_content.side_effect = RuntimeError("api down")
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=MagicMock())

    # WHEN / THEN
    with pytest.raises(SuggestionExtractionError):
        service.apply_from_report(FAKE_REPORT_ID, db)


def test_given_llm_returns_invalid_json_when_applied_then_raises_extraction_error() -> None:
    # GIVEN
    db = _mock_db(report=_make_report(), enterprise=_make_enterprise(), menus=[])
    gemini = MagicMock()
    response = MagicMock()
    response.text = "not a json"
    gemini.models.generate_content.return_value = response
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=MagicMock())

    # WHEN / THEN
    with pytest.raises(SuggestionExtractionError):
        service.apply_from_report(FAKE_REPORT_ID, db)


# ---------------------------------------------------------------------------
# Construção do payload AutoApplyRequest
# ---------------------------------------------------------------------------


def test_given_suggestion_when_applied_then_request_uses_report_empresa_id() -> None:
    # GIVEN
    report = _make_report()
    db = _mock_db(report=report, enterprise=_make_enterprise(), menus=[])
    gemini = _mock_gemini(
        [
            {
                "target": "enterprise",
                "menu_item_id": None,
                "campo_para_alterar": "telefone",
                "novo_valor": "81000",
            },
        ]
    )
    auto_apply = MagicMock()
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=auto_apply)

    # WHEN
    service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    request_arg = auto_apply.apply.call_args[0][0]
    assert request_arg.enterprise_id == FAKE_ENTERPRISE_ID
    assert request_arg.target == AutoApplyTarget.ENTERPRISE
    assert request_arg.campo_para_alterar == "telefone"


# ---------------------------------------------------------------------------
# Novos casos de segurança
# ---------------------------------------------------------------------------


def test_given_missing_enterprise_when_applied_then_raises_404() -> None:
    # GIVEN — report existe mas empresa foi deletada
    db = _mock_db(report=_make_report(), enterprise=None, menus=[])
    service = ReportAutoApplyService(
        gemini_client=MagicMock(),
        auto_apply_service=MagicMock(),
    )

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        service.apply_from_report(FAKE_REPORT_ID, db)


def test_given_llm_returns_menu_without_id_when_applied_then_marks_rejected() -> None:
    # GIVEN — LLM retorna menu_item sem menu_item_id (violação de schema)
    db = _mock_db(report=_make_report(), enterprise=_make_enterprise(), menus=[])
    gemini = _mock_gemini(
        [
            {
                "target": "menu_item",
                "menu_item_id": None,
                "campo_para_alterar": "preco",
                "novo_valor": "15.00",
            },
        ]
    )
    service = ReportAutoApplyService(gemini_client=gemini, auto_apply_service=MagicMock())

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN — ValueError do model_validator capturado como rejeição, não crash
    assert response.total == 1
    assert response.rejeitadas == 1
    assert response.resultados[0].status == SuggestionStatus.REJECTED
    assert response.resultados[0].erro is not None
