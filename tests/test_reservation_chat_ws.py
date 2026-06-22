"""Testes BDD para o endpoint WebSocket do chat de reservas.

Conexão escopada por reserva, validação de pertencimento, broadcast e
persistência. Usa TestClient.websocket_connect + DB SQLite in-memory.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy import select

from app.models.enterprise import Enterprise
from app.models.reservation import Reservation
from app.models.reservation_message import ReservationMessage
from app.models.user import TipoUsuario, User


def _seed(db):
    turista = User(nome="Turista", cpf=str(uuid.uuid4().int)[:11], tipo_usuario=TipoUsuario.TURISTA)
    dono = User(nome="Dono", cpf=str(uuid.uuid4().int)[:11], tipo_usuario=TipoUsuario.TURISTA)
    db.add_all([turista, dono])
    db.flush()

    empresa = Enterprise(nome=f"Empresa {uuid.uuid4()}", usuario_id=dono.id_usuario)
    db.add(empresa)
    db.flush()

    reserva = Reservation(
        horario_reserva=datetime(2026, 1, 1, tzinfo=timezone.utc),
        num_pessoas=2,
        usuario_id=turista.id_usuario,
        empresa_id=empresa.id_empresa,
    )
    db.add(reserva)
    db.commit()
    return reserva, turista, dono


def test_given_tourist_when_connect_then_accepts(client, db):
    # GIVEN
    reserva, turista, _ = _seed(db)

    # WHEN / THEN
    url = f"/chat/{reserva.id_reserva}/ws?remetente_id={turista.id_usuario}"
    with client.websocket_connect(url):
        pass


def test_given_outsider_when_connect_then_closes_1008(client, db):
    # GIVEN
    reserva, _, _ = _seed(db)
    outsider = uuid.uuid4()

    # WHEN / THEN
    url = f"/chat/{reserva.id_reserva}/ws?remetente_id={outsider}"
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(url) as ws:
            ws.receive_json()


def test_given_missing_reservation_when_connect_then_closes_1008(client, db):
    # GIVEN
    url = f"/chat/{uuid.uuid4()}/ws?remetente_id={uuid.uuid4()}"

    # WHEN / THEN
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(url) as ws:
            ws.receive_json()


def test_given_message_sent_when_broadcast_then_both_clients_receive(client, db):
    # GIVEN
    reserva, turista, dono = _seed(db)
    rid = reserva.id_reserva
    turista_url = f"/chat/{rid}/ws?remetente_id={turista.id_usuario}"
    dono_url = f"/chat/{rid}/ws?remetente_id={dono.id_usuario}"

    # WHEN
    with client.websocket_connect(turista_url) as ws_turista:
        with client.websocket_connect(dono_url) as ws_dono:
            ws_turista.send_json({"conteudo": "ola"})

            # THEN
            received_turista = ws_turista.receive_json()
            received_dono = ws_dono.receive_json()

    assert received_turista["conteudo"] == "ola"
    assert received_turista["tipo_remetente"] == "turista"
    assert received_dono["conteudo"] == "ola"


def test_given_message_sent_when_persisted_then_stored_in_db(client, db):
    # GIVEN
    reserva, turista, _ = _seed(db)
    url = f"/chat/{reserva.id_reserva}/ws?remetente_id={turista.id_usuario}"

    # WHEN
    with client.websocket_connect(url) as ws:
        ws.send_json({"conteudo": "mensagem persistida"})
        ws.receive_json()

    # THEN
    stored = db.scalars(
        select(ReservationMessage).where(ReservationMessage.reserva_id == reserva.id_reserva)
    ).all()
    assert len(stored) == 1
    assert stored[0].conteudo == "mensagem persistida"
