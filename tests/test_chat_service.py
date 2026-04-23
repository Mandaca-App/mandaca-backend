import uuid
from unittest.mock import AsyncMock, MagicMock

import groq as groq_sdk
import pytest

from app.core.exceptions import (
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceError,
    ChatServiceTimeoutError,
)
from app.services.chat_context_service import ChatContextService
from app.services.chat_service import _CHAT_MODEL, ChatService

FAKE_REPLY = "Para melhorar suas vendas, comece identificando seu público-alvo."
FAKE_ENTERPRISE_ID = uuid.uuid4()


def _mock_groq_client(reply: str | None = FAKE_REPLY) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.choices[0].message.content = reply
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def _mock_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    return db


def _mock_context_service(context: str = "") -> MagicMock:
    svc = MagicMock(spec=ChatContextService)
    svc.build_context.return_value = context
    return svc


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_message_when_sent_then_returns_reply():
    # GIVEN
    service = ChatService(groq_client=_mock_groq_client(), context_service=_mock_context_service())
    db = _mock_db()

    # WHEN
    result = await service.send_message("Como melhorar minhas vendas?", FAKE_ENTERPRISE_ID, db)

    # THEN
    assert result == FAKE_REPLY


@pytest.mark.anyio
async def test_given_valid_message_when_sent_then_uses_versatile_model():
    # GIVEN
    mock_client = _mock_groq_client()
    service = ChatService(groq_client=mock_client, context_service=_mock_context_service())
    db = _mock_db()

    # WHEN
    await service.send_message("Qual o melhor horário para abrir?", FAKE_ENTERPRISE_ID, db)

    # THEN
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == _CHAT_MODEL


@pytest.mark.anyio
async def test_given_valid_message_when_sent_then_includes_system_prompt():
    # GIVEN
    mock_client = _mock_groq_client()
    service = ChatService(groq_client=mock_client, context_service=_mock_context_service())
    db = _mock_db()

    # WHEN
    await service.send_message("Como formalizar meu negócio?", FAKE_ENTERPRISE_ID, db)

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
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.RateLimitError("rate limit", response=MagicMock(), body=None)
    )
    service = ChatService(groq_client=mock_client, context_service=_mock_context_service())
    db = _mock_db()

    # WHEN / THEN
    with pytest.raises(ChatRateLimitError) as exc_info:
        await service.send_message("Qualquer mensagem", FAKE_ENTERPRISE_ID, db)

    assert "Tente novamente" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_timeout_when_sent_then_raises_chat_service_timeout():
    # GIVEN
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.APITimeoutError(request=MagicMock())
    )
    service = ChatService(groq_client=mock_client, context_service=_mock_context_service())
    db = _mock_db()

    # WHEN / THEN
    with pytest.raises(ChatServiceTimeoutError) as exc_info:
        await service.send_message("Qualquer mensagem", FAKE_ENTERPRISE_ID, db)

    assert "demorou demais" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_connection_error_when_sent_then_raises_connection_error():
    # GIVEN
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.APIConnectionError(request=MagicMock())
    )
    service = ChatService(groq_client=mock_client, context_service=_mock_context_service())
    db = _mock_db()

    # WHEN / THEN
    with pytest.raises(ChatServiceConnectionError) as exc_info:
        await service.send_message("Qualquer mensagem", FAKE_ENTERPRISE_ID, db)

    assert "conectar" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_api_status_error_when_sent_then_raises_chat_service_error():
    # GIVEN
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.InternalServerError(
            "Internal Server Error", response=MagicMock(), body=None
        )
    )
    service = ChatService(groq_client=mock_client, context_service=_mock_context_service())
    db = _mock_db()

    # WHEN / THEN
    with pytest.raises(ChatServiceError) as exc_info:
        await service.send_message("Qualquer mensagem", FAKE_ENTERPRISE_ID, db)

    assert "inesperado" in str(exc_info.value)


@pytest.mark.anyio
async def test_given_none_content_when_groq_returns_then_returns_empty_string():
    # GIVEN
    service = ChatService(
        groq_client=_mock_groq_client(reply=None), context_service=_mock_context_service()
    )
    db = _mock_db()

    # WHEN
    result = await service.send_message("Qualquer mensagem", FAKE_ENTERPRISE_ID, db)

    # THEN
    assert result == ""


# ---------------------------------------------------------------------------
# RAG: injecao de contexto no system prompt
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_context_available_when_message_sent_then_context_injected_in_system_prompt():
    # GIVEN
    fake_context = "=== CONTEXTO DO ESTABELECIMENTO ===\nNome: Barraca da Dona Maria\n==="
    mock_client = _mock_groq_client()
    service = ChatService(
        groq_client=mock_client,
        context_service=_mock_context_service(context=fake_context),
    )
    db = _mock_db()

    # WHEN
    await service.send_message("Como melhorar minhas vendas?", FAKE_ENTERPRISE_ID, db)

    # THEN
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_message = call_kwargs["messages"][0]
    assert system_message["role"] == "system"
    assert fake_context in system_message["content"]


@pytest.mark.anyio
async def test_given_empty_context_when_message_sent_then_system_prompt_unchanged():
    # GIVEN
    mock_client = _mock_groq_client()
    service = ChatService(groq_client=mock_client, context_service=_mock_context_service())
    db = _mock_db()

    # WHEN
    await service.send_message("Qualquer mensagem", FAKE_ENTERPRISE_ID, db)

    # THEN
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_content = call_kwargs["messages"][0]["content"]
    assert "===" not in system_content
