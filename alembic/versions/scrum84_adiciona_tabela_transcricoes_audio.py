"""SCRUM-84: adiciona tabela transcricoes_audio

Revision ID: scrum84_transcricoes
Revises: 704af55ddbf5
Create Date: 2026-04-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "scrum84_transcricoes"
down_revision: Union[str, Sequence[str], None] = "704af55ddbf5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transcricoes_audio",
        sa.Column(
            "id_transcricao",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("url_audio", sa.Text(), nullable=True),
        sa.Column("texto_bruto", sa.Text(), nullable=True),
        sa.Column("nome_extraido", sa.String(255), nullable=True),
        sa.Column("especialidade_extraida", sa.String(100), nullable=True),
        sa.Column("endereco_extraido", sa.String(255), nullable=True),
        sa.Column("historia_extraida", sa.String(500), nullable=True),
        sa.Column("telefone_extraido", sa.String(20), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_transcricoes_audio_usuario_id",
        "transcricoes_audio",
        ["usuario_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transcricoes_audio_usuario_id", table_name="transcricoes_audio")
    op.drop_table("transcricoes_audio")
