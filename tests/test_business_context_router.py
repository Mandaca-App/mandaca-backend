"""
Testes smoke para os endpoints de business-contexts (app/routers/business_context.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: BusinessContextService injetado via dependency_overrides do FastAPI;
lógica de negócio é coberta em test_business_context_service.py.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.routers.business_context import get_business_context_service
from app.schemas.business_contexts import BusinessContextResponse

FAKE_CONTEXT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
FAKE_ENTERPRISE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

FAKE_DADOS = {
    "nome": "Restaurante Teste",
    "especialidade": "Nordestina",
    "cardapio": [{"categoria": "prato_principal", "descricao": "Baião de dois", "preco": "35.00"}],
}

_CONTEXT_RESPONSE = BusinessContextResponse(
    id_contexto=FAKE_CONTEXT_ID,
    empresa_id=FAKE_ENTERPRISE_ID,
    hash_contexto="a" * 64,
    dados_contexto=FAKE_DADOS,
    criado_em=datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc),
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_client(mock_service: MagicMock) -> TestClient:
    """Cria um TestClient com o service mockado via dependency_overrides."""
    app.dependency_overrides[get_business_context_service] = lambda: mock_service
    client = TestClient(app, raise_server_exceptions=False)
    return client


def _make_mock_service() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# GET /by-enterprise/{enterprise_id}
# ---------------------------------------------------------------------------


def test_given_contexts_exist_when_list_by_enterprise_then_returns_200():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.list_by_enterprise.return_value = [_CONTEXT_RESPONSE]
    client = _make_client(mock_service)

    # WHEN
    response = client.get(f"/business-contexts/by-enterprise/{FAKE_ENTERPRISE_ID}")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["empresa_id"] == str(FAKE_ENTERPRISE_ID)

    app.dependency_overrides.clear()


def test_given_no_contexts_when_list_by_enterprise_then_returns_200_empty():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.list_by_enterprise.return_value = []
    client = _make_client(mock_service)

    # WHEN
    response = client.get(f"/business-contexts/by-enterprise/{FAKE_ENTERPRISE_ID}")

    # THEN
    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()


def test_given_invalid_uuid_when_list_by_enterprise_then_returns_422():
    # WHEN
    response = TestClient(app, raise_server_exceptions=False).get(
        "/business-contexts/by-enterprise/not-a-uuid"
    )

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /{context_id}
# ---------------------------------------------------------------------------


def test_given_context_exists_when_get_by_id_then_returns_200():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.get_by_id.return_value = _CONTEXT_RESPONSE
    client = _make_client(mock_service)

    # WHEN
    response = client.get(f"/business-contexts/{FAKE_CONTEXT_ID}")

    # THEN
    assert response.status_code == 200
    body = response.json()
    assert body["id_contexto"] == str(FAKE_CONTEXT_ID)
    assert body["hash_contexto"] == "a" * 64
    assert body["dados_contexto"]["nome"] == "Restaurante Teste"

    app.dependency_overrides.clear()


def test_given_invalid_uuid_when_get_by_id_then_returns_422():
    # WHEN
    response = TestClient(app, raise_server_exceptions=False).get("/business-contexts/not-a-uuid")

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /{enterprise_id}  — create_from_enterprise (sem body)
# ---------------------------------------------------------------------------


def test_given_enterprise_exists_when_create_from_enterprise_then_returns_201():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.create_from_enterprise.return_value = _CONTEXT_RESPONSE
    client = _make_client(mock_service)

    # WHEN
    response = client.post(f"/business-contexts/{FAKE_ENTERPRISE_ID}")

    # THEN
    assert response.status_code == 201
    body = response.json()
    assert body["empresa_id"] == str(FAKE_ENTERPRISE_ID)
    assert len(body["hash_contexto"]) == 64

    app.dependency_overrides.clear()


def test_given_valid_enterprise_when_create_from_enterprise_then_returns_context_fields():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.create_from_enterprise.return_value = _CONTEXT_RESPONSE
    client = _make_client(mock_service)

    # WHEN
    response = client.post(f"/business-contexts/{FAKE_ENTERPRISE_ID}")

    # THEN
    body = response.json()
    assert body["dados_contexto"]["especialidade"] == "Nordestina"
    assert body["id_contexto"] == str(FAKE_CONTEXT_ID)

    app.dependency_overrides.clear()


def test_given_invalid_uuid_when_create_from_enterprise_then_returns_422():
    # WHEN
    response = TestClient(app, raise_server_exceptions=False).post("/business-contexts/not-a-uuid")

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PUT /{context_id}
# ---------------------------------------------------------------------------


def test_given_valid_payload_when_update_then_returns_200():
    # GIVEN
    updated_response = BusinessContextResponse(
        id_contexto=FAKE_CONTEXT_ID,
        empresa_id=FAKE_ENTERPRISE_ID,
        hash_contexto="b" * 64,
        dados_contexto={"nome": "Atualizado"},
        criado_em=datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc),
    )
    mock_service = _make_mock_service()
    mock_service.update.return_value = updated_response
    client = _make_client(mock_service)

    # WHEN
    response = client.put(
        f"/business-contexts/{FAKE_CONTEXT_ID}",
        json={"dados_contexto": {"nome": "Atualizado"}},
    )

    # THEN
    assert response.status_code == 200
    body = response.json()
    assert body["dados_contexto"]["nome"] == "Atualizado"
    assert body["hash_contexto"] == "b" * 64

    app.dependency_overrides.clear()


def test_given_empty_payload_when_update_then_returns_200():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.update.return_value = _CONTEXT_RESPONSE
    client = _make_client(mock_service)

    # WHEN
    response = client.put(f"/business-contexts/{FAKE_CONTEXT_ID}", json={})

    # THEN
    assert response.status_code == 200

    app.dependency_overrides.clear()


def test_given_dados_contexto_as_string_when_update_then_returns_422():
    # WHEN — dados_contexto deve ser objeto JSON, não string; Pydantic rejeita antes do service
    response = TestClient(app, raise_server_exceptions=False).put(
        f"/business-contexts/{FAKE_CONTEXT_ID}",
        json={"dados_contexto": "isso nao e um objeto"},
    )

    # THEN
    assert response.status_code == 422


def test_given_invalid_uuid_when_update_then_returns_422():
    # WHEN
    response = TestClient(app, raise_server_exceptions=False).put(
        "/business-contexts/not-a-uuid", json={}
    )

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /{context_id}
# ---------------------------------------------------------------------------


def test_given_existing_context_when_delete_then_returns_204():
    # GIVEN
    mock_service = _make_mock_service()
    mock_service.delete.return_value = None
    client = _make_client(mock_service)

    # WHEN
    response = client.delete(f"/business-contexts/{FAKE_CONTEXT_ID}")

    # THEN
    assert response.status_code == 204
    assert response.content == b""

    app.dependency_overrides.clear()


def test_given_invalid_uuid_when_delete_then_returns_422():
    # WHEN
    response = TestClient(app, raise_server_exceptions=False).delete(
        "/business-contexts/not-a-uuid"
    )

    # THEN
    assert response.status_code == 422
