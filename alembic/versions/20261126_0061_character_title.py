"""Título persistido do personagem: ``Caminhante das Cinzas`` como valor inicial.

Personagens existentes recebem o mesmo valor pelo ``server_default``. O sistema de
Títulos (Cosméticos) continua podendo substituí-lo na exibição.

Revision ID: 20261126_0061
Revises: 20261125_0060
Create Date: 2026-11-26 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261126_0061"
down_revision: str | None = "20261125_0060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column(
            "title",
            sa.String(length=64),
            nullable=False,
            server_default="Caminhante das Cinzas",
        ),
    )


def downgrade() -> None:
    op.drop_column("characters", "title")
