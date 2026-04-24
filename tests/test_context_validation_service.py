import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import BusinessContextNotFoundError
from app.models.business_context import BusinessContext
from app.models.report import AIReport
from app.services.business_context_service import BusinessContextService
from app.services.context_validation_service import ContextValidationService

FAKE_EMPRESA_ID = uuid.uuid4()
FAKE_CONTEXTO_ID = uuid.uuid4()
FAKE_REPORT_ID = uuid.uuid4()

FAKE_DADOS = {"nome": "Restaurante Teste", "especialidade": "Nordestina"}


def _make_context(**kwargs) -> BusinessContext:
    return BusinessContext(
        id_contexto=kwargs.get("id_contexto", FAKE_CONTEXTO_ID),
        empresa_id=kwargs.get("empresa_id", FAKE_EMPRESA_ID),
        hash_contexto=kwargs.get("hash_contexto", "a" * 64),
        dados_contexto=kwargs.get("dados_contexto", FAKE_DADOS),
        criado_em=kwargs.get("criado_em", datetime.now(timezone.utc)),
    )


def _make_report(**kwargs) -> AIReport:
    return AIReport(
        id_relatorio=kwargs.get("id_relatorio", FAKE_REPORT_ID),
        empresa_id=kwargs.get("empresa_id", FAKE_EMPRESA_ID),
        contexto_id=kwargs.get("contexto_id", FAKE_CONTEXTO_ID),
        pontos_positivos_resumo="Boa comida.",
        pontos_positivos_detalhado="Alta qualidade.",
        melhorias_resumo="Atendimento lento.",
        melhorias_detalhado="Mais funcionarios.",
        recomendacoes_resumo="Investir em marketing.",
        recomendacoes_detalhado="Campanhas nas redes sociais.",
        criado_em=kwargs.get("criado_em", datetime.now(timezone.utc)),
    )


def _mock_db(reusable_report: AIReport | None = None) -> MagicMock:
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = reusable_report
    db.execute.return_value = execute_result
    return db


def _mock_context_service(contexts: list[BusinessContext]) -> MagicMock:
    svc = MagicMock()
    svc.list_by_enterprise.return_value = contexts
    svc.compute_hash.side_effect = BusinessContextService().compute_hash
    return svc


def _mock_builder(snapshot: dict) -> MagicMock:
    builder = MagicMock()
    builder.build_snapshot.return_value = snapshot
    return builder


def test_given_saved_context_when_current_context_differs_then_identifies_change():
    # GIVEN
    saved_context = _make_context(hash_contexto=BusinessContextService().compute_hash(FAKE_DADOS))
    current_snapshot = {"nome": "Restaurante Teste", "especialidade": "Regional"}
    service = ContextValidationService(
        context_service=_mock_context_service([saved_context]),
        context_builder=_mock_builder(current_snapshot),
    )

    # WHEN
    result = service.validate_for_report(FAKE_EMPRESA_ID, _mock_db())

    # THEN
    assert result.context_changed is True
    assert result.current_context_data == current_snapshot
    assert result.saved_context is saved_context


def test_given_changed_context_when_validate_then_does_not_reuse_report():
    # GIVEN
    saved_context = _make_context(hash_contexto=BusinessContextService().compute_hash(FAKE_DADOS))
    current_snapshot = {"nome": "Novo nome"}
    report = _make_report()
    db = _mock_db(reusable_report=report)
    service = ContextValidationService(
        context_service=_mock_context_service([saved_context]),
        context_builder=_mock_builder(current_snapshot),
    )

    # WHEN
    result = service.validate_for_report(FAKE_EMPRESA_ID, db)

    # THEN
    assert result.context_changed is True
    assert result.reusable_report is None


def test_given_same_context_when_validate_then_reuses_existing_report():
    # GIVEN
    saved_hash = BusinessContextService().compute_hash(FAKE_DADOS)
    saved_context = _make_context(hash_contexto=saved_hash)
    report = _make_report()
    service = ContextValidationService(
        context_service=_mock_context_service([saved_context]),
        context_builder=_mock_builder(FAKE_DADOS),
    )

    # WHEN
    result = service.validate_for_report(FAKE_EMPRESA_ID, _mock_db(reusable_report=report))

    # THEN
    assert result.context_changed is False
    assert result.reusable_report is report


def test_given_no_saved_context_when_validate_then_raises_not_found():
    # GIVEN
    service = ContextValidationService(
        context_service=_mock_context_service([]),
        context_builder=_mock_builder(FAKE_DADOS),
    )

    # WHEN / THEN
    with pytest.raises(BusinessContextNotFoundError):
        service.validate_for_report(FAKE_EMPRESA_ID, _mock_db())
