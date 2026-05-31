from uuid import UUID

from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from app.models.chatbot_ajuda import Chatbot, ChatbotKind, ChatbotKnowledgeModule
from app.schemas.chatbot_ajuda import ChatbotCreate, ChatbotUpdate, KnowledgeModuleCreate


class ChatbotAjudaRepository:
    def list_chatbots(
        self,
        db: Session,
        tipo: ChatbotKind | None = None,
        active_only: bool = False,
    ) -> list[Chatbot]:
        stmt = select(Chatbot)
        if tipo is not None:
            stmt = stmt.where(Chatbot.tipo == tipo)
        if active_only:
            stmt = stmt.where(Chatbot.ativo.is_(True))

        return list(
            db.scalars(stmt.order_by(cast(Chatbot.tipo, String).asc(), Chatbot.nome.asc())).all()
        )

    def get_by_id(self, db: Session, chatbot_id: UUID) -> Chatbot | None:
        return db.get(Chatbot, chatbot_id)

    def get_by_type(self, db: Session, tipo: ChatbotKind) -> Chatbot | None:
        stmt = select(Chatbot).where(Chatbot.tipo == tipo)
        return db.scalars(stmt).first()

    def create_chatbot(self, db: Session, payload: ChatbotCreate) -> Chatbot:
        chatbot = Chatbot(**payload.model_dump())
        db.add(chatbot)
        db.commit()
        db.refresh(chatbot)
        return chatbot

    def update_chatbot(
        self,
        db: Session,
        chatbot: Chatbot,
        payload: ChatbotUpdate,
    ) -> Chatbot:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(chatbot, field, value)

        db.commit()
        db.refresh(chatbot)
        return chatbot

    def list_modules(
        self,
        db: Session,
        chatbot_id: UUID,
        active_only: bool = False,
        topicos: list[str] | None = None,
    ) -> list[ChatbotKnowledgeModule]:
        stmt = select(ChatbotKnowledgeModule).where(ChatbotKnowledgeModule.chatbot_id == chatbot_id)
        if active_only:
            stmt = stmt.where(ChatbotKnowledgeModule.ativo.is_(True))
        if topicos:
            stmt = stmt.where(ChatbotKnowledgeModule.topico.in_(topicos))

        return list(
            db.scalars(
                stmt.order_by(
                    ChatbotKnowledgeModule.ordem.asc(),
                    ChatbotKnowledgeModule.topico.asc(),
                )
            ).all()
        )

    def create_module(
        self,
        db: Session,
        chatbot_id: UUID,
        payload: KnowledgeModuleCreate,
    ) -> ChatbotKnowledgeModule:
        module = ChatbotKnowledgeModule(chatbot_id=chatbot_id, **payload.model_dump())
        db.add(module)
        db.commit()
        db.refresh(module)
        return module
