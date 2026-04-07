"""
Testes de smoke para os exception handlers centrais (app/main.py).

Foco: verificar que cada exceção de domínio é convertida ao status HTTP correto.
Estratégia: TestClient com serviços mockados para forçar cada tipo de exceção.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.exceptions import (
    AddressNotFoundError,
    DuplicateEnterpriseNameError,
    EnterpriseNotFoundError,
    GeocodingUnavailableError,
    UserAlreadyHasEnterpriseError,
    UserNotFoundError,
)
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

FAKE_UUID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# 404 handlers
# ---------------------------------------------------------------------------


def test_given_enterprise_not_found_when_get_then_returns_404():
    # GIVEN
    with patch(
        "app.services.enterprise_service.get_by_id",
        side_effect=EnterpriseNotFoundError(FAKE_UUID),
    ):
        # WHEN
        response = client.get(f"/enterprises/{FAKE_UUID}")

    # THEN
    assert response.status_code == 404
    assert "não encontrada" in response.json()["detail"].lower()


def test_given_user_not_found_when_creating_enterprise_then_returns_404():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=UserNotFoundError(FAKE_UUID)),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa X", "usuario_id": FAKE_UUID},
        )

    # THEN
    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 400 handlers
# ---------------------------------------------------------------------------


def test_given_duplicate_name_when_creating_enterprise_then_returns_400():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=DuplicateEnterpriseNameError("Empresa X")),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa X", "usuario_id": FAKE_UUID},
        )

    # THEN
    assert response.status_code == 400
    assert "empresa" in response.json()["detail"].lower()


def test_given_user_already_has_enterprise_when_creating_then_returns_400():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=UserAlreadyHasEnterpriseError(FAKE_UUID)),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa Y", "usuario_id": FAKE_UUID},
        )

    # THEN
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 422 handler
# ---------------------------------------------------------------------------


def test_given_address_not_found_when_creating_enterprise_then_returns_422():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=AddressNotFoundError("Rua Inventada, 999")),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa Z", "usuario_id": FAKE_UUID, "endereco": "Rua Inventada, 999"},
        )

    # THEN
    assert response.status_code == 422
    assert "geocodific" in response.json()["detail"].lower() or (
        "encontrado" in response.json()["detail"].lower()
    )


# ---------------------------------------------------------------------------
# 503 handler
# ---------------------------------------------------------------------------


def test_given_geocoding_unavailable_when_creating_enterprise_then_returns_503():
    # GIVEN
    with patch(
        "app.services.enterprise_service.create",
        new=AsyncMock(side_effect=GeocodingUnavailableError()),
    ):
        # WHEN
        response = client.post(
            "/enterprises/",
            json={"nome": "Empresa W", "usuario_id": FAKE_UUID, "endereco": "Qualquer Rua"},
        )

    # THEN
    assert response.status_code == 503
    assert "indispon" in response.json()["detail"].lower()
