import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ChatbotNotFoundError, DuplicateChatbotTypeError
from app.models.chatbot_ajuda import Chatbot, ChatbotKind, KnowledgeModuleType
from app.schemas.chatbot_ajuda import ChatbotCreate, ChatbotMessageCreate, KnowledgeModuleCreate
from app.services.chatbot_ajuda_service import ChatbotAjudaService

FAKE_REPLY = "1. Abra o cardapio. 2. Edite o prato. 3. Envie uma foto image/*."


def _response(content: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


def _mock_groq_client(reply: str | None = FAKE_REPLY) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=_response(reply))
    return client


def _create_chatbot(db, tipo: ChatbotKind = ChatbotKind.AJUDA, ativo: bool = True) -> Chatbot:
    chatbot = Chatbot(tipo=tipo, nome=f"Chatbot {tipo.value}", ativo=ativo)
    db.add(chatbot)
    db.commit()
    db.refresh(chatbot)
    return chatbot


def test_given_chatbot_payload_when_create_then_persists_base_entity(db):
    service = ChatbotAjudaService()

    chatbot = service.create_chatbot(
        db,
        ChatbotCreate(
            tipo=ChatbotKind.AJUDA,
            nome="Chatbot de Ajuda",
            descricao="Base da Central de Ajuda",
        ),
    )

    assert chatbot.tipo == ChatbotKind.AJUDA
    assert chatbot.ativo is True
    assert db.scalar(select(func.count()).select_from(Chatbot)) == 1


def test_given_existing_type_when_create_then_raises_duplicate(db):
    service = ChatbotAjudaService()
    _create_chatbot(db, tipo=ChatbotKind.AJUDA)

    with pytest.raises(DuplicateChatbotTypeError):
        service.create_chatbot(
            db,
            ChatbotCreate(tipo=ChatbotKind.AJUDA, nome="Outro chatbot"),
        )


@pytest.mark.anyio
async def test_given_dynamic_modules_when_message_sent_then_injects_filtered_knowledge(db):
    async def fake_completion(**kwargs):
        system_prompt = kwargs["messages"][0]["content"]
        user_prompt = kwargs["messages"][1]["content"]

        assert "Dicas para fotos do cardapio" in system_prompt
        assert "Fluxo de reservas" not in system_prompt
        assert "inativo" not in system_prompt
        assert "Cardapio e fotos dos pratos" in system_prompt
        assert "Como melhorar fotos do cardapio?" in user_prompt
        return _response("Use uma foto clara, em formato de imagem, ao editar o prato.")

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_completion)
    service = ChatbotAjudaService(groq_client=client)
    chatbot = _create_chatbot(db)
    service.create_module(
        db,
        chatbot.id_chatbot,
        KnowledgeModuleCreate(
            topico="cardapio",
            tipo=KnowledgeModuleType.TUTORIAL,
            conteudo="Dicas para fotos do cardapio",
            ordem=2,
        ),
    )
    service.create_module(
        db,
        chatbot.id_chatbot,
        KnowledgeModuleCreate(
            topico="reserva",
            tipo=KnowledgeModuleType.FAQ,
            conteudo="Fluxo de reservas",
            ordem=1,
        ),
    )
    service.create_module(
        db,
        chatbot.id_chatbot,
        KnowledgeModuleCreate(
            topico="inativo",
            tipo=KnowledgeModuleType.GERAL,
            ativo=False,
        ),
    )

    reply = await service.send_message(
        db,
        ChatbotKind.AJUDA,
        ChatbotMessageCreate(
            empresa_id=uuid.uuid4(),
            usuario_id=uuid.uuid4(),
            mensagem="Como melhorar fotos do cardapio?",
            topicos=["cardapio"],
        ),
    )

    assert "foto clara" in reply
    assert "prato" in reply


@pytest.mark.anyio
async def test_given_development_feature_when_message_sent_then_prompt_prevents_hallucination(db):
    async def fake_completion(**kwargs):
        system_prompt = kwargs["messages"][0]["content"]
        user_prompt = kwargs["messages"][1]["content"]

        assert "funcionalidade com status em_desenvolvimento" in system_prompt
        assert "Nunca alucine fluxo de uso" in system_prompt
        assert "delivery" in user_prompt
        return _response(
            "Esse recurso ainda nao aparece na base atual da Mandaca. "
            "A equipe esta trabalhando para ampliar os tutoriais e funcionalidades."
        )

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_completion)
    service = ChatbotAjudaService(groq_client=client)
    _create_chatbot(db)

    reply = await service.send_message(
        db,
        ChatbotKind.AJUDA,
        ChatbotMessageCreate(mensagem="Como configuro delivery pelo app?"),
    )

    assert "base atual" in reply
    assert "trabalhando" in reply


@pytest.mark.anyio
async def test_given_out_of_scope_question_when_message_sent_then_prompt_guides_refusal(db):
    async def fake_completion(**kwargs):
        system_prompt = kwargs["messages"][0]["content"]
        user_prompt = kwargs["messages"][1]["content"]

        assert "Fallback fora do escopo" in system_prompt
        assert "Nao forneca a resposta fora de escopo" in system_prompt
        assert "quem ganhou a Copa de 2022?" in user_prompt
        return _response(
            "Sou o assistente do aplicativo Mandaca. Posso te ajudar com cardapio, "
            "fotos, reservas, relatorios ou tutoriais do seu estabelecimento."
        )

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_completion)
    service = ChatbotAjudaService(groq_client=client)
    _create_chatbot(db)

    reply = await service.send_message(
        db,
        ChatbotKind.AJUDA,
        ChatbotMessageCreate(mensagem="quem ganhou a Copa de 2022?"),
    )

    assert "Mandaca" in reply
    assert "cardapio" in reply
    assert "Argentina" not in reply


@pytest.mark.anyio
async def test_given_none_content_when_llm_returns_then_returns_empty_string(db):
    service = ChatbotAjudaService(groq_client=_mock_groq_client(reply=None))
    _create_chatbot(db)

    reply = await service.send_message(
        db,
        ChatbotKind.AJUDA,
        ChatbotMessageCreate(mensagem="Como vejo tutoriais?"),
    )

    assert reply == ""


@pytest.mark.anyio
async def test_given_inactive_chatbot_when_message_sent_then_raises_not_found(db):
    service = ChatbotAjudaService()
    _create_chatbot(db, ativo=False)

    with pytest.raises(ChatbotNotFoundError):
        await service.send_message(
            db,
            ChatbotKind.AJUDA,
            ChatbotMessageCreate(mensagem="Oi"),
        )
