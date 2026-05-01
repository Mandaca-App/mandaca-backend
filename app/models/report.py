import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class AIReport(Base):
    __tablename__ = "relatorios_ia"

    id_relatorio: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id_empresa", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contexto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contextos_negocio.id_contexto", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pontos_positivos: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    melhorias: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recomendacoes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    contexto = relationship("BusinessContext", back_populates="relatorios")
    empresa = relationship("Enterprise", back_populates="relatorios_ia")
