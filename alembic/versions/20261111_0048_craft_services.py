"""craft services: public Crafting Services in the Personal Shop (§27.3)

Revision ID: 20261111_0047
Revises: 20261111_0045
Create Date: 2026-11-11 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261111_0047"
down_revision: str | None = "20261111_0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "craft_service_offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("recipe_id", sa.String(length=96), nullable=False),
        sa.Column("profession_id", sa.String(length=32), nullable=False),
        sa.Column("recipe_signature", sa.String(length=64), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column("service_offer_revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("gross_total", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("fee_total", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("executions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fee_bps", sa.Integer(), server_default="500", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("price > 0", name="ck_craft_service_offer_price"),
        sa.CheckConstraint("service_offer_revision >= 1", name="ck_craft_service_offer_revision"),
        sa.CheckConstraint(
            "status IN ('active','cancelled','expired','republished','closed')",
            name="ck_craft_service_offer_status",
        ),
        sa.CheckConstraint("fee_bps BETWEEN 0 AND 500", name="ck_craft_service_offer_fee_bps"),
        sa.ForeignKeyConstraint(["shop_id"], ["player_shops.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_craft_service_offer_shop_status",
        "craft_service_offers",
        ["shop_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_craft_service_offer_active_expiry",
        "craft_service_offers",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "craft_service_price_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("owner_character_id", sa.Uuid(), nullable=True),
        sa.Column("old_price", sa.BigInteger(), nullable=False),
        sa.Column("new_price", sa.BigInteger(), nullable=False),
        sa.Column("service_offer_revision", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["craft_service_offers.id"]),
        sa.ForeignKeyConstraint(["owner_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_craft_service_price_change_offer",
        "craft_service_price_changes",
        ["offer_id"],
        unique=False,
    )
    op.create_table(
        "craft_service_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("client_character_id", sa.Uuid(), nullable=True),
        sa.Column("artisan_character_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_id", sa.String(length=96), nullable=False),
        sa.Column("service_offer_revision", sa.Integer(), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column("recipe_cost", sa.BigInteger(), nullable=False),
        sa.Column("item_level", sa.Integer(), nullable=True),
        sa.Column("preview_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_key", sa.String(length=80), nullable=False),
        sa.Column("seed", sa.String(length=120), nullable=False),
        sa.Column("gross", sa.BigInteger(), nullable=True),
        sa.Column("fee", sa.BigInteger(), nullable=True),
        sa.Column("net", sa.BigInteger(), nullable=True),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="preview", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('preview','committed')", name="ck_craft_service_order_status"
        ),
        sa.ForeignKeyConstraint(["offer_id"], ["craft_service_offers.id"]),
        sa.ForeignKeyConstraint(["client_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["artisan_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", name="uq_craft_service_order_source_key"),
    )
    op.create_index(
        "ix_craft_service_order_offer", "craft_service_orders", ["offer_id"], unique=False
    )
    op.create_index(
        "ix_craft_service_order_preview_expiry",
        "craft_service_orders",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'preview'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_craft_service_order_preview_expiry",
        table_name="craft_service_orders",
        postgresql_where=sa.text("status = 'preview'"),
    )
    op.drop_index("ix_craft_service_order_offer", table_name="craft_service_orders")
    op.drop_table("craft_service_orders")
    op.drop_index("ix_craft_service_price_change_offer", table_name="craft_service_price_changes")
    op.drop_table("craft_service_price_changes")
    op.drop_index(
        "ix_craft_service_offer_active_expiry",
        table_name="craft_service_offers",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_index("ix_craft_service_offer_shop_status", table_name="craft_service_offers")
    op.drop_table("craft_service_offers")
