"""A Ruptura do Véu: persisted combat state of a participant (barrier and effects).

Revision ID: 20261123_0059
Revises: 20261123_0058
Create Date: 2026-11-23 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261123_0059"
down_revision: str | None = "20261123_0058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "veu_event_participants",
        sa.Column(
            "combat_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("veu_event_participants", "combat_state")
