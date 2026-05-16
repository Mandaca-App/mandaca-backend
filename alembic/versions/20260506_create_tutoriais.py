"""create_tutoriais

Revision ID: 20260506tutoriais
Revises: 1a08a2dc2532
Create Date: 2026-05-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260506tutoriais"
down_revision: Union[str, Sequence[str], None] = "1a08a2dc2532"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    categoria_tutorial_enum = postgresql.ENUM(
        "cardapio",
        "reserva",
        "relatorios",
        "geral",
        name="categoria_tutorial_enum",
        create_type=False,
    )
    categoria_tutorial_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tutoriais",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria", categoria_tutorial_enum, nullable=False),
        sa.Column("titulo", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.String(length=500), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tutoriais_categoria_ordem", "tutoriais", ["categoria", "ordem"])
    op.create_index("ix_tutoriais_ativo", "tutoriais", ["ativo"])


def downgrade() -> None:
    op.drop_index("ix_tutoriais_ativo", table_name="tutoriais")
    op.drop_index("ix_tutoriais_categoria_ordem", table_name="tutoriais")
    op.drop_table("tutoriais")
    postgresql.ENUM(name="categoria_tutorial_enum").drop(op.get_bind(), checkfirst=True)
