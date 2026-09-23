"""Persist open-world hunt and round location for Charneca."""

import sqlalchemy as sa

from alembic import op

revision = "20260923_0009"
down_revision = "20260923_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "world_states",
        sa.Column("last_brazier_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "hunt_contexts",
        sa.Column(
            "local_id",
            sa.String(64),
            nullable=False,
            server_default="Estrada das Cinzas",
        ),
    )
    op.add_column(
        "hunt_contexts",
        sa.Column("recovery_brazier_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "hunt_rounds",
        sa.Column(
            "local_id",
            sa.String(64),
            nullable=False,
            server_default="Estrada das Cinzas",
        ),
    )
    op.add_column(
        "hunt_rounds",
        sa.Column("recovery_brazier_id", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hunt_rounds", "recovery_brazier_id")
    op.drop_column("hunt_rounds", "local_id")
    op.drop_column("hunt_contexts", "recovery_brazier_id")
    op.drop_column("hunt_contexts", "local_id")
    op.drop_column("world_states", "last_brazier_id")
