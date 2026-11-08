"""Store Consumables and Runes in the Warehouse.

Revision ID: 20261107_0033
Revises: 20261026_0032
"""

import sqlalchemy as sa

from alembic import op

revision = "20261107_0033"
down_revision = "20261026_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouse_consumable_stacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("consumable_id", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity BETWEEN 1 AND 99", name="ck_warehouse_consumable_quantity"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_warehouse_consumable_character",
        "warehouse_consumable_stacks",
        ["character_id"],
    )
    op.create_table(
        "warehouse_rune_stacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("family", sa.String(length=32), nullable=False),
        sa.Column("rarity", sa.String(length=16), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("potency", sa.String(length=24), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("bound", sa.Boolean(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_warehouse_rune_quantity"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_warehouse_rune_character",
        "warehouse_rune_stacks",
        ["character_id"],
    )


def downgrade() -> None:
    # Refuse to destroy stored items: a player's stacks would vanish without a trace.
    connection = op.get_bind()
    for table in ("warehouse_consumable_stacks", "warehouse_rune_stacks"):
        if connection.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError(f"{table} still holds player items; move them before downgrading.")
    op.drop_index("ix_warehouse_rune_character", table_name="warehouse_rune_stacks")
    op.drop_table("warehouse_rune_stacks")
    op.drop_index("ix_warehouse_consumable_character", table_name="warehouse_consumable_stacks")
    op.drop_table("warehouse_consumable_stacks")
