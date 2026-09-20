"""Foreground duels, audited grants and minimal character progression.

Revision ID: 20260920_0003
Revises: 20260920_0002
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260920_0003"
down_revision = "20260920_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters", sa.Column("level", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "characters", sa.Column("xp", sa.BigInteger(), nullable=False, server_default="0")
    )
    op.add_column("characters", sa.Column("hp", sa.Numeric(), nullable=True))
    op.add_column("characters", sa.Column("max_hp", sa.Numeric(), nullable=True))
    # Frozen Nv.1 HP from the source, preserving the exact racial composition.
    op.execute("""
        UPDATE characters SET max_hp =
          (CASE character_class
             WHEN 'sentinela' THEN 702 WHEN 'errante' THEN 618 WHEN 'vigia' THEN 631
             WHEN 'tecelao' THEN 605 WHEN 'oraculo' THEN 644 WHEN 'luminar' THEN 670
           END) * (CASE WHEN race = 'remanescente' THEN 1.015 ELSE 1 END)
    """)
    op.execute("UPDATE characters SET hp = max_hp")
    op.execute("""
        UPDATE characters SET ruleset_version = 'gdd-1.4.2-baseline-1.0'
        WHERE stage = 'cinzas_na_estrada:intro'
          AND ruleset_version = 'gdd-1.4.1-baseline-1.0'
    """)
    op.alter_column("characters", "hp", nullable=False)
    op.alter_column("characters", "max_hp", nullable=False)
    op.create_check_constraint(
        "ck_character_progress", "characters", "level BETWEEN 1 AND 60 AND xp >= 0"
    )
    op.create_check_constraint(
        "ck_character_hp", "characters", "hp >= 0 AND hp <= max_hp AND max_hp > 0"
    )
    op.create_table(
        "game_activities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("character_id", sa.Uuid(), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("content_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("state_version", sa.BigInteger(), nullable=False),
        sa.Column("ruleset_version", sa.String(48), nullable=False),
        sa.UniqueConstraint("id", "character_id", name="uq_activity_character"),
        sa.CheckConstraint("status IN ('active','completed','failed')", name="ck_activity_status"),
        sa.CheckConstraint("state_version >= 0", name="ck_activity_version"),
    )
    op.create_index(
        "uq_active_foreground",
        "game_activities",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "uq_first_combat_occurrence",
        "game_activities",
        ["character_id", "content_id"],
        unique=True,
        postgresql_where=sa.text("content_id = 'prologue_first_combat'"),
    )
    op.create_table(
        "encounters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "game_activity_id",
            sa.Uuid(),
            sa.ForeignKey("game_activities.id"),
            nullable=False,
            unique=True,
        ),
    )
    op.create_table(
        "combats",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "encounter_id", sa.Uuid(), sa.ForeignKey("encounters.id"), nullable=False, unique=True
        ),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "reward_grants",
        sa.Column("game_activity_id", sa.Uuid(), primary_key=True),
        sa.Column("character_id", sa.Uuid(), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("xp", sa.BigInteger(), nullable=False),
        sa.Column("ruleset_version", sa.String(48), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["game_activity_id", "character_id"],
            ["game_activities.id", "game_activities.character_id"],
            name="fk_grant_activity_character",
        ),
        sa.CheckConstraint("xp >= 0", name="ck_grant_xp"),
    )
    op.create_index("ix_reward_grants_character_id", "reward_grants", ["character_id"])


def downgrade() -> None:
    # Destructive reversal is only safe before any gameplay has used these tables.
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM game_activities)")):
        raise RuntimeError("Cannot downgrade populated combat state; restore an explicit backup")
    op.drop_index("ix_reward_grants_character_id", table_name="reward_grants")
    op.drop_table("reward_grants")
    op.drop_table("combats")
    op.drop_table("encounters")
    op.drop_index("uq_first_combat_occurrence", table_name="game_activities")
    op.drop_index("uq_active_foreground", table_name="game_activities")
    op.drop_table("game_activities")
    op.drop_constraint("ck_character_hp", "characters")
    op.drop_constraint("ck_character_progress", "characters")
    for column in ("max_hp", "hp", "xp", "level"):
        op.drop_column("characters", column)
