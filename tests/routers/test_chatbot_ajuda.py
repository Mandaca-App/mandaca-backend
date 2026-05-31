from sqlalchemy import func, select

from app.models.chatbot_ajuda import Chatbot, ChatbotKind


def _create_chatbot(db, tipo: ChatbotKind = ChatbotKind.AJUDA) -> Chatbot:
    chatbot = Chatbot(tipo=tipo, nome=f"Chatbot {tipo.value}")
    db.add(chatbot)
    db.commit()
    db.refresh(chatbot)
    return chatbot


def test_given_payload_when_create_chatbot_then_returns_201(client, db):
    response = client.post(
        "/chatbots",
        json={
            "tipo": "ajuda",
            "nome": "Chatbot de Ajuda",
            "descricao": "Central de Ajuda",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["tipo"] == "ajuda"
    assert data["nome"] == "Chatbot de Ajuda"
    assert data["ativo"] is True
    assert db.scalar(select(func.count()).select_from(Chatbot)) == 1


def test_given_chatbot_when_module_created_then_can_list_active_modules(client, db):
    chatbot = _create_chatbot(db)
    create_response = client.post(
        f"/chatbots/{chatbot.id_chatbot}/modules",
        json={
            "topico": "cardapio",
            "tipo": "tutorial",
            "conteudo": "Como cadastrar itens no cardapio",
            "ordem": 1,
        },
    )

    assert create_response.status_code == 201

    list_response = client.get(f"/chatbots/{chatbot.id_chatbot}/modules?active_only=true")

    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 1
    assert data[0]["topico"] == "cardapio"


def test_given_help_chatbot_when_message_sent_then_returns_chat_reply_contract(client, db):
    chatbot = _create_chatbot(db)
    client.post(
        f"/chatbots/{chatbot.id_chatbot}/modules",
        json={
            "topico": "tutorial",
            "tipo": "tutorial",
            "conteudo": "Artigos da Central de Ajuda",
        },
    )

    response = client.post(
        "/chatbots/ajuda/message",
        json={
            "mensagem": "Como vejo tutoriais?",
            "topicos": ["tutorial"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert list(data.keys()) == ["reply"]
    assert "tutorial" in data["reply"]


def test_given_invalid_chatbot_type_when_message_sent_then_returns_422(client):
    response = client.post(
        "/chatbots/inexistente/message",
        json={"mensagem": "Oi"},
    )

    assert response.status_code == 422
