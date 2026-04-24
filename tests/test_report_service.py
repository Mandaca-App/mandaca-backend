"""
Testes unitários para ReportService.

Foco: lógica de negócio da camada de service isolada.
Estratégia: SQLAlchemy Session, BusinessContextService e genai.Client mockados.
Não há banco real nem chamadas de rede nestes testes.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    AIReportGenerationError,
    AIReportNotFoundError,
    BusinessContextNotFoundError,
)
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

FAKE_LLM_JSON = json.dumps(
    {
        "pontos_positivos_resumo": "Boa comida.",
        "pontos_positivos_detalhado": "O restaurante apresenta pratos de alta qualidade.",
        "melhorias_resumo": "Atendimento lento.",
        "melhorias_detalhado": "O tempo de espera pode ser reduzido com mais funcionários.",
        "recomendacoes_resumo": "Investir em marketing.",
        "recomendacoes_detalhado": "Campanhas nas redes sociais podem ampliar a visibilidade.",
    }
)


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
        pontos_positivos_resumo=kwargs.get("pontos_positivos_resumo", "Boa comida."),
        pontos_positivos_detalhado=kwargs.get("pontos_positivos_detalhado", "Alta qualidade."),
        melhorias_resumo=kwargs.get("melhorias_resumo", "Atendimento lento."),
        melhorias_detalhado=kwargs.get("melhorias_detalhado", "Mais funcionários."),
        recomendacoes_resumo=kwargs.get("recomendacoes_resumo", "Investir em marketing."),
        recomendacoes_detalhado=kwargs.get(
            "recomendacoes_detalhado", "Campanhas nas redes sociais."
        ),
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


def _mock_gemini_client(response_text: str = FAKE_LLM_JSON) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.text = response_text
    client.models.generate_content.return_value = response
    return client


def _mock_context_service(contexts: list) -> MagicMock:
    svc = MagicMock()
    svc.list_by_enterprise.return_value = contexts
    return svc


def _mock_validation_service(
    context: BusinessContext,
    *,
    context_changed: bool = False,
    current_context_data: dict | None = None,
    reusable_report: AIReport | None = None,
) -> MagicMock:
    svc = MagicMock()
    svc.validate_for_report.return_value = ContextValidationResult(
        context_changed=context_changed,
        saved_context=context,
        current_context_data=(
            current_context_data if current_context_data is not None else context.dados_contexto
        ),
        current_context_hash=context.hash_contexto,
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
    gemini = _mock_gemini_client()
    ctx_svc = _mock_context_service([ctx])
    validation_svc = _mock_validation_service(ctx)

    service = ReportService(
        gemini_client=gemini,
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    assert result is not None
    assert result.empresa_id == FAKE_EMPRESA_ID
    assert result.contexto_id == FAKE_CONTEXTO_ID


def test_given_valid_empresa_when_generate_then_persists_all_fields():
    # GIVEN
    from app.services.report_service import ReportService

    ctx = _make_context()
    db = _mock_db()
    db.refresh = MagicMock()
    gemini = _mock_gemini_client()
    ctx_svc = _mock_context_service([ctx])
    validation_svc = _mock_validation_service(ctx)

    service = ReportService(
        gemini_client=gemini,
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    assert result.pontos_positivos_resumo == "Boa comida."
    assert result.pontos_positivos_detalhado == "O restaurante apresenta pratos de alta qualidade."
    assert result.melhorias_resumo == "Atendimento lento."
    assert (
        result.melhorias_detalhado == "O tempo de espera pode ser reduzido com mais funcionários."
    )
    assert result.recomendacoes_resumo == "Investir em marketing."
    assert (
        result.recomendacoes_detalhado
        == "Campanhas nas redes sociais podem ampliar a visibilidade."
    )
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_given_empresa_no_context_when_generate_then_raises_not_found():
    # GIVEN
    from app.services.report_service import ReportService

    db = _mock_db()
    gemini = _mock_gemini_client()
    ctx_svc = _mock_context_service([])
    validation_svc = MagicMock()
    validation_svc.validate_for_report.side_effect = BusinessContextNotFoundError(
        f"nenhum contexto salvo para a empresa {FAKE_EMPRESA_ID}"
    )

    service = ReportService(
        gemini_client=gemini,
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN / THEN
    with pytest.raises(BusinessContextNotFoundError):
        service.generate_report(FAKE_EMPRESA_ID, db)


def test_given_invalid_empresa_when_generate_then_raises_not_found():
    # GIVEN
    from app.core.exceptions import EnterpriseNotFoundError
    from app.services.report_service import ReportService

    db = _mock_db()
    gemini = _mock_gemini_client()
    ctx_svc = MagicMock()
    ctx_svc.list_by_enterprise.side_effect = EnterpriseNotFoundError(FAKE_EMPRESA_ID)
    validation_svc = MagicMock()
    validation_svc.validate_for_report.side_effect = EnterpriseNotFoundError(FAKE_EMPRESA_ID)

    service = ReportService(
        gemini_client=gemini,
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN / THEN
    with pytest.raises(EnterpriseNotFoundError):
        service.generate_report(FAKE_EMPRESA_ID, db)


def test_given_gemini_error_when_generate_then_raises_generation_error():
    # GIVEN
    from app.services.report_service import ReportService

    ctx = _make_context()
    db = _mock_db()
    gemini = _mock_gemini_client()
    gemini.models.generate_content.side_effect = Exception("API unavailable")
    ctx_svc = _mock_context_service([ctx])
    validation_svc = _mock_validation_service(ctx)

    service = ReportService(
        gemini_client=gemini,
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN / THEN
    with pytest.raises(AIReportGenerationError):
        service.generate_report(FAKE_EMPRESA_ID, db)


def test_given_unchanged_context_with_existing_report_when_generate_then_reuses_report():
    # GIVEN
    from app.services.report_service import ReportService

    ctx = _make_context()
    existing_report = _make_report()
    db = _mock_db()
    gemini = _mock_gemini_client()
    ctx_svc = _mock_context_service([ctx])
    validation_svc = _mock_validation_service(ctx, reusable_report=existing_report)

    service = ReportService(
        gemini_client=gemini,
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    assert result is existing_report
    gemini.models.generate_content.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_given_changed_context_when_generate_then_persists_new_context_before_report():
    # GIVEN
    from app.services.report_service import ReportService

    old_ctx = _make_context(dados_contexto={"nome": "Antigo"})
    new_ctx = _make_context(id_contexto=uuid.uuid4(), dados_contexto=FAKE_DADOS_CONTEXTO)
    db = _mock_db()
    gemini = _mock_gemini_client()
    ctx_svc = _mock_context_service([old_ctx])
    ctx_svc.create_from_snapshot.return_value = new_ctx
    validation_svc = _mock_validation_service(
        old_ctx,
        context_changed=True,
        current_context_data=FAKE_DADOS_CONTEXTO,
    )

    service = ReportService(
        gemini_client=gemini,
        context_service=ctx_svc,
        context_validation_service=validation_svc,
    )

    # WHEN
    result = service.generate_report(FAKE_EMPRESA_ID, db)

    # THEN
    ctx_svc.create_from_snapshot.assert_called_once_with(
        FAKE_EMPRESA_ID,
        FAKE_DADOS_CONTEXTO,
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
    assert result.pontos_positivos_resumo == "Boa comida."
    assert result.melhorias_resumo == "Atendimento lento."
    assert result.recomendacoes_resumo == "Investir em marketing."


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
