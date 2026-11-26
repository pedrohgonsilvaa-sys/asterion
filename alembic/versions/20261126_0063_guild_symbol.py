"""Guilda: símbolo escolhido pelo Líder na fundação (decisão do autor 2026-11-26 §16).

Lista controlada de 20 símbolos; Guildas já existentes ficam sem símbolo (NULL) e a
interface usa o emoji padrão da Guilda até que exista um fluxo de troca aprovado.

Revision ID: 20261126_0063
Revises: 20261126_0062
Create Date: 2026-11-26 00:00:02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261126_0063"
down_revision: str | None = "20261126_0062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("guilds", sa.Column("symbol", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("guilds", "symbol")
