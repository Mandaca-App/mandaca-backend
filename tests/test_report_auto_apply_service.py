"""
Testes unitários para ReportAutoApplyService (SCRUM-215).

Foco: aplicação de sugestões pré-computadas sem chamada ao LLM.
Mocks: db.get(AIReport) e AutoApplyService.apply.
"""

import inspect
import uuid
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    AIReportNotFoundError,
    AutoApplyPersistenceError,
    FieldNotAllowedError,
    InvalidFieldValueError,
)
from app.models.report import AIReport
from app.schemas.auto_apply import AutoApplyTarget, SuggestionStatus
from app.services.auto_apply_service import AutoApplyService
from app.services.report_auto_apply_service import ReportAutoApplyService

FAKE_REPORT_ID = uuid.uuid4()
FAKE_ENTERPRISE_ID = uuid.uuid4()
FAKE_MENU_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sugestao_dict(**overrides: object) -> dict:
    base = {
        "mensagem": "Sugestão de teste",
        "target": "enterprise",
        "menu_item_id": None,
        "campo_para_alterar": "historia",
        "novo_valor": "Novo texto",
    }
    base.update(overrides)
    return base


def _make_item_dict(pode_auto_aplicar: bool = True, sugestao: dict | None = None) -> dict:
    return {
        "titulo": "Item teste",
        "resumo": "Resumo",
        "descricao": "Descrição",
        "pode_auto_aplicar": pode_auto_aplicar,
        "sugestao": (
            sugestao
            if sugestao is not None
            else (_make_sugestao_dict() if pode_auto_aplicar else None)
        ),
    }


def _make_mock_report(
    pontos_positivos: list | None = None,
    melhorias: list | None = None,
    recomendacoes: list | None = None,
) -> MagicMock:
    report = MagicMock(spec=AIReport)
    report.id_relatorio = FAKE_REPORT_ID
    report.empresa_id = FAKE_ENTERPRISE_ID
    report.pontos_positivos = pontos_positivos or []
    report.melhorias = melhorias or []
    report.recomendacoes = recomendacoes or []
    return report


def _mock_db(report: MagicMock | None = None) -> MagicMock:
    db = MagicMock()
    db.get.return_value = report
    return db


# ---------------------------------------------------------------------------
# Contrato da interface (SCRUM-215: Gemini removido)
# ---------------------------------------------------------------------------


def test_given_refactored_service_when_inspected_then_no_gemini_param() -> None:
    # GIVEN / WHEN
    sig = inspect.signature(ReportAutoApplyService.__init__)

    # THEN — gemini_client foi removido do construtor
    assert "gemini_client" not in sig.parameters


def test_given_refactored_module_when_imported_then_genai_not_imported() -> None:
    # GIVEN / WHEN
    import app.services.report_auto_apply_service as module

    # THEN — módulo não referencia genai
    assert not hasattr(module, "genai")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_given_auto_apply_items_when_applied_then_returns_applied_count() -> None:
    # GIVEN
    sugestao_enterprise = _make_sugestao_dict(campo_para_alterar="historia", novo_valor="Novo")
    sugestao_menu = _make_sugestao_dict(
        target="menu_item",
        menu_item_id=str(FAKE_MENU_ID),
        campo_para_alterar="preco",
        novo_valor="25.00",
    )
    report = _make_mock_report(
        melhorias=[_make_item_dict(sugestao=sugestao_enterprise)],
        recomendacoes=[_make_item_dict(sugestao=sugestao_menu)],
    )
    db = _mock_db(report=report)
    auto_apply = MagicMock(spec=AutoApplyService)
    service = ReportAutoApplyService(auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 2
    assert response.aplicadas == 2
    assert response.rejeitadas == 0
    assert auto_apply.apply.call_count == 2
    db.commit.assert_called_once()
    for call in auto_apply.apply.call_args_list:
        assert call.kwargs.get("commit") is False


def test_given_auto_apply_items_when_applied_then_request_uses_report_empresa_id() -> None:
    # GIVEN
    report = _make_mock_report(
        melhorias=[
            _make_item_dict(
                sugestao=_make_sugestao_dict(campo_para_alterar="telefone", novo_valor="81999")
            )
        ]
    )
    db = _mock_db(report=report)
    auto_apply = MagicMock(spec=AutoApplyService)
    service = ReportAutoApplyService(auto_apply_service=auto_apply)

    # WHEN
    service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN — empresa_id do relatório é propagado como primeiro argumento ao service
    enterprise_id_arg = auto_apply.apply.call_args[0][0]
    request_arg = auto_apply.apply.call_args[0][1]
    assert enterprise_id_arg == FAKE_ENTERPRISE_ID
    assert request_arg.target == AutoApplyTarget.ENTERPRISE
    assert request_arg.campo_para_alterar == "telefone"


# ---------------------------------------------------------------------------
# Filtragem de itens
# ---------------------------------------------------------------------------


def test_given_false_flag_items_when_applied_then_ignored() -> None:
    # GIVEN — todos os itens têm pode_auto_aplicar=False
    report = _make_mock_report(
        pontos_positivos=[_make_item_dict(pode_auto_aplicar=False, sugestao=None)],
        melhorias=[_make_item_dict(pode_auto_aplicar=False, sugestao=None)],
    )
    db = _mock_db(report=report)
    auto_apply = MagicMock(spec=AutoApplyService)
    service = ReportAutoApplyService(auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 0
    assert response.aplicadas == 0
    assert response.rejeitadas == 0
    auto_apply.apply.assert_not_called()
    db.commit.assert_not_called()


def test_given_malformed_item_json_when_applied_then_item_skipped() -> None:
    # GIVEN — item com target inválido no banco (regressão de SCRUM-213)
    malformed = {
        "titulo": "Item corrompido",
        "resumo": "x",
        "descricao": "x",
        "pode_auto_aplicar": True,
        "sugestao": {"target": "INVALIDO", "campo_para_alterar": "historia", "novo_valor": "y"},
    }
    valid = _make_item_dict()
    report = _make_mock_report(melhorias=[malformed, valid])
    db = _mock_db(report=report)
    auto_apply = MagicMock(spec=AutoApplyService)
    service = ReportAutoApplyService(auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN — item malformado ignorado; item válido aplicado normalmente
    assert response.total == 1
    assert response.aplicadas == 1
    auto_apply.apply.assert_called_once()


def test_given_no_candidates_when_applied_then_zero_counts() -> None:
    # GIVEN — relatório sem itens
    report = _make_mock_report()
    db = _mock_db(report=report)
    service = ReportAutoApplyService(auto_apply_service=MagicMock(spec=AutoApplyService))

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 0
    assert response.aplicadas == 0
    assert response.rejeitadas == 0
    assert response.resultados == []


# ---------------------------------------------------------------------------
# Falhas individuais não derrubam o lote
# ---------------------------------------------------------------------------


def test_given_invalid_suggestion_when_applied_then_marked_rejected() -> None:
    # GIVEN — campo fora da whitelist
    report = _make_mock_report(
        melhorias=[_make_item_dict(sugestao=_make_sugestao_dict(campo_para_alterar="owner_id"))]
    )
    db = _mock_db(report=report)
    auto_apply = MagicMock(spec=AutoApplyService)
    auto_apply.apply.side_effect = FieldNotAllowedError("owner_id")
    service = ReportAutoApplyService(auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 1
    assert response.aplicadas == 0
    assert response.rejeitadas == 1
    assert response.resultados[0].status == SuggestionStatus.REJECTED
    assert "owner_id" in response.resultados[0].erro
    db.commit.assert_not_called()


def test_given_apply_service_raises_when_applied_then_item_rejected_and_batch_continues() -> None:
    # GIVEN — 1º item falha, 2º item deve ser aplicado normalmente
    report = _make_mock_report(
        melhorias=[
            _make_item_dict(sugestao=_make_sugestao_dict(campo_para_alterar="preco")),
            _make_item_dict(sugestao=_make_sugestao_dict(campo_para_alterar="historia")),
        ]
    )
    db = _mock_db(report=report)
    auto_apply = MagicMock(spec=AutoApplyService)
    auto_apply.apply.side_effect = [InvalidFieldValueError("preco", "valor inválido"), None]
    service = ReportAutoApplyService(auto_apply_service=auto_apply)

    # WHEN
    response = service.apply_from_report(FAKE_REPORT_ID, db)

    # THEN
    assert response.total == 2
    assert response.aplicadas == 1
    assert response.rejeitadas == 1
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Erros bloqueantes
# ---------------------------------------------------------------------------


def test_given_report_not_found_when_applied_then_raises() -> None:
    # GIVEN
    db = _mock_db(report=None)
    service = ReportAutoApplyService(auto_apply_service=MagicMock(spec=AutoApplyService))

    # WHEN / THEN
    with pytest.raises(AIReportNotFoundError):
        service.apply_from_report(FAKE_REPORT_ID, db)


def test_given_commit_fails_when_applied_then_raises_persistence_error() -> None:
    # GIVEN
    report = _make_mock_report(melhorias=[_make_item_dict()])
    db = _mock_db(report=report)
    db.commit.side_effect = RuntimeError("db down")
    auto_apply = MagicMock(spec=AutoApplyService)
    service = ReportAutoApplyService(auto_apply_service=auto_apply)

    # WHEN / THEN
    with pytest.raises(AutoApplyPersistenceError):
        service.apply_from_report(FAKE_REPORT_ID, db)
    db.rollback.assert_called_once()
