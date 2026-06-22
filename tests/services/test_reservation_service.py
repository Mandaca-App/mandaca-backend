"""
Testes unitários para reservation_service.

Foco: lógica de negócio da camada de service isolada.
Estratégia: SQLAlchemy Session completamente mockada.
Não há banco real nem chamadas de rede nestes testes.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    EnterpriseNotFoundError,
    ReservationNotFoundError,
    UserNotFoundError,
)
from app.models.enterprise import Enterprise
from app.models.reservation import Reservation, StatusReserva
from app.models.user import User
from app.schemas.reservations import ReservationCreate
from app.services import reservation_service

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FAKE_RESERVATION_ID = uuid.uuid4()
FAKE_USER_ID = uuid.uuid4()
FAKE_ENTERPRISE_ID = uuid.uuid4()
FAKE_DATE = datetime(2026, 6, 20, 19, 30)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_reservation(**kwargs) -> Reservation:
    return Reservation(
        id_reserva=kwargs.get("id_reserva", FAKE_RESERVATION_ID),
        horario_reserva=kwargs.get("horario_reserva", FAKE_DATE),
        num_pessoas=kwargs.get("num_pessoas", 4),
        mensagem=kwargs.get("mensagem", None),
        status=kwargs.get("status", StatusReserva.AGUARDANDO),
        usuario_id=kwargs.get("usuario_id", FAKE_USER_ID),
        empresa_id=kwargs.get("empresa_id", FAKE_ENTERPRISE_ID),
    )


def _mock_db() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def test_given_existing_reservation_when_get_by_id_then_returns_reservation():
    db = _mock_db()
    reservation = _make_reservation()

    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = reservation
    db.execute.return_value = mock_execute

    result = reservation_service.get_by_id(FAKE_RESERVATION_ID, db)

    assert result == reservation
    db.execute.assert_called_once()


def test_given_missing_reservation_when_get_by_id_then_raises_not_found():
    db = _mock_db()

    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_execute

    with pytest.raises(ReservationNotFoundError):
        reservation_service.get_by_id(FAKE_RESERVATION_ID, db)


# ---------------------------------------------------------------------------
# list_by_enterprise
# ---------------------------------------------------------------------------


def test_given_existing_enterprise_when_list_by_enterprise_then_returns_reservations():
    db = _mock_db()
    enterprise = Enterprise(id_empresa=FAKE_ENTERPRISE_ID)
    reservations = [_make_reservation(), _make_reservation()]

    db.get.return_value = enterprise

    mock_execute = MagicMock()
    mock_execute.scalars.return_value.all.return_value = reservations
    db.execute.return_value = mock_execute

    result = reservation_service.list_by_enterprise(FAKE_ENTERPRISE_ID, db)

    assert result == reservations
    db.get.assert_called_once_with(Enterprise, FAKE_ENTERPRISE_ID)


def test_given_missing_enterprise_when_list_by_enterprise_then_raises_not_found():
    db = _mock_db()
    db.get.return_value = None

    with pytest.raises(EnterpriseNotFoundError):
        reservation_service.list_by_enterprise(FAKE_ENTERPRISE_ID, db)


# ---------------------------------------------------------------------------
# list_by_user
# ---------------------------------------------------------------------------


def test_given_existing_user_when_list_by_user_then_returns_reservations():
    db = _mock_db()
    user = User(id_usuario=FAKE_USER_ID)
    reservations = [_make_reservation()]

    db.get.return_value = user

    mock_execute = MagicMock()
    mock_execute.scalars.return_value.all.return_value = reservations
    db.execute.return_value = mock_execute

    result = reservation_service.list_by_user(FAKE_USER_ID, db)

    assert result == reservations
    db.get.assert_called_once_with(User, FAKE_USER_ID)


def test_given_missing_user_when_list_by_user_then_raises_not_found():
    db = _mock_db()
    db.get.return_value = None

    with pytest.raises(UserNotFoundError):
        reservation_service.list_by_user(FAKE_USER_ID, db)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_given_valid_payload_when_create_then_status_is_aguardando():
    db = _mock_db()
    db.get.side_effect = [Enterprise(), User()]

    payload = ReservationCreate(
        horario_reserva=FAKE_DATE,
        num_pessoas=4,
        empresa_id=FAKE_ENTERPRISE_ID,
        usuario_id=FAKE_USER_ID,
    )

    result = reservation_service.create(payload, db)

    assert result.status == StatusReserva.AGUARDANDO


def test_given_valid_payload_when_create_then_persists_reservation():
    db = _mock_db()
    db.get.side_effect = [Enterprise(), User()]

    payload = ReservationCreate(
        horario_reserva=FAKE_DATE,
        num_pessoas=8,
        mensagem="Mesa perto da janela, por favor.",
        empresa_id=FAKE_ENTERPRISE_ID,
        usuario_id=FAKE_USER_ID,
    )

    reservation_service.create(payload, db)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    added: Reservation = db.add.call_args[0][0]

    assert added.horario_reserva == FAKE_DATE
    assert added.num_pessoas == 8
    assert added.mensagem == "Mesa perto da janela, por favor."
    assert added.empresa_id == FAKE_ENTERPRISE_ID
    assert added.usuario_id == FAKE_USER_ID


def test_given_payload_without_mensagem_when_create_then_mensagem_is_none():
    db = _mock_db()
    db.get.side_effect = [Enterprise(), User()]

    payload = ReservationCreate(
        horario_reserva=FAKE_DATE,
        num_pessoas=2,
        empresa_id=FAKE_ENTERPRISE_ID,
        usuario_id=FAKE_USER_ID,
    )

    result = reservation_service.create(payload, db)
    assert result.mensagem is None


def test_given_missing_enterprise_when_create_then_raises_enterprise_not_found():
    db = _mock_db()
    db.get.return_value = None

    payload = ReservationCreate(
        horario_reserva=FAKE_DATE,
        num_pessoas=4,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    with pytest.raises(EnterpriseNotFoundError):
        reservation_service.create(payload, db)


def test_given_missing_enterprise_when_create_then_does_not_persist():
    db = _mock_db()
    db.get.return_value = None

    payload = ReservationCreate(
        horario_reserva=FAKE_DATE,
        num_pessoas=4,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    with pytest.raises(EnterpriseNotFoundError):
        reservation_service.create(payload, db)

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_given_missing_user_when_create_then_raises_user_not_found():
    db = _mock_db()
    db.get.side_effect = [Enterprise(), None]

    payload = ReservationCreate(
        horario_reserva=FAKE_DATE,
        num_pessoas=4,
        empresa_id=FAKE_ENTERPRISE_ID,
        usuario_id=FAKE_USER_ID,
    )

    with pytest.raises(UserNotFoundError):
        reservation_service.create(payload, db)


def test_given_payload_without_empresa_and_usuario_when_create_then_persists():
    db = _mock_db()

    payload = ReservationCreate(
        horario_reserva=FAKE_DATE,
        num_pessoas=2,
        empresa_id=None,
        usuario_id=None,
    )

    result = reservation_service.create(payload, db)

    assert result.empresa_id is None
    assert result.usuario_id is None
    db.add.assert_called_once()
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# accept
# ---------------------------------------------------------------------------


def test_given_existing_reservation_when_accept_then_changes_status_to_aceito():
    db = _mock_db()
    reservation = _make_reservation(status=StatusReserva.AGUARDANDO)

    with patch("app.services.reservation_service.get_by_id", return_value=reservation):
        result = reservation_service.accept(FAKE_RESERVATION_ID, db)

    assert result.status == StatusReserva.ACEITO
    db.commit.assert_called_once()


def test_given_missing_reservation_when_accept_then_raises_domain_error():
    db = _mock_db()

    with patch(
        "app.services.reservation_service.get_by_id",
        side_effect=ReservationNotFoundError(FAKE_RESERVATION_ID),
    ):
        with pytest.raises(ReservationNotFoundError):
            reservation_service.accept(FAKE_RESERVATION_ID, db)

    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_given_existing_reservation_when_delete_then_removes_from_db():
    db = _mock_db()
    reservation = _make_reservation()

    with patch("app.services.reservation_service.get_by_id", return_value=reservation):
        reservation_service.delete(FAKE_RESERVATION_ID, db)

    db.delete.assert_called_once_with(reservation)
    db.commit.assert_called_once()


def test_given_missing_reservation_when_delete_then_raises_domain_error():
    db = _mock_db()

    with patch(
        "app.services.reservation_service.get_by_id",
        side_effect=ReservationNotFoundError(FAKE_RESERVATION_ID),
    ):
        with pytest.raises(ReservationNotFoundError):
            reservation_service.delete(FAKE_RESERVATION_ID, db)

    db.commit.assert_not_called()
