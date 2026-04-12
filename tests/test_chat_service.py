from unittest.mock import AsyncMock, MagicMock, patch

import groq as groq_sdk
import pytest

from app.core.exceptions import (
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceError,
    ChatServiceTimeoutError,
)
from app.services.chat_service import _CHAT_MODEL, ChatService

FAKE_REPLY = "Para melhorar suas vendas, comece identificando seu público-alvo."


def _mock_groq_client(reply: str | None = FAKE_REPLY) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.choices[0].message.content = reply
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_message_when_sent_then_returns_reply():
    # GIVEN
    service = ChatService()

    # WHEN
    with patch("app.services.chat_service.AsyncGroq", return_value=_mock_groq_client()):
        result = await service.send_message("Como melhorar minhas vendas?")

    # THEN
    assert result == FAKE_REPLY


@pytest.mark.anyio
async def test_given_valid_message_when_sent_then_uses_versatile_model():
    # GIVEN
    service = ChatService()
    mock_client = _mock_groq_client()

    # WHEN
    with patch("app.services.chat_service.AsyncGroq", return_value=mock_client):
        await service.send_message("Qual o melhor horário para abrir?")

    # THEN
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == _CHAT_MODEL


@pytest.mark.anyio
async def test_given_valid_message_when_sent_then_includes_system_prompt():
    # GIVEN
    service = ChatService()
    mock_client = _mock_groq_client()

    # WHEN
    with patch("app.services.chat_service.AsyncGroq", return_value=mock_client):
        await service.send_message("Como formalizar meu negócio?")

    # THEN
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


# ---------------------------------------------------------------------------
# Excecoes de infraestrutura
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_rate_limit_when_sent_then_raises_chat_rate_limit():
    # GIVEN
    service = ChatService()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.RateLimitError("rate limit", response=MagicMock(), body=None)
    )

    # WHEN / THEN
    with patch("app.services.chat_service.AsyncGroq", return_value=mock_client):
        with pytest.raises(ChatRateLimitError) as exc_info:
            await service.send_message("Qualquer mensagem")

    assert "Tente novamente" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_timeout_when_sent_then_raises_chat_service_timeout():
    # GIVEN
    service = ChatService()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.APITimeoutError(request=MagicMock())
    )

    # WHEN / THEN
    with patch("app.services.chat_service.AsyncGroq", return_value=mock_client):
        with pytest.raises(ChatServiceTimeoutError) as exc_info:
            await service.send_message("Qualquer mensagem")

    assert "demorou demais" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_connection_error_when_sent_then_raises_connection_error():
    # GIVEN
    service = ChatService()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.APIConnectionError(request=MagicMock())
    )

    # WHEN / THEN
    with patch("app.services.chat_service.AsyncGroq", return_value=mock_client):
        with pytest.raises(ChatServiceConnectionError) as exc_info:
            await service.send_message("Qualquer mensagem")

    assert "conectar" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_api_status_error_when_sent_then_raises_chat_service_error():
    # GIVEN
    service = ChatService()
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.InternalServerError(
            "Internal Server Error", response=MagicMock(), body=None
        )
    )

    # WHEN / THEN
    with patch("app.services.chat_service.AsyncGroq", return_value=mock_client):
        with pytest.raises(ChatServiceError) as exc_info:
            await service.send_message("Qualquer mensagem")

    assert "inesperado" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_none_content_when_groq_returns_then_returns_empty_string():
    # GIVEN
    service = ChatService()
    mock_client = _mock_groq_client(reply=None)

    # WHEN
    with patch("app.services.chat_service.AsyncGroq", return_value=mock_client):
        result = await service.send_message("Qualquer mensagem")

    # THEN
    assert result == ""
