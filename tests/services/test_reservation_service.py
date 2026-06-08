"""
Testes unitários para reservation_service.

Foco: lógica de negócio da camada de service isolada.
Estratégia: SQLAlchemy Session completamente mockada.
Não há banco real nem chamadas de rede nestes testes.
"""

import uuid
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_reservation(**kwargs) -> Reservation:
    return Reservation(
        id_reserva=kwargs.get("id_reserva", FAKE_RESERVATION_ID),
        num_mesas=kwargs.get("num_mesas", 2),
        num_pessoas=kwargs.get("num_pessoas", 4),
        mensagem=kwargs.get("mensagem", None),
        status=kwargs.get("status", StatusReserva.AGUARDANDO),
        usuario_id=kwargs.get("usuario_id", FAKE_USER_ID),
        empresa_id=kwargs.get("empresa_id", FAKE_ENTERPRISE_ID),
    )


def _make_enterprise(**kwargs) -> Enterprise:
    e = Enterprise(
        id_empresa=kwargs.get("id_empresa", FAKE_ENTERPRISE_ID),
        nome=kwargs.get("nome", "Empresa Teste"),
        especialidade=None,
        endereco=None,
        historia=None,
        hora_abrir=None,
        hora_fechar=None,
        telefone=None,
        latitude=None,
        longitude=None,
        usuario_id=uuid.uuid4(),
        deleted_at=None,
    )
    e.fotos = []
    e.cardapios = []
    e.reservas = []
    e.avaliacoes = []
    return e


def _make_user(**kwargs) -> User:
    return User(
        id_usuario=kwargs.get("id_usuario", FAKE_USER_ID),
        nome=kwargs.get("nome", "Usuário Teste"),
    )


def _mock_db() -> MagicMock:
    db = MagicMock()

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result

    db.get.return_value = None
    return db


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def test_given_existing_reservation_when_get_by_id_then_returns_it():
    db = _mock_db()
    reservation = _make_reservation()
    db.execute.return_value.scalar_one_or_none.return_value = reservation

    result = reservation_service.get_by_id(FAKE_RESERVATION_ID, db)

    assert result is reservation


def test_given_missing_reservation_when_get_by_id_then_raises_domain_error():
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(ReservationNotFoundError) as exc_info:
        reservation_service.get_by_id(FAKE_RESERVATION_ID, db)

    assert exc_info.value.reservation_id == FAKE_RESERVATION_ID


def test_given_accepted_reservation_when_get_by_id_then_returns_it():
    db = _mock_db()
    reservation = _make_reservation(status=StatusReserva.ACEITO)
    db.execute.return_value.scalar_one_or_none.return_value = reservation

    result = reservation_service.get_by_id(FAKE_RESERVATION_ID, db)

    assert result is reservation
    assert result.status == StatusReserva.ACEITO


# ---------------------------------------------------------------------------
# list_by_enterprise
# ---------------------------------------------------------------------------


def test_given_existing_enterprise_when_list_by_enterprise_then_returns_reservations():
    db = _mock_db()
    enterprise = _make_enterprise()
    reservations = [
        _make_reservation(),
        _make_reservation(id_reserva=uuid.uuid4(), num_pessoas=6),
    ]
    db.get.return_value = enterprise
    db.execute.return_value.scalars.return_value.all.return_value = reservations

    result = reservation_service.list_by_enterprise(FAKE_ENTERPRISE_ID, db)

    assert len(result) == 2


def test_given_existing_enterprise_with_no_reservations_when_list_by_enterprise_then_returns():
    db = _mock_db()
    enterprise = _make_enterprise()
    db.get.return_value = enterprise
    db.execute.return_value.scalars.return_value.all.return_value = []

    result = reservation_service.list_by_enterprise(FAKE_ENTERPRISE_ID, db)

    assert result == []


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
    user = _make_user()
    reservations = [
        _make_reservation(),
        _make_reservation(id_reserva=uuid.uuid4(), num_mesas=1),
    ]
    db.get.return_value = user
    db.execute.return_value.scalars.return_value.all.return_value = reservations

    result = reservation_service.list_by_user(FAKE_USER_ID, db)

    assert len(result) == 2


def test_given_existing_user_with_no_reservations_when_list_by_user_then_returns_empty():
    db = _mock_db()
    user = _make_user()
    db.get.return_value = user
    db.execute.return_value.scalars.return_value.all.return_value = []

    result = reservation_service.list_by_user(FAKE_USER_ID, db)

    assert result == []


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
    db.get.return_value = _make_enterprise()
    payload = ReservationCreate(
        num_mesas=2,
        num_pessoas=4,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    reservation_service.create(payload, db)

    added: Reservation = db.add.call_args[0][0]
    assert added.status == StatusReserva.AGUARDANDO


def test_given_valid_payload_when_create_then_persists_reservation():
    db = _mock_db()
    db.get.return_value = _make_enterprise()
    payload = ReservationCreate(
        num_mesas=3,
        num_pessoas=8,
        mensagem="Mesa perto da janela, por favor.",
        empresa_id=FAKE_ENTERPRISE_ID,
        usuario_id=FAKE_USER_ID,
    )

    reservation_service.create(payload, db)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    added: Reservation = db.add.call_args[0][0]
    assert added.num_mesas == 3
    assert added.num_pessoas == 8
    assert added.mensagem == "Mesa perto da janela, por favor."
    assert added.empresa_id == FAKE_ENTERPRISE_ID
    assert added.usuario_id == FAKE_USER_ID


def test_given_payload_without_mensagem_when_create_then_mensagem_is_none():
    db = _mock_db()
    db.get.return_value = _make_enterprise()
    payload = ReservationCreate(
        num_mesas=1,
        num_pessoas=2,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    reservation_service.create(payload, db)

    added: Reservation = db.add.call_args[0][0]
    assert added.mensagem is None


def test_given_missing_enterprise_when_create_then_raises_enterprise_not_found():
    db = _mock_db()
    db.get.return_value = None
    payload = ReservationCreate(
        num_mesas=2,
        num_pessoas=4,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    with pytest.raises(EnterpriseNotFoundError):
        reservation_service.create(payload, db)


def test_given_missing_enterprise_when_create_then_does_not_persist():
    db = _mock_db()
    db.get.return_value = None
    payload = ReservationCreate(
        num_mesas=2,
        num_pessoas=4,
        empresa_id=FAKE_ENTERPRISE_ID,
    )

    with pytest.raises(EnterpriseNotFoundError):
        reservation_service.create(payload, db)

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_given_missing_user_when_create_then_raises_user_not_found():
    db = _mock_db()

    def get_side_effect(model, pk):
        if model is Enterprise:
            return _make_enterprise()
        return None  # User não encontrado

    db.get.side_effect = get_side_effect
    payload = ReservationCreate(
        num_mesas=2,
        num_pessoas=4,
        empresa_id=FAKE_ENTERPRISE_ID,
        usuario_id=FAKE_USER_ID,
    )

    with pytest.raises(UserNotFoundError):
        reservation_service.create(payload, db)

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_given_payload_without_empresa_and_usuario_when_create_then_persists():
    """Ambos os campos são opcionais; nenhuma validação deve ocorrer."""
    db = _mock_db()
    payload = ReservationCreate(num_mesas=1, num_pessoas=2)

    reservation_service.create(payload, db)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    added: Reservation = db.add.call_args[0][0]
    assert added.empresa_id is None
    assert added.usuario_id is None


# ---------------------------------------------------------------------------
# accept
# ---------------------------------------------------------------------------


def test_given_awaiting_reservation_when_accept_then_status_becomes_aceito():
    db = _mock_db()
    reservation = _make_reservation(status=StatusReserva.AGUARDANDO)

    with patch("app.services.reservation_service.get_by_id", return_value=reservation):
        reservation_service.accept(FAKE_RESERVATION_ID, db)

    assert reservation.status == StatusReserva.ACEITO
    db.commit.assert_called_once()


def test_given_awaiting_reservation_when_accept_then_persists_and_refreshes():
    db = _mock_db()
    reservation = _make_reservation(status=StatusReserva.AGUARDANDO)

    with patch("app.services.reservation_service.get_by_id", return_value=reservation):
        reservation_service.accept(FAKE_RESERVATION_ID, db)

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(reservation)


def test_given_already_accepted_reservation_when_accept_then_status_remains_aceito():
    db = _mock_db()
    reservation = _make_reservation(status=StatusReserva.ACEITO)

    with patch("app.services.reservation_service.get_by_id", return_value=reservation):
        reservation_service.accept(FAKE_RESERVATION_ID, db)

    assert reservation.status == StatusReserva.ACEITO
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


def test_given_existing_reservation_when_delete_then_calls_db_delete():
    db = _mock_db()
    reservation = _make_reservation()

    with patch("app.services.reservation_service.get_by_id", return_value=reservation):
        reservation_service.delete(FAKE_RESERVATION_ID, db)

    db.delete.assert_called_once_with(reservation)
