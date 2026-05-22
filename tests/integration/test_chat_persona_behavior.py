import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chat_context_service import ChatContextService
from app.services.chat_service import ChatService
from app.services.prompts.consultor_persona import EnterpriseContext

FAKE_ENTERPRISE_ID = uuid.uuid4()
FAKE_USER_ID = uuid.uuid4()


def _response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


def _mock_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    return db


def _context_service() -> MagicMock:
    service = MagicMock(spec=ChatContextService)
    service.build_enterprise_context.return_value = EnterpriseContext(
        enterprise_name="Restaurante Mandacaru",
        category="restaurante",
        city="Caruaru",
        state="PE",
    )
    service.build_context.return_value = ""
    return service


@pytest.mark.anyio
async def test_given_in_scope_question_when_llm_called_then_persona_guides_mandaca_answer():
    # GIVEN
    async def fake_completion(**kwargs):
        system_prompt = kwargs["messages"][0]["content"]
        user_prompt = kwargs["messages"][1]["content"]
        assert "Consultor Mandaca" in system_prompt
        assert "cardapio, fotos, reservas" in system_prompt
        assert "Como melhorar minhas fotos do cardapio?" in user_prompt
        return _response(
            "Oxente, bora caprichar nessas fotos, visse? Na Mandaca, use luz natural, "
            "mostre o prato inteiro e destaque os itens mais pedidos no cardapio."
        )

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_completion)
    service = ChatService(groq_client=client, context_service=_context_service())

    # WHEN
    reply = await service.send_message(
        "Como melhorar minhas fotos do cardapio?",
        FAKE_ENTERPRISE_ID,
        FAKE_USER_ID,
        _mock_db(),
    )

    # THEN
    assert "Mandaca" in reply
    assert "visse" in reply
    assert "cardapio" in reply


@pytest.mark.anyio
async def test_given_out_of_scope_question_when_llm_called_then_persona_refuses_politely():
    # GIVEN
    async def fake_completion(**kwargs):
        system_prompt = kwargs["messages"][0]["content"]
        user_prompt = kwargs["messages"][1]["content"]
        assert "Recusa para fora de escopo" in system_prompt
        assert "Nao forneca a informacao fora de escopo" in system_prompt
        assert "quem ganhou a Copa de 2022?" in user_prompt
        return _response(
            "Opa, essa pergunta foge do que eu consigo ajudar por aqui. "
            "Posso te orientar sobre seu negocio, cardapio, reservas ou a Mandaca."
        )

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_completion)
    service = ChatService(groq_client=client, context_service=_context_service())

    # WHEN
    reply = await service.send_message(
        "quem ganhou a Copa de 2022?",
        FAKE_ENTERPRISE_ID,
        FAKE_USER_ID,
        _mock_db(),
    )

    # THEN
    assert "foge" in reply
    assert "negocio" in reply
    assert "Argentina" not in reply
