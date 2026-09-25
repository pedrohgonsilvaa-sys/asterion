"""Persist equipped item slots and combat configuration version."""

import sqlalchemy as sa

from alembic import op

revision = "20260925_0010"
down_revision = "20260924_0009"
branch_labels = None
depends_on = None

EQUIPMENT_SLOTS = (
    "Principal",
    "Secundária",
    "Cabeça",
    "Torso",
    "Mãos",
    "Pés",
    "Acessório",
    "Artefato",
)


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column(
            "combat_configuration_version",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_character_combat_configuration_version",
        "characters",
        "combat_configuration_version >= 0",
    )
    op.create_table(
        "character_equipment_slots",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.String(length=24), nullable=False),
        sa.Column("equipment_item_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "slot IN (" + ", ".join(f"'{slot}'" for slot in EQUIPMENT_SLOTS) + ")",
            name="ck_character_equipment_slots_slot",
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"],
            name="fk_character_equipment_slots_character_id_characters",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_item_id"], ["equipment_items.id"],
            name="fk_character_equipment_slots_equipment_item_id_equipment_items",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "character_id", "slot", name="pk_character_equipment_slots"
        ),
        sa.UniqueConstraint("equipment_item_id", name="uq_equipment_slot_item"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        "LOCK TABLE character_equipment_slots IN SHARE ROW EXCLUSIVE MODE"
    )
    if bind.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM character_equipment_slots)")
    ):
        raise RuntimeError(
            "Cannot downgrade while characters have equipped EquipmentItems"
        )
    op.drop_table("character_equipment_slots")
    op.drop_constraint(
        "ck_character_combat_configuration_version", "characters", type_="check"
    )
    op.drop_column("characters", "combat_configuration_version")
