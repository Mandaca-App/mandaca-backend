"""scrum212_relatorios_ia_jsonb

Revision ID: 66d55a4c17ee
Revises: 8d2587d835ea
Create Date: 2026-05-01 10:03:13.408440

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '66d55a4c17ee'
down_revision: Union[str, Sequence[str], None] = '8d2587d835ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('relatorios_ia', 'pontos_positivos_resumo')
    op.drop_column('relatorios_ia', 'pontos_positivos_detalhado')
    op.drop_column('relatorios_ia', 'melhorias_resumo')
    op.drop_column('relatorios_ia', 'melhorias_detalhado')
    op.drop_column('relatorios_ia', 'recomendacoes_resumo')
    op.drop_column('relatorios_ia', 'recomendacoes_detalhado')
    op.add_column('relatorios_ia', sa.Column(
        'pontos_positivos',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default='[]',
    ))
    op.add_column('relatorios_ia', sa.Column(
        'melhorias',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default='[]',
    ))
    op.add_column('relatorios_ia', sa.Column(
        'recomendacoes',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default='[]',
    ))


def downgrade() -> None:
    op.drop_column('relatorios_ia', 'pontos_positivos')
    op.drop_column('relatorios_ia', 'melhorias')
    op.drop_column('relatorios_ia', 'recomendacoes')
    op.add_column('relatorios_ia', sa.Column(
        'pontos_positivos_resumo', sa.Text(), nullable=False, server_default=''
    ))
    op.add_column('relatorios_ia', sa.Column(
        'pontos_positivos_detalhado', sa.Text(), nullable=False, server_default=''
    ))
    op.add_column('relatorios_ia', sa.Column(
        'melhorias_resumo', sa.Text(), nullable=False, server_default=''
    ))
    op.add_column('relatorios_ia', sa.Column(
        'melhorias_detalhado', sa.Text(), nullable=False, server_default=''
    ))
    op.add_column('relatorios_ia', sa.Column(
        'recomendacoes_resumo', sa.Text(), nullable=False, server_default=''
    ))
    op.add_column('relatorios_ia', sa.Column(
        'recomendacoes_detalhado', sa.Text(), nullable=False, server_default=''
    ))
