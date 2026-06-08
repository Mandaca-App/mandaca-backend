import uuid
from unittest.mock import AsyncMock, MagicMock

import groq as groq_sdk
import pytest

from app.models.business_context import BusinessContext
from app.models.chat_message import ChatMessage
from app.services.conversation_summary_service import (
    _CONVERSATION_NOTES_HASH,
    _SUMMARY_MODEL,
    _SUMMARY_THRESHOLD,
    ConversationSummaryService,
)

FAKE_ENTERPRISE_ID = uuid.uuid4()
FAKE_SUMMARY = "Empreendedor quer melhorar vendas; foco em cardapio regional."


def _make_messages(quantity: int) -> list[ChatMessage]:
    return [
        ChatMessage(
            empresa_id=FAKE_ENTERPRISE_ID,
            conteudo_usuario=f"pergunta {i}",
            conteudo_assistente=f"resposta {i}",
        )
        for i in range(quantity)
    ]


def _mock_groq_client(reply: str | None = FAKE_SUMMARY) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.choices[0].message.content = reply
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def _mock_db(
    count: int, messages: list[ChatMessage], notes_row: BusinessContext | None
) -> MagicMock:
    db = MagicMock()
    db.scalar.return_value = count
    scalars_result = MagicMock()
    scalars_result.all.return_value = messages
    scalars_result.first.return_value = notes_row
    db.scalars.return_value = scalars_result
    return db


def _notes_row(notas: str | None = None) -> BusinessContext:
    return BusinessContext(
        empresa_id=FAKE_ENTERPRISE_ID,
        hash_contexto=_CONVERSATION_NOTES_HASH,
        dados_contexto={},
        notas_conversa=notas,
    )


# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_below_threshold_when_maybe_summarize_then_no_groq_call():
    # GIVEN
    client = _mock_groq_client()
    service = ConversationSummaryService(groq_client=client)
    db = _mock_db(count=_SUMMARY_THRESHOLD - 1, messages=[], notes_row=None)

    # WHEN
    await service.maybe_summarize(FAKE_ENTERPRISE_ID, db)

    # THEN
    client.chat.completions.create.assert_not_called()


@pytest.mark.anyio
async def test_given_threshold_reached_when_summarize_then_calls_groq():
    # GIVEN
    client = _mock_groq_client()
    service = ConversationSummaryService(groq_client=client)
    messages = _make_messages(_SUMMARY_THRESHOLD)
    db = _mock_db(count=_SUMMARY_THRESHOLD, messages=messages, notes_row=_notes_row())

    # WHEN
    await service.maybe_summarize(FAKE_ENTERPRISE_ID, db)

    # THEN
    call_kwargs = client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == _SUMMARY_MODEL


# ---------------------------------------------------------------------------
# Persistencia e delecao
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_threshold_reached_when_summarize_then_persists_notes():
    # GIVEN
    client = _mock_groq_client()
    service = ConversationSummaryService(groq_client=client)
    notes_row = _notes_row()
    messages = _make_messages(_SUMMARY_THRESHOLD)
    db = _mock_db(count=_SUMMARY_THRESHOLD, messages=messages, notes_row=notes_row)

    # WHEN
    await service.maybe_summarize(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert notes_row.notas_conversa == FAKE_SUMMARY
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_given_threshold_reached_when_summarize_then_hard_deletes_messages():
    # GIVEN
    client = _mock_groq_client()
    service = ConversationSummaryService(groq_client=client)
    messages = _make_messages(_SUMMARY_THRESHOLD)
    db = _mock_db(count=_SUMMARY_THRESHOLD, messages=messages, notes_row=_notes_row())

    # WHEN
    await service.maybe_summarize(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert db.delete.call_count == _SUMMARY_THRESHOLD


@pytest.mark.anyio
async def test_given_no_notes_row_when_summarize_then_creates_one():
    # GIVEN
    client = _mock_groq_client()
    service = ConversationSummaryService(groq_client=client)
    messages = _make_messages(_SUMMARY_THRESHOLD)
    db = _mock_db(count=_SUMMARY_THRESHOLD, messages=messages, notes_row=None)

    # WHEN
    await service.maybe_summarize(FAKE_ENTERPRISE_ID, db)

    # THEN
    added = db.add.call_args.args[0]
    assert isinstance(added, BusinessContext)
    assert added.hash_contexto == _CONVERSATION_NOTES_HASH


# ---------------------------------------------------------------------------
# Sumarizacao incremental
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_existing_notes_when_summarize_then_feeds_previous_summary():
    # GIVEN
    client = _mock_groq_client()
    service = ConversationSummaryService(groq_client=client)
    notes_row = _notes_row(notas="Resumo antigo da conversa.")
    messages = _make_messages(_SUMMARY_THRESHOLD)
    db = _mock_db(count=_SUMMARY_THRESHOLD, messages=messages, notes_row=notes_row)

    # WHEN
    await service.maybe_summarize(FAKE_ENTERPRISE_ID, db)

    # THEN
    prompt = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "Resumo antigo da conversa." in prompt


# ---------------------------------------------------------------------------
# Isolamento de falha
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_groq_error_when_summarize_then_does_not_raise():
    # GIVEN
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.APITimeoutError(request=MagicMock())
    )
    service = ConversationSummaryService(groq_client=client)
    notes_row = _notes_row()
    messages = _make_messages(_SUMMARY_THRESHOLD)
    db = _mock_db(count=_SUMMARY_THRESHOLD, messages=messages, notes_row=notes_row)

    # WHEN
    await service.maybe_summarize(FAKE_ENTERPRISE_ID, db)

    # THEN
    assert notes_row.notas_conversa is None
    db.delete.assert_not_called()
    db.rollback.assert_called_once()
