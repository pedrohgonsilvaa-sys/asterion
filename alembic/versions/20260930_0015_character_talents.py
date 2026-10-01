"""Persist one Talent choice per earned point slot."""

import sqlalchemy as sa

from alembic import op

revision = "20260930_0015"
down_revision = "20260930_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_talent_choices",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("point_slot", sa.Integer(), nullable=False),
        sa.Column("talent_id", sa.String(length=96), nullable=False),
        sa.CheckConstraint("point_slot BETWEEN 1 AND 12", name="ck_character_talent_point_slot"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"],
            name="fk_character_talent_choices_character_id_characters",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "character_id", "point_slot", name="pk_character_talent_choices"
        ),
        sa.UniqueConstraint(
            "character_id", "talent_id", name="uq_character_talent_choice"
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        "LOCK TABLE character_talent_choices IN SHARE ROW EXCLUSIVE MODE"
    )
    if bind.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM character_talent_choices)")):
        raise RuntimeError("Cannot downgrade while characters have Talent choices")
    op.drop_table("character_talent_choices")
