"""Conversao de tipo_avalicao para inteiro

Revision ID: 9f1d420a9524
Revises: 66d55a4c17ee
Create Date: 2026-05-01 15:16:26.224539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f1d420a9524'
down_revision: Union[str, Sequence[str], None] = '66d55a4c17ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
 
    # --- avaliacoes.tipo_avaliacao: ENUM → INTEGER ----------------------------
    # O PostgreSQL não converte ENUM → INTEGER automaticamente.
    # Precisamos usar USING com CASE para mapear cada label ao índice correto.
    op.execute("""
        ALTER TABLE avaliacoes
        ALTER COLUMN tipo_avaliacao TYPE INTEGER
        USING (
            CASE tipo_avaliacao::text
                WHEN 'POSITIVA' THEN 0
                WHEN 'NEGATIVA' THEN 1
                WHEN 'NEUTRA'   THEN 2
                WHEN 'SUGESTAO' THEN 3
                WHEN 'DUVIDA'   THEN 4
            END
        )
    """)
 
    # Remove o tipo ENUM do banco — não é mais necessário.
    op.execute("DROP TYPE IF EXISTS tipo_avaliacao_enum")
 
 
def downgrade() -> None:
    """Downgrade schema."""
 
    # --- avaliacoes.tipo_avaliacao: INTEGER → ENUM ----------------------------
    # Recria o tipo ENUM antes de converter de volta.
    op.execute("""
        CREATE TYPE tipo_avaliacao_enum
        AS ENUM ('POSITIVA', 'NEGATIVA', 'NEUTRA', 'SUGESTAO', 'DUVIDA')
    """)
 
    op.execute("""
        ALTER TABLE avaliacoes
        ALTER COLUMN tipo_avaliacao TYPE tipo_avaliacao_enum
        USING (
            CASE tipo_avaliacao
                WHEN 0 THEN 'POSITIVA'
                WHEN 1 THEN 'NEGATIVA'
                WHEN 2 THEN 'NEUTRA'
                WHEN 3 THEN 'SUGESTAO'
                WHEN 4 THEN 'DUVIDA'
            END
        )::tipo_avaliacao_enum
    """)
    # ### end Alembic commands ###
