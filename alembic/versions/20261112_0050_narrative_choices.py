"""narrative choices, memories and rapport

Revision ID: 20261112_0050
Revises: 20261111_0049
Create Date: 2026-11-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261112_0050"
down_revision: str | None = "20261111_0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def _jsonb_list(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'[]'::jsonb"),
        nullable=False,
    )


def _character_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE")


def upgrade() -> None:
    op.create_table(
        "narrative_choices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("choice_id", sa.String(length=64), nullable=False),
        sa.Column("mission_id", sa.String(length=8), nullable=False),
        sa.Column("step_context", sa.Text(), nullable=False),
        sa.Column("selected_option", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("catalog_version", sa.String(length=16), nullable=False),
        _jsonb_list("character_memory_tags"),
        _jsonb_list("npc_memory_targets"),
        _jsonb_list("future_hooks"),
        _jsonb_list("identity_conditions"),
        sa.Column("committed_at", _TZ, nullable=False),
        sa.CheckConstraint(
            "source IN ('player','neutral_backfill')", name="ck_narrative_choice_source"
        ),
        _character_fk(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("character_id", "choice_id", name="uq_narrative_choice"),
    )
    op.create_index(
        "ix_narrative_choice_mission", "narrative_choices", ["character_id", "mission_id"]
    )
    op.create_table(
        "character_narrative_memories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("source_choice_id", sa.String(length=64), nullable=False),
        sa.Column("recorded_at", _TZ, nullable=False),
        _character_fk(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "character_id", "source_choice_id", "tag", name="uq_character_narrative_memory"
        ),
    )
    op.create_table(
        "npc_narrative_memories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("npc_id", sa.String(length=32), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("source_choice_id", sa.String(length=64), nullable=False),
        sa.Column("knowledge", sa.String(length=16), nullable=False),
        sa.Column("recorded_at", _TZ, nullable=False),
        sa.CheckConstraint(
            "knowledge IN ('witnessed','report','record')", name="ck_npc_memory_knowledge"
        ),
        _character_fk(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "character_id", "npc_id", "source_choice_id", "tag", name="uq_npc_narrative_memory"
        ),
    )
    op.create_table(
        "npc_rapport_states",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("npc_id", sa.String(length=32), nullable=False),
        sa.Column("rapport_state", sa.String(length=16), nullable=False),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.CheckConstraint(
            "rapport_state IN ('neutral','open','trusting','guarded','skeptical',"
            "'respectful','strained')",
            name="ck_npc_rapport_state",
        ),
        _character_fk(),
        sa.PrimaryKeyConstraint("character_id", "npc_id", name="pk_npc_rapport_states"),
    )


def downgrade() -> None:
    op.drop_table("npc_rapport_states")
    op.drop_table("npc_narrative_memories")
    op.drop_table("character_narrative_memories")
    op.drop_index("ix_narrative_choice_mission", table_name="narrative_choices")
    op.drop_table("narrative_choices")
