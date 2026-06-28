"""merge remove_num_mesas and scrum258_auth_fields

Revision ID: 29ebe5663ece
Revises: 1d65c4e27110, 20260621scrum258
Create Date: 2026-06-22 15:27:02.689415

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29ebe5663ece'
down_revision: Union[str, Sequence[str], None] = ('1d65c4e27110', '20260621scrum258')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
