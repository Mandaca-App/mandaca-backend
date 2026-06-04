"""
Testes smoke para os endpoints de reservas (app/routers/reservations.py).

Foco: verificar wire-up HTTP correto (roteamento, status codes, serialização da response).
Estratégia: service completamente mockado; lógica de negócio é coberta em test_reservation_service
"""

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import EnterpriseNotFoundError, ReservationNotFoundError, UserNotFoundError
from app.core.session import get_db
from app.main import app
from app.models.reservation import StatusReserva

client = TestClient(app, raise_server_exceptions=False)

FAKE_RESERVATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
FAKE_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
FAKE_ENTERPRISE_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

_RESERVATION_RESPONSE = SimpleNamespace(
    id_reserva=FAKE_RESERVATION_ID,
    num_mesas=2,
    num_pessoas=4,
    mensagem="Mesa perto da janela.",
    status=StatusReserva.AGUARDANDO,
    usuario_id=FAKE_USER_ID,
    empresa_id=FAKE_ENTERPRISE_ID,
)

_ACCEPTED_RESERVATION_RESPONSE = SimpleNamespace(
    id_reserva=FAKE_RESERVATION_ID,
    num_mesas=2,
    num_pessoas=4,
    mensagem="Mesa perto da janela.",
    status=StatusReserva.ACEITO,
    usuario_id=FAKE_USER_ID,
    empresa_id=FAKE_ENTERPRISE_ID,
)

_RESERVATION_NO_OPTIONAL = SimpleNamespace(
    id_reserva=FAKE_RESERVATION_ID,
    num_mesas=1,
    num_pessoas=2,
    mensagem=None,
    status=StatusReserva.AGUARDANDO,
    usuario_id=None,
    empresa_id=None,
)

_RESERVATIONS_LIST = [_RESERVATION_RESPONSE]


@pytest.fixture
def db_mock():
    def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# POST /reservations/
# ---------------------------------------------------------------------------


def test_given_valid_payload_when_create_then_returns_201(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.create",
        return_value=_RESERVATION_RESPONSE,
    ):
        response = client.post(
            "/reservations/",
            json={
                "num_mesas": 2,
                "num_pessoas": 4,
                "mensagem": "Mesa perto da janela.",
                "usuario_id": str(FAKE_USER_ID),
                "empresa_id": str(FAKE_ENTERPRISE_ID),
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id_reserva"] == str(FAKE_RESERVATION_ID)
    assert data["num_mesas"] == 2
    assert data["num_pessoas"] == 4
    assert data["status"] == "aguardando"
    assert data["empresa_id"] == str(FAKE_ENTERPRISE_ID)


def test_given_payload_without_optional_fields_when_create_then_returns_201(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.create",
        return_value=_RESERVATION_NO_OPTIONAL,
    ):
        response = client.post(
            "/reservations/",
            json={"num_mesas": 1, "num_pessoas": 2},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["mensagem"] is None
    assert data["usuario_id"] is None
    assert data["empresa_id"] is None


def test_given_missing_num_mesas_when_create_then_returns_422(db_mock):
    response = client.post(
        "/reservations/",
        json={"num_pessoas": 4},
    )
    assert response.status_code == 422


def test_given_missing_num_pessoas_when_create_then_returns_422(db_mock):
    response = client.post(
        "/reservations/",
        json={"num_mesas": 2},
    )
    assert response.status_code == 422


def test_given_create_response_when_status_is_aguardando_by_default(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.create",
        return_value=_RESERVATION_RESPONSE,
    ):
        response = client.post(
            "/reservations/",
            json={"num_mesas": 2, "num_pessoas": 4},
        )

    assert response.json()["status"] == "aguardando"


# ---------------------------------------------------------------------------
# GET /reservations/{reservation_id}
# ---------------------------------------------------------------------------


def test_given_reservation_exists_when_get_by_id_then_returns_200(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.get_by_id",
        return_value=_RESERVATION_RESPONSE,
    ):
        response = client.get(f"/reservations/{FAKE_RESERVATION_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id_reserva"] == str(FAKE_RESERVATION_ID)
    assert data["status"] == "aguardando"


def test_given_reservation_not_found_when_get_by_id_then_returns_404(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.get_by_id",
        side_effect=ReservationNotFoundError(FAKE_RESERVATION_ID),
    ):
        response = client.get(f"/reservations/{FAKE_RESERVATION_ID}")

    assert response.status_code == 404


def test_given_invalid_uuid_when_get_by_id_then_returns_422(db_mock):
    response = client.get("/reservations/nao-e-um-uuid")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /reservations/by-enterprise/{empresa_id}
# ---------------------------------------------------------------------------


def test_given_enterprise_exists_when_list_by_enterprise_then_returns_200(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.list_by_enterprise",
        return_value=_RESERVATIONS_LIST,
    ):
        response = client.get(f"/reservations/by-enterprise/{FAKE_ENTERPRISE_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["empresa_id"] == str(FAKE_ENTERPRISE_ID)
    assert data[0]["status"] == "aguardando"


def test_given_enterprise_not_found_when_list_by_enterprise_then_returns_404(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.list_by_enterprise",
        side_effect=EnterpriseNotFoundError(FAKE_ENTERPRISE_ID),
    ):
        response = client.get(f"/reservations/by-enterprise/{FAKE_ENTERPRISE_ID}")

    assert response.status_code == 404


def test_given_enterprise_with_no_reservations_when_list_by_enterprise_then_returns_empty_list(
    db_mock,
):
    with patch(
        "app.routers.reservations.reservation_service.list_by_enterprise",
        return_value=[],
    ):
        response = client.get(f"/reservations/by-enterprise/{FAKE_ENTERPRISE_ID}")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /reservations/by-user/{usuario_id}
# ---------------------------------------------------------------------------


def test_given_user_exists_when_list_by_user_then_returns_200(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.list_by_user",
        return_value=_RESERVATIONS_LIST,
    ):
        response = client.get(f"/reservations/by-user/{FAKE_USER_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["usuario_id"] == str(FAKE_USER_ID)


def test_given_user_not_found_when_list_by_user_then_returns_404(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.list_by_user",
        side_effect=UserNotFoundError(FAKE_USER_ID),
    ):
        response = client.get(f"/reservations/by-user/{FAKE_USER_ID}")

    assert response.status_code == 404


def test_given_user_with_no_reservations_when_list_by_user_then_returns_empty_list(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.list_by_user",
        return_value=[],
    ):
        response = client.get(f"/reservations/by-user/{FAKE_USER_ID}")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# PATCH /reservations/{reservation_id}/accept
# ---------------------------------------------------------------------------


def test_given_reservation_exists_when_accept_then_returns_200(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.accept",
        return_value=_ACCEPTED_RESERVATION_RESPONSE,
    ):
        response = client.patch(f"/reservations/{FAKE_RESERVATION_ID}/accept")

    assert response.status_code == 200
    data = response.json()
    assert data["id_reserva"] == str(FAKE_RESERVATION_ID)
    assert data["status"] == "aceito"


def test_given_accept_endpoint_when_called_then_no_body_required(db_mock):
    """Garante que o endpoint não exige body — basta a URL."""
    with patch(
        "app.routers.reservations.reservation_service.accept",
        return_value=_ACCEPTED_RESERVATION_RESPONSE,
    ):
        response = client.patch(f"/reservations/{FAKE_RESERVATION_ID}/accept")

    assert response.status_code == 200


def test_given_reservation_not_found_when_accept_then_returns_404(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.accept",
        side_effect=ReservationNotFoundError(FAKE_RESERVATION_ID),
    ):
        response = client.patch(f"/reservations/{FAKE_RESERVATION_ID}/accept")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /reservations/{reservation_id}
# ---------------------------------------------------------------------------


def test_given_reservation_exists_when_cancel_then_returns_204(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.delete",
        return_value=None,
    ):
        response = client.delete(f"/reservations/{FAKE_RESERVATION_ID}")

    assert response.status_code == 204


def test_given_reservation_not_found_when_cancel_then_returns_404(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.delete",
        side_effect=ReservationNotFoundError(FAKE_RESERVATION_ID),
    ):
        response = client.delete(f"/reservations/{FAKE_RESERVATION_ID}")

    assert response.status_code == 404


def test_given_cancel_when_returns_204_then_body_is_empty(db_mock):
    with patch(
        "app.routers.reservations.reservation_service.delete",
        return_value=None,
    ):
        response = client.delete(f"/reservations/{FAKE_RESERVATION_ID}")

    assert response.status_code == 204
    assert response.content == b""
