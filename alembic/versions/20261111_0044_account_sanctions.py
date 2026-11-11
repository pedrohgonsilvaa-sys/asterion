"""account sanctions

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

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "account_sanctions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("expires_at", _TZ, nullable=True),
        sa.Column("revoked_at", _TZ, nullable=True),
        sa.Column("revoked_by", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_sanctions_account", "account_sanctions", ["telegram_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_account_sanctions_account", table_name="account_sanctions")
    op.drop_table("account_sanctions")
