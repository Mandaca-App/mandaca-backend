"""SCRUM-258 add auth fields to usuarios

Revision ID: 20260621scrum258
Revises: cc35bffcf9a7
Create Date: 2026-06-21 19:17:26.331592

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260621scrum258"
down_revision: Union[str, Sequence[str], None] = "cc35bffcf9a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("usuarios", sa.Column("auth_user_id", sa.UUID(), nullable=True))
    op.add_column("usuarios", sa.Column("email", sa.String(length=255), nullable=True))
    op.create_index("ix_usuarios_auth_user_id", "usuarios", ["auth_user_id"], unique=True)
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_index("ix_usuarios_auth_user_id", table_name="usuarios")
    op.drop_column("usuarios", "email")
    op.drop_column("usuarios", "auth_user_id")
