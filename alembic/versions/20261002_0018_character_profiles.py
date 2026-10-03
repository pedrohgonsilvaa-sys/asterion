"""Persist optional player-authored character history."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261002_0018"
down_revision = "20261002_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_profiles",
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("history", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("history_prompt_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("revision >= 0", name="ck_character_profile_revision"),
        sa.CheckConstraint(
            "history IS NULL OR char_length(history) <= 1200",
            name="ck_character_profile_history_length",
        ),
        sa.CheckConstraint(
            "history_prompt_message_id IS NULL OR history_prompt_message_id > 0",
            name="ck_character_profile_prompt_message_id",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    has_profile_rows = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM character_profiles)")
    ).scalar_one()
    if has_profile_rows:
        raise RuntimeError(
            "Refusing to drop character_profiles while profile or pending input data exists."
        )
    op.drop_table("character_profiles")
