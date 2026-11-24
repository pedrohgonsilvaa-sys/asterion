"""A Ruptura do Véu: combat state, round results and settlement.

Adds the participant's HP inside the Event, the first round a participant may act in the
current Núcleo (entry/switch rule, §14.1-§14.2), the per-participant settlement outcome,
the resolved-round result (history/support lines) and the occurrence settlement mark.
Enemy HP lives in ``veu_event_nuclei.enemy_state``, which 0056 already created.

Revision ID: 20261123_0058
Revises: 20261123_0057
Create Date: 2026-11-23 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261123_0058"
down_revision: str | None = "20261123_0057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("veu_event_participants", sa.Column("hp", sa.Numeric(14, 2), nullable=True))
    op.add_column(
        "veu_event_participants",
        sa.Column("acts_from_round", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "veu_event_participants",
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("veu_event_participants", sa.Column("eligible", sa.Boolean(), nullable=True))
    op.add_column(
        "veu_event_participants",
        sa.Column(
            "reward",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "veu_event_rounds",
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "veu_event_occurrences",
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("veu_event_occurrences", "settled_at")
    op.drop_column("veu_event_rounds", "result")
    op.drop_column("veu_event_participants", "reward")
    op.drop_column("veu_event_participants", "eligible")
    op.drop_column("veu_event_participants", "settled_at")
    op.drop_column("veu_event_participants", "acts_from_round")
    op.drop_column("veu_event_participants", "hp")
