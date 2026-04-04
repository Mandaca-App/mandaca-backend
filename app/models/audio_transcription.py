import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class AudioTranscription(Base):
    __tablename__ = "transcricoes_audio"

    id_transcricao: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url_audio: Mapped[str | None] = mapped_column(Text, nullable=True)
    texto_bruto: Mapped[str | None] = mapped_column(Text, nullable=True)
    nome_extraido: Mapped[str | None] = mapped_column(String(255), nullable=True)
    especialidade_extraida: Mapped[str | None] = mapped_column(String(100), nullable=True)
    endereco_extraido: Mapped[str | None] = mapped_column(String(255), nullable=True)
    historia_extraida: Mapped[str | None] = mapped_column(String(500), nullable=True)
    telefone_extraido: Mapped[str | None] = mapped_column(String(20), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario = relationship("User", foreign_keys=[usuario_id])
