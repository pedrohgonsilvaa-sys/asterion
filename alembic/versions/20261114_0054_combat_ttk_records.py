"""combat TTK telemetry table (Beta, docs/TTK_DESENHO.md)

Creates only the telemetry table. No existing table is altered and nothing is
backfilled; the table is read by balance reports, never by game rules.

Revision ID: 20261114_0054
Revises: 20261113_0053
Create Date: 2026-11-14 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261114_0054"
down_revision: str | None = "20261113_0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "combat_ttk_records",
        sa.Column("combat_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=True),
        sa.Column("character_class", sa.String(length=24), nullable=False),
        sa.Column("player_level", sa.Integer(), nullable=False),
        sa.Column("creature_id", sa.String(length=64), nullable=False),
        sa.Column("creature_category", sa.String(length=16), nullable=False),
        sa.Column("enemy_level", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.String(length=16), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=12), nullable=False),
        sa.Column("player_actions", sa.Integer(), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=False),
        sa.Column("consumable_uses", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column("ruleset_version", sa.String(length=48), nullable=False),
        sa.Column("build_version", sa.String(length=64), nullable=False),
        sa.CheckConstraint("source IN ('hunt_manual','round_auto')", name="ck_ttk_source"),
        sa.CheckConstraint("result IN ('victory','defeat','abandoned')", name="ck_ttk_result"),
        sa.CheckConstraint(
            "player_actions >= 0 AND rounds >= 0 AND consumable_uses >= 0",
            name="ck_ttk_counts",
        ),
        sa.CheckConstraint("enemy_level >= 1 AND player_level >= 1", name="ck_ttk_levels"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("combat_id"),
    )
    op.create_index(
        "ix_ttk_creature_finished", "combat_ttk_records", ["creature_id", "finished_at"]
    )
    op.create_index("ix_ttk_finished", "combat_ttk_records", ["finished_at"])


def downgrade() -> None:
    op.drop_index("ix_ttk_finished", table_name="combat_ttk_records")
    op.drop_index("ix_ttk_creature_finished", table_name="combat_ttk_records")
    op.drop_table("combat_ttk_records")
