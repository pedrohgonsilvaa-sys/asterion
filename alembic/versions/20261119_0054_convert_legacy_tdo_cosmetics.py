"""convert the two canonical legacy TDO cosmetics, non-destructively

Emblem "Nome Apagado" becomes the Title and Banner "Ocaso" becomes the Frame
(GDD 33.4, TDO 17). Legacy rows are never deleted: the two converted ones stay
as inert legacy data and the four retired ones (Lápide Raspada, Selo Fraturado,
Profundezas do Ocaso, Última Vigília) are untouched. Idempotent.

Revision ID: 20261119_0054
Revises: 20261119_0053
Create Date: 2026-11-19 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261119_0054"
down_revision: str | None = "20261119_0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONVERSIONS = (
    ("cosmetic.emblem.tdo.nome_apagado", "emblem", "cosmetic.title.tdo.nome_apagado", "title"),
    ("cosmetic.banner.tdo.ocaso", "banner", "cosmetic.frame.tdo.ocaso", "frame"),
)


# Ownership first (the selection row references it).
OWNERSHIP_SQL = """
INSERT INTO character_cosmetics
    (character_id, cosmetic_id, cosmetic_type, source_achievement_id, acquired_at)
SELECT character_id, :new_id, :new_type, source_achievement_id, acquired_at
FROM character_cosmetics
WHERE cosmetic_id = :old_id AND cosmetic_type = :old_type
ON CONFLICT DO NOTHING
"""
# Carry the equipped choice over only when the target category has none.
SELECTION_SQL = """
INSERT INTO character_cosmetic_selections (character_id, cosmetic_type, cosmetic_id)
SELECT character_id, :new_type, :new_id
FROM character_cosmetic_selections
WHERE cosmetic_id = :old_id AND cosmetic_type = :old_type
ON CONFLICT DO NOTHING
"""


def upgrade() -> None:
    for old_id, old_type, new_id, new_type in CONVERSIONS:
        params = {"old_id": old_id, "old_type": old_type, "new_id": new_id, "new_type": new_type}
        op.execute(sa.text(OWNERSHIP_SQL).bindparams(**params))
        op.execute(sa.text(SELECTION_SQL).bindparams(**params))


def downgrade() -> None:
    # Non-destructive: converted rows may also have been granted natively, so
    # nothing is removed. The legacy rows were never deleted.
    pass
