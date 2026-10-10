"""Persist PvPvE queues, collisions, cooldowns, and Domain grants.

Revision ID: 20261008_0025
Revises: 20261008_0024
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261008_0025"
down_revision = "20261008_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pvpve_queues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("local_id", sa.String(64), nullable=False),
        sa.Column("roster_size", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True)),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "roster_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), server_default="waiting", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("roster_size BETWEEN 1 AND 4", name="ck_pvpve_queue_roster_size"),
        sa.CheckConstraint(
            "source_type IN ('manual','group','round')", name="ck_pvpve_queue_source"
        ),
        sa.CheckConstraint(
            "status IN ('waiting','matched','expired','cancelled')", name="ck_pvpve_queue_status"
        ),
        sa.CheckConstraint("jsonb_typeof(roster_snapshot) = 'array'", name="ck_pvpve_queue_roster"),
        sa.ForeignKeyConstraint(["group_id"], ["social_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["group_activity_proposals.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_pvpve_queue_proposal"),
    )
    op.create_index(
        "ix_pvpve_queue_match",
        "pvpve_queues",
        ["server_id", "local_id", "roster_size", "status", "created_at"],
    )
    op.create_index(
        "uq_pvpve_queue_waiting_group",
        "pvpve_queues",
        ["group_id"],
        unique=True,
        postgresql_where=sa.text("status = 'waiting' AND group_id IS NOT NULL"),
    )

    op.create_table(
        "pvpve_queue_members",
        sa.Column("queue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("game_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_key", sa.String(16), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.CheckConstraint("ordinal BETWEEN 1 AND 4", name="ck_pvpve_queue_ordinal"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_activity_id"], ["game_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["queue_id"], ["pvpve_queues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("queue_id", "character_id"),
        sa.UniqueConstraint("game_activity_id", name="uq_pvpve_queue_activity"),
    )
    op.create_index(
        "ix_pvpve_queue_member_character", "pvpve_queue_members", ["character_id", "queue_id"]
    )

    op.create_table(
        "pvpve_collisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("local_id", sa.String(64), nullable=False),
        sa.Column("roster_size", sa.Integer(), nullable=False),
        sa.Column("queue_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("queue_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("combat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ruleset_version", sa.String(48), nullable=False),
        sa.Column("state_version", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("combat_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("winner_side", sa.String(1)),
        sa.Column("prey_reference_level", sa.Integer()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("roster_size BETWEEN 1 AND 4", name="ck_pvpve_collision_roster"),
        sa.CheckConstraint("state_version >= 0", name="ck_pvpve_collision_version"),
        sa.CheckConstraint(
            "status IN ('active','prey','completed','failed')", name="ck_pvpve_collision_status"
        ),
        sa.CheckConstraint(
            "winner_side IS NULL OR winner_side IN ('a','b')", name="ck_pvpve_collision_winner"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(combat_snapshot) = 'object'", name="ck_pvpve_collision_snapshot"
        ),
        sa.ForeignKeyConstraint(["queue_a_id"], ["pvpve_queues.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["queue_b_id"], ["pvpve_queues.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("queue_a_id", name="uq_pvpve_collision_queue_a"),
        sa.UniqueConstraint("queue_b_id", name="uq_pvpve_collision_queue_b"),
        sa.UniqueConstraint("combat_id", name="uq_pvpve_collision_combat"),
    )
    op.create_index(
        "ix_pvpve_collision_local_created", "pvpve_collisions", ["local_id", "created_at"]
    )

    op.create_table(
        "pvpve_collision_members",
        sa.Column("collision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("game_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_key", sa.String(16), nullable=False),
        sa.Column("side", sa.String(1), nullable=False),
        sa.Column("contributed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("domain_eligible", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "result_acknowledged", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("prey_result", sa.String(16)),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("side IN ('a','b')", name="ck_pvpve_collision_member_side"),
        sa.CheckConstraint(
            "status IN ('active','prey','defeated','settled')",
            name="ck_pvpve_collision_member_status",
        ),
        sa.CheckConstraint(
            "prey_result IS NULL OR prey_result IN ('victory','defeat')",
            name="ck_pvpve_collision_member_prey_result",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collision_id"], ["pvpve_collisions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["game_activity_id"], ["game_activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("collision_id", "character_id"),
        sa.UniqueConstraint("game_activity_id", name="uq_pvpve_collision_member_activity"),
        sa.UniqueConstraint(
            "collision_id", "actor_key", name="uq_pvpve_collision_member_actor"
        ),
    )
    op.create_index(
        "ix_pvpve_collision_member_account",
        "pvpve_collision_members",
        ["account_id", "collision_id"],
    )

    op.create_table(
        "pvpve_account_pairs",
        sa.Column("account_a", sa.BigInteger(), nullable=False),
        sa.Column("account_b", sa.BigInteger(), nullable=False),
        sa.Column("last_match_at", sa.DateTime(timezone=True)),
        sa.Column("domain_until", sa.DateTime(timezone=True)),
        sa.CheckConstraint("account_a < account_b", name="ck_pvpve_account_pair_order"),
        sa.ForeignKeyConstraint(["account_a"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_b"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_a", "account_b"),
    )
    op.create_table(
        "pvpve_account_cooldowns",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("pvp_until", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_id"),
    )
    op.create_table(
        "pvpve_domain_grants",
        sa.Column("collision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crowns", sa.BigInteger(), nullable=False),
        sa.Column("material_id", sa.String(96)),
        sa.Column("status", sa.String(24), server_default="granted", nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("crowns >= 0", name="ck_pvpve_domain_crowns"),
        sa.CheckConstraint(
            "status IN ('granted','locked','no_economic_reward','no_opponent')",
            name="ck_pvpve_domain_status",
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["collision_id"], ["pvpve_collisions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("collision_id", "character_id"),
    )
    op.add_column(
        "hunt_contexts",
        sa.Column("pvpve_collision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "hunt_contexts", sa.Column("pvpve_reference_level", sa.Integer(), nullable=True)
    )
    op.add_column(
        "hunt_contexts",
        sa.Column(
            "pvpve_domain_eligible",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_hunt_context_pvpve_collision",
        "hunt_contexts",
        "pvpve_collisions",
        ["pvpve_collision_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_hunt_context_pvpve_collision", "hunt_contexts", type_="foreignkey"
    )
    op.drop_column("hunt_contexts", "pvpve_domain_eligible")
    op.drop_column("hunt_contexts", "pvpve_reference_level")
    op.drop_column("hunt_contexts", "pvpve_collision_id")
    op.drop_table("pvpve_domain_grants")
    op.drop_table("pvpve_account_cooldowns")
    op.drop_table("pvpve_account_pairs")
    op.drop_index(
        "ix_pvpve_collision_member_account", table_name="pvpve_collision_members"
    )
    op.drop_table("pvpve_collision_members")
    op.drop_index("ix_pvpve_collision_local_created", table_name="pvpve_collisions")
    op.drop_table("pvpve_collisions")
    op.drop_index("ix_pvpve_queue_member_character", table_name="pvpve_queue_members")
    op.drop_table("pvpve_queue_members")
    op.drop_index("uq_pvpve_queue_waiting_group", table_name="pvpve_queues")
    op.drop_index("ix_pvpve_queue_match", table_name="pvpve_queues")
    op.drop_table("pvpve_queues")
