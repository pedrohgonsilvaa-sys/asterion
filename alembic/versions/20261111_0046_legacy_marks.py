"""legacy marks: active Marcas de Legado and respec Recarga

Revision ID: 20261111_0046
Revises: 20261111_0045
Create Date: 2026-11-11 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261111_0046"
down_revision: str | None = "20261111_0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("legacy_mark_respec_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "character_legacy_marks",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("mark_id", sa.String(length=32), nullable=False),
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mark_id IN ('bolsa_funda','armazem_amplo','entregas_guardadas','banca_extra',"
            "'sexta_doutrina','chamado_do_braseiro','pregao_constante','vigia_do_vigor',"
            "'mensageiro','lembrete_de_recargas')",
            name="ck_character_legacy_mark_id",
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id", "mark_id"),
    )


def downgrade() -> None:
    op.drop_table("character_legacy_marks")
    op.drop_column("characters", "legacy_mark_respec_at")
