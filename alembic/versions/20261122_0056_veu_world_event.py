"""A Ruptura do Véu: persistence of the global World Event.

Adds the occurrence, per-phase global N snapshot, Núcleos A-I, participants (event-level
and Núcleo-level state, AFK streak), rounds, actions and enemy decisions. The regional
``world_event_*`` tables are left untouched until the application layer replaces them.

Revision ID: 20261122_0056
Revises: 20261120_0055
Create Date: 2026-11-22 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261122_0056"
down_revision: str | None = "20261120_0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "veu_event_occurrences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("occurrence_key", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phase_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("ruleset_version", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "state IN ('AGENDADO','ABERTO','EM_ANDAMENTO','CONCLUIDO','FRACASSADO','ENCERRADO')",
            name="ck_veu_occurrence_state",
        ),
        sa.CheckConstraint("phase BETWEEN 1 AND 3", name="ck_veu_occurrence_phase"),
        sa.CheckConstraint("deadline_at > scheduled_at", name="ck_veu_occurrence_deadline"),
        sa.CheckConstraint("entry_closes_at > scheduled_at", name="ck_veu_occurrence_entry"),
        sa.CheckConstraint("state_version >= 0", name="ck_veu_occurrence_version"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "occurrence_key", name="uq_veu_occurrence"),
    )
    op.create_index(
        "ix_veu_occurrence_state", "veu_event_occurrences", ["server_id", "state"], unique=False
    )
    op.create_table(
        "veu_event_phase_snapshots",
        sa.Column("occurrence_id", sa.Uuid(), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("phase BETWEEN 1 AND 3", name="ck_veu_snapshot_phase"),
        sa.CheckConstraint("n BETWEEN 0 AND 200", name="ck_veu_snapshot_n"),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["veu_event_occurrences.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("occurrence_id", "phase"),
    )
    op.create_table(
        "veu_event_nuclei",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurrence_id", sa.Uuid(), nullable=False),
        sa.Column("nucleus_key", sa.String(length=1), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column(
            "enemy_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "nucleus_key IN ('A','B','C','D','E','F','G','H','I')", name="ck_veu_nucleus_key"
        ),
        sa.CheckConstraint(
            "state IN ('ATIVA','RESOLVENDO','RESOLVIDA','COLAPSADA','SUBSTITUIDA')",
            name="ck_veu_nucleus_state",
        ),
        sa.CheckConstraint(
            "(nucleus_key IN ('A','B','C') AND phase = 1) "
            "OR (nucleus_key IN ('D','E','F') AND phase = 2) "
            "OR (nucleus_key IN ('G','H','I') AND phase = 3)",
            name="ck_veu_nucleus_phase",
        ),
        sa.CheckConstraint("state_version >= 0", name="ck_veu_nucleus_version"),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["veu_event_occurrences.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "occurrence_id", name="uq_veu_nucleus_occurrence"),
        sa.UniqueConstraint("occurrence_id", "nucleus_key", name="uq_veu_nucleus_key"),
    )
    op.create_index(
        "ix_veu_nucleus_phase", "veu_event_nuclei", ["occurrence_id", "phase"], unique=False
    )
    op.create_table(
        "veu_event_participants",
        sa.Column("occurrence_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("voluntary_exit", sa.Boolean(), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("defeated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reentry_available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_nucleus_id", sa.Uuid(), nullable=True),
        sa.Column("nucleus_entered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nucleus_removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("afk_streak", sa.Integer(), nullable=False),
        sa.Column("significant_actions", sa.Integer(), nullable=False),
        sa.Column("major_contributions", sa.Integer(), nullable=False),
        sa.Column(
            "phases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint("afk_streak BETWEEN 0 AND 3", name="ck_veu_participant_afk"),
        sa.CheckConstraint(
            "current_nucleus_id IS NULL OR nucleus_removed_at IS NULL",
            name="ck_veu_participant_removal",
        ),
        sa.CheckConstraint(
            "voluntary_exit = (left_at IS NOT NULL)", name="ck_veu_participant_exit"
        ),
        sa.CheckConstraint(
            "significant_actions >= 0 AND major_contributions >= 0",
            name="ck_veu_participant_contribution",
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["current_nucleus_id", "occurrence_id"],
            ["veu_event_nuclei.id", "veu_event_nuclei.occurrence_id"],
            name="fk_veu_participant_nucleus",
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["veu_event_occurrences.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("occurrence_id", "character_id"),
    )
    op.create_index(
        "ix_veu_participant_character", "veu_event_participants", ["character_id"], unique=False
    )
    op.create_index(
        "ix_veu_participant_nucleus", "veu_event_participants", ["current_nucleus_id"], unique=False
    )
    op.create_table(
        "veu_event_rounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurrence_id", sa.Uuid(), nullable=False),
        sa.Column("nucleus_id", sa.Uuid(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('OPEN','RESOLVING','RESOLVED')", name="ck_veu_round_state"
        ),
        sa.CheckConstraint("round_number >= 1", name="ck_veu_round_number"),
        sa.CheckConstraint(
            "decision_deadline = opened_at + interval '10 seconds'", name="ck_veu_round_window"
        ),
        sa.CheckConstraint(
            "(state = 'OPEN' AND resolution_started_at IS NULL AND resolved_at IS NULL) "
            "OR (state = 'RESOLVING' AND resolution_started_at IS NOT NULL "
            "AND resolved_at IS NULL) "
            "OR (state = 'RESOLVED' AND resolution_started_at IS NOT NULL "
            "AND resolved_at IS NOT NULL)",
            name="ck_veu_round_resolution",
        ),
        sa.ForeignKeyConstraint(
            ["nucleus_id", "occurrence_id"],
            ["veu_event_nuclei.id", "veu_event_nuclei.occurrence_id"],
            name="fk_veu_round_nucleus",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "occurrence_id", name="uq_veu_round_occurrence"),
        sa.UniqueConstraint("nucleus_id", "round_number", name="uq_veu_round_number"),
    )
    op.create_index(
        "ix_veu_round_due", "veu_event_rounds", ["state", "decision_deadline"], unique=False
    )
    op.create_index(
        "uq_veu_round_unresolved",
        "veu_event_rounds",
        ["nucleus_id"],
        unique=True,
        postgresql_where=sa.text("state <> 'RESOLVED'"),
    )
    op.create_table(
        "veu_event_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurrence_id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(length=16), nullable=False),
        sa.Column("art_slot", sa.Integer(), nullable=True),
        sa.Column("target_ref", sa.String(length=64), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid", sa.Boolean(), nullable=True),
        sa.Column("significant", sa.Boolean(), nullable=False),
        sa.Column("major_contribution", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "action_type IN ('attack','defend','art')", name="ck_veu_action_type"
        ),
        sa.CheckConstraint(
            "(action_type = 'art' AND art_slot IS NOT NULL AND art_slot BETWEEN 1 AND 3) "
            "OR (action_type <> 'art' AND art_slot IS NULL)",
            name="ck_veu_action_art_slot",
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id", "character_id"],
            ["veu_event_participants.occurrence_id", "veu_event_participants.character_id"],
            name="fk_veu_action_participant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["round_id", "occurrence_id"],
            ["veu_event_rounds.id", "veu_event_rounds.occurrence_id"],
            name="fk_veu_action_round",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("round_id", "character_id", name="uq_veu_action_round_character"),
    )
    op.create_index(
        "ix_veu_action_character", "veu_event_actions", ["character_id"], unique=False
    )
    op.create_table(
        "veu_event_enemy_decisions",
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("enemy_key", sa.String(length=64), nullable=False),
        sa.Column("action_key", sa.String(length=64), nullable=False),
        sa.Column(
            "target_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("telegraph_key", sa.String(length=64), nullable=True),
        sa.Column("seed", sa.Numeric(precision=20, scale=0), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("seed >= 0", name="ck_veu_enemy_seed"),
        sa.ForeignKeyConstraint(["round_id"], ["veu_event_rounds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("round_id", "enemy_key"),
    )


def downgrade() -> None:
    op.drop_table("veu_event_enemy_decisions")
    op.drop_index("ix_veu_action_character", table_name="veu_event_actions")
    op.drop_table("veu_event_actions")
    op.drop_index(
        "uq_veu_round_unresolved",
        table_name="veu_event_rounds",
        postgresql_where=sa.text("state <> 'RESOLVED'"),
    )
    op.drop_index("ix_veu_round_due", table_name="veu_event_rounds")
    op.drop_table("veu_event_rounds")
    op.drop_index("ix_veu_participant_nucleus", table_name="veu_event_participants")
    op.drop_index("ix_veu_participant_character", table_name="veu_event_participants")
    op.drop_table("veu_event_participants")
    op.drop_index("ix_veu_nucleus_phase", table_name="veu_event_nuclei")
    op.drop_table("veu_event_nuclei")
    op.drop_table("veu_event_phase_snapshots")
    op.drop_index("ix_veu_occurrence_state", table_name="veu_event_occurrences")
    op.drop_table("veu_event_occurrences")
