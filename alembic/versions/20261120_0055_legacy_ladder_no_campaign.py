"""Legado I–V ladder: ascension no longer records a campaign quest.

Legado I no longer requires P36 or any campaign; the ascension audit row
therefore stores no campaign quest id. Existing rows keep their P36 value.

Revision ID: 20261120_0055
Revises: 20261119_0054
Create Date: 2026-11-20 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261120_0055"
down_revision: str | None = "20261119_0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "legacy_ascensions",
        "campaign_quest_id",
        existing_type=sa.String(length=32),
        nullable=True,
    )


def downgrade() -> None:
    # Rows written by the new ladder have no campaign quest; backfill the
    # historical value before restoring NOT NULL.
    op.execute(
        "UPDATE legacy_ascensions SET campaign_quest_id = 'P36' "
        "WHERE campaign_quest_id IS NULL"
    )
    op.alter_column(
        "legacy_ascensions",
        "campaign_quest_id",
        existing_type=sa.String(length=32),
        nullable=False,
    )
