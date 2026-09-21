"""Persist vigor, brazier discovery, achievements, quests and world state."""

import sqlalchemy as sa

from alembic import op

revision = "20260920_0004"
down_revision = "20260920_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE characters SET ruleset_version = 'gdd-1.4.3-baseline-1.0' "
        "WHERE ruleset_version = 'gdd-1.4.2-baseline-1.0' "
        "AND stage IN ('cinzas_na_estrada:intro', 'cinzas_na_estrada:ready_for_first_brazier')"
    )
    op.add_column(
        "characters", sa.Column("vigor", sa.Integer(), nullable=False, server_default="100")
    )
    op.add_column(
        "characters", sa.Column("max_vigor", sa.Integer(), nullable=False, server_default="100")
    )
    op.create_check_constraint(
        "ck_character_vigor", "characters", "vigor BETWEEN 0 AND max_vigor AND max_vigor = 100"
    )
    op.create_table(
        "braziers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("brazier_id", sa.String(64), nullable=False),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "brazier_id", name="uq_character_brazier"),
    )
    op.create_table(
        "achievements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("achievement_id", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "achievement_id", name="uq_character_achievement"),
    )
    op.create_table(
        "quests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("quest_id", sa.String(32), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content_version", sa.String(32), nullable=False, server_default="tdo-1.0.1"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "quest_id", name="uq_character_quest"),
        sa.CheckConstraint("status IN ('active','completed')", name="ck_quest_status"),
        sa.CheckConstraint("step >= 1", name="ck_quest_step"),
    )
    op.create_table(
        "world_states",
        sa.Column("character_id", sa.Uuid(), primary_key=True),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("location", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
    )
    op.execute(
        "INSERT INTO braziers (id, character_id, brazier_id) "
        "SELECT gen_random_uuid(), id, 'tdo.brazier.estrada' FROM characters "
        "WHERE stage = 'cinzas_na_estrada:ready_for_first_brazier' "
        "ON CONFLICT (character_id, brazier_id) DO NOTHING"
    )
    op.execute(
        "INSERT INTO world_states (character_id, region, location) "
        "SELECT id, 'Terras do Ocaso', 'Estrada das Cinzas' FROM characters "
        "WHERE stage = 'cinzas_na_estrada:ready_for_first_brazier' "
        "ON CONFLICT (character_id) DO NOTHING"
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM braziers) OR EXISTS "
            "(SELECT 1 FROM achievements) OR EXISTS (SELECT 1 FROM quests) "
            "OR EXISTS (SELECT 1 FROM world_states)"
        )
    ):
        raise RuntimeError("Cannot downgrade populated brazier/menu state")
    op.drop_table("world_states")
    op.drop_table("quests")
    op.drop_table("achievements")
    op.drop_table("braziers")
    op.drop_constraint("ck_character_vigor", "characters", type_="check")
    op.drop_column("characters", "max_vigor")
    op.drop_column("characters", "vigor")
