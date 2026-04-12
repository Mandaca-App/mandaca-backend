"""
Testes smoke para o endpoint de chat (app/routers/chat.py).

Foco: verificar wire-up HTTP correto (roteamento, serialização, status codes).
Estratégia: ChatService.send_message completamente mockado; lógica de negócio
é coberta em test_chat_service.py.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.exceptions import (
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceError,
    ChatServiceTimeoutError,
)
from app.main import app
from app.services.chat_service import ChatService

client = TestClient(app, raise_server_exceptions=False)

FAKE_UUID = "00000000-0000-0000-0000-000000000001"
_VALID_BODY = {"enterprise_id": FAKE_UUID, "message": "Como melhorar minhas vendas?"}
_FAKE_REPLY = "Foque em divulgar seus produtos nas redes sociais locais."


# ---------------------------------------------------------------------------
# Caminho feliz
# ---------------------------------------------------------------------------


def test_given_valid_body_when_message_sent_then_returns_200_with_reply():
    # GIVEN
    with patch.object(ChatService, "send_message", new=AsyncMock(return_value=_FAKE_REPLY)):
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 200
    assert response.json()["reply"] == _FAKE_REPLY


# ---------------------------------------------------------------------------
# Validacao de schema (422)
# ---------------------------------------------------------------------------


def test_given_missing_enterprise_id_when_message_sent_then_returns_422():
    # GIVEN
    body = {"message": "Qualquer pergunta"}

    # WHEN
    response = client.post("/chat/message", json=body)

    # THEN
    assert response.status_code == 422


def test_given_invalid_uuid_when_message_sent_then_returns_422():
    # GIVEN
    body = {"enterprise_id": "nao-e-um-uuid", "message": "Qualquer pergunta"}

    # WHEN
    response = client.post("/chat/message", json=body)

    # THEN
    assert response.status_code == 422


def test_given_missing_message_when_message_sent_then_returns_422():
    # GIVEN
    body = {"enterprise_id": FAKE_UUID}

    # WHEN
    response = client.post("/chat/message", json=body)

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Excecoes do service → status codes HTTP
# ---------------------------------------------------------------------------


def test_given_rate_limit_when_message_sent_then_returns_429():
    # GIVEN
    with patch.object(ChatService, "send_message", new=AsyncMock(side_effect=ChatRateLimitError())):
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 429


def test_given_timeout_when_message_sent_then_returns_504():
    # GIVEN
    with patch.object(
        ChatService, "send_message", new=AsyncMock(side_effect=ChatServiceTimeoutError())
    ):
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 504


def test_given_connection_error_when_message_sent_then_returns_502():
    # GIVEN
    with patch.object(
        ChatService, "send_message", new=AsyncMock(side_effect=ChatServiceConnectionError())
    ):
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 502


def test_given_api_status_error_when_message_sent_then_returns_502():
    # GIVEN
    with patch.object(ChatService, "send_message", new=AsyncMock(side_effect=ChatServiceError())):
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 502
