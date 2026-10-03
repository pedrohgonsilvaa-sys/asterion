"""Persist Bot notifications and character account workflows."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261003_0020"
down_revision = "20261002_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_notification_preferences",
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint(
            "character_id", "category", name="pk_character_notification_preferences"
        ),
        sa.CheckConstraint(
            "category IN ('essentials','events','competitive','guild','market','chronicle')",
            name="ck_character_notification_category",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_character_notification_revision"),
    )
    op.create_table(
        "character_name_reservations",
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("normalized_name", sa.String(16), nullable=False),
        sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("origin_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint(
            "server_id", "normalized_name", name="pk_character_name_reservations"
        ),
        sa.CheckConstraint("normalized_name ~ '^[a-z]{3,16}$'", name="ck_name_reservation_name"),
        sa.CheckConstraint("source IN ('rename','deletion')", name="ck_name_reservation_source"),
    )
    op.create_index("ix_name_reservation_expiry", "character_name_reservations", ["reserved_until"])
    op.create_table(
        "character_rename_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("old_name", sa.String(16), nullable=False),
        sa.Column("new_name", sa.String(16), nullable=False),
        sa.Column("renamed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.CheckConstraint("origin IN ('player')", name="ck_character_rename_origin"),
    )
    op.create_index(
        "ix_character_rename_history", "character_rename_history", ["character_id", "renamed_at"]
    )
    op.create_table(
        "character_deletion_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("name_at_request", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "status IN ('preview','pending','cancelled','completed')",
            name="ck_character_deletion_status",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_character_deletion_revision"),
        sa.CheckConstraint("due_at > requested_at", name="ck_character_deletion_due"),
    )
    op.create_index(
        "uq_open_character_deletion",
        "character_deletion_requests",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('preview','pending')"),
    )
    op.create_index(
        "ix_due_character_deletions",
        "character_deletion_requests",
        ["due_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "character_account_inputs",
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("prompt_message_id", sa.BigInteger(), nullable=False),
        sa.Column("current_name", sa.String(16), nullable=False),
        sa.Column("new_name", sa.String(16), nullable=True),
        sa.Column("last_update_id", sa.BigInteger(), nullable=True),
        sa.Column("error", sa.String(16), nullable=True),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('awaiting','preview','invalid','unavailable')",
            name="ck_character_account_input_status",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_character_account_input_revision"),
        sa.CheckConstraint("prompt_message_id > 0", name="ck_character_account_input_prompt"),
    )
    op.create_table(
        "character_pending_inputs",
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("input_kind", sa.String(24), nullable=False),
        sa.Column("prompt_message_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "input_kind IN ('history','doctrine_name','rename')",
            name="ck_character_pending_input_kind",
        ),
        sa.CheckConstraint("prompt_message_id > 0", name="ck_character_pending_input_prompt"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "character_pending_inputs",
        "character_account_inputs",
        "character_deletion_requests",
        "character_rename_history",
        "character_name_reservations",
        "character_notification_preferences",
    ):
        bind.execute(sa.text(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE"))
        if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            raise RuntimeError(f"Refusing to drop populated B3 table {table}.")
    op.drop_table("character_pending_inputs")
    op.drop_table("character_account_inputs")
    op.drop_index("ix_due_character_deletions", table_name="character_deletion_requests")
    op.drop_index("uq_open_character_deletion", table_name="character_deletion_requests")
    op.drop_table("character_deletion_requests")
    op.drop_index("ix_character_rename_history", table_name="character_rename_history")
    op.drop_table("character_rename_history")
    op.drop_index("ix_name_reservation_expiry", table_name="character_name_reservations")
    op.drop_table("character_name_reservations")
    op.drop_table("character_notification_preferences")
