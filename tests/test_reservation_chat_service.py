"""Testes BDD para reservation_chat_service.

Lógica de domínio do chat de reservas: histórico e envio de mensagens com
derivação do tipo de remetente. Supabase/SQLAlchemy mockados via MagicMock.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import ReservationNotFoundError, SenderNotInReservationError
from app.models.enterprise import Enterprise
from app.models.reservation import Reservation
from app.models.reservation_message import ReservationMessage, TipoRemetente
from app.services import reservation_chat_service

RESERVA_ID = uuid.uuid4()
TURISTA_ID = uuid.uuid4()
DONO_ID = uuid.uuid4()
EMPRESA_ID = uuid.uuid4()


def _mock_db() -> MagicMock:
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    execute_result.scalar_one_or_none.return_value = None
    db.execute.return_value = execute_result
    return db


def _reservation() -> Reservation:
    return Reservation(
        id_reserva=RESERVA_ID,
        horario_reserva=datetime(2026, 1, 1, tzinfo=timezone.utc),
        num_pessoas=2,
        usuario_id=TURISTA_ID,
        empresa_id=EMPRESA_ID,
    )


def test_given_existing_reservation_when_get_history_then_returns_ordered():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = _reservation()
    msgs = [ReservationMessage(conteudo="oi"), ReservationMessage(conteudo="tudo bem?")]
    db.execute.return_value.scalars.return_value.all.return_value = msgs

    # WHEN
    result = reservation_chat_service.get_history(RESERVA_ID, db)

    # THEN
    assert result == msgs


def test_given_missing_reservation_when_get_history_then_raises_not_found():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = None

    # WHEN / THEN
    with pytest.raises(ReservationNotFoundError):
        reservation_chat_service.get_history(RESERVA_ID, db)


def test_given_limit_when_get_history_then_passes_to_query():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = _reservation()
    msgs = [ReservationMessage(conteudo="oi")]
    db.execute.return_value.scalars.return_value.all.return_value = msgs

    # WHEN
    result = reservation_chat_service.get_history(RESERVA_ID, db, limit=1)

    # THEN
    assert result == msgs
    db.get.assert_not_called()


def test_given_before_id_when_get_history_then_returns_older_reversed():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = _reservation()
    pivot = ReservationMessage(conteudo="pivot", criado_em=datetime.now(timezone.utc))
    db.get.return_value = pivot
    older = [ReservationMessage(conteudo="b"), ReservationMessage(conteudo="a")]
    db.execute.return_value.scalars.return_value.all.return_value = older

    # WHEN
    result = reservation_chat_service.get_history(RESERVA_ID, db, limit=2, before_id=uuid.uuid4())

    # THEN
    assert [m.conteudo for m in result] == ["a", "b"]
    db.get.assert_called_once()


def test_given_tourist_sender_when_send_message_then_persists_as_turista():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = _reservation()

    # WHEN
    reservation_chat_service.send_message(RESERVA_ID, TURISTA_ID, "olá", db)

    # THEN
    db.add.assert_called_once()
    db.commit.assert_called_once()
    saved: ReservationMessage = db.add.call_args[0][0]
    assert saved.tipo_remetente == TipoRemetente.TURISTA
    assert saved.remetente_id == TURISTA_ID
    assert saved.conteudo == "olá"


def test_given_owner_sender_when_send_message_then_persists_as_empreendedor():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = _reservation()
    db.get.return_value = Enterprise(id_empresa=EMPRESA_ID, usuario_id=DONO_ID)

    # WHEN
    reservation_chat_service.send_message(RESERVA_ID, DONO_ID, "bom dia", db)

    # THEN
    saved: ReservationMessage = db.add.call_args[0][0]
    assert saved.tipo_remetente == TipoRemetente.EMPREENDEDOR


def test_given_outsider_sender_when_send_message_then_raises_forbidden():
    # GIVEN
    db = _mock_db()
    db.execute.return_value.scalar_one_or_none.return_value = _reservation()
    db.get.return_value = Enterprise(id_empresa=EMPRESA_ID, usuario_id=DONO_ID)

    # WHEN / THEN
    with pytest.raises(SenderNotInReservationError):
        reservation_chat_service.send_message(RESERVA_ID, uuid.uuid4(), "intruso", db)
    db.add.assert_not_called()
