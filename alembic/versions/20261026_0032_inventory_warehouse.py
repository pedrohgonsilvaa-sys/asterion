"""Add canonical Warehouse storage and idempotent transfer receipts.

Revision ID: 20261026_0032
Revises: 20261023_0031
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261026_0032"
down_revision = "20261023_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouse_equipment_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("item_name", sa.String(length=120), nullable=False),
        sa.Column("rarity", sa.String(length=16), nullable=False),
        sa.Column("slot", sa.String(length=24), nullable=False),
        sa.Column("item_level", sa.Integer(), nullable=False),
        sa.Column("bound", sa.Boolean(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "stored_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "character_id", "source_key", name="uq_warehouse_equipment_source"
        ),
    )
    op.create_index(
        "ix_warehouse_equipment_character",
        "warehouse_equipment_items",
        ["character_id"],
    )
    op.create_table(
        "warehouse_material_stacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.String(length=96), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("bound", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "quantity BETWEEN 1 AND 999", name="ck_warehouse_material_quantity"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_warehouse_material_character",
        "warehouse_material_stacks",
        ["character_id"],
    )
    op.create_table(
        "warehouse_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="preview"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "direction IN ('deposit','withdraw','claim_pending')",
            name="ck_warehouse_operation_direction",
        ),
        sa.CheckConstraint(
            "kind IN ('equipment','material','rune','consumable')",
            name="ck_warehouse_operation_kind",
        ),
        sa.CheckConstraint(
            "status IN ('preview','committed','cancelled','stale','expired')",
            name="ck_warehouse_operation_status",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_warehouse_operation_quantity"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_warehouse_operation_character_status",
        "warehouse_operations",
        ["character_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_warehouse_operation_character_status", table_name="warehouse_operations"
    )
    op.drop_table("warehouse_operations")
    op.drop_index("ix_warehouse_material_character", table_name="warehouse_material_stacks")
    op.drop_table("warehouse_material_stacks")
    op.drop_index("ix_warehouse_equipment_character", table_name="warehouse_equipment_items")
    op.drop_table("warehouse_equipment_items")
