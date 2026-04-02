import uuid
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.session import Base


class Photo(Base):
    __tablename__ = "fotos"

    id_foto: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url_foto_empresa: Mapped[str] = mapped_column(Text, nullable=True)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("empresas.id_empresa", ondelete="CASCADE"),nullable=False,index=True,
    )

    empresa = relationship("Enterprise", back_populates="fotos")