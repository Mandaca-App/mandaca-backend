"""
Testes smoke para os endpoints de reports (app/routers/reports.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: ReportService injetado via dependency_overrides do FastAPI;
lógica de negócio é coberta em test_report_service.py.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AIReportGenerationError,
    AIReportNotFoundError,
    BusinessContextNotFoundError,
)
from app.main import app
from app.models.report import AIReport
from app.routers.reports import get_report_service

FAKE_REPORT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
FAKE_EMPRESA_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
FAKE_CONTEXTO_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
FAKE_CRIADO_EM = datetime(2026, 4, 22, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


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
        criado_em=kwargs.get("criado_em", FAKE_CRIADO_EM),
    )
    return r


def _make_client(mock_service: MagicMock) -> TestClient:
    app.dependency_overrides[get_report_service] = lambda: mock_service
    return TestClient(app, raise_server_exceptions=False)


def _make_mock_service() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# POST /reports/generate/{empresa_id}
# ---------------------------------------------------------------------------


def test_given_valid_empresa_when_generate_then_returns_201():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.generate_report.return_value = _make_report()
    client = _make_client(mock_service)

    # WHEN
    response = client.post(f"/reports/generate/{FAKE_EMPRESA_ID}")

    # THEN
    assert response.status_code == 201
    body = response.json()
    assert body["empresa_id"] == str(FAKE_EMPRESA_ID)
    assert body["contexto_id"] == str(FAKE_CONTEXTO_ID)
    assert "pontos_positivos_detalhado" in body


def test_given_valid_empresa_when_generate_then_returns_all_detail_fields():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.generate_report.return_value = _make_report()
    client = _make_client(mock_service)

    # WHEN
    response = client.post(f"/reports/generate/{FAKE_EMPRESA_ID}")

    # THEN
    body = response.json()
    assert body["pontos_positivos_resumo"] == "Boa comida."
    assert body["melhorias_resumo"] == "Atendimento lento."
    assert body["recomendacoes_resumo"] == "Investir em marketing."
    assert body["melhorias_detalhado"] == "Mais funcionários."


def test_given_no_context_when_generate_then_returns_404():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.generate_report.side_effect = BusinessContextNotFoundError(
        f"nenhum contexto salvo para a empresa {FAKE_EMPRESA_ID}"
    )
    client = _make_client(mock_service)

    # WHEN
    response = client.post(f"/reports/generate/{FAKE_EMPRESA_ID}")

    # THEN
    assert response.status_code == 404


def test_given_gemini_failure_when_generate_then_returns_502():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.generate_report.side_effect = AIReportGenerationError("API unavailable")
    client = _make_client(mock_service)

    # WHEN
    response = client.post(f"/reports/generate/{FAKE_EMPRESA_ID}")

    # THEN
    assert response.status_code == 502


def test_given_invalid_uuid_when_generate_then_returns_422():
    # WHEN
    response = TestClient(app, raise_server_exceptions=False).post("/reports/generate/not-a-uuid")

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /reports/by-enterprise/{empresa_id}
# ---------------------------------------------------------------------------


def test_given_reports_exist_when_list_by_enterprise_then_returns_200():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.list_by_enterprise.return_value = [
        _make_report(),
        _make_report(id_relatorio=uuid.uuid4()),
    ]
    client = _make_client(mock_service)

    # WHEN
    response = client.get(f"/reports/by-enterprise/{FAKE_EMPRESA_ID}")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["empresa_id"] == str(FAKE_EMPRESA_ID)


def test_given_no_reports_when_list_by_enterprise_then_returns_200_empty():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.list_by_enterprise.return_value = []
    client = _make_client(mock_service)

    # WHEN
    response = client.get(f"/reports/by-enterprise/{FAKE_EMPRESA_ID}")

    # THEN
    assert response.status_code == 200
    assert response.json() == []


def test_given_summary_fields_when_list_by_enterprise_then_excludes_detail_fields():
    # GIVEN — AIReportSummary não expõe campos *_detalhado
    mock_service = _make_mock_service()
    mock_service.list_by_enterprise.return_value = [_make_report()]
    client = _make_client(mock_service)

    # WHEN
    response = client.get(f"/reports/by-enterprise/{FAKE_EMPRESA_ID}")

    # THEN
    body = response.json()[0]
    assert "pontos_positivos_detalhado" not in body
    assert "melhorias_detalhado" not in body
    assert "recomendacoes_detalhado" not in body


def test_given_invalid_uuid_when_list_by_enterprise_then_returns_422():
    # WHEN
    response = TestClient(app, raise_server_exceptions=False).get(
        "/reports/by-enterprise/not-a-uuid"
    )

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /reports/{report_id}
# ---------------------------------------------------------------------------


def test_given_report_exists_when_get_by_id_then_returns_200():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.get_by_id.return_value = _make_report()
    client = _make_client(mock_service)

    # WHEN
    response = client.get(f"/reports/{FAKE_REPORT_ID}")

    # THEN
    assert response.status_code == 200
    body = response.json()
    assert body["id_relatorio"] == str(FAKE_REPORT_ID)
    assert "pontos_positivos_detalhado" in body


def test_given_report_not_found_when_get_by_id_then_returns_404():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.get_by_id.side_effect = AIReportNotFoundError(FAKE_REPORT_ID)
    client = _make_client(mock_service)

    # WHEN
    response = client.get(f"/reports/{FAKE_REPORT_ID}")

    # THEN
    assert response.status_code == 404
    assert "Relatório IA não encontrado" in response.json()["detail"]


def test_given_invalid_uuid_when_get_by_id_then_returns_422():
    # WHEN
    response = TestClient(app, raise_server_exceptions=False).get("/reports/not-a-uuid")

    # THEN
    assert response.status_code == 422
