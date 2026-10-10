"""Persist player takeover of an AI-controlled Ronda PvPvE side.

Revision ID: 20261009_0026
Revises: 20261008_0025
"""

import sqlalchemy as sa

from alembic import op

revision = "20261009_0026"
down_revision = "20261008_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pvpve_collision_members",
        sa.Column(
            "round_takeover",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("pvpve_collision_members", "round_takeover")
