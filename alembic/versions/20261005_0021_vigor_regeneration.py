"""Persist the natural Vigor regeneration anchor."""

import sqlalchemy as sa

from alembic import op

revision = "20261005_0021"
down_revision = "20261003_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column(
            "vigor_regen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("characters", "vigor_regen_at")