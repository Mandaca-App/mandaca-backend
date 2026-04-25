"""scrum49_merge_heads

Revision ID: f2bc2c1e8eb6
Revises: 6748fb7ea73c, scrum88_add_notificacoes
Create Date: 2026-04-13 08:05:31.200267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2bc2c1e8eb6'
down_revision: Union[str, Sequence[str], None] = ('6748fb7ea73c', 'scrum88_add_notificacoes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
