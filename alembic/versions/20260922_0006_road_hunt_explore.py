"""Road hunt and exploration persistence."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260922_0006"
down_revision = "20260921_0005"
branch_labels = None
depends_on = None


def _uuid():
    return sa.Uuid()


def upgrade() -> None:
    op.create_table(
        "hunt_contexts",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("game_activity_id", _uuid(), nullable=False),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("creature_id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("enemy_level", sa.Integer(), nullable=False),
        sa.Column("variant", sa.String(24)),
        sa.Column("seed", sa.String(128), nullable=False),
        sa.Column("loot_profile", sa.String(32), nullable=False, server_default="hunt"),
        sa.ForeignKeyConstraint(["game_activity_id"], ["game_activities.id"]),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("game_activity_id", name="uq_hunt_activity"),
        sa.CheckConstraint("enemy_level >= 1", name="ck_hunt_enemy_level"),
    )
    op.create_table(
        "exploration_attempts",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("local_id", sa.String(64), nullable=False),
        sa.Column("ruleset_version", sa.String(48), nullable=False),
        sa.Column("seed", sa.String(128), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("result_id", sa.String(96), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("state_version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("progress", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("activity_id", _uuid()),
        sa.Column("encounter_id", _uuid()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.ForeignKeyConstraint(["activity_id"], ["game_activities.id"]),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"]),
        sa.UniqueConstraint("character_id", "id", name="uq_exploration_character"),
        sa.CheckConstraint("state_version >= 0", name="ck_exploration_version"),
        sa.CheckConstraint(
            "status IN ('active','completed','failed')", name="ck_exploration_status"
        ),
    )
    op.create_table(
        "bestiary_entries",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("creature_id", sa.String(64), nullable=False),
        sa.Column("bkp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stage", sa.String(32), nullable=False, server_default="observed"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "creature_id", name="uq_character_bestiary"),
    )
    op.create_table(
        "bestiary_evidence",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("creature_id", sa.String(64), nullable=False),
        sa.Column("evidence_id", sa.String(96), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint(
            "character_id", "creature_id", "evidence_id", name="uq_bestiary_evidence"
        ),
    )
    op.create_table(
        "codex_fragments",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("entry_id", sa.String(96), nullable=False),
        sa.Column("fragment_id", sa.String(96), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "fragment_id", name="uq_character_fragment"),
    )
    op.create_table(
        "equipment_items",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("source_key", sa.String(160), nullable=False, unique=True),
        sa.Column("item_name", sa.String(120), nullable=False),
        sa.Column("rarity", sa.String(16), nullable=False),
        sa.Column("slot", sa.String(24), nullable=False),
        sa.Column("item_level", sa.Integer(), nullable=False),
        sa.Column("bound", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
    )
    op.create_table(
        "rune_stacks",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("family", sa.String(32), nullable=False),
        sa.Column("rarity", sa.String(16), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("potency", sa.String(24), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("bound", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint(
            "character_id", "family", "rarity", "grade", "bound", name="uq_character_rune"
        ),
    )
    op.create_table(
        "pending_items",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("source_key", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "source_key", name="uq_character_pending_source"),
        sa.CheckConstraint("quantity > 0", name="ck_pending_quantity"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = (
        "pending_items",
        "rune_stacks",
        "equipment_items",
        "codex_fragments",
        "bestiary_evidence",
        "bestiary_entries",
        "exploration_attempts",
        "hunt_contexts",
    )
    for table in tables:
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError("Cannot downgrade populated road hunt/explore state")
    for table in tables:
        op.drop_table(table)
