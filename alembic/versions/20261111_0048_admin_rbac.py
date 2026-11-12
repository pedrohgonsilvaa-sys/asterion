"""admin roles and audit log

Revision ID: 20261111_0048
Revises: 20261111_0046
Create Date: 2026-11-11 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261111_0048"
down_revision: str | None = "20261111_0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "admin_role_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("granted_by", sa.BigInteger(), nullable=False),
        sa.Column("granted_at", _TZ, nullable=False),
        sa.Column("revoked_at", _TZ, nullable=True),
        sa.Column("revoked_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_admin_role_grants_active",
        "admin_role_grants",
        ["telegram_id", "role"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "admin_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", _TZ, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_actions_actor", "admin_actions", ["actor_telegram_id", "created_at"]
    )
    op.create_index(
        "ix_admin_actions_target", "admin_actions", ["target_type", "target_id", "created_at"]
    )
    # Append-only audit: the database itself refuses UPDATE and DELETE.
    op.execute(
        """
        CREATE FUNCTION admin_actions_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'admin_actions is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER admin_actions_append_only
        BEFORE UPDATE OR DELETE ON admin_actions
        FOR EACH ROW EXECUTE FUNCTION admin_actions_append_only()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER admin_actions_append_only ON admin_actions")
    op.execute("DROP FUNCTION admin_actions_append_only()")
    op.drop_index("ix_admin_actions_target", table_name="admin_actions")
    op.drop_index("ix_admin_actions_actor", table_name="admin_actions")
    op.drop_table("admin_actions")
    op.drop_index("uq_admin_role_grants_active", table_name="admin_role_grants")
    op.drop_table("admin_role_grants")
