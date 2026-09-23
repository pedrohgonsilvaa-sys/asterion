"""Ronda de Caça persistence and consumable inventory."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260922_0007"
down_revision = "20260922_0006"
branch_labels = None
depends_on = None


def _uuid():
    return sa.Uuid()


def upgrade() -> None:
    op.create_table(
        "consumable_stacks",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("consumable_id", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "consumable_id", name="uq_character_consumable"),
        sa.CheckConstraint("quantity BETWEEN 0 AND 99", name="ck_consumable_quantity"),
    )
    op.create_table(
        "hunt_rounds",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("character_id", _uuid(), nullable=False),
        sa.Column("activity_id", _uuid(), unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="preparing"),
        sa.Column("end_reason", sa.String(32)),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("completed_encounters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state_version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("seed", sa.String(128), nullable=False),
        sa.Column("prepared_heal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prepared_purify", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "config_snapshot",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("next_resolution_at", sa.DateTime(timezone=True)),
        sa.Column("result_acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("elite_engaged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.ForeignKeyConstraint(["activity_id"], ["game_activities.id"]),
        sa.CheckConstraint("batch_size IN (5, 10, 20)", name="ck_hunt_round_batch"),
        sa.CheckConstraint("completed_encounters >= 0", name="ck_hunt_round_completed"),
        sa.CheckConstraint("state_version >= 0", name="ck_hunt_round_version"),
        sa.CheckConstraint(
            "status IN ('preparing','active','completed','cancelled',"
            "'defeated','ended','interrupted')",
            name="ck_hunt_round_status",
        ),
    )
    op.create_index(
        "uq_open_hunt_round",
        "hunt_rounds",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('preparing','active','interrupted')"),
    )
    op.create_table(
        "hunt_round_encounters",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("round_id", _uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("activity_id", _uuid(), unique=True),
        sa.Column("combat_id", _uuid(), nullable=False, unique=True),
        sa.Column("seed", sa.String(160), nullable=False),
        sa.Column("creature_id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("enemy_level", sa.Integer(), nullable=False),
        sa.Column("variant", sa.String(24)),
        sa.Column("status", sa.String(24), nullable=False, server_default="materialized"),
        sa.Column("state_version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("combat_snapshot", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["round_id"], ["hunt_rounds.id"]),
        sa.ForeignKeyConstraint(["activity_id"], ["game_activities.id"]),
        sa.UniqueConstraint("round_id", "ordinal", name="uq_hunt_round_ordinal"),
        sa.CheckConstraint("ordinal >= 1", name="ck_hunt_round_encounter_ordinal"),
        sa.CheckConstraint("enemy_level >= 1", name="ck_hunt_round_enemy_level"),
        sa.CheckConstraint(
            "status IN ('materialized','completed','defeated','interrupted','elite_combat')",
            name="ck_hunt_round_encounter_status",
        ),
        sa.CheckConstraint("state_version >= 0", name="ck_hunt_round_encounter_version"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("hunt_round_encounters", "hunt_rounds", "consumable_stacks"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError("Cannot downgrade populated Ronda de Caça state")
    op.drop_table("hunt_round_encounters")
    op.drop_index("uq_open_hunt_round", table_name="hunt_rounds")
    op.drop_table("hunt_rounds")
    op.drop_table("consumable_stacks")
