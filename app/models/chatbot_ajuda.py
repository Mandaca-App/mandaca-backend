import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class ChatbotKind(str, enum.Enum):
    RELATORIOS = "relatorios"
    AJUDA = "ajuda"


class KnowledgeModuleType(str, enum.Enum):
    TUTORIAL = "tutorial"
    FAQ = "faq"
    RELATORIO = "relatorio"
    GERAL = "geral"


class Chatbot(Base):
    __tablename__ = "chatbots"
    __table_args__ = (UniqueConstraint("tipo", name="uq_chatbots_tipo"),)

    id_chatbot: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tipo: Mapped[ChatbotKind] = mapped_column(
        Enum(
            ChatbotKind,
            name="chatbot_tipo_enum",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    modulos = relationship(
        "ChatbotKnowledgeModule",
        back_populates="chatbot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChatbotKnowledgeModule(Base):
    __tablename__ = "chatbot_modulos_conhecimento"

    id_modulo: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chatbot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chatbots.id_chatbot", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topico: Mapped[str] = mapped_column(String(80), nullable=False)
    tipo: Mapped[KnowledgeModuleType] = mapped_column(
        Enum(
            KnowledgeModuleType,
            name="modulo_conhecimento_tipo_enum",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    conteudo: Mapped[str | None] = mapped_column(Text, nullable=True)
    referencia: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chatbot = relationship("Chatbot", back_populates="modulos")
