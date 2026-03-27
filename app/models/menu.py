import uuid
import enum
from decimal import Decimal

from sqlalchemy import String, Numeric, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.session import Base


class CategoriaCardapio(str, enum.Enum):
    ENTRADA = "entrada"
    PRATO_PRINCIPAL = "prato_principal"
    SOBREMESA = "sobremesa"
    BEBIDA = "bebida"
    LANCHE = "lanche"


class Menu(Base):
    __tablename__ = "cardapios"

    id_cardapio: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    historia: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    categoria: Mapped[CategoriaCardapio] = mapped_column(Enum(CategoriaCardapio, name="categoria_cardapio_enum"), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("empresas.id_empresa", ondelete="CASCADE"),nullable=False,index=True,)

    empresa = relationship("Enterprise", back_populates="cardapios")