"""O Despertar dos Flagelos: barras regionais, contribuições, Flagelo global, participantes,
rodadas de 10 s, ações e liquidação idempotente das recompensas.

Exceção autoral ao GDD §21/§49.15 registrada em ``SOURCE_AUTHORITY.md``. As tabelas
``world_event_*`` e ``veu_event_*`` não mudam.

Revision ID: 20261125_0060
Revises: 20261123_0059
Create Date: 2026-11-25 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261125_0060"
down_revision: str | None = "20261123_0059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "flagelo_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("region_id", sa.String(length=32), nullable=False),
        sa.Column("flagelo_id", sa.String(length=32), nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("spawned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("defeated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifetime_seconds", sa.BigInteger(), nullable=True),
        sa.Column("base_hp", sa.Integer(), nullable=False),
        sa.Column("base_atq", sa.Integer(), nullable=False),
        sa.Column("base_def", sa.Integer(), nullable=False),
        sa.Column("base_agi", sa.Integer(), nullable=False),
        sa.Column("max_hp", sa.Integer(), nullable=False),
        sa.Column("attack", sa.Integer(), nullable=False),
        sa.Column("hp_current", sa.Integer(), nullable=False),
        sa.Column("abandonment_steps", sa.Integer(), nullable=False),
        sa.Column("hp_scaling_bonus", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("atq_scaling_bonus", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("last_zero_combat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "enemy_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("equipment_winner_id", sa.Uuid(), nullable=True),
        sa.Column("equipment_status", sa.String(length=24), nullable=True),
        sa.Column(
            "rankings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "(status = 'active') = (defeated_at IS NULL)", name="ck_flagelo_event_defeat"
        ),
        sa.CheckConstraint(
            "status IN ('active','defeated','settled')", name="ck_flagelo_event_status"
        ),
        sa.CheckConstraint("abandonment_steps BETWEEN 0 AND 10", name="ck_flagelo_event_steps"),
        sa.CheckConstraint("hp_current >= 0 AND hp_current <= max_hp", name="ck_flagelo_event_hp"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "region_id", "cycle", name="uq_flagelo_event_cycle"),
    )
    op.create_index(
        "uq_flagelo_event_active",
        "flagelo_events",
        ["server_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "flagelo_region_progress",
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("region_id", sa.String(length=32), nullable=False),
        sa.Column("current_points", sa.Integer(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("active_flagelo_id", sa.Uuid(), nullable=True),
        sa.Column("threshold_reached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_defeated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "current_points >= 0 AND current_points <= threshold", name="ck_flagelo_progress_points"
        ),
        sa.CheckConstraint("cycle >= 1", name="ck_flagelo_progress_cycle"),
        sa.CheckConstraint("threshold > 0", name="ck_flagelo_progress_threshold"),
        sa.PrimaryKeyConstraint("server_id", "region_id"),
    )
    op.create_table(
        "flagelo_rounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("flagelo_id", sa.Uuid(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "boss_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "decision",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('OPEN','RESOLVING','RESOLVED')", name="ck_flagelo_round_state"
        ),
        sa.CheckConstraint("round_number >= 1", name="ck_flagelo_round_number"),
        sa.ForeignKeyConstraint(["flagelo_id"], ["flagelo_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flagelo_id", "round_number", name="uq_flagelo_round"),
    )
    op.create_index(
        "uq_flagelo_round_open",
        "flagelo_rounds",
        ["flagelo_id"],
        unique=True,
        postgresql_where=sa.text("state <> 'RESOLVED'"),
    )
    op.create_table(
        "flagelo_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(length=16), nullable=False),
        sa.Column("art_slot", sa.Integer(), nullable=True),
        sa.Column("target_ref", sa.String(length=64), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(action_type = 'art') = (art_slot IS NOT NULL)", name="ck_flagelo_action_art"
        ),
        sa.CheckConstraint(
            "action_type IN ('attack','defend','art')", name="ck_flagelo_action_type"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["round_id"], ["flagelo_rounds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("round_id", "character_id", name="uq_flagelo_action"),
    )
    op.create_table(
        "flagelo_contributions",
        sa.Column("seq", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("activity_id", sa.String(length=160), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("region_id", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("counted_points", sa.Integer(), nullable=True),
        sa.Column("cycle", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "counted_points IS NULL OR counted_points >= 0", name="ck_flagelo_contribution_counted"
        ),
        sa.CheckConstraint("points > 0", name="ck_flagelo_contribution_points"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("seq"),
        sa.UniqueConstraint(
            "server_id", "activity_id", "character_id", name="uq_flagelo_contribution"
        ),
    )
    op.create_index(
        "ix_flagelo_contribution_pending",
        "flagelo_contributions",
        ["server_id", "seq"],
        unique=False,
        postgresql_where=sa.text("applied_at IS NULL"),
    )
    op.create_table(
        "flagelo_participants",
        sa.Column("flagelo_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("in_combat", sa.Boolean(), nullable=False),
        sa.Column("combat_entered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acts_from_round", sa.Integer(), nullable=False),
        sa.Column("idle_rounds", sa.Integer(), nullable=False),
        sa.Column(
            "entry_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("hp", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column(
            "combat_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("reentry_available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("defeated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_damage", sa.BigInteger(), nullable=False),
        sa.Column("effective_healing", sa.BigInteger(), nullable=False),
        sa.Column("barrier_absorbed", sa.BigInteger(), nullable=False),
        sa.Column("defender_prevented_damage", sa.BigInteger(), nullable=False),
        sa.Column("meaningful_effects", sa.BigInteger(), nullable=False),
        sa.Column("participation_points", sa.Integer(), nullable=False),
        sa.Column(
            "first_metric_timestamps",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("eligible", sa.Boolean(), nullable=True),
        sa.Column(
            "reward",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "effective_damage >= 0 AND effective_healing >= 0 AND barrier_absorbed >= 0 "
            "AND defender_prevented_damage >= 0 AND meaningful_effects >= 0",
            name="ck_flagelo_participant_metrics",
        ),
        sa.CheckConstraint(
            "participation_points BETWEEN 0 AND 5", name="ck_flagelo_participant_points"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flagelo_id"], ["flagelo_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("flagelo_id", "character_id"),
    )
    op.create_index(
        "ix_flagelo_participant_character", "flagelo_participants", ["character_id"], unique=False
    )
    op.create_index(
        "ix_flagelo_participant_combat",
        "flagelo_participants",
        ["flagelo_id", "in_combat"],
        unique=False,
    )
    op.create_table(
        "flagelo_reward_settlements",
        sa.Column("flagelo_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("reward_type", sa.String(length=32), nullable=False),
        sa.Column("settlement_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('granted','pending_catalog','skipped')", name="ck_flagelo_settlement_status"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flagelo_id"], ["flagelo_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("flagelo_id", "character_id", "reward_type"),
        sa.UniqueConstraint("settlement_key", name="uq_flagelo_settlement_key"),
    )


def downgrade() -> None:
    op.drop_table("flagelo_reward_settlements")
    op.drop_index("ix_flagelo_participant_combat", table_name="flagelo_participants")
    op.drop_index("ix_flagelo_participant_character", table_name="flagelo_participants")
    op.drop_table("flagelo_participants")
    op.drop_index(
        "ix_flagelo_contribution_pending",
        table_name="flagelo_contributions",
        postgresql_where=sa.text("applied_at IS NULL"),
    )
    op.drop_table("flagelo_contributions")
    op.drop_table("flagelo_actions")
    op.drop_index(
        "uq_flagelo_round_open",
        table_name="flagelo_rounds",
        postgresql_where=sa.text("state <> 'RESOLVED'"),
    )
    op.drop_table("flagelo_rounds")
    op.drop_table("flagelo_region_progress")
    op.drop_index(
        "uq_flagelo_event_active",
        table_name="flagelo_events",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_table("flagelo_events")
