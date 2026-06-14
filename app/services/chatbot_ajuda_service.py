from uuid import UUID

import groq as groq_sdk
from groq import AsyncGroq
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ChatbotNotFoundError,
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceError,
    ChatServiceTimeoutError,
    DuplicateChatbotTypeError,
)
from app.models.chatbot_ajuda import Chatbot, ChatbotKind, ChatbotKnowledgeModule
from app.repositories.chatbot_ajuda_repository import ChatbotAjudaRepository
from app.schemas.chatbot_ajuda import (
    ChatbotCreate,
    ChatbotMessageCreate,
    ChatbotUpdate,
    KnowledgeModuleCreate,
)
from app.services.prompts.chatbot_ajuda_tutorial import (
    ChatbotAjudaPromptModule,
    build_chatbot_ajuda_system_prompt,
)

_CHATBOT_AJUDA_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 700
_TEMPERATURE = 0.2


class ChatbotAjudaService:
    def __init__(
        self,
        repository: ChatbotAjudaRepository | None = None,
        groq_client: AsyncGroq | None = None,
    ) -> None:
        self._repository = repository or ChatbotAjudaRepository()
        self._client = groq_client or AsyncGroq(api_key=settings.groq_api_key)

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

    async def send_message(
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
        system_prompt = build_chatbot_ajuda_system_prompt(self._build_prompt_modules(modules))

        try:
            response = await self._client.chat.completions.create(
                model=_CHATBOT_AJUDA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._build_user_message(chatbot, payload)},
                ],
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
            )
            return (response.choices[0].message.content or "").strip()
        except groq_sdk.RateLimitError:
            raise ChatRateLimitError()
        except groq_sdk.APITimeoutError:
            raise ChatServiceTimeoutError()
        except groq_sdk.APIConnectionError:
            raise ChatServiceConnectionError()
        except groq_sdk.APIStatusError:
            raise ChatServiceError()

    def _build_prompt_modules(
        self,
        modules: list[ChatbotKnowledgeModule],
    ) -> list[ChatbotAjudaPromptModule]:
        prompt_modules: list[ChatbotAjudaPromptModule] = []
        for module in modules:
            content = module.conteudo or "Modulo cadastrado sem conteudo detalhado."
            if module.referencia:
                content = f"{content} Consulte tambem: {module.referencia}."
            prompt_modules.append(
                ChatbotAjudaPromptModule(
                    topic=module.topico,
                    title=f"Modulo {module.topico}",
                    status="ativo",
                    content=content,
                    reference=module.referencia,
                )
            )
        return prompt_modules

    def _build_user_message(
        self,
        chatbot: Chatbot,
        payload: ChatbotMessageCreate,
    ) -> str:
        context_lines = [
            f"Tipo de chatbot: {chatbot.tipo.value}",
            f"Pergunta: {payload.mensagem}",
        ]
        if payload.topicos:
            context_lines.append("Topicos solicitados: " + ", ".join(payload.topicos))
        return "\n".join(context_lines)
