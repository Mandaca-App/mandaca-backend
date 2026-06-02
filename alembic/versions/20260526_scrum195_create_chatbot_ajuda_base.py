"""SCRUM-195 create chatbot ajuda base

Revision ID: 20260526scrum195
Revises: ea6b8f4e6c3b
Create Date: 2026-05-26 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260526scrum195"
down_revision: Union[str, Sequence[str], None] = "ea6b8f4e6c3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    chatbot_tipo_enum = postgresql.ENUM(
        "relatorios",
        "ajuda",
        name="chatbot_tipo_enum",
        create_type=False,
    )
    modulo_tipo_enum = postgresql.ENUM(
        "tutorial",
        "faq",
        "relatorio",
        "geral",
        name="modulo_conhecimento_tipo_enum",
        create_type=False,
    )
    chatbot_tipo_enum.create(op.get_bind(), checkfirst=True)
    modulo_tipo_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "chatbots",
        sa.Column("id_chatbot", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", chatbot_tipo_enum, nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.String(length=500), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id_chatbot"),
        sa.UniqueConstraint("tipo", name="uq_chatbots_tipo"),
    )

    op.create_table(
        "chatbot_modulos_conhecimento",
        sa.Column("id_modulo", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chatbot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topico", sa.String(length=80), nullable=False),
        sa.Column("tipo", modulo_tipo_enum, nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=True),
        sa.Column("referencia", sa.String(length=500), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["chatbot_id"],
            ["chatbots.id_chatbot"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_modulo"),
    )
    op.create_index(
        "ix_chatbot_modulos_chatbot_topico",
        "chatbot_modulos_conhecimento",
        ["chatbot_id", "topico"],
    )
    op.create_index(
        "ix_chatbot_modulos_chatbot_ativo",
        "chatbot_modulos_conhecimento",
        ["chatbot_id", "ativo"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chatbot_modulos_chatbot_ativo",
        table_name="chatbot_modulos_conhecimento",
    )
    op.drop_index(
        "ix_chatbot_modulos_chatbot_topico",
        table_name="chatbot_modulos_conhecimento",
    )
    op.drop_table("chatbot_modulos_conhecimento")
    op.drop_table("chatbots")
    postgresql.ENUM(name="modulo_conhecimento_tipo_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="chatbot_tipo_enum").drop(op.get_bind(), checkfirst=True)
