import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class TipoAvaliacao(str, enum.Enum):
    POSITIVA = "positiva"
    NEGATIVA = "negativa"
    NEUTRA = "neutra"
    SUGESTAO = "sugestao"
    DUVIDA = "duvida"


class Assessment(Base):
    __tablename__ = "avaliacoes"

    id_avaliacao: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    texto: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo_avaliacao: Mapped[TipoAvaliacao] = mapped_column(
        Enum(TipoAvaliacao, name="tipo_avaliacao_enum"),
        nullable=False,
        default=TipoAvaliacao.NEUTRA,
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
