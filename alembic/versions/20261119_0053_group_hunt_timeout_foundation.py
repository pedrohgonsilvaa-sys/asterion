"""persist Group Hunt turn deadline and member timeout counters

Revision ID: 20261119_0053
Revises: 20261116_0052
Create Date: 2026-11-19 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261119_0053"
down_revision: str | None = "20261116_0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "group_hunt_encounters",
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "group_hunt_members",
        sa.Column(
            "consecutive_timeouts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
    )
    op.add_column(
        "group_hunt_members",
        sa.Column("total_timeouts", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "group_hunt_members",
        sa.Column(
            "inactive_for_contribution",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_group_hunt_member_consec_timeouts",
        "group_hunt_members",
        "consecutive_timeouts >= 0",
    )
    op.create_check_constraint(
        "ck_group_hunt_member_total_timeouts",
        "group_hunt_members",
        "total_timeouts >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_group_hunt_member_total_timeouts", "group_hunt_members", type_="check"
    )
    op.drop_constraint(
        "ck_group_hunt_member_consec_timeouts", "group_hunt_members", type_="check"
    )
    op.drop_column("group_hunt_members", "inactive_for_contribution")
    op.drop_column("group_hunt_members", "total_timeouts")
    op.drop_column("group_hunt_members", "consecutive_timeouts")
    op.drop_column("group_hunt_encounters", "deadline_at")
