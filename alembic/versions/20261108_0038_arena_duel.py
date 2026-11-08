"""Add Duelo and Arena da Vigilia.

Revision ID: 20261108_0038
Revises: 20261108_0037
Create Date: 2026-11-08 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261108_0038"
down_revision: str | None = "20261108_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "arena_profiles",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("renome", sa.Integer(), nullable=False),
        sa.Column("mmr", sa.Integer(), nullable=False),
        sa.Column("placement_played", sa.Integer(), nullable=False),
        sa.Column("placement_wins", sa.Integer(), nullable=False),
        sa.Column("matches_played", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("draws", sa.Integer(), nullable=False),
        sa.Column("queue_blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_match_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_decay_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("renome >= 0", name="ck_arena_profile_renome"),
        sa.CheckConstraint(
            "placement_played BETWEEN 0 AND 5 AND placement_wins BETWEEN 0 AND placement_played",
            name="ck_arena_profile_placement",
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id"),
    )
    op.create_index("ix_arena_profiles_ranking", "arena_profiles", ["server_id", "renome"])
    op.create_table(
        "arena_queue_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("game_activity_id", sa.Uuid(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("mmr", sa.Integer(), nullable=False),
        sa.Column("configuration_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('waiting','matched','left','released')", name="ck_arena_queue_status"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_activity_id"], ["game_activities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_arena_queue_open_character",
        "arena_queue_entries",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('waiting','matched')"),
    )
    op.create_index(
        "ix_arena_queue_waiting", "arena_queue_entries", ["server_id", "status", "entered_at"]
    )
    op.create_table(
        "pvp_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("combat_id", sa.Uuid(), nullable=True),
        sa.Column("ruleset_version", sa.String(length=48), nullable=True),
        sa.Column("state_version", sa.BigInteger(), nullable=False),
        sa.Column("combat_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("winner_side", sa.String(length=1), nullable=True),
        sa.Column("end_reason", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('duel','arena')", name="ck_pvp_match_kind"),
        sa.CheckConstraint(
            "status IN ('invited','confirming','active','finished','cancelled')",
            name="ck_pvp_match_status",
        ),
        sa.CheckConstraint(
            "winner_side IS NULL OR winner_side IN ('a','b')", name="ck_pvp_match_winner"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pvp_matches_due", "pvp_matches", ["server_id", "status", "deadline_at"])
    op.create_index("ix_pvp_matches_finished", "pvp_matches", ["server_id", "kind", "finished_at"])
    op.create_table(
        "pvp_match_members",
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("side", sa.String(length=1), nullable=False),
        sa.Column("actor_key", sa.String(length=8), nullable=False),
        sa.Column("is_challenger", sa.Boolean(), nullable=False),
        sa.Column("game_activity_id", sa.Uuid(), nullable=True),
        sa.Column("queue_entry_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_timeouts", sa.Integer(), nullable=False),
        sa.Column("total_timeouts", sa.Integer(), nullable=False),
        sa.Column("renome_before", sa.Integer(), nullable=True),
        sa.Column("renome_after", sa.Integer(), nullable=True),
        sa.Column("placed_before", sa.Boolean(), nullable=True),
        sa.Column("placed_after", sa.Boolean(), nullable=True),
        sa.Column("placement_played_after", sa.Integer(), nullable=True),
        sa.CheckConstraint("side IN ('a','b')", name="ck_pvp_member_side"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_activity_id"], ["game_activities.id"]),
        sa.ForeignKeyConstraint(["match_id"], ["pvp_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["queue_entry_id"], ["arena_queue_entries.id"]),
        sa.PrimaryKeyConstraint("match_id", "character_id"),
        sa.UniqueConstraint("match_id", "side", name="uq_pvp_member_side"),
    )
    op.create_index("ix_pvp_member_character", "pvp_match_members", ["character_id"])
    op.create_table(
        "arena_dodges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["pvp_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arena_dodges_character_at", "arena_dodges", ["character_id", "occurred_at"])


def downgrade() -> None:
    op.drop_table("arena_dodges")
    op.drop_table("pvp_match_members")
    op.drop_table("pvp_matches")
    op.drop_table("arena_queue_entries")
    op.drop_table("arena_profiles")
