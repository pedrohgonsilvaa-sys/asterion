"""Persist cooperative campaign journeys and shared encounters."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261008_0023"
down_revision = "20261008_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign_journeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quest_id", sa.String(32), nullable=False),
        sa.Column("checkpoint", sa.String(96), nullable=False),
        sa.Column("journey_reference_character_id", postgresql.UUID(as_uuid=True)),
        sa.Column("technical_host_character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "context_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active','paused','completed','cancelled')",
            name="ck_campaign_journey_status",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_campaign_journey_revision"),
        sa.CheckConstraint(
            "jsonb_typeof(context_payload) = 'object'",
            name="ck_campaign_journey_context_object",
        ),
        sa.ForeignKeyConstraint(["group_id"], ["social_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["journey_reference_character_id"], ["characters.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["technical_host_character_id"], ["characters.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_campaign_journeys_group_status",
        "campaign_journeys",
        ["group_id", "status", "created_at"],
    )

    op.create_table(
        "campaign_journey_members",
        sa.Column("journey_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("checkpoint_snapshot", sa.String(96), nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("role IN ('eligible','helper')", name="ck_campaign_journey_member_role"),
        sa.CheckConstraint(
            "status IN ('active','left','completed')",
            name="ck_campaign_journey_member_status",
        ),
        sa.ForeignKeyConstraint(
            ["journey_id"], ["campaign_journeys.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("journey_id", "character_id"),
    )
    op.create_index(
        "ix_campaign_journey_member_character",
        "campaign_journey_members",
        ["character_id", "status"],
    )

    op.create_table(
        "campaign_shared_encounters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True)),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True)),
        sa.Column("quest_id", sa.String(32), nullable=False),
        sa.Column("content_id", sa.String(64), nullable=False),
        sa.Column("journey_reference_character_id", postgresql.UUID(as_uuid=True)),
        sa.Column("technical_host_character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("roster_size", sa.Integer(), nullable=False),
        sa.Column("scaling_snapshot", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("ruleset_version", sa.String(48), nullable=False),
        sa.Column("state_version", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("combat_snapshot", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('active','completed','failed','paused')",
            name="ck_campaign_shared_encounter_status",
        ),
        sa.CheckConstraint(
            "roster_size BETWEEN 1 AND 4", name="ck_campaign_shared_encounter_roster_size"
        ),
        sa.CheckConstraint("state_version >= 0", name="ck_campaign_shared_encounter_version"),
        sa.CheckConstraint(
            "scaling_snapshot IS NULL OR jsonb_typeof(scaling_snapshot) = 'object'",
            name="ck_campaign_shared_encounter_scaling_object",
        ),
        sa.CheckConstraint(
            "combat_snapshot IS NULL OR jsonb_typeof(combat_snapshot) = 'object'",
            name="ck_campaign_shared_encounter_combat_object",
        ),
        sa.ForeignKeyConstraint(["journey_id"], ["campaign_journeys.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["group_activity_proposals.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["journey_reference_character_id"], ["characters.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["technical_host_character_id"], ["characters.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_campaign_shared_encounter_proposal"),
    )
    op.create_index(
        "ix_campaign_shared_encounters_journey_status",
        "campaign_shared_encounters",
        ["journey_id", "status"],
    )

    op.create_table(
        "campaign_shared_encounter_members",
        sa.Column("shared_encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_key", sa.String(16), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("checkpoint_snapshot", sa.String(96), nullable=False),
        sa.Column("settlement_state", sa.String(16), server_default="pending", nullable=False),
        sa.Column("result", sa.String(16)),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("role IN ('eligible','helper')", name="ck_campaign_shared_member_role"),
        sa.CheckConstraint(
            "settlement_state IN ('pending','settled')",
            name="ck_campaign_shared_member_settlement",
        ),
        sa.ForeignKeyConstraint(
            ["shared_encounter_id"], ["campaign_shared_encounters.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_activity_id"], ["game_activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("shared_encounter_id", "character_id"),
        sa.UniqueConstraint("game_activity_id", name="uq_campaign_shared_member_activity"),
        sa.UniqueConstraint(
            "shared_encounter_id", "actor_key", name="uq_campaign_shared_member_actor"
        ),
    )
    op.create_index(
        "ix_campaign_shared_member_character",
        "campaign_shared_encounter_members",
        ["character_id", "shared_encounter_id"],
    )

    op.create_table(
        "campaign_objective_credits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True)),
        sa.Column("quest_id", sa.String(32), nullable=False),
        sa.Column("objective_id", sa.String(96), nullable=False),
        sa.Column("source_key", sa.String(128), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journey_id"], ["campaign_journeys.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "character_id",
            "quest_id",
            "objective_id",
            "source_key",
            name="uq_campaign_objective_credit",
        ),
    )
    op.create_index(
        "ix_campaign_objective_credit_source",
        "campaign_objective_credits",
        ["source_key", "quest_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_objective_credit_source", table_name="campaign_objective_credits")
    op.drop_table("campaign_objective_credits")
    op.drop_index(
        "ix_campaign_shared_member_character", table_name="campaign_shared_encounter_members"
    )
    op.drop_table("campaign_shared_encounter_members")
    op.drop_index(
        "ix_campaign_shared_encounters_journey_status", table_name="campaign_shared_encounters"
    )
    op.drop_table("campaign_shared_encounters")
    op.drop_index("ix_campaign_journey_member_character", table_name="campaign_journey_members")
    op.drop_table("campaign_journey_members")
    op.drop_index("ix_campaign_journeys_group_status", table_name="campaign_journeys")
    op.drop_table("campaign_journeys")
