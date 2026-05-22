import logging
import uuid

import groq as groq_sdk
from groq import AsyncGroq
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ChatRateLimitError,
    ChatServiceConnectionError,
    ChatServiceError,
    ChatServiceTimeoutError,
)
from app.models.chat_message import ChatMessage
from app.services.chat_context_service import ChatContextService
from app.services.prompts.consultor_persona import build_system_prompt

logger = logging.getLogger(__name__)

_CHAT_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 1024
_TEMPERATURE = 0.7


class ChatService:
    def __init__(
        self,
        groq_client: AsyncGroq | None = None,
        context_service: ChatContextService | None = None,
    ) -> None:
        self._client = groq_client or AsyncGroq(api_key=settings.groq_api_key)
        self._context_service = context_service or ChatContextService()

    async def send_message(
        self,
        message: str,
        enterprise_id: uuid.UUID,
        user_id: uuid.UUID,
        db: Session,
    ) -> str:
        enterprise_context = self._context_service.build_enterprise_context(enterprise_id, db)
        context = self._context_service.build_context(enterprise_id, db, user_id)
        system_content = build_system_prompt(enterprise_context)
        if context:
            system_content = f"{system_content}\n\n{context}"

        try:
            response = await self._client.chat.completions.create(
                model=_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": message},
                ],
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
            )
            content = response.choices[0].message.content or ""
        except groq_sdk.RateLimitError:
            raise ChatRateLimitError()
        except groq_sdk.APITimeoutError:
            raise ChatServiceTimeoutError()
        except groq_sdk.APIConnectionError:
            raise ChatServiceConnectionError()
        except groq_sdk.APIStatusError:
            raise ChatServiceError()

        chat_message = ChatMessage(
            empresa_id=enterprise_id,
            conteudo_usuario=message,
            conteudo_assistente=content,
        )
        try:
            db.add(chat_message)
            db.commit()
        except Exception:
            db.rollback()
            raise

        return content

    def get_chat_history(self, enterprise_id: uuid.UUID, db: Session) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.empresa_id == enterprise_id,
                ChatMessage.deleted_at.is_(None),
            )
            .order_by(ChatMessage.criado_em.asc())
        )
        return list(db.scalars(stmt).all())
