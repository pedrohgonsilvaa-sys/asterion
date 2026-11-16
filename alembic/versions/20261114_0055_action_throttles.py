"""action throttles (TdO v1.0.18 33.2 e L13)

Persists, per character, the time of the last Explorar/Desbravar click (anti-spam
of 3 s) and whether one attempt is still resolving. No effect on rewards.

Revision ID: 20261114_0055
Revises: 20261114_0054
Create Date: 2026-11-14 00:00:02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261114_0055"
down_revision: str | None = "20261114_0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "character_action_throttles",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("last_action", sa.String(length=32), nullable=False),
        sa.Column("last_click_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolving", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id"),
    )


def downgrade() -> None:
    op.drop_table("character_action_throttles")
