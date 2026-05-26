import uuid

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ChatbotNotFoundError, DuplicateChatbotTypeError
from app.models.chatbot import Chatbot, ChatbotKind, KnowledgeModuleType
from app.schemas.chatbot import ChatbotCreate, ChatbotMessageCreate, KnowledgeModuleCreate
from app.services.chatbot_service import ChatbotService


def _create_chatbot(db, tipo: ChatbotKind = ChatbotKind.AJUDA, ativo: bool = True) -> Chatbot:
    chatbot = Chatbot(tipo=tipo, nome=f"Chatbot {tipo.value}", ativo=ativo)
    db.add(chatbot)
    db.commit()
    db.refresh(chatbot)
    return chatbot


def test_given_chatbot_payload_when_create_then_persists_base_entity(db):
    service = ChatbotService()

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
    service = ChatbotService()
    _create_chatbot(db, tipo=ChatbotKind.AJUDA)

    with pytest.raises(DuplicateChatbotTypeError):
        service.create_chatbot(
            db,
            ChatbotCreate(tipo=ChatbotKind.AJUDA, nome="Outro chatbot"),
        )


def test_given_dynamic_modules_when_message_sent_then_uses_active_filtered_topics(db):
    service = ChatbotService()
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

    reply = service.send_message(
        db,
        ChatbotKind.AJUDA,
        ChatbotMessageCreate(
            empresa_id=uuid.uuid4(),
            usuario_id=uuid.uuid4(),
            mensagem="Como melhorar fotos do cardapio?",
            topicos=["cardapio"],
        ),
    )

    assert "chatbot ajuda" in reply
    assert "cardapio" in reply
    assert "reserva" not in reply
    assert "inativo" not in reply


def test_given_inactive_chatbot_when_message_sent_then_raises_not_found(db):
    service = ChatbotService()
    _create_chatbot(db, ativo=False)

    with pytest.raises(ChatbotNotFoundError):
        service.send_message(
            db,
            ChatbotKind.AJUDA,
            ChatbotMessageCreate(mensagem="Oi"),
        )
