"""guild works: market fee fixed per listing (Tesouraria Obra)

Revision ID: 20261111_0044
Revises: 20261110_0043
Create Date: 2026-11-11 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261111_0044"
down_revision: str | None = "20261110_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "market_listings",
        sa.Column("fee_bps", sa.Integer(), server_default="500", nullable=False),
    )
    op.create_check_constraint(
        "ck_market_listing_fee_bps", "market_listings", "fee_bps BETWEEN 0 AND 500"
    )


def downgrade() -> None:
    op.drop_constraint("ck_market_listing_fee_bps", "market_listings", type_="check")
    op.drop_column("market_listings", "fee_bps")
