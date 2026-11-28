"""Doutrinas: Doutrina ativa registrada no banco e nomes definidos pelo sistema.

Revision ID: 20261128_0065
Revises: 20261128_0064
Create Date: 2026-11-28 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261128_0065"
down_revision: str | None = "20261128_0064"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "character_doctrines",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "uq_character_doctrine_active",
        "character_doctrines",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_character_doctrine_active", table_name="character_doctrines")
    op.drop_column("character_doctrines", "is_active")
