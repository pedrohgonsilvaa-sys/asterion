"""Persist shared Hunt combat and member leases."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261008_0024"
down_revision = "20261008_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_hunt_encounters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("local_id", sa.String(64), nullable=False),
        sa.Column("creature_id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("enemy_level", sa.Integer(), nullable=False),
        sa.Column("reference_level", sa.Integer(), nullable=False),
        sa.Column("variant", sa.String(24)),
        sa.Column("seed", sa.String(128), nullable=False),
        sa.Column("roster_size", sa.Integer(), nullable=False),
        sa.Column("scaling_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("combat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ruleset_version", sa.String(48), nullable=False),
        sa.Column("state_version", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("combat_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("roster_size BETWEEN 2 AND 4", name="ck_group_hunt_roster_size"),
        sa.CheckConstraint("enemy_level >= 1", name="ck_group_hunt_enemy_level"),
        sa.CheckConstraint("reference_level >= 1", name="ck_group_hunt_reference_level"),
        sa.CheckConstraint("state_version >= 0", name="ck_group_hunt_version"),
        sa.CheckConstraint(
            "status IN ('active','completed','failed')", name="ck_group_hunt_status"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(scaling_snapshot) = 'object'",
            name="ck_group_hunt_scaling_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(combat_snapshot) = 'object'",
            name="ck_group_hunt_combat_object",
        ),
        sa.ForeignKeyConstraint(["group_id"], ["social_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["group_activity_proposals.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_group_hunt_proposal"),
        sa.UniqueConstraint("combat_id", name="uq_group_hunt_combat"),
    )
    op.create_index(
        "ix_group_hunt_group_status",
        "group_hunt_encounters",
        ["group_id", "status", "created_at"],
    )

    op.create_table(
        "group_hunt_members",
        sa.Column("group_hunt_encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_key", sa.String(16), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("loot_seed", sa.String(128), nullable=False),
        sa.Column("consumable_uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("settlement_state", sa.String(16), server_default="pending", nullable=False),
        sa.Column("result", sa.String(16)),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("ordinal BETWEEN 1 AND 4", name="ck_group_hunt_member_ordinal"),
        sa.CheckConstraint("consumable_uses >= 0", name="ck_group_hunt_member_consumables"),
        sa.CheckConstraint(
            "settlement_state IN ('pending','settled')",
            name="ck_group_hunt_member_settlement",
        ),
        sa.ForeignKeyConstraint(
            ["group_hunt_encounter_id"],
            ["group_hunt_encounters.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_activity_id"], ["game_activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_hunt_encounter_id", "character_id"),
        sa.UniqueConstraint("game_activity_id", name="uq_group_hunt_member_activity"),
        sa.UniqueConstraint(
            "group_hunt_encounter_id", "actor_key", name="uq_group_hunt_member_actor"
        ),
    )
    op.create_index(
        "ix_group_hunt_member_character",
        "group_hunt_members",
        ["character_id", "group_hunt_encounter_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_group_hunt_member_character", table_name="group_hunt_members")
    op.drop_table("group_hunt_members")
    op.drop_index("ix_group_hunt_group_status", table_name="group_hunt_encounters")
    op.drop_table("group_hunt_encounters")
