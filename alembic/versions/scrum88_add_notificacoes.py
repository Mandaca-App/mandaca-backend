"""SCRUM-88: add notificacoes table

Revision ID: scrum88_add_notificacoes
Revises: scrum84_remove_transcricoes
Create Date: 2026-04-07

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "scrum88_add_notificacoes"
down_revision: Union[str, Sequence[str], None] = "scrum84_remove_transcricoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notificacoes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("usuario_id", sa.UUID(), nullable=False),
        sa.Column("titulo", sa.String(length=100), nullable=False),
        sa.Column("mensagem", sa.String(length=255), nullable=False),
        sa.Column("lida", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column(
            "data_criacao",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id_usuario"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notificacoes_id"), "notificacoes", ["id"], unique=False)
    op.create_index(
        op.f("ix_notificacoes_usuario_id"), "notificacoes", ["usuario_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notificacoes_usuario_id"), table_name="notificacoes")
    op.drop_index(op.f("ix_notificacoes_id"), table_name="notificacoes")
    op.drop_table("notificacoes")
