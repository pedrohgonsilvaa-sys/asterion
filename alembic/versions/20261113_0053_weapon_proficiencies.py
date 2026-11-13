"""weapon proficiencies (spec Proficiências v1.0.0)

Creates the permanent per-character Proficiência table, seeds the free initial
Proficiência of every existing character from its Classe, and binds the three
pre-metadata TDO drop templates to their canonical weapon_type_id. Those legacy
rows carry the exact template name and slot the drop table produced before
2026-10-17; any other weapon without identity stays unmapped and cannot be
equipped (author decision, 2026-11-13).

Revision ID: 20261113_0053
Revises: 20261113_0052
Create Date: 2026-11-13 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261113_0053"
down_revision: str | None = "20261113_0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INITIAL = {
    "sentinela": "proficiency.swords",
    "errante": "proficiency.blades",
    "vigia": "proficiency.bows",
    "tecelao": "proficiency.arcane_foci",
    "oraculo": "proficiency.arcane_foci",
    "luminar": "proficiency.arcane_foci",
}
_LEGACY_DROPS = (
    ("Arma do Caminhante", "Principal", "weapon.type.tdo.arma_caminhante"),
    ("Guarda do Caminhante", "Secundária", "weapon.type.tdo.guarda_caminhante"),
    ("Arma Pesada do Caminhante", "2H", "weapon.type.tdo.arma_pesada_caminhante"),
)


def upgrade() -> None:
    op.create_table(
        "character_weapon_proficiencies",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("family", sa.String(length=32), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("cost_crowns", sa.Integer(), nullable=False),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "family IN ('proficiency.swords','proficiency.blades','proficiency.blunt',"
            "'proficiency.axes','proficiency.polearms','proficiency.bows',"
            "'proficiency.crossbows','proficiency.arcane_foci','proficiency.shield')",
            name="ck_character_weapon_proficiency_family",
        ),
        sa.CheckConstraint("ordinal >= 1", name="ck_character_weapon_proficiency_ordinal"),
        sa.CheckConstraint("cost_crowns >= 0", name="ck_character_weapon_proficiency_cost"),
        sa.CheckConstraint(
            "source IN ('initial','trainer')", name="ck_character_weapon_proficiency_source"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id", "family"),
        sa.UniqueConstraint(
            "character_id", "ordinal", name="uq_character_weapon_proficiency_ordinal"
        ),
    )
    for character_class, family in _INITIAL.items():
        op.execute(
            sa.text(
                "INSERT INTO character_weapon_proficiencies "
                "(character_id, family, ordinal, source, cost_crowns) "
                "SELECT id, :family, 1, 'initial', 0 FROM characters "
                "WHERE character_class = :character_class"
            ).bindparams(family=family, character_class=character_class)
        )
    for item_name, slot, weapon_type_id in _LEGACY_DROPS:
        for table in ("equipment_items", "warehouse_equipment_items"):
            op.execute(
                sa.text(
                    f"UPDATE {table} SET payload = payload || "
                    "jsonb_build_object('weapon_type_id', CAST(:weapon_type_id AS text)) "
                    "WHERE item_name = :item_name AND slot = :slot "
                    "AND payload->'weapon_type_id' IS NULL"
                ).bindparams(weapon_type_id=weapon_type_id, item_name=item_name, slot=slot)
            )
        op.execute(
            sa.text(
                "UPDATE pending_items SET payload = payload || "
                "jsonb_build_object('weapon_type_id', CAST(:weapon_type_id AS text)) "
                "WHERE kind = 'equipment' AND payload->>'item_name' = :item_name "
                "AND payload->>'slot' = :slot AND payload->'weapon_type_id' IS NULL"
            ).bindparams(weapon_type_id=weapon_type_id, item_name=item_name, slot=slot)
        )


def downgrade() -> None:
    # The legacy weapon_type_id backfill is kept: it only names what the row already was.
    op.drop_table("character_weapon_proficiencies")
