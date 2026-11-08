"""Add Personal Shops, Market listings and Direct Trade.

Revision ID: 20261108_0037
Revises: 20261108_0036
Create Date: 2026-11-08 13:39:53.061974
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261108_0037"
down_revision: str | None = "20261108_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "player_shops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_character_id", sa.Uuid(), nullable=True),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("public_name", sa.String(length=36), nullable=True),
        sa.Column("description", sa.String(length=240), nullable=True),
        sa.Column("last_promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_player_shop_code"),
        sa.UniqueConstraint("owner_character_id"),
    )
    op.create_table(
        "shop_search_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shop_search_character_time",
        "shop_search_attempts",
        ["character_id", "attempted_at"],
        unique=False,
    )
    op.create_table(
        "trade_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("initiator_character_id", sa.Uuid(), nullable=True),
        sa.Column("partner_character_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("initiator_steps", sa.Integer(), server_default="0", nullable=False),
        sa.Column("partner_steps", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_reason", sa.String(length=32), nullable=True),
        sa.CheckConstraint(
            "status IN ('invited','open','committed','cancelled','expired','declined')",
            name="ck_trade_session_status",
        ),
        sa.ForeignKeyConstraint(["initiator_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_trade_session_initiator", "trade_sessions", ["initiator_character_id"], unique=False
    )
    op.create_index(
        "ix_trade_session_live",
        "trade_sessions",
        ["status", "last_activity_at"],
        unique=False,
        postgresql_where=sa.text("status IN ('invited','open')"),
    )
    op.create_index(
        "ix_trade_session_partner", "trade_sessions", ["partner_character_id"], unique=False
    )
    op.create_table(
        "market_listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("item_kind", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("rarity", sa.String(length=16), nullable=True),
        sa.Column("item_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("initial_quantity", sa.Integer(), nullable=False),
        sa.Column("remaining_quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("terms_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("gross_sold_total", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("fee_charged_total", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "item_kind IN ('equipment','material','consumable','rune')",
            name="ck_market_listing_kind",
        ),
        sa.CheckConstraint(
            "status IN ('active','sold_out','removed','expired','closed')",
            name="ck_market_listing_status",
        ),
        sa.CheckConstraint(
            "remaining_quantity >= 0 AND remaining_quantity <= initial_quantity",
            name="ck_market_listing_quantity",
        ),
        sa.CheckConstraint("unit_price > 0", name="ck_market_listing_price"),
        sa.ForeignKeyConstraint(
            ["shop_id"],
            ["player_shops.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_listing_active_expiry",
        "market_listings",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_market_listing_shop_status", "market_listings", ["shop_id", "status"], unique=False
    )
    op.create_table(
        "trade_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("owner_character_id", sa.Uuid(), nullable=True),
        sa.Column("item_kind", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("rarity", sa.String(length=16), nullable=True),
        sa.Column("item_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="escrow", nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "item_kind IN ('equipment','material','consumable','rune')", name="ck_trade_item_kind"
        ),
        sa.CheckConstraint(
            "status IN ('escrow','delivered','returned','withdrawn','discarded')",
            name="ck_trade_item_status",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_trade_item_quantity"),
        sa.ForeignKeyConstraint(["owner_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["trade_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trade_item_trade", "trade_items", ["trade_id"], unique=False)
    op.create_table(
        "market_price_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("owner_character_id", sa.Uuid(), nullable=True),
        sa.Column("old_price", sa.BigInteger(), nullable=False),
        sa.Column("new_price", sa.BigInteger(), nullable=False),
        sa.Column("terms_version", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["market_listings.id"],
        ),
        sa.ForeignKeyConstraint(["owner_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_price_change_listing", "market_price_changes", ["listing_id"], unique=False
    )
    op.create_table(
        "market_purchases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_character_id", sa.Uuid(), nullable=True),
        sa.Column("seller_character_id", sa.Uuid(), nullable=True),
        sa.Column("terms_version", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("gross", sa.BigInteger(), nullable=True),
        sa.Column("fee", sa.BigInteger(), nullable=True),
        sa.Column("net", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="preview", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('preview','committed')", name="ck_market_purchase_status"),
        sa.CheckConstraint("quantity > 0", name="ck_market_purchase_quantity"),
        sa.ForeignKeyConstraint(["buyer_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["market_listings.id"],
        ),
        sa.ForeignKeyConstraint(["seller_character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_purchase_listing", "market_purchases", ["listing_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_market_purchase_listing", table_name="market_purchases")
    op.drop_table("market_purchases")
    op.drop_index("ix_market_price_change_listing", table_name="market_price_changes")
    op.drop_table("market_price_changes")
    op.drop_index("ix_trade_item_trade", table_name="trade_items")
    op.drop_table("trade_items")
    op.drop_index("ix_market_listing_shop_status", table_name="market_listings")
    op.drop_index(
        "ix_market_listing_active_expiry",
        table_name="market_listings",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_table("market_listings")
    op.drop_index("ix_trade_session_partner", table_name="trade_sessions")
    op.drop_index(
        "ix_trade_session_live",
        table_name="trade_sessions",
        postgresql_where=sa.text("status IN ('invited','open')"),
    )
    op.drop_index("ix_trade_session_initiator", table_name="trade_sessions")
    op.drop_table("trade_sessions")
    op.drop_index("ix_shop_search_character_time", table_name="shop_search_attempts")
    op.drop_table("shop_search_attempts")
    op.drop_table("player_shops")
