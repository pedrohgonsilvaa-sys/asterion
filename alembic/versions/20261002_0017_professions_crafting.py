"""Persist active profession progression and idempotent crafting receipts."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261002_0017"
down_revision = "20261001_0016"
branch_labels = None
depends_on = None

# Dungeon drops before C2 stored the right rune grade but always wrote the
# Grade I potency. Only these exact legacy values are eligible for correction.
# Current values are frozen here so this historical migration stays stable.
_LEGACY_RUNE_POTENCIES = (
    ("Brasa", "Rara", "0.35%", "0.40%", "0.40%", "0.45%", "0.55%", "0.60%"),
    ("Brasa", "Épica", "0.45%", "0.50%", "0.55%", "0.65%", "0.70%", "0.80%"),
    ("Brasa", "Lendária", "0.55%", "0.60%", "0.70%", "0.80%", "0.90%", "1.00%"),
    ("Pedra", "Rara", "0.55%", "0.60%", "0.70%", "0.80%", "0.90%", "1.00%"),
    ("Pedra", "Épica", "0.80%", "0.90%", "1.00%", "1.10%", "1.25%", "1.40%"),
    ("Pedra", "Lendária", "1.00%", "1.10%", "1.25%", "1.40%", "1.60%", "1.80%"),
    ("Caminhante", "Rara", "0.55%", "0.60%", "0.70%", "0.80%", "0.90%", "1.00%"),
    ("Caminhante", "Épica", "0.80%", "0.90%", "1.00%", "1.10%", "1.25%", "1.40%"),
    ("Caminhante", "Lendária", "1.00%", "1.10%", "1.25%", "1.40%", "1.60%", "1.80%"),
    (
        "Fresta", "Rara", "0.25 p.p.", "0.25 p.p.", "0.25 p.p.",
        "0.50 p.p.", "0.50 p.p.", "0.50 p.p.",
    ),
    (
        "Fresta", "Épica", "0.50 p.p.", "0.50 p.p.", "0.50 p.p.",
        "0.50 p.p.", "0.75 p.p.", "0.75 p.p.",
    ),
    (
        "Fresta", "Lendária", "0.50 p.p.", "0.50 p.p.", "0.75 p.p.",
        "0.75 p.p.", "1.00 p.p.", "1.00 p.p.",
    ),
    (
        "Presságio", "Rara", "0.25 p.p.", "0.25 p.p.", "0.25 p.p.",
        "0.50 p.p.", "0.50 p.p.", "0.50 p.p.",
    ),
    (
        "Presságio", "Épica", "0.50 p.p.", "0.50 p.p.", "0.50 p.p.",
        "0.50 p.p.", "0.75 p.p.", "0.75 p.p.",
    ),
    (
        "Presságio", "Lendária", "0.50 p.p.", "0.50 p.p.", "0.75 p.p.",
        "0.75 p.p.", "1.00 p.p.", "1.00 p.p.",
    ),
    ("Persistência", "Rara", "0.35%", "0.40%", "0.40%", "0.45%", "0.55%", "0.60%"),
    ("Persistência", "Épica", "0.45%", "0.50%", "0.55%", "0.65%", "0.70%", "0.80%"),
    ("Persistência", "Lendária", "0.55%", "0.60%", "0.70%", "0.80%", "0.90%", "1.00%"),
    (
        "Desvio", "Rara", "0.25 p.p.", "0.25 p.p.", "0.25 p.p.",
        "0.25 p.p.", "0.25 p.p.", "0.25 p.p.",
    ),
    (
        "Desvio", "Épica", "0.25 p.p.", "0.25 p.p.", "0.25 p.p.",
        "0.50 p.p.", "0.50 p.p.", "0.50 p.p.",
    ),
    (
        "Desvio", "Lendária", "0.25 p.p.", "0.25 p.p.", "0.25 p.p.",
        "0.50 p.p.", "0.50 p.p.", "0.50 p.p.",
    ),
    (
        "Guarda", "Rara", "0.25 p.p.", "0.25 p.p.", "0.25 p.p.",
        "0.50 p.p.", "0.50 p.p.", "0.50 p.p.",
    ),
    (
        "Guarda", "Épica", "0.50 p.p.", "0.50 p.p.", "0.50 p.p.",
        "0.50 p.p.", "0.75 p.p.", "0.75 p.p.",
    ),
    (
        "Guarda", "Lendária", "0.50 p.p.", "0.50 p.p.", "0.75 p.p.",
        "0.75 p.p.", "1.00 p.p.", "1.00 p.p.",
    ),
)


def _backfill_legacy_rune_potencies(bind) -> None:
    values_sql = []
    parameters = {}
    for row_index, row in enumerate(_LEGACY_RUNE_POTENCIES):
        placeholders = []
        for column_index, value in enumerate(row):
            parameter = f"v_{row_index}_{column_index}"
            placeholders.append(f":{parameter}")
            parameters[parameter] = value
        values_sql.append("(" + ", ".join(placeholders) + ")")

    bind.execute(
        sa.text(
            "UPDATE rune_stacks AS stack "
            "SET potency = CASE stack.grade "
            "WHEN 2 THEN legacy.grade_2 WHEN 3 THEN legacy.grade_3 "
            "WHEN 4 THEN legacy.grade_4 WHEN 5 THEN legacy.grade_5 "
            "WHEN 6 THEN legacy.grade_6 END "
            "FROM (VALUES "
            + ", ".join(values_sql)
            + ") AS legacy(family, rarity, grade_i, grade_2, grade_3, grade_4, grade_5, grade_6) "
            "WHERE stack.grade BETWEEN 2 AND 6 "
            "AND stack.family = legacy.family AND stack.rarity = legacy.rarity "
            "AND stack.potency = legacy.grade_i"
        ),
        parameters,
    )


def upgrade() -> None:
    op.create_table(
        "character_professions",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.String(length=12), nullable=False),
        sa.Column("profession_id", sa.String(length=24), nullable=False),
        sa.Column("level", sa.Integer(), server_default="1", nullable=False),
        sa.Column("pxp", sa.BigInteger(), server_default="0", nullable=False),
        sa.CheckConstraint("slot IN ('primary','secondary')", name="ck_character_profession_slot"),
        sa.CheckConstraint(
            "profession_id IN ('blacksmith','artificer','alchemist','leatherworker','jeweler')",
            name="ck_character_profession_id",
        ),
        sa.CheckConstraint("level BETWEEN 1 AND 30", name="ck_character_profession_level"),
        sa.CheckConstraint(
            "slot != 'secondary' OR level <= 15",
            name="ck_character_profession_secondary_cap",
        ),
        sa.CheckConstraint("pxp >= 0", name="ck_character_profession_pxp"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id", "slot", name="pk_character_professions"),
        sa.UniqueConstraint("character_id", "profession_id", name="uq_character_profession"),
    )
    op.create_table(
        "crafting_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.String(length=96), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="preview", nullable=False),
        sa.Column("preview_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("seed", sa.String(length=128), nullable=False),
        sa.Column("output_kind", sa.String(length=24), nullable=True),
        sa.Column(
            "output_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('preview','committed','cancelled','expired')",
            name="ck_crafting_receipt_status",
        ),
        sa.CheckConstraint(
            "output_payload IS NULL OR jsonb_typeof(output_payload) = 'object'",
            name="ck_crafting_receipt_payload",
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_crafting_receipts"),
        sa.UniqueConstraint("character_id", "source_key", name="uq_character_craft_source"),
    )
    op.create_index(
        "ix_crafting_receipts_character_status",
        "crafting_receipts",
        ["character_id", "status"],
        unique=False,
    )
    _backfill_legacy_rune_potencies(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("crafting_receipts", "character_professions"):
        bind.exec_driver_sql(f"LOCK TABLE {table} IN SHARE ROW EXCLUSIVE MODE")
        if bind.scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")):
            raise RuntimeError(f"Cannot downgrade while {table} contains character data")
    op.drop_index("ix_crafting_receipts_character_status", table_name="crafting_receipts")
    op.drop_table("crafting_receipts")
    op.drop_table("character_professions")
