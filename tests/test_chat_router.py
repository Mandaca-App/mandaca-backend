"""
Testes smoke para os endpoints de chat (app/routers/chat.py).

Foco: verificar wire-up HTTP correto (roteamento, serialização, status codes).
Estratégia: ChatService e get_chat_history completamente mockados; lógica de
negócio é coberta em test_chat_service.py e test_chat_history_service.py.

Convenção de TestClient:
  - Caminho feliz (200): TestClient(app) — exceções inesperadas do servidor
    aparecem como falhas explícitas no teste.
  - Caminhos de erro (4xx/5xx): TestClient(app, raise_server_exceptions=False)
    — evita que o handler de exceção de domínio quebre o cliente de teste.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.exceptions import (
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceError,
    ChatServiceTimeoutError,
)
from app.main import app
from app.services.chat_service import ChatService

FAKE_UUID = "00000000-0000-0000-0000-000000000001"
_VALID_BODY = {"empresa_id": FAKE_UUID, "mensagem": "Como melhorar minhas vendas?"}
_FAKE_REPLY = "Foque em divulgar seus produtos nas redes sociais locais."

_FAKE_HISTORY = [
    MagicMock(
        id_mensagem=uuid.UUID(FAKE_UUID),
        empresa_id=uuid.UUID(FAKE_UUID),
        conteudo_usuario="Pergunta",
        conteudo_assistente="Resposta",
        criado_em=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
]


# ---------------------------------------------------------------------------
# POST /chat/message — caminho feliz
# ---------------------------------------------------------------------------


def test_given_valid_body_when_message_sent_then_returns_200_with_reply():
    # GIVEN
    with patch.object(ChatService, "send_message", new=AsyncMock(return_value=_FAKE_REPLY)):
        client = TestClient(app)
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == _FAKE_REPLY
    assert len(body) == 1


# ---------------------------------------------------------------------------
# POST /chat/message — validacao de schema (422)
# ---------------------------------------------------------------------------


def test_given_missing_enterprise_id_when_message_sent_then_returns_422():
    # GIVEN
    client = TestClient(app, raise_server_exceptions=False)

    # WHEN
    response = client.post("/chat/message", json={"mensagem": "Qualquer pergunta"})

    # THEN
    assert response.status_code == 422


def test_given_invalid_uuid_when_message_sent_then_returns_422():
    # GIVEN
    client = TestClient(app, raise_server_exceptions=False)

    # WHEN
    response = client.post(
        "/chat/message", json={"empresa_id": "nao-e-um-uuid", "mensagem": "Qualquer pergunta"}
    )

    # THEN
    assert response.status_code == 422


def test_given_missing_message_when_message_sent_then_returns_422():
    # GIVEN
    client = TestClient(app, raise_server_exceptions=False)

    # WHEN
    response = client.post("/chat/message", json={"empresa_id": FAKE_UUID})

    # THEN
    assert response.status_code == 422


def test_given_whitespace_only_message_when_sent_then_returns_422():
    # GIVEN
    client = TestClient(app, raise_server_exceptions=False)

    # WHEN
    response = client.post("/chat/message", json={"empresa_id": FAKE_UUID, "mensagem": "   "})

    # THEN
    assert response.status_code == 422


def test_given_message_over_max_length_when_sent_then_returns_422():
    # GIVEN
    client = TestClient(app, raise_server_exceptions=False)
    body = {"empresa_id": FAKE_UUID, "mensagem": "x" * 2001}

    # WHEN
    response = client.post("/chat/message", json=body)

    # THEN
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /chat/message — excecoes do service -> status codes HTTP
# ---------------------------------------------------------------------------


def test_given_rate_limit_when_message_sent_then_returns_429():
    # GIVEN
    with patch.object(ChatService, "send_message", new=AsyncMock(side_effect=ChatRateLimitError())):
        client = TestClient(app, raise_server_exceptions=False)
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 429


def test_given_timeout_when_message_sent_then_returns_504():
    # GIVEN
    with patch.object(
        ChatService, "send_message", new=AsyncMock(side_effect=ChatServiceTimeoutError())
    ):
        client = TestClient(app, raise_server_exceptions=False)
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 504


def test_given_connection_error_when_message_sent_then_returns_502():
    # GIVEN
    with patch.object(
        ChatService, "send_message", new=AsyncMock(side_effect=ChatServiceConnectionError())
    ):
        client = TestClient(app, raise_server_exceptions=False)
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 502


def test_given_api_status_error_when_message_sent_then_returns_502():
    # GIVEN
    with patch.object(ChatService, "send_message", new=AsyncMock(side_effect=ChatServiceError())):
        client = TestClient(app, raise_server_exceptions=False)
        # WHEN
        response = client.post("/chat/message", json=_VALID_BODY)

    # THEN
    assert response.status_code == 502


# ---------------------------------------------------------------------------
# GET /chat/history/{enterprise_id} — caminho feliz
# ---------------------------------------------------------------------------


def test_given_valid_enterprise_when_history_requested_then_returns_200():
    # GIVEN
    with patch.object(ChatService, "get_chat_history", return_value=_FAKE_HISTORY):
        client = TestClient(app)
        # WHEN
        response = client.get(f"/chat/history/{FAKE_UUID}")

    # THEN
    assert response.status_code == 200
    body = response.json()
    assert "historico" in body
    assert len(body["historico"]) == 1
    assert body["historico"][0]["conteudo_usuario"] == "Pergunta"


def test_given_empty_history_when_requested_then_returns_200_with_empty_list():
    # GIVEN
    with patch.object(ChatService, "get_chat_history", return_value=[]):
        client = TestClient(app)
        # WHEN
        response = client.get(f"/chat/history/{FAKE_UUID}")

    # THEN
    assert response.status_code == 200
    assert response.json() == {"historico": []}


def test_given_nonexistent_enterprise_when_history_requested_then_returns_200_empty():
    # GIVEN — empresa_id valido mas sem mensagens: contrato e 200 + lista vazia, nao 404
    with patch.object(ChatService, "get_chat_history", return_value=[]):
        client = TestClient(app)
        nonexistent_id = "00000000-0000-0000-0000-000000000099"
        # WHEN
        response = client.get(f"/chat/history/{nonexistent_id}")

    # THEN
    assert response.status_code == 200
    assert response.json() == {"historico": []}


# ---------------------------------------------------------------------------
# GET /chat/history/{enterprise_id} — validacao de path (422)
# ---------------------------------------------------------------------------


def test_given_invalid_uuid_when_history_requested_then_returns_422():
    # GIVEN
    client = TestClient(app, raise_server_exceptions=False)

    # WHEN
    response = client.get("/chat/history/nao-e-um-uuid")

    # THEN
    assert response.status_code == 422
