"""
Testes smoke para os endpoints de enterprises (app/routers/enterprises.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: services completamente mockados; lógica de negócio é coberta em
test_enterprise_service.py.
"""

import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enterprises import (
    EnterpriseOverviewResponse,
    EnterprisePercentageResponse,
    EnterpriseResponse,
)

client = TestClient(app, raise_server_exceptions=False)

FAKE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

_ENTERPRISE_RESPONSE = EnterpriseResponse(
    id_empresa=FAKE_ID,
    nome="Empresa Teste",
    usuario_id=USER_ID,
)

_OVERVIEW_RESPONSE = EnterpriseOverviewResponse(
    id_empresa=FAKE_ID,
    fotos=[],
)

_PERCENTAGE_RESPONSE = EnterprisePercentageResponse(
    id_empresa=FAKE_ID,
    nome="Empresa Teste",
    porcentagem=20.0,
    campos_preenchidos=[],
    campos_faltando=[
        "especialidade",
        "endereco",
        "historia",
        "hora_abrir",
        "hora_fechar",
        "telefone",
        "fotos",
        "cardapios",
    ],
)


def test_given_enterprises_exist_when_list_then_returns_200():
    # GIVEN
    with patch(
        "app.services.enterprise_service.list_all",
        return_value=[_ENTERPRISE_RESPONSE],
    ):
        # WHEN
        response = client.get("/enterprises/")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nome"] == "Empresa Teste"


def test_given_enterprise_exists_when_get_overview_then_returns_200():
    # GIVEN
    with patch(
        "app.services.enterprise_service.get_overview",
        return_value=_OVERVIEW_RESPONSE,
    ):
        # WHEN
        response = client.get(f"/enterprises/overview?enterprise_id={FAKE_ID}")

    # THEN
    assert response.status_code == 200
    assert response.json()["id_empresa"] == str(FAKE_ID)
    assert response.json()["fotos"] == []


def test_given_enterprise_exists_when_get_percentage_then_returns_200():
    # GIVEN
    with patch(
        "app.services.enterprise_service.get_percentage",
        return_value=_PERCENTAGE_RESPONSE,
    ):
        # WHEN
        response = client.get(f"/enterprises/percentage/{FAKE_ID}")

    # THEN
    assert response.status_code == 200
    assert response.json()["porcentagem"] == 20.0
    assert response.json()["campos_preenchidos"] == []


def test_given_valid_payload_when_update_then_returns_200():
    # GIVEN
    with patch(
        "app.services.enterprise_service.update",
        new=AsyncMock(return_value=_ENTERPRISE_RESPONSE),
    ):
        # WHEN
        response = client.put(
            f"/enterprises/{FAKE_ID}",
            json={"nome": "Nome Atualizado"},
        )

    # THEN
    assert response.status_code == 200
    assert response.json()["id_empresa"] == str(FAKE_ID)
