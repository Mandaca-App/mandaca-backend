"""
Testes unitários para persistência de histórico de chat (SCRUM-49).

Foco: lógica de persistência de mensagens e consulta de histórico.
Estratégia:
  - Groq API isolada via injecao no construtor de ChatService (DIP).
  - DB usa SQLite in-memory via fixture db (conftest.py).
  - User e Enterprise criados como pré-requisito de FK.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import groq as groq_sdk
import pytest
from sqlalchemy import func, select

from app.core.exceptions import (
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceTimeoutError,
)
from app.models.chat_message import ChatMessage
from app.models.enterprise import Enterprise
from app.models.user import TipoUsuario, User
from app.services.chat_service import ChatService

FAKE_REPLY = "Foque em divulgar seus produtos nas redes sociais locais."
FAKE_MESSAGE = "Como melhorar minhas vendas?"


def _mock_groq_client(reply: str = FAKE_REPLY) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.choices[0].message.content = reply
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def _create_enterprise(db, enterprise_id: uuid.UUID | None = None) -> Enterprise:
    """Cria User + Enterprise no banco para satisfazer as FK de mensagens_chat."""
    user = User(
        tipo_usuario=TipoUsuario.EMPREENDEDOR,
        nome="Empreendedor Teste",
        cpf=str(uuid.uuid4().int)[:11],
    )
    db.add(user)
    db.flush()

    empresa = Enterprise(
        id_empresa=enterprise_id or uuid.uuid4(),
        nome=f"Empresa {uuid.uuid4().hex[:6]}",
        usuario_id=user.id_usuario,
    )
    db.add(empresa)
    db.commit()
    return empresa


# ---------------------------------------------------------------------------
# Persistência ao enviar mensagem
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_given_valid_message_when_sent_then_persists_chat_message(db):
    # GIVEN
    empresa = _create_enterprise(db)
    service = ChatService(groq_client=_mock_groq_client())

    # WHEN
    await service.send_message(FAKE_MESSAGE, empresa.id_empresa, db)

    # THEN
    saved = db.scalars(
        select(ChatMessage).where(ChatMessage.empresa_id == empresa.id_empresa)
    ).first()
    assert saved is not None
    assert saved.conteudo_usuario == FAKE_MESSAGE
    assert saved.conteudo_assistente == FAKE_REPLY


@pytest.mark.anyio
async def test_given_valid_message_when_sent_then_reply_matches_groq_response(db):
    # GIVEN
    empresa = _create_enterprise(db)
    service = ChatService(groq_client=_mock_groq_client())

    # WHEN
    result = await service.send_message(FAKE_MESSAGE, empresa.id_empresa, db)

    # THEN
    assert result == FAKE_REPLY


@pytest.mark.anyio
async def test_given_rate_limit_error_when_sent_then_does_not_persist(db):
    # GIVEN
    empresa = _create_enterprise(db)
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.RateLimitError("rate limit", response=MagicMock(), body=None)
    )
    service = ChatService(groq_client=mock_client)

    # WHEN / THEN
    with pytest.raises(ChatRateLimitError):
        await service.send_message(FAKE_MESSAGE, empresa.id_empresa, db)

    assert db.scalar(select(func.count(ChatMessage.id_mensagem))) == 0


@pytest.mark.anyio
async def test_given_timeout_error_when_sent_then_does_not_persist(db):
    # GIVEN
    empresa = _create_enterprise(db)
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.APITimeoutError(request=MagicMock())
    )
    service = ChatService(groq_client=mock_client)

    # WHEN / THEN
    with pytest.raises(ChatServiceTimeoutError):
        await service.send_message(FAKE_MESSAGE, empresa.id_empresa, db)

    assert db.scalar(select(func.count(ChatMessage.id_mensagem))) == 0


@pytest.mark.anyio
async def test_given_connection_error_when_sent_then_does_not_persist(db):
    # GIVEN
    empresa = _create_enterprise(db)
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=groq_sdk.APIConnectionError(request=MagicMock())
    )
    service = ChatService(groq_client=mock_client)

    # WHEN / THEN
    with pytest.raises(ChatServiceConnectionError):
        await service.send_message(FAKE_MESSAGE, empresa.id_empresa, db)

    assert db.scalar(select(func.count(ChatMessage.id_mensagem))) == 0


@pytest.mark.anyio
async def test_given_db_failure_after_groq_when_committing_then_rolls_back(db):
    # GIVEN
    empresa = _create_enterprise(db)
    service = ChatService(groq_client=_mock_groq_client())

    with patch.object(db, "commit", side_effect=Exception("DB unavailable")):
        with patch.object(db, "rollback") as mock_rollback:
            # WHEN / THEN
            with pytest.raises(Exception, match="DB unavailable"):
                await service.send_message(FAKE_MESSAGE, empresa.id_empresa, db)

    mock_rollback.assert_called_once()


# ---------------------------------------------------------------------------
# Consulta de histórico
# ---------------------------------------------------------------------------


def test_given_valid_enterprise_when_history_requested_then_returns_messages(db):
    # GIVEN
    empresa = _create_enterprise(db)
    msg = ChatMessage(
        empresa_id=empresa.id_empresa,
        conteudo_usuario=FAKE_MESSAGE,
        conteudo_assistente=FAKE_REPLY,
    )
    db.add(msg)
    db.commit()
    service = ChatService()

    # WHEN
    result = service.get_chat_history(empresa.id_empresa, db)

    # THEN
    assert len(result) == 1
    assert result[0].conteudo_usuario == FAKE_MESSAGE
    assert result[0].conteudo_assistente == FAKE_REPLY


def test_given_empty_history_when_requested_then_returns_empty_list(db):
    # GIVEN
    empresa = _create_enterprise(db)
    service = ChatService()

    # WHEN
    result = service.get_chat_history(empresa.id_empresa, db)

    # THEN
    assert result == []


def test_given_soft_deleted_message_when_history_requested_then_not_returned(db):
    # GIVEN
    empresa = _create_enterprise(db)
    msg = ChatMessage(
        empresa_id=empresa.id_empresa,
        conteudo_usuario=FAKE_MESSAGE,
        conteudo_assistente=FAKE_REPLY,
        deleted_at=datetime.now(timezone.utc),
    )
    db.add(msg)
    db.commit()
    service = ChatService()

    # WHEN
    result = service.get_chat_history(empresa.id_empresa, db)

    # THEN
    assert result == []


def test_given_multiple_enterprises_when_history_requested_then_isolates_by_enterprise(db):
    # GIVEN
    empresa_a = _create_enterprise(db)
    empresa_b = _create_enterprise(db)
    msg_a = ChatMessage(
        empresa_id=empresa_a.id_empresa,
        conteudo_usuario="Pergunta A",
        conteudo_assistente="Resposta A",
    )
    msg_b = ChatMessage(
        empresa_id=empresa_b.id_empresa,
        conteudo_usuario="Pergunta B",
        conteudo_assistente="Resposta B",
    )
    db.add_all([msg_a, msg_b])
    db.commit()
    service = ChatService()

    # WHEN
    result = service.get_chat_history(empresa_a.id_empresa, db)

    # THEN
    assert len(result) == 1
    assert result[0].empresa_id == empresa_a.id_empresa


def test_given_multiple_messages_when_history_requested_then_returns_ordered_by_date(db):
    # GIVEN
    empresa = _create_enterprise(db)
    msg1 = ChatMessage(
        empresa_id=empresa.id_empresa,
        conteudo_usuario="Primeira pergunta",
        conteudo_assistente="Primeira resposta",
        criado_em=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    msg2 = ChatMessage(
        empresa_id=empresa.id_empresa,
        conteudo_usuario="Segunda pergunta",
        conteudo_assistente="Segunda resposta",
        criado_em=datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
    )
    db.add_all([msg2, msg1])
    db.commit()
    service = ChatService()

    # WHEN
    result = service.get_chat_history(empresa.id_empresa, db)

    # THEN
    assert result[0].conteudo_usuario == "Primeira pergunta"
    assert result[1].conteudo_usuario == "Segunda pergunta"
    assert result[0].criado_em < result[1].criado_em
