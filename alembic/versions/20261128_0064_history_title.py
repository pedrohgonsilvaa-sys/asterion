"""História do personagem: título (5 a 16 caracteres) e rascunho do título.

Revision ID: 20261128_0064
Revises: 20261126_0063
Create Date: 2026-11-28 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261128_0064"
down_revision: str | None = "20261126_0063"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("character_profiles", sa.Column("history_title", sa.String(16), nullable=True))
    op.add_column(
        "character_profiles", sa.Column("history_title_draft", sa.String(16), nullable=True)
    )
    op.create_check_constraint(
        "ck_character_profile_history_title_length",
        "character_profiles",
        "history_title IS NULL OR char_length(history_title) BETWEEN 5 AND 16",
    )
    op.create_check_constraint(
        "ck_character_profile_history_title_draft_length",
        "character_profiles",
        "history_title_draft IS NULL OR char_length(history_title_draft) BETWEEN 5 AND 16",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_character_profile_history_title_draft_length", "character_profiles", type_="check"
    )
    op.drop_constraint(
        "ck_character_profile_history_title_length", "character_profiles", type_="check"
    )
    op.drop_column("character_profiles", "history_title_draft")
    op.drop_column("character_profiles", "history_title")
