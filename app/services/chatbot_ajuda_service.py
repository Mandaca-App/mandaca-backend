from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ChatbotNotFoundError, DuplicateChatbotTypeError
from app.models.chatbot_ajuda import Chatbot, ChatbotKind, ChatbotKnowledgeModule
from app.repositories.chatbot_ajuda_repository import ChatbotAjudaRepository
from app.schemas.chatbot_ajuda import (
    ChatbotCreate,
    ChatbotMessageCreate,
    ChatbotUpdate,
    KnowledgeModuleCreate,
)


class ChatbotAjudaService:
    def __init__(self, repository: ChatbotAjudaRepository | None = None) -> None:
        self._repository = repository or ChatbotAjudaRepository()

    def list_chatbots(
        self,
        db: Session,
        tipo: ChatbotKind | None = None,
        active_only: bool = False,
    ) -> list[Chatbot]:
        return self._repository.list_chatbots(db, tipo=tipo, active_only=active_only)

    def get_by_type(
        self,
        db: Session,
        tipo: ChatbotKind,
        active_only: bool = False,
    ) -> Chatbot:
        chatbot = self._repository.get_by_type(db, tipo)
        if chatbot is None or (active_only and not chatbot.ativo):
            raise ChatbotNotFoundError(tipo.value)
        return chatbot

    def create_chatbot(self, db: Session, payload: ChatbotCreate) -> Chatbot:
        if self._repository.get_by_type(db, payload.tipo) is not None:
            raise DuplicateChatbotTypeError(payload.tipo.value)
        return self._repository.create_chatbot(db, payload)

    def update_chatbot(self, db: Session, chatbot_id: UUID, payload: ChatbotUpdate) -> Chatbot:
        chatbot = self._repository.get_by_id(db, chatbot_id)
        if chatbot is None:
            raise ChatbotNotFoundError(chatbot_id)
        return self._repository.update_chatbot(db, chatbot, payload)

    def create_module(
        self,
        db: Session,
        chatbot_id: UUID,
        payload: KnowledgeModuleCreate,
    ) -> ChatbotKnowledgeModule:
        if self._repository.get_by_id(db, chatbot_id) is None:
            raise ChatbotNotFoundError(chatbot_id)
        return self._repository.create_module(db, chatbot_id, payload)

    def list_modules(
        self,
        db: Session,
        chatbot_id: UUID,
        active_only: bool = False,
        topicos: list[str] | None = None,
    ) -> list[ChatbotKnowledgeModule]:
        if self._repository.get_by_id(db, chatbot_id) is None:
            raise ChatbotNotFoundError(chatbot_id)
        return self._repository.list_modules(
            db,
            chatbot_id=chatbot_id,
            active_only=active_only,
            topicos=topicos,
        )

    def send_message(
        self,
        db: Session,
        tipo: ChatbotKind,
        payload: ChatbotMessageCreate,
    ) -> str:
        chatbot = self.get_by_type(db, tipo, active_only=True)
        modules = self._repository.list_modules(
            db,
            chatbot_id=chatbot.id_chatbot,
            active_only=True,
            topicos=payload.topicos or None,
        )
        return self._build_scaffold_reply(chatbot, modules)

    def _build_scaffold_reply(
        self,
        chatbot: Chatbot,
        modules: list[ChatbotKnowledgeModule],
    ) -> str:
        if modules:
            topics = ", ".join(module.topico for module in modules)
            return (
                f"Recebi sua mensagem no chatbot {chatbot.tipo.value}. "
                f"Modulos de conhecimento carregados: {topics}."
            )

        return (
            f"Recebi sua mensagem no chatbot {chatbot.tipo.value}. "
            "Nenhum modulo de conhecimento ativo foi encontrado para esta conversa."
        )
