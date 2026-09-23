"""Persist open-world hunt and round location for Charneca."""

import sqlalchemy as sa

from alembic import op

revision = "20260923_0009"
down_revision = "20260923_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        "hunt_rounds",
        sa.Column(
            "local_id",
            sa.String(64),
            nullable=False,
            server_default="Estrada das Cinzas",
        ),
    )


def downgrade() -> None:
    op.drop_column("hunt_rounds", "local_id")
    op.drop_column("hunt_contexts", "local_id")
