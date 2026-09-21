"""Persist vigor, brazier discovery, achievements, quests and world state."""

import sqlalchemy as sa

from alembic import op

revision = "20260920_0004"
down_revision = "20260920_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters", sa.Column("vigor", sa.Integer(), nullable=False, server_default="100")
    )
    op.add_column(
        "characters", sa.Column("max_vigor", sa.Integer(), nullable=False, server_default="100")
    )
    op.create_check_constraint(
        "ck_character_vigor", "characters", "vigor BETWEEN 0 AND max_vigor AND max_vigor = 100"
    )
    for table, cols, uniques in (
        (
            "braziers",
            [
                ("id", sa.Uuid(), True),
                ("character_id", sa.Uuid(), False),
                ("brazier_id", sa.String(64), False),
            ],
            "uq_character_brazier",
        ),
        (
            "achievements",
            [
                ("id", sa.Uuid(), True),
                ("character_id", sa.Uuid(), False),
                ("achievement_id", sa.String(64), False),
            ],
            "uq_character_achievement",
        ),
    ):
        op.create_table(
            table,
            *[sa.Column(name, typ, primary_key=pk, nullable=not pk) for name, typ, pk in cols],
            sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
            sa.UniqueConstraint("character_id", cols[-1][0], name=uniques),
        )
    op.create_table(
        "quests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("quest_id", sa.String(32), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "quest_id", name="uq_character_quest"),
    )
    op.create_table(
        "world_states",
        sa.Column("character_id", sa.Uuid(), primary_key=True),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("location", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
    )


def downgrade() -> None:
    op.drop_table("world_states")
    op.drop_table("quests")
    op.drop_table("achievements")
    op.drop_table("braziers")
    op.drop_constraint("ck_character_vigor", "characters", type_="check")
    op.drop_column("characters", "max_vigor")
    op.drop_column("characters", "vigor")
