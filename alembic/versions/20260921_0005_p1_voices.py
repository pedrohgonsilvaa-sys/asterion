"""P1 mission state and minimal regional persistence."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260921_0005"
down_revision = "20260920_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM quests WHERE quest_id='P1' AND
        (step > 1 OR status <> 'active' OR content_version <> 'tdo-1.0.1')) THEN
        RAISE EXCEPTION 'Cannot migrate incompatible P1 state';
      END IF;
    END $$""")
    op.add_column(
        "characters", sa.Column("crowns", sa.BigInteger(), nullable=False, server_default="0")
    )
    op.create_check_constraint("ck_character_crowns", "characters", "crowns >= 0")
    op.add_column(
        "quests", sa.Column("state_version", sa.BigInteger(), nullable=False, server_default="0")
    )
    op.add_column("quests", sa.Column("progress", JSONB(), nullable=False, server_default="{}"))
    op.execute(
        "UPDATE quests SET content_version='tdo-1.0.2' WHERE quest_id='P1' AND status='active' AND step=1 AND content_version='tdo-1.0.1'"  # noqa: E501
    )
    op.alter_column("quests", "content_version", server_default="tdo-1.0.2")
    for table, ident in (
        ("location_discoveries", "location"),
        ("codex_entries", "entry"),
        ("unlocks", "unlock"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("character_id", sa.Uuid(), nullable=False),
            sa.Column(f"{ident}_id", sa.String(96 if ident != "location" else 64), nullable=False),
            sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
            sa.UniqueConstraint("character_id", f"{ident}_id", name=f"uq_character_{ident}"),
        )
    op.create_table(
        "material_stacks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.String(96), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bound", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "material_id", "bound", name="uq_character_material"),
        sa.CheckConstraint("quantity BETWEEN 0 AND 999", name="ck_material_quantity"),
    )
    op.create_table(
        "reward_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(96), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("character_id", "source_id", name="uq_character_reward_source"),
    )
    op.create_table(
        "reward_components",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reward_event_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("item_id", sa.String(96)),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["reward_event_id"], ["reward_events.id"]),
    )
    op.execute(
        "INSERT INTO location_discoveries (id, character_id, location_id) SELECT gen_random_uuid(), c.id, 'tdo.location.estrada_das_cinzas' FROM characters c JOIN braziers b ON b.character_id=c.id WHERE b.brazier_id='tdo.brazier.estrada' ON CONFLICT DO NOTHING"  # noqa: E501
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM reward_events) OR "
            "EXISTS (SELECT 1 FROM location_discoveries) OR "
            "EXISTS (SELECT 1 FROM codex_entries) OR EXISTS (SELECT 1 FROM unlocks) OR "
            "EXISTS (SELECT 1 FROM material_stacks)"
        )
    ):
        raise RuntimeError("Cannot downgrade populated P1 state")
    op.drop_table("reward_components")
    op.drop_table("reward_events")
    op.drop_table("material_stacks")
    op.drop_table("unlocks")
    op.drop_table("codex_entries")
    op.drop_table("location_discoveries")
    op.alter_column("quests", "content_version", server_default="tdo-1.0.1")
    op.drop_column("quests", "progress")
    op.drop_column("quests", "state_version")
    op.drop_constraint("ck_character_crowns", "characters", type_="check")
    op.drop_column("characters", "crowns")
