"""persist Telegram file ids for local artwork

Revision ID: 20261116_0052
Revises: 20261113_0051
Create Date: 2026-11-16 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261116_0052"
down_revision: str | None = "20261114_0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_media_cache",
        sa.Column("asset_key", sa.String(length=512), nullable=False),
        sa.Column("fingerprint", sa.String(length=96), nullable=False),
        sa.Column("file_id", sa.String(length=512), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("asset_key"),
    )


def downgrade() -> None:
    op.drop_table("telegram_media_cache")
