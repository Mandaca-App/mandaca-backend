import uuid
import enum
from sqlalchemy import String, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.session import Base


class TipoUsuario(str, enum.Enum):
    TURISTA = "turista"
    EMPREENDEDOR = "empreendedor"


class User(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4,unique=True,index=True,)
    tipo_usuario: Mapped[TipoUsuario] = mapped_column(Enum(TipoUsuario, name="tipo_usuario_enum"),nullable=False, default=TipoUsuario.TURISTA)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), nullable=False, unique=True)
    url_foto_usuario: Mapped[str | None] = mapped_column(Text, nullable=True)
    empresa = relationship("Enterprise",back_populates="usuario",uselist=False,cascade="all, delete-orphan",single_parent=True,passive_deletes=True,)
    reservas = relationship("Reservation",back_populates="usuario",cascade="all, delete-orphan",passive_deletes=True,)
    avaliacoes = relationship("Assessment",back_populates="usuario",cascade="all, delete-orphan",passive_deletes=True,)