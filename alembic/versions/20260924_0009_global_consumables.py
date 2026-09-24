"""Track the daily cycle in which a character used a Vigor Consumable."""

import sqlalchemy as sa

from alembic import op

revision = "20260924_0009"
down_revision = "20260923_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("vigor_consumable_cycle", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    # Conflicts with ordinary INSERT/UPDATE/DELETE and serializes concurrent downgrades.
    bind.exec_driver_sql("LOCK TABLE characters IN SHARE ROW EXCLUSIVE MODE")
    if bind.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM characters WHERE vigor_consumable_cycle IS NOT NULL)")
    ):
        raise RuntimeError("Cannot downgrade used Vigor Consumable cycle state")
    op.drop_column("characters", "vigor_consumable_cycle")
