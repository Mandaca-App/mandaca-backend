import uuid
from datetime import time

from sqlalchemy import Float, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class Enterprise(Base):
    __tablename__ = "empresas"

    id_empresa: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    especialidade: Mapped[str] = mapped_column(String(100), nullable=True)
    endereco: Mapped[str] = mapped_column(String(255), nullable=True)
    historia: Mapped[str] = mapped_column(String(500), nullable=True)
    hora_abrir: Mapped[time] = mapped_column(Time, nullable=True)
    hora_fechar: Mapped[time] = mapped_column(Time, nullable=True)
    telefone: Mapped[str] = mapped_column(String(20), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    usuario = relationship(
        "User",
        back_populates="empresa",
        foreign_keys=[usuario_id],
    )

    reservas = relationship(
        "Reservation",
        back_populates="empresa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    fotos = relationship(
        "Photo",
        back_populates="empresa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    avaliacoes = relationship(
        "Assessment",
        back_populates="empresa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    cardapios = relationship(
        "Menu",
        back_populates="empresa",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
