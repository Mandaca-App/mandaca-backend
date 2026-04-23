import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class BusinessContext(Base):
    __tablename__ = "contextos_negocio"

    id_contexto: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id_empresa", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hash_contexto: Mapped[str] = mapped_column(String(64), nullable=False)
    dados_contexto: Mapped[dict] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    empresa = relationship("Enterprise", back_populates="contextos")
    relatorios = relationship("AIReport", back_populates="contexto", cascade="all, delete-orphan")
