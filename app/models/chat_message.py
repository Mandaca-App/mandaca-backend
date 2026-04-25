import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class ChatMessage(Base):
    __tablename__ = "mensagens_chat"

    id_mensagem: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id_empresa", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conteudo_usuario: Mapped[str] = mapped_column(Text, nullable=False)
    conteudo_assistente: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    empresa = relationship("Enterprise", back_populates="mensagens_chat")
