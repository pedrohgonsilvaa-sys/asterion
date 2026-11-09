"""chronicle, trilha, vote and salao da vigilia

Revision ID: 20261110_0043
Revises: 20261109_0042
Create Date: 2026-11-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261110_0043"
down_revision: str | None = "20261109_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "chronicle_cycles",
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("day1", sa.Date(), nullable=False),
        sa.Column("end_at", _TZ, nullable=False),
        sa.Column("vote_closed_at", _TZ, nullable=True),
        sa.Column("runoff_options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("runoff_closed_at", _TZ, nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("finalized_at", _TZ, nullable=True),
        sa.Column("liquidated_at", _TZ, nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN "
            "('selar','estabilizar','herdeiros','destruir','em_espera')",
            name="ck_chronicle_cycle_outcome",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_chronicle_cycle_revision"),
        sa.PrimaryKeyConstraint("server_id", "chronicle_id"),
    )
    op.create_table(
        "chronicle_cycle_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
        sa.Column("created_at", _TZ, nullable=False),
        sa.CheckConstraint("action IN ('set_day1','extend')", name="ck_chronicle_log_action"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chronicle_cycle_logs_cycle",
        "chronicle_cycle_logs",
        ["server_id", "chronicle_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "chronicle_accounts",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("repeatable_points", sa.Integer(), nullable=False),
        sa.Column("premium_at", _TZ, nullable=True),
        sa.Column("premium_source", sa.String(length=32), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.CheckConstraint(
            "points >= 0 AND repeatable_points >= 0 AND repeatable_points <= points",
            name="ck_chronicle_account_points",
        ),
        sa.PrimaryKeyConstraint("account_id", "server_id", "chronicle_id"),
    )
    op.create_table(
        "chronicle_completions",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("objective_id", sa.String(length=48), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("completed_at", _TZ, nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id", "chronicle_id", "objective_id"),
    )
    op.create_index(
        "ix_chronicle_completions_account",
        "chronicle_completions",
        ["account_id", "server_id", "chronicle_id"],
        unique=False,
    )
    op.create_table(
        "chronicle_point_grants",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("source_id", sa.String(length=48), nullable=False),
        sa.Column("repeatable", sa.Boolean(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=True),
        sa.Column("cycle_date", sa.Date(), nullable=False),
        sa.Column("granted_at", _TZ, nullable=False),
        sa.CheckConstraint("points > 0", name="ck_chronicle_grant_points"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("account_id", "server_id", "chronicle_id", "source_key"),
    )
    op.create_index(
        "ix_chronicle_grants_daily",
        "chronicle_point_grants",
        ["account_id", "server_id", "chronicle_id", "source_id", "cycle_date"],
        unique=False,
    )
    op.create_table(
        "chronicle_claims",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("track", sa.String(length=8), nullable=False),
        sa.Column("milestone", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=True),
        sa.Column("via", sa.String(length=16), nullable=False),
        sa.Column("claimed_at", _TZ, nullable=False),
        sa.CheckConstraint("track IN ('free','premium')", name="ck_chronicle_claim_track"),
        sa.CheckConstraint("milestone BETWEEN 1 AND 40", name="ck_chronicle_claim_milestone"),
        sa.CheckConstraint("via IN ('claim','liquidation')", name="ck_chronicle_claim_via"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("account_id", "server_id", "chronicle_id", "track", "milestone"),
    )
    op.create_table(
        "chronicle_votes",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("round", sa.String(length=8), nullable=False),
        sa.Column("option", sa.String(length=16), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.CheckConstraint("round IN ('main','runoff')", name="ck_chronicle_vote_round"),
        sa.CheckConstraint(
            "option IN ('selar','estabilizar','herdeiros','destruir')",
            name="ck_chronicle_vote_option",
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("account_id", "server_id", "chronicle_id", "round"),
    )
    op.create_table(
        "chronicle_electorate",
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("frozen_at", _TZ, nullable=False),
        sa.PrimaryKeyConstraint("server_id", "chronicle_id", "account_id"),
    )
    op.create_table(
        "vigil_hall_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("chronicle_id", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("elo", sa.String(length=24), nullable=True),
        sa.Column("matches", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("reward_eligible", sa.Boolean(), nullable=False),
        sa.Column("reward_tier", sa.String(length=24), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.CheckConstraint(
            "kind IN ('arena','guild_battle','guild_battle_member')",
            name="ck_vigil_hall_kind",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "server_id", "chronicle_id", "kind", "subject_id", name="uq_vigil_hall_subject"
        ),
    )
    op.create_index(
        "ix_vigil_hall_position",
        "vigil_hall_entries",
        ["server_id", "chronicle_id", "kind", "position"],
        unique=False,
    )
    op.add_column(
        "arena_profiles",
        sa.Column("cycle_matches", sa.Integer(), server_default="0", nullable=False),
    )
    # Before any Crônica existed every match belonged to the first cycle.
    op.execute("UPDATE arena_profiles SET cycle_matches = matches_played")
    op.add_column(
        "guild_battle_profiles",
        sa.Column("career_real_battles", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute("UPDATE guild_battle_profiles SET career_real_battles = real_battles")


def downgrade() -> None:
    op.drop_column("guild_battle_profiles", "career_real_battles")
    op.drop_column("arena_profiles", "cycle_matches")
    op.drop_index("ix_vigil_hall_position", table_name="vigil_hall_entries")
    op.drop_table("vigil_hall_entries")
    op.drop_table("chronicle_electorate")
    op.drop_table("chronicle_votes")
    op.drop_table("chronicle_claims")
    op.drop_index("ix_chronicle_grants_daily", table_name="chronicle_point_grants")
    op.drop_table("chronicle_point_grants")
    op.drop_index("ix_chronicle_completions_account", table_name="chronicle_completions")
    op.drop_table("chronicle_completions")
    op.drop_table("chronicle_accounts")
    op.drop_index("ix_chronicle_cycle_logs_cycle", table_name="chronicle_cycle_logs")
    op.drop_table("chronicle_cycle_logs")
    op.drop_table("chronicle_cycles")
