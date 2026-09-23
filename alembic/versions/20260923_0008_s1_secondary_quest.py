"""S1 secondary-quest abandonment and tracking state."""

import sqlalchemy as sa

from alembic import op

revision = "20260923_0008"
down_revision = "20260922_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_quest_status", "quests", type_="check")
    op.create_check_constraint(
        "ck_quest_status",
        "quests",
        "status IN ('active','completed','abandoned')",
    )
    op.add_column(
        "characters",
        sa.Column("tracked_secondary_quest_id", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM quests WHERE status='abandoned') OR "
            "EXISTS (SELECT 1 FROM quests WHERE quest_id='S1') OR "
            "EXISTS (SELECT 1 FROM characters WHERE tracked_secondary_quest_id IS NOT NULL)"
        )
    ):
        raise RuntimeError("Cannot downgrade populated S1/secondary-quest state")
    op.drop_column("characters", "tracked_secondary_quest_id")
    op.drop_constraint("ck_quest_status", "quests", type_="check")
    op.create_check_constraint(
        "ck_quest_status",
        "quests",
        "status IN ('active','completed')",
    )
