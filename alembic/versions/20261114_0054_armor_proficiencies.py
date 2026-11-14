"""armor proficiencies (spec Classes de Armadura v1.0.0 §5)

Creates the permanent per-character Proficiência de Armadura table. Veste is the
free initial Proficiência and stays implicit (no row). Existing items are not
touched: the armor class is derived from the item template at read time.

Revision ID: 20261114_0054
Revises: 20261113_0053
Create Date: 2026-11-14 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261114_0054"
down_revision: str | None = "20261113_0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "character_armor_proficiencies",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("armor_class", sa.String(length=16), nullable=False),
        sa.Column("cost_crowns", sa.Integer(), nullable=False),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "armor_class IN ('veste','leve','media','pesada')",
            name="ck_character_armor_proficiency_class",
        ),
        sa.CheckConstraint("cost_crowns >= 0", name="ck_character_armor_proficiency_cost"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id", "armor_class"),
    )


def downgrade() -> None:
    op.drop_table("character_armor_proficiencies")
