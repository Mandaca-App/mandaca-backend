"""SCRUM-84: remove tabela transcricoes_audio (dados vao direto para empresas)

Revision ID: scrum84_remove_transcricoes
Revises: scrum84_transcricoes
Create Date: 2026-04-04

"""

from typing import Sequence, Union

from alembic import op

revision: str = "scrum84_remove_transcricoes"
down_revision: Union[str, Sequence[str], None] = "scrum84_transcricoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        "ix_transcricoes_audio_usuario_id",
        table_name="transcricoes_audio",
        if_exists=True,
    )
    op.drop_table("transcricoes_audio", if_exists=True)


def downgrade() -> None:
    pass
