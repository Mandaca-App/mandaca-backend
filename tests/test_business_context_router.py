"""
Testes smoke para os endpoints de business-contexts (app/routers/business_context.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: services completamente mockados; lógica de negócio é coberta em
test_business_context_service.py.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.business_contexts import BusinessContextResponse

client = TestClient(app, raise_server_exceptions=False)

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
# GET /by-enterprise/{enterprise_id}
# ---------------------------------------------------------------------------


def test_given_contexts_exist_when_list_by_enterprise_then_returns_200():
    # GIVEN
    with patch(
        "app.services.business_context_service.list_by_enterprise",
        return_value=[_CONTEXT_RESPONSE],
    ):
        # WHEN
        response = client.get(f"/business-contexts/by-enterprise/{FAKE_ENTERPRISE_ID}")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["empresa_id"] == str(FAKE_ENTERPRISE_ID)


def test_given_no_contexts_when_list_by_enterprise_then_returns_200_empty():
    # GIVEN
    with patch(
        "app.services.business_context_service.list_by_enterprise",
        return_value=[],
    ):
        # WHEN
        response = client.get(f"/business-contexts/by-enterprise/{FAKE_ENTERPRISE_ID}")

    # THEN
    assert response.status_code == 200
    assert response.json() == []


def test_given_invalid_uuid_when_list_by_enterprise_then_returns_422():
    # WHEN
    response = client.get("/business-contexts/by-enterprise/not-a-uuid")

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /{context_id}
# ---------------------------------------------------------------------------


def test_given_context_exists_when_get_by_id_then_returns_200():
    # GIVEN
    with patch(
        "app.services.business_context_service.get_by_id",
        return_value=_CONTEXT_RESPONSE,
    ):
        # WHEN
        response = client.get(f"/business-contexts/{FAKE_CONTEXT_ID}")

    # THEN
    assert response.status_code == 200
    body = response.json()
    assert body["id_contexto"] == str(FAKE_CONTEXT_ID)
    assert body["hash_contexto"] == "a" * 64
    assert body["dados_contexto"]["nome"] == "Restaurante Teste"


def test_given_invalid_uuid_when_get_by_id_then_returns_422():
    # WHEN
    response = client.get("/business-contexts/not-a-uuid")

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /{enterprise_id}  — create_from_enterprise (sem body)
# ---------------------------------------------------------------------------


def test_given_enterprise_exists_when_create_from_enterprise_then_returns_201():
    # GIVEN
    with patch(
        "app.services.business_context_service.create_from_enterprise",
        return_value=_CONTEXT_RESPONSE,
    ):
        # WHEN
        response = client.post(f"/business-contexts/{FAKE_ENTERPRISE_ID}")

    # THEN
    assert response.status_code == 201
    body = response.json()
    assert body["empresa_id"] == str(FAKE_ENTERPRISE_ID)
    assert len(body["hash_contexto"]) == 64


def test_given_valid_enterprise_when_create_from_enterprise_then_returns_context_fields():
    # GIVEN
    with patch(
        "app.services.business_context_service.create_from_enterprise",
        return_value=_CONTEXT_RESPONSE,
    ):
        # WHEN
        response = client.post(f"/business-contexts/{FAKE_ENTERPRISE_ID}")

    # THEN
    body = response.json()
    assert body["dados_contexto"]["especialidade"] == "Nordestina"
    assert body["id_contexto"] == str(FAKE_CONTEXT_ID)


def test_given_invalid_uuid_when_create_from_enterprise_then_returns_422():
    # WHEN
    response = client.post("/business-contexts/not-a-uuid")

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

    with patch(
        "app.services.business_context_service.update",
        return_value=updated_response,
    ):
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


def test_given_empty_payload_when_update_then_returns_200():
    # GIVEN — payload vazio é válido (todos os campos são opcionais no Update)
    with patch(
        "app.services.business_context_service.update",
        return_value=_CONTEXT_RESPONSE,
    ):
        # WHEN
        response = client.put(f"/business-contexts/{FAKE_CONTEXT_ID}", json={})

    # THEN
    assert response.status_code == 200


def test_given_dados_contexto_as_string_when_update_then_returns_422():
    # WHEN — dados_contexto deve ser objeto JSON, não string
    response = client.put(
        f"/business-contexts/{FAKE_CONTEXT_ID}",
        json={"dados_contexto": "isso nao e um objeto"},
    )

    # THEN
    assert response.status_code == 422


def test_given_invalid_uuid_when_update_then_returns_422():
    # WHEN
    response = client.put("/business-contexts/not-a-uuid", json={})

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /{context_id}
# ---------------------------------------------------------------------------


def test_given_existing_context_when_delete_then_returns_204():
    # GIVEN
    with patch(
        "app.services.business_context_service.delete",
        return_value=None,
    ):
        # WHEN
        response = client.delete(f"/business-contexts/{FAKE_CONTEXT_ID}")

    # THEN
    assert response.status_code == 204
    assert response.content == b""


def test_given_invalid_uuid_when_delete_then_returns_422():
    # WHEN
    response = client.delete("/business-contexts/not-a-uuid")

    # THEN
    assert response.status_code == 422