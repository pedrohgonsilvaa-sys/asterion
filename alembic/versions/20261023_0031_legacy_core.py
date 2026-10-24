"""Add persistent Legacy rank, confirmations and ascension history.

Revision ID: 20261023_0031
Revises: 20261023_0030
"""

import sqlalchemy as sa
from alembic import op


revision = "20261023_0031"
down_revision = "20261023_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("legacy_level", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "ck_character_legacy_level", "characters", "legacy_level BETWEEN 0 AND 5"
    )
    op.create_table(
        "legacy_ascensions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("legacy_level_after", sa.Integer(), nullable=False),
        sa.Column("character_level_before", sa.Integer(), nullable=False),
        sa.Column("xp_before", sa.BigInteger(), nullable=False),
        sa.Column("campaign_quest_id", sa.String(length=32), nullable=False),
        sa.Column("operation_key", sa.Uuid(), nullable=False),
        sa.Column("configuration_version_before", sa.Integer(), nullable=False),
        sa.Column(
            "ascended_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "legacy_level_after BETWEEN 1 AND 5", name="ck_legacy_ascension_level"
        ),
        sa.CheckConstraint(
            "character_level_before = 60", name="ck_legacy_ascension_level_before"
        ),
        sa.CheckConstraint("xp_before >= 0", name="ck_legacy_ascension_xp_before"),
        sa.CheckConstraint(
            "configuration_version_before >= 0", name="ck_legacy_ascension_config_version"
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "character_id", "legacy_level_after", name="uq_legacy_level_per_character"
        ),
        sa.UniqueConstraint("operation_key", name="uq_legacy_ascension_operation"),
    )
    op.create_index(
        "ix_legacy_ascensions_character_id", "legacy_ascensions", ["character_id"]
    )
    op.create_table(
        "legacy_ascension_confirmations",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("confirmation_key", sa.Uuid(), nullable=False),
        sa.Column("expected_configuration_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "expected_configuration_version >= 0",
            name="ck_legacy_confirmation_config_version",
        ),
        sa.CheckConstraint("expires_at > created_at", name="ck_legacy_confirmation_expiry"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("character_id"),
        sa.UniqueConstraint("confirmation_key", name="uq_legacy_confirmation_key"),
    )


def downgrade() -> None:
    op.drop_table("legacy_ascension_confirmations")
    op.drop_index("ix_legacy_ascensions_character_id", table_name="legacy_ascensions")
    op.drop_table("legacy_ascensions")
    op.drop_constraint("ck_character_legacy_level", "characters", type_="check")
    op.drop_column("characters", "legacy_level")
