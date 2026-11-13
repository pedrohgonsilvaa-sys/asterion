"""character gender chosen at creation

Revision ID: 20261113_0051
Revises: 20261112_0050
Create Date: 2026-11-13 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261113_0051"
down_revision: str | None = "20261112_0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("creation_drafts", sa.Column("gender", sa.String(length=16), nullable=True))
    op.add_column("characters", sa.Column("gender", sa.String(length=16), nullable=True))
    op.create_check_constraint(
        "ck_character_gender",
        "characters",
        "gender IS NULL OR gender IN ('masculino','feminino')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_character_gender", "characters", type_="check")
    op.drop_column("characters", "gender")
    op.drop_column("creation_drafts", "gender")
