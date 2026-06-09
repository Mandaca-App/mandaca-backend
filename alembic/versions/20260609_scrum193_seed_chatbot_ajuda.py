"""SCRUM-193 seed chatbot ajuda

Revision ID: 20260609scrum193
Revises: 415578617141
Create Date: 2026-06-09 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260609scrum193"
down_revision: Union[str, Sequence[str], None] = "415578617141"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHATBOT_AJUDA_ID = "19300000-0000-0000-0000-000000000193"


def upgrade() -> None:
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
    op.execute(
        sa.text(
            """
            DELETE FROM chatbots
            WHERE id_chatbot = :id_chatbot
            """
        ).bindparams(id_chatbot=_CHATBOT_AJUDA_ID)
    )
