"""payment orders, order audit events and Patrono accounts

Revision ID: 20261111_0046
Revises: 20261111_0045
Create Date: 2026-11-11 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261111_0046"
down_revision: str | None = "20261111_0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)
_EMPTY = sa.text("'{}'::jsonb")


def upgrade() -> None:
    op.create_table(
        "payment_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("order_nsu", sa.String(length=160), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("product", sa.String(length=32), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("invoice_slug", sa.String(length=128), nullable=True),
        sa.Column("transaction_nsu", sa.String(length=128), nullable=True),
        sa.Column("capture_method", sa.String(length=32), nullable=True),
        sa.Column("paid_amount_cents", sa.Integer(), nullable=True),
        sa.Column("recovered", sa.Boolean(), nullable=False),
        sa.Column("terms_version", sa.String(length=32), nullable=True),
        sa.Column("terms_accepted_at", _TZ, nullable=True),
        sa.Column(
            "grant",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=_EMPTY,
            nullable=False,
        ),
        sa.Column("grant_error", sa.String(length=64), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("expires_at", _TZ, nullable=True),
        sa.Column("paid_at", _TZ, nullable=True),
        sa.Column("granted_at", _TZ, nullable=True),
        sa.Column("revoked_at", _TZ, nullable=True),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.CheckConstraint(
            "status IN ('created','paid','expired','refunded','reversed')",
            name="ck_payment_order_status",
        ),
        sa.CheckConstraint(
            "product IN ('patron','chronicle_pass')", name="ck_payment_order_product"
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_payment_order_amount"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_nsu"),
        sa.UniqueConstraint("transaction_nsu"),
    )
    op.create_index(
        "ix_payment_orders_account_created", "payment_orders", ["account_id", "created_at"]
    )
    op.create_index(
        "ix_payment_orders_status_expires", "payment_orders", ["status", "expires_at"]
    )
    op.create_table(
        "payment_order_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=_EMPTY,
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["payment_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_order_events_order", "payment_order_events", ["order_id", "created_at"]
    )
    op.create_table(
        "patron_accounts",
        sa.Column("account_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("active_until", _TZ, nullable=True),
        sa.Column("paid_days", sa.Integer(), nullable=False),
        sa.Column("temporary_granted", sa.Boolean(), nullable=False),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.CheckConstraint("paid_days >= 0", name="ck_patron_paid_days"),
        sa.PrimaryKeyConstraint("account_id"),
    )


def downgrade() -> None:
    op.drop_table("patron_accounts")
    op.drop_index("ix_payment_order_events_order", table_name="payment_order_events")
    op.drop_table("payment_order_events")
    op.drop_index("ix_payment_orders_status_expires", table_name="payment_orders")
    op.drop_index("ix_payment_orders_account_created", table_name="payment_orders")
    op.drop_table("payment_orders")
