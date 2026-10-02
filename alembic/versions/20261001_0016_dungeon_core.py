"""Persist global dungeon runs, members, encounters, and pity."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261001_0016"
down_revision = "20260930_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dungeon_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dungeon_family_id", sa.String(length=96), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ruleset_version", sa.String(length=48), nullable=False),
        sa.Column("content_version", sa.String(length=48), nullable=False),
        sa.Column("reference_level", sa.Integer(), nullable=False),
        sa.Column("initial_group_size", sa.Integer(), nullable=False),
        sa.Column("current_encounter_ordinal", sa.Integer(), nullable=False),
        sa.Column("state_version", sa.BigInteger(), nullable=False),
        sa.Column("seed", sa.String(length=128), nullable=False),
        sa.Column("has_brazier", sa.Boolean(), nullable=False),
        sa.Column("brazier_activated", sa.Boolean(), nullable=False),
        sa.Column("brazier_after_encounter", sa.Integer(), nullable=True),
        sa.Column("active_checkpoint_encounter", sa.Integer(), nullable=True),
        sa.Column(
            "progress",
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
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active','completed','failed','expired')", name="ck_dungeon_run_status"
        ),
        sa.CheckConstraint(
            "difficulty IN ('stable','fractured','rupture')", name="ck_dungeon_run_difficulty"
        ),
        sa.CheckConstraint("initial_group_size BETWEEN 1 AND 4", name="ck_dungeon_run_group_size"),
        sa.CheckConstraint("current_encounter_ordinal >= 1", name="ck_dungeon_run_ordinal"),
        sa.CheckConstraint("state_version >= 0", name="ck_dungeon_run_state_version"),
        sa.CheckConstraint(
            "active_checkpoint_encounter IS NULL OR active_checkpoint_encounter >= 1",
            name="ck_dungeon_run_checkpoint",
        ),
        sa.CheckConstraint("jsonb_typeof(progress) = 'object'", name="ck_dungeon_run_progress"),
        sa.PrimaryKeyConstraint("id", name="pk_dungeon_runs"),
    )
    op.create_index(
        "ix_dungeon_runs_active_updated",
        "dungeon_runs",
        ["last_activity_at"],
        unique=False,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "dungeon_run_members",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("foreground_activity_id", sa.Uuid(), nullable=True),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("vigor_reserved", sa.Integer(), nullable=False),
        sa.Column(
            "vigor_refunded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("consumable_uses", sa.Integer(), nullable=False),
        sa.Column(
            "combat_configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("hp", sa.Numeric(), nullable=False),
        sa.Column("max_hp", sa.Numeric(), nullable=False),
        sa.Column(
            "run_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "contribution",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint("position BETWEEN 1 AND 4", name="ck_dungeon_run_member_position"),
        sa.CheckConstraint(
            "status IN ('active','defeated','left')", name="ck_dungeon_run_member_status"
        ),
        sa.CheckConstraint("vigor_reserved >= 0", name="ck_dungeon_run_member_vigor"),
        sa.CheckConstraint("consumable_uses >= 0", name="ck_dungeon_run_member_consumables"),
        sa.CheckConstraint(
            "hp >= 0 AND max_hp > 0 AND hp <= max_hp", name="ck_dungeon_run_member_hp"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(combat_configuration) = 'object'", name="ck_dungeon_run_member_config"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(run_state) = 'object'", name="ck_dungeon_run_member_state"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(contribution) = 'object'", name="ck_dungeon_run_member_contribution"
        ),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
            name="fk_dungeon_run_members_character_id_characters",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["dungeon_runs.id"],
            name="fk_dungeon_run_members_run_id_dungeon_runs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["foreground_activity_id"],
            ["game_activities.id"],
            name="fk_dungeon_run_members_foreground_activity_id_game_activities",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("run_id", "character_id", name="pk_dungeon_run_members"),
        sa.UniqueConstraint("foreground_activity_id", name="uq_dungeon_run_member_foreground"),
        sa.UniqueConstraint("run_id", "position", name="uq_dungeon_run_member_position"),
    )
    op.create_index(
        "uq_dungeon_active_member",
        "dungeon_run_members",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('active','defeated')"),
    )
    op.create_table(
        "dungeon_run_encounters",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_ordinal", sa.Integer(), nullable=False),
        sa.Column("definition_id", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column(
            "progress",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("reward_settled", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "encounter_ordinal >= 1", name="ck_dungeon_encounter_ordinal"
        ),
        sa.CheckConstraint(
            "status IN ('pending','active','completed')", name="ck_dungeon_encounter_status"
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_dungeon_encounter_attempt_count"),
        sa.CheckConstraint(
            "jsonb_typeof(progress) = 'object'", name="ck_dungeon_encounter_progress"
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"], ["game_activities.id"], name="fk_dungeon_encounter_activity"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["dungeon_runs.id"],
            name="fk_dungeon_run_encounters_run_id_dungeon_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id", "encounter_ordinal", name="pk_dungeon_run_encounters"),
        sa.UniqueConstraint("activity_id", name="uq_dungeon_encounter_activity"),
    )
    op.create_table(
        "dungeon_pity_states",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("legendary_plus_points", sa.Integer(), nullable=False),
        sa.Column("mythic_points", sa.Integer(), nullable=False),
        sa.CheckConstraint("legendary_plus_points >= 0", name="ck_dungeon_pity_legendary_points"),
        sa.CheckConstraint("mythic_points >= 0", name="ck_dungeon_pity_mythic_points"),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
            name="fk_dungeon_pity_states_character_id_characters",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("character_id", name="pk_dungeon_pity_states"),
    )
    op.create_table(
        "dungeon_lobbies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dungeon_family_id", sa.String(length=96), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("leader_character_id", sa.Uuid(), nullable=False),
        sa.Column("state_version", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmation_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("mode IN ('invite','matchmaking')", name="ck_dungeon_lobby_mode"),
        sa.CheckConstraint(
            "status IN ('forming','confirming','started','cancelled','expired')",
            name="ck_dungeon_lobby_status",
        ),
        sa.CheckConstraint("state_version >= 0", name="ck_dungeon_lobby_state_version"),
        sa.ForeignKeyConstraint(
            ["leader_character_id"],
            ["characters.id"],
            name="fk_dungeon_lobbies_leader_character_id_characters",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["dungeon_runs.id"], name="fk_dungeon_lobbies_run_id_dungeon_runs",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dungeon_lobbies"),
    )
    op.create_index(
        "ix_dungeon_lobbies_open",
        "dungeon_lobbies",
        ["dungeon_family_id", "difficulty", "created_at"],
        unique=False,
        postgresql_where=sa.text("status IN ('forming','confirming')"),
    )
    op.create_table(
        "dungeon_lobby_members",
        sa.Column("lobby_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("foreground_activity_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("position BETWEEN 1 AND 4", name="ck_dungeon_lobby_position"),
        sa.CheckConstraint(
            "status IN ('invited','joined','queued','matched','confirmed','declined','left')",
            name="ck_dungeon_lobby_member_status",
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"],
            name="fk_dungeon_lobby_members_character_id_characters", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lobby_id"], ["dungeon_lobbies.id"],
            name="fk_dungeon_lobby_members_lobby_id_dungeon_lobbies", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["foreground_activity_id"], ["game_activities.id"],
            name="fk_dungeon_lobby_members_foreground_activity_id_game_activities",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("lobby_id", "character_id", name="pk_dungeon_lobby_members"),
        sa.UniqueConstraint(
            "foreground_activity_id", name="uq_dungeon_lobby_member_foreground"
        ),
        sa.UniqueConstraint("lobby_id", "position", name="uq_dungeon_lobby_position"),
    )
    op.create_index(
        "uq_dungeon_open_lobby_member",
        "dungeon_lobby_members",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('invited','joined','queued','matched','confirmed')"
        ),
    )
    op.create_table(
        "dungeon_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lobby_id", sa.Uuid(), nullable=False),
        sa.Column("inviter_character_id", sa.Uuid(), nullable=False),
        sa.Column("invitee_character_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("state_version", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','accepted','declined','cancelled','expired')",
            name="ck_dungeon_invite_status",
        ),
        sa.CheckConstraint("state_version >= 0", name="ck_dungeon_invite_version"),
        sa.ForeignKeyConstraint(
            ["invitee_character_id"], ["characters.id"],
            name="fk_dungeon_invites_invitee_character_id_characters", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inviter_character_id"], ["characters.id"],
            name="fk_dungeon_invites_inviter_character_id_characters", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lobby_id"], ["dungeon_lobbies.id"],
            name="fk_dungeon_invites_lobby_id_dungeon_lobbies", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dungeon_invites"),
        sa.UniqueConstraint("lobby_id", "invitee_character_id", name="uq_dungeon_invite_target"),
    )
    op.create_index(
        "ix_dungeon_invites_pending",
        "dungeon_invites",
        ["invitee_character_id", "expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "dungeon_match_queue",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("dungeon_family_id", sa.String(length=96), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("lobby_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('queued','matched','cancelled','expired')",
            name="ck_dungeon_match_queue_status",
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"],
            name="fk_dungeon_match_queue_character_id_characters", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lobby_id"], ["dungeon_lobbies.id"],
            name="fk_dungeon_match_queue_lobby_id_dungeon_lobbies", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("character_id", name="pk_dungeon_match_queue"),
    )
    op.create_index(
        "ix_dungeon_match_queue_grouping",
        "dungeon_match_queue",
        ["dungeon_family_id", "difficulty", "created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'queued'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "dungeon_match_queue",
        "dungeon_invites",
        "dungeon_lobby_members",
        "dungeon_lobbies",
        "dungeon_run_encounters",
        "dungeon_run_members",
        "dungeon_runs",
        "dungeon_pity_states",
    ):
        bind.exec_driver_sql(f'LOCK TABLE "{table}" IN SHARE ROW EXCLUSIVE MODE')
        if bind.scalar(sa.text(f'SELECT EXISTS (SELECT 1 FROM "{table}")')):
            raise RuntimeError(f"Cannot downgrade while {table} contains dungeon state")
    op.drop_index("ix_dungeon_match_queue_grouping", table_name="dungeon_match_queue")
    op.drop_table("dungeon_match_queue")
    op.drop_index("ix_dungeon_invites_pending", table_name="dungeon_invites")
    op.drop_table("dungeon_invites")
    op.drop_index("uq_dungeon_open_lobby_member", table_name="dungeon_lobby_members")
    op.drop_table("dungeon_lobby_members")
    op.drop_index("ix_dungeon_lobbies_open", table_name="dungeon_lobbies")
    op.drop_table("dungeon_lobbies")
    op.drop_table("dungeon_run_encounters")
    op.drop_index("uq_dungeon_active_member", table_name="dungeon_run_members")
    op.drop_table("dungeon_run_members")
    op.drop_index("ix_dungeon_runs_active_updated", table_name="dungeon_runs")
    op.drop_table("dungeon_runs")
    op.drop_table("dungeon_pity_states")
