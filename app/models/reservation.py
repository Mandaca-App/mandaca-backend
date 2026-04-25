import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class Reservation(Base):
    __tablename__ = "reservas"

    id_reserva: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    num_mesas: Mapped[int] = mapped_column(Integer, nullable=False)
    num_pessoas: Mapped[int] = mapped_column(Integer, nullable=False)
    mensagem: Mapped[str | None] = mapped_column(String(120), nullable=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id_empresa", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    usuario = relationship("User", back_populates="reservas")
    empresa = relationship("Enterprise", back_populates="reservas")
