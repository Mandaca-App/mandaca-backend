import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class TipoAvaliacao(int, enum.Enum):
    POSITIVA = 0
    NEGATIVA = 1
    NEUTRA = 2
    SUGESTAO = 3
    DUVIDA = 4


class Assessment(Base):
    __tablename__ = "avaliacoes"

    id_avaliacao: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    texto: Mapped[str] = mapped_column(String(500), nullable=False)

    tipo_avaliacao: Mapped[TipoAvaliacao] = mapped_column(
        Integer,
        nullable=False,
        default=TipoAvaliacao.NEUTRA,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id_empresa", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    usuario = relationship("User", back_populates="avaliacoes")
    empresa = relationship("Enterprise", back_populates="avaliacoes")
