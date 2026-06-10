import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class TipoRemetente(str, enum.Enum):
    TURISTA = "turista"
    EMPREENDEDOR = "empreendedor"


class ReservationMessage(Base):
    __tablename__ = "mensagens_reserva"

    id_mensagem: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reserva_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reservas.id_reserva", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    remetente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_remetente: Mapped[TipoRemetente] = mapped_column(
        Enum(
            TipoRemetente,
            name="tipo_remetente_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    reserva = relationship("Reservation", back_populates="mensagens")
