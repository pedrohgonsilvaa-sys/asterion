"""regional contracts (Documento B)

Revision ID: 20261113_0052
Revises: 20261113_0051
Create Date: 2026-11-13 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261113_0052"
down_revision: str | None = "20261113_0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "hunt_contexts",
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "contract_instances",
        sa.Column("contract_instance_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("contract_definition_id", sa.String(length=32), nullable=False),
        sa.Column("region_id", sa.String(length=4), nullable=False),
        sa.Column("contract_type", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("target", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("claimed", sa.Boolean(), nullable=False),
        sa.Column("reward_profile", sa.String(length=40), nullable=False),
        sa.Column("source_refresh_id", sa.String(length=48), nullable=False),
        sa.Column(
            "eligibility_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "state IN ('DISPONIVEL','ACEITO','EM_ANDAMENTO','CONCLUIDO','RESGATADO',"
            "'EXPIRADO','ABANDONADO')",
            name="ck_contract_instance_state",
        ),
        sa.CheckConstraint("progress >= 0 AND target >= 1", name="ck_contract_instance_progress"),
        sa.CheckConstraint("version >= 0", name="ck_contract_instance_version"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("contract_instance_id"),
        sa.UniqueConstraint(
            "character_id",
            "contract_definition_id",
            "source_refresh_id",
            name="uq_contract_instance_offer",
        ),
    )
    op.create_index(
        "ix_contract_instance_character_state",
        "contract_instances",
        ["character_id", "state"],
    )


def downgrade() -> None:
    op.drop_index("ix_contract_instance_character_state", table_name="contract_instances")
    op.drop_table("contract_instances")
    op.drop_column("hunt_contexts", "started_at")
