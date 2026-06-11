"""SCRUM-193 seed chatbot ajuda

Revision ID: 20260609scrum193
Revises: e0457fdbd5b7
Create Date: 2026-06-10 21:10:24.753686

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260609scrum193"
down_revision: Union[str, Sequence[str], None] = "e0457fdbd5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHATBOT_AJUDA_ID = "19300000-0000-0000-0000-000000000193"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            """
            INSERT INTO chatbots (
                id_chatbot,
                tipo,
                nome,
                descricao,
                ativo,
                created_at,
                updated_at
            )
            SELECT
                CAST(:id_chatbot AS UUID),
                'ajuda',
                'Chatbot de Ajuda',
                'Assistente de onboarding para microempreendedores',
                TRUE,
                NOW(),
                NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM chatbots WHERE tipo = 'ajuda'
            )
            """
        ).bindparams(id_chatbot=_CHATBOT_AJUDA_ID)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            DELETE FROM chatbots
            WHERE id_chatbot = :id_chatbot
            """
        ).bindparams(id_chatbot=_CHATBOT_AJUDA_ID)
    )
