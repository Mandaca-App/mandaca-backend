import logging
import uuid

import groq as groq_sdk
from groq import AsyncGroq
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.business_context import BusinessContext
from app.models.chat_message import ChatMessage
from app.services.prompts.conversa_summary import build_summary_prompt

logger = logging.getLogger(__name__)

_SUMMARY_THRESHOLD = 10
_CONVERSATION_NOTES_HASH = "conversa-notas"
_SUMMARY_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 1024
_TEMPERATURE = 0.3


class ConversationSummaryService:
    def __init__(self, groq_client: AsyncGroq) -> None:
        self._client = groq_client

    async def maybe_summarize(self, enterprise_id: uuid.UUID, db: Session) -> None:
        if self._count_messages(enterprise_id, db) < _SUMMARY_THRESHOLD:
            return

        mensagens = self._fetch_messages(enterprise_id, db)
        if not mensagens:
            return

        notes_row = self._get_or_create_notes_row(enterprise_id, db)
        prompt = build_summary_prompt(notes_row.notas_conversa, mensagens)

        try:
            resumo = await self._summarize(prompt)
        except groq_sdk.APIError:
            db.rollback()
            logger.warning("Falha ao sumarizar conversa da empresa %s", enterprise_id)
            return

        notes_row.notas_conversa = resumo
        for mensagem in mensagens:
            db.delete(mensagem)
        db.commit()

    def _count_messages(self, enterprise_id: uuid.UUID, db: Session) -> int:
        stmt = (
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.empresa_id == enterprise_id)
        )
        return db.scalar(stmt) or 0

    def _fetch_messages(self, enterprise_id: uuid.UUID, db: Session) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.empresa_id == enterprise_id)
            .order_by(ChatMessage.criado_em.asc())
        )
        return list(db.scalars(stmt).all())

    def _get_or_create_notes_row(self, enterprise_id: uuid.UUID, db: Session) -> BusinessContext:
        stmt = select(BusinessContext).where(
            BusinessContext.empresa_id == enterprise_id,
            BusinessContext.hash_contexto == _CONVERSATION_NOTES_HASH,
        )
        notes_row = db.scalars(stmt).first()
        if notes_row is None:
            notes_row = BusinessContext(
                empresa_id=enterprise_id,
                hash_contexto=_CONVERSATION_NOTES_HASH,
                dados_contexto={},
            )
            db.add(notes_row)
        return notes_row

    async def _summarize(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=_SUMMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
        return response.choices[0].message.content or ""
