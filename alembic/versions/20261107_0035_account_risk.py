"""Add multi-account review: admin account links and co-occurrence flags (GDD §36).

Revision ID: 20261107_0035
Revises: 20261107_0034
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261107_0035"
down_revision = "20261107_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_links",
        sa.Column("account_a", sa.BigInteger(), nullable=False),
        sa.Column("account_b", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("account_a < account_b", name="ck_account_link_order"),
        sa.ForeignKeyConstraint(["account_a"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_b"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_a", "account_b"),
    )
    op.create_table(
        "account_risk_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_a", sa.BigInteger(), nullable=False),
        sa.Column("account_b", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("activity_kind", sa.String(length=32), nullable=False),
        sa.Column("activity_reference", sa.String(length=96), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), server_default="open", nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("account_a < account_b", name="ck_account_risk_flag_order"),
        sa.CheckConstraint(
            "status IN ('open','reviewed','dismissed')", name="ck_account_risk_flag_status"
        ),
        sa.ForeignKeyConstraint(["account_a"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_b"], ["accounts.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "activity_kind",
            "activity_reference",
            "account_a",
            "account_b",
            name="uq_account_risk_flag_activity_pair",
        ),
    )
    op.create_index(
        "ix_account_risk_flags_status_created",
        "account_risk_flags",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_account_risk_flags_status_created", table_name="account_risk_flags")
    op.drop_table("account_risk_flags")
    op.drop_table("account_links")
