"""foundation transactional outbox

Revision ID: 20260920_0001
Revises:
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260920_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("dedup_key", sa.String(length=200), nullable=False),
        sa.Column("aggregate_key", sa.String(length=200), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key"),
    )
    op.create_index(
        op.f("ix_outbox_messages_aggregate_key"),
        "outbox_messages",
        ["aggregate_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_outbox_messages_status"),
        "outbox_messages",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_messages_status"), table_name="outbox_messages")
    op.drop_index(
        op.f("ix_outbox_messages_aggregate_key"),
        table_name="outbox_messages",
    )
    op.drop_table("outbox_messages")
