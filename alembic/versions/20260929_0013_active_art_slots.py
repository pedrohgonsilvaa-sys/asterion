"""Persist the three authoritative active-Art slots."""

import sqlalchemy as sa

from alembic import op

revision = "20260929_0013"
down_revision = "20260929_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_active_art_slots",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("art_id", sa.String(length=96), nullable=False),
        sa.CheckConstraint("slot BETWEEN 1 AND 3", name="ck_character_active_art_slot"),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
            name="fk_character_active_art_slots_character_id_characters",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "character_id", "slot", name="pk_character_active_art_slots"
        ),
        sa.UniqueConstraint("character_id", "art_id", name="uq_character_active_art"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        "LOCK TABLE character_active_art_slots IN SHARE ROW EXCLUSIVE MODE"
    )
    if bind.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM character_active_art_slots)")
    ):
        raise RuntimeError("Cannot downgrade while characters have equipped active Arts")
    op.drop_table("character_active_art_slots")
