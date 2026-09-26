"""Persist the originating location for each hunt encounter."""

import sqlalchemy as sa

from alembic import op

revision = "20260926_0011"
down_revision = "20260925_0010"
branch_labels = None
depends_on = None

ROAD_LOCATION = "tdo.location.estrada_das_cinzas"


def upgrade() -> None:
    op.add_column(
        "hunt_contexts",
        sa.Column("local_id", sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text("UPDATE hunt_contexts SET local_id = :road_location").bindparams(
            road_location=ROAD_LOCATION
        )
    )
    op.alter_column("hunt_contexts", "local_id", nullable=False)


def downgrade() -> None:
    op.drop_column("hunt_contexts", "local_id")
