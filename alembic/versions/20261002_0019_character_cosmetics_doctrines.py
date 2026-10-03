"""Persist TDO cosmetics and saved combat doctrines."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261002_0019"
down_revision = "20261002_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_cosmetics",
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cosmetic_id", sa.String(96), nullable=False),
        sa.Column("cosmetic_type", sa.String(16), nullable=False),
        sa.Column("source_achievement_id", sa.String(64), nullable=False),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("character_id", "cosmetic_id", name="pk_character_cosmetics"),
        sa.UniqueConstraint(
            "character_id",
            "cosmetic_type",
            "cosmetic_id",
            name="uq_character_cosmetic_type_id",
        ),
        sa.CheckConstraint(
            "cosmetic_type IN ('appearance','title','emblem','frame','banner')",
            name="ck_character_cosmetic_type",
        ),
    )
    op.create_table(
        "character_cosmetic_selections",
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cosmetic_type", sa.String(16), nullable=False),
        sa.Column("cosmetic_id", sa.String(96), nullable=False),
        sa.PrimaryKeyConstraint(
            "character_id", "cosmetic_type", name="pk_character_cosmetic_selection"
        ),
        sa.ForeignKeyConstraint(
            ["character_id", "cosmetic_type", "cosmetic_id"],
            [
                "character_cosmetics.character_id",
                "character_cosmetics.cosmetic_type",
                "character_cosmetics.cosmetic_id",
            ],
            ondelete="CASCADE",
            name="fk_character_cosmetic_selection_owned",
        ),
        sa.CheckConstraint(
            "cosmetic_type IN ('appearance','title','emblem','frame','banner')",
            name="ck_character_cosmetic_selection_type",
        ),
    )
    op.create_table(
        "character_doctrines",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("id", "character_id", name="uq_character_doctrine_owner"),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 40", name="ck_doctrine_name_length"
        ),
        sa.CheckConstraint("revision >= 0", name="ck_doctrine_revision"),
        sa.CheckConstraint(
            "jsonb_typeof(configuration) = 'object'",
            name="ck_doctrine_configuration_object",
        ),
    )
    op.create_index(
        "uq_character_doctrine_name",
        "character_doctrines",
        ["character_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "character_doctrine_inputs",
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("action", sa.String(8), nullable=False),
        sa.Column("doctrine_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expected_revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "expected_configuration_version",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("prompt_message_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["doctrine_id", "character_id"],
            ["character_doctrines.id", "character_doctrines.character_id"],
            ondelete="CASCADE",
            name="fk_character_doctrine_input_target",
        ),
        sa.CheckConstraint(
            "action IN ('create','rename')", name="ck_doctrine_input_action"
        ),
        sa.CheckConstraint(
            "(action = 'create' AND doctrine_id IS NULL) OR "
            "(action = 'rename' AND doctrine_id IS NOT NULL)",
            name="ck_doctrine_input_target",
        ),
        sa.CheckConstraint(
            "expected_revision >= 0", name="ck_doctrine_input_revision"
        ),
        sa.CheckConstraint(
            "expected_configuration_version >= 0",
            name="ck_doctrine_input_config_version",
        ),
        sa.CheckConstraint("prompt_message_id > 0", name="ck_doctrine_input_prompt"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "LOCK TABLE character_doctrine_inputs, character_doctrines, "
            "character_cosmetic_selections, character_cosmetics "
            "IN ACCESS EXCLUSIVE MODE"
        )
    )
    for table in (
        "character_doctrine_inputs",
        "character_doctrines",
        "character_cosmetic_selections",
        "character_cosmetics",
    ):
        populated = bind.execute(
            sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")
        ).scalar_one()
        if populated:
            raise RuntimeError(
                f"Refusing to drop {table} while B2 data exists."
            )
    op.drop_table("character_doctrine_inputs")
    op.drop_index("uq_character_doctrine_name", table_name="character_doctrines")
    op.drop_table("character_doctrines")
    op.drop_table("character_cosmetic_selections")
    op.drop_table("character_cosmetics")
