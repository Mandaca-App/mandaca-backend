"""Testes smoke para os endpoints de chat de reservas (app/routers/reservation_chat.py).

Foco: wire-up HTTP (roteamento, status codes, serialização). O service é mockado;
a lógica de negócio é coberta em test_reservation_chat_service.py.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.exceptions import ReservationNotFoundError, SenderNotInReservationError
from app.main import app
from app.models.reservation_message import ReservationMessage, TipoRemetente

client = TestClient(app, raise_server_exceptions=False)

RESERVA_ID = uuid.uuid4()
REMETENTE_ID = uuid.uuid4()


def _message() -> ReservationMessage:
    return ReservationMessage(
        id_mensagem=uuid.uuid4(),
        reserva_id=RESERVA_ID,
        remetente_id=REMETENTE_ID,
        tipo_remetente=TipoRemetente.TURISTA,
        conteudo="olá",
        criado_em=datetime.now(timezone.utc),
    )


def test_given_messages_exist_when_list_then_returns_200():
    # GIVEN
    with patch(
        "app.services.reservation_chat_service.get_history",
        return_value=[_message()],
    ):
        # WHEN
        response = client.get(f"/chat/{RESERVA_ID}/messages")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["conteudo"] == "olá"
    assert data[0]["tipo_remetente"] == "turista"


def test_given_missing_reservation_when_list_then_returns_404():
    # GIVEN
    with patch(
        "app.services.reservation_chat_service.get_history",
        side_effect=ReservationNotFoundError(RESERVA_ID),
    ):
        # WHEN
        response = client.get(f"/chat/{RESERVA_ID}/messages")

    # THEN
    assert response.status_code == 404


def test_given_valid_payload_when_send_then_returns_201():
    # GIVEN
    with patch(
        "app.services.reservation_chat_service.send_message",
        return_value=_message(),
    ):
        # WHEN
        response = client.post(
            f"/chat/{RESERVA_ID}/messages",
            json={"remetente_id": str(REMETENTE_ID), "conteudo": "olá"},
        )

    # THEN
    assert response.status_code == 201
    assert response.json()["conteudo"] == "olá"


def test_given_outsider_sender_when_send_then_returns_403():
    # GIVEN
    with patch(
        "app.services.reservation_chat_service.send_message",
        side_effect=SenderNotInReservationError(REMETENTE_ID),
    ):
        # WHEN
        response = client.post(
            f"/chat/{RESERVA_ID}/messages",
            json={"remetente_id": str(REMETENTE_ID), "conteudo": "intruso"},
        )

    # THEN
    assert response.status_code == 403


def test_given_blank_content_when_send_then_returns_422():
    # WHEN
    response = client.post(
        f"/chat/{RESERVA_ID}/messages",
        json={"remetente_id": str(REMETENTE_ID), "conteudo": "   "},
    )

    # THEN
    assert response.status_code == 422
