"""
Testes unitários para ReportService.

Foco: lógica de negócio da camada de service isolada.
Estratégia: SQLAlchemy Session, BusinessContextService e genai.Client mockados.
Não há banco real nem chamadas de rede nestes testes.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import AIReportNotFoundError
from app.models.business_context import BusinessContext
from app.models.report import AIReport
from app.services.context_validation_service import ContextValidationResult

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_REPORT_ID = uuid.uuid4()
FAKE_EMPRESA_ID = uuid.uuid4()
FAKE_CONTEXTO_ID = uuid.uuid4()

FAKE_DADOS_CONTEXTO = {
    "nome": "Restaurante Teste",
    "especialidade": "Nordestina",
    "avaliacoes": [{"texto": "Ótimo!", "tipo": "POSITIVA"}],
    "cardapio": [{"descricao": "Baião de dois", "preco": "35.00"}],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**kwargs) -> BusinessContext:
    ctx = BusinessContext(
        id_contexto=kwargs.get("id_contexto", FAKE_CONTEXTO_ID),
        empresa_id=kwargs.get("empresa_id", FAKE_EMPRESA_ID),
        hash_contexto="a" * 64,
        dados_contexto=kwargs.get("dados_contexto", FAKE_DADOS_CONTEXTO),
        criado_em=kwargs.get("criado_em", datetime.now(timezone.utc)),
    )
    return ctx


def _make_report(**kwargs) -> AIReport:
    r = AIReport(
        id_relatorio=kwargs.get("id_relatorio", FAKE_REPORT_ID),
        empresa_id=kwargs.get("empresa_id", FAKE_EMPRESA_ID),
        contexto_id=kwargs.get("contexto_id", FAKE_CONTEXTO_ID),
        pontos_positivos=kwargs.get("pontos_positivos", []),
        melhorias=kwargs.get("melhorias", []),
        recomendacoes=kwargs.get("recomendacoes", []),
        criado_em=kwargs.get("criado_em", datetime.now(timezone.utc)),
    )
    return r


def _mock_db() -> MagicMock:
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    db.execute.return_value = execute_result
    db.get.return_value = None
    return db


def _mock_context_service(contexts: list) -> MagicMock:
    svc = MagicMock()
    svc.list_by_enterprise.return_value = contexts
    return svc


def _mock_validation_service(
    context: BusinessContext | None,
    *,
    context_changed: bool = False,
    current_context_data: dict | None = None,
    current_context_hash: str | None = None,
    reusable_report: AIReport | None = None,
) -> MagicMock:
    svc = MagicMock()
    svc.validate_for_report.return_value = ContextValidationResult(
        context_changed=context_changed,
        saved_context=context,
        current_context_data=(
            current_context_data
            if current_context_data is not None
            else context.dados_contexto if context is not None else FAKE_DADOS_CONTEXTO
        ),
        current_context_hash=(
            current_context_hash
            if current_context_hash is not None
            else context.hash_contexto if context is not None else "b" * 64
        ),
        reusable_report=reusable_report,
    )
    return svc


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------


def test_given_valid_empresa_when_generate_then_returns_report():
    # GIVEN
    from app.services.report_service import ReportService

    ctx = _make_context()
    db = _mock_db()
    db.refresh = MagicMock()
    ctx_svc = _mock_context_service([ctx])
    validation_svc = _mock_validation_service(ctx)

    service = ReportService(
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    assert result is not None
    assert result.empresa_id == FAKE_EMPRESA_ID
    assert result.contexto_id == FAKE_CONTEXTO_ID


def test_given_valid_empresa_when_generate_then_saves_empty_lists():
    # GIVEN
    from app.services.report_service import ReportService

    ctx = _make_context()
    db = _mock_db()
    db.refresh = MagicMock()
    ctx_svc = _mock_context_service([ctx])
    validation_svc = _mock_validation_service(ctx)

    service = ReportService(
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    assert isinstance(result.pontos_positivos, list)
    assert isinstance(result.melhorias, list)
    assert isinstance(result.recomendacoes, list)
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_given_empresa_no_context_when_generate_then_persists_first_context_before_report():
    # GIVEN
    from app.services.report_service import ReportService

    db = _mock_db()
    new_ctx = _make_context(id_contexto=uuid.uuid4(), dados_contexto=FAKE_DADOS_CONTEXTO)
    ctx_svc = _mock_context_service([])
    ctx_svc.create_from_snapshot.return_value = new_ctx
    validation_svc = _mock_validation_service(
        None,
        context_changed=True,
        current_context_data=FAKE_DADOS_CONTEXTO,
    )

    service = ReportService(
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    ctx_svc.create_from_snapshot.assert_called_once_with(
        FAKE_EMPRESA_ID,
        FAKE_DADOS_CONTEXTO,
        "b" * 64,
        db,
    )
    assert result.contexto_id == new_ctx.id_contexto


def test_given_invalid_empresa_when_generate_then_raises_not_found():
    # GIVEN
    from app.core.exceptions import EnterpriseNotFoundError
    from app.services.report_service import ReportService

    db = _mock_db()
    ctx_svc = MagicMock()
    validation_svc = MagicMock()
    validation_svc.validate_for_report.side_effect = EnterpriseNotFoundError(FAKE_EMPRESA_ID)

    service = ReportService(
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        service.generate_report(FAKE_EMPRESA_ID, db)


def test_given_unchanged_context_with_existing_report_when_generate_then_reuses_report():
    # GIVEN
    from app.services.report_service import ReportService

    ctx = _make_context()
    existing_report = _make_report()
    db = _mock_db()
    ctx_svc = _mock_context_service([ctx])
    validation_svc = _mock_validation_service(ctx, reusable_report=existing_report)

    service = ReportService(
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    assert result is existing_report
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_given_changed_context_when_generate_then_persists_new_context_before_report():
    # GIVEN
    from app.services.report_service import ReportService

    old_ctx = _make_context(dados_contexto={"nome": "Antigo"})
    new_ctx = _make_context(id_contexto=uuid.uuid4(), dados_contexto=FAKE_DADOS_CONTEXTO)
    db = _mock_db()
    ctx_svc = _mock_context_service([old_ctx])
    ctx_svc.create_from_snapshot.return_value = new_ctx
    validation_svc = _mock_validation_service(
        old_ctx,
        context_changed=True,
        current_context_data=FAKE_DADOS_CONTEXTO,
        current_context_hash="b" * 64,
    )

    service = ReportService(
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    ctx_svc.create_from_snapshot.assert_called_once_with(
        FAKE_EMPRESA_ID,
        FAKE_DADOS_CONTEXTO,
        "b" * 64,
        db,
    )
    assert result.contexto_id == new_ctx.id_contexto


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def test_given_report_id_when_get_by_id_then_returns_report():
    # GIVEN
    from app.services.report_service import ReportService

    db = _mock_db()
    report = _make_report()
    db.get.return_value = report

    service = ReportService()

    # WHEN
    result = service.get_by_id(FAKE_REPORT_ID, db)

    # THEN
    assert result is report
    assert isinstance(result.pontos_positivos, list)
    assert isinstance(result.melhorias, list)
    assert isinstance(result.recomendacoes, list)


def test_given_invalid_id_when_get_by_id_then_raises_not_found():
    # GIVEN
    from app.services.report_service import ReportService

    db = _mock_db()
    db.get.return_value = None

    service = ReportService()

    # WHEN / THEN
    with pytest.raises(AIReportNotFoundError):
        service.get_by_id(FAKE_REPORT_ID, db)


# ---------------------------------------------------------------------------
# list_by_enterprise
# ---------------------------------------------------------------------------


def test_given_empresa_when_list_reports_then_returns_ordered():
    # GIVEN
    from app.services.report_service import ReportService

    db = _mock_db()
    reports = [_make_report(), _make_report(id_relatorio=uuid.uuid4())]
    db.execute.return_value.scalars.return_value.all.return_value = reports

    service = ReportService()

    # WHEN
    result = service.list_by_enterprise(FAKE_EMPRESA_ID, db)

    # THEN
    assert len(result) == 2


# ---------------------------------------------------------------------------
# ReportItem schema validation
# ---------------------------------------------------------------------------


def test_given_valid_fields_when_report_item_created_then_ok():
    # GIVEN / WHEN
    from app.schemas.reports import ReportItem

    item = ReportItem(
        titulo="Sopa de feijão",
        resumo="Sopa de feijão está sendo muito bem avaliada",
        descricao="A sopa de feijão foi o prato mais pedido do mês.",
        pode_auto_aplicar=False,
    )

    # THEN
    assert item.titulo == "Sopa de feijão"
    assert item.sugestao is None


def test_given_auto_apply_true_with_sugestao_when_item_created_then_ok():
    # GIVEN / WHEN
    from app.schemas.auto_apply import AutoApplySuggestion, AutoApplyTarget
    from app.schemas.reports import ReportItem

    sug = AutoApplySuggestion(
        mensagem="Vou destacar a sopa como prato principal no cardápio",
        target=AutoApplyTarget.MENU_ITEM,
        menu_item_id=uuid.uuid4(),
        campo_para_alterar="destaque",
        novo_valor="true",
    )
    item = ReportItem(
        titulo="Sopa de feijão",
        resumo="Sopa de feijão está sendo muito bem avaliada",
        descricao="A sopa de feijão foi o prato mais pedido do mês.",
        pode_auto_aplicar=True,
        sugestao=sug,
    )

    # THEN
    assert item.pode_auto_aplicar is True
    assert item.sugestao.mensagem == "Vou destacar a sopa como prato principal no cardápio"


def test_given_auto_apply_true_without_sugestao_when_item_created_then_raises():
    # GIVEN
    from app.schemas.reports import ReportItem

    # WHEN / THEN
    with pytest.raises(Exception):
        ReportItem(
            titulo="Sopa de feijão",
            resumo="Resumo",
            descricao="Descricao",
            pode_auto_aplicar=True,
            sugestao=None,
        )
