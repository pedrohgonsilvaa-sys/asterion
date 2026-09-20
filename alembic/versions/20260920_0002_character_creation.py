"""Persistent character creation and the opening prologue state.

Revision ID: 20260920_0002
Revises: 20260920_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260920_0002"
down_revision = "20260920_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("telegram_id", sa.BigInteger(), primary_key=True, autoincrement=False),
    )
    op.create_table(
        "creation_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "telegram_id", sa.BigInteger(), sa.ForeignKey("accounts.telegram_id"), nullable=False
        ),
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(48), nullable=False),
        sa.Column("name", sa.String(16)),
        sa.Column("race", sa.String(24)),
        sa.Column("character_class", sa.String(24)),
        sa.Column("editing", sa.Boolean(), nullable=False),
        sa.Column("error", sa.String(24)),
        sa.Column("rejected_name", sa.String(16)),
        sa.UniqueConstraint("telegram_id", "server_id", name="uq_draft_actor_server"),
        sa.CheckConstraint("version >= 0", name="ck_draft_version"),
    )
    op.create_table(
        "characters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "telegram_id", sa.BigInteger(), sa.ForeignKey("accounts.telegram_id"), nullable=False
        ),
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(16), nullable=False),
        sa.Column("race", sa.String(24), nullable=False),
        sa.Column("character_class", sa.String(24), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("ruleset_version", sa.String(48), nullable=False),
        sa.UniqueConstraint("telegram_id", "server_id", name="uq_character_actor_server"),
        sa.CheckConstraint("name ~ '^[A-Z][a-z]{2,15}$'", name="ck_character_name"),
        sa.CheckConstraint(
            "race IN ('remanescente','velado','cinereo','hemario','alvorano')",
            name="ck_character_race",
        ),
        sa.CheckConstraint(
            "character_class IN ('sentinela','errante','vigia','tecelao','oraculo','luminar')",
            name="ck_character_class",
        ),
    )
    op.create_index(
        "uq_character_server_name", "characters", ["server_id", sa.text("lower(name)")], unique=True
    )
    op.create_table(
        "creation_inputs",
        sa.Column(
            "telegram_id", sa.BigInteger(), sa.ForeignKey("accounts.telegram_id"), primary_key=True
        ),
        sa.Column("server_id", sa.String(64), primary_key=True),
        sa.Column("update_id", sa.BigInteger(), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("creation_inputs")
    op.drop_index("uq_character_server_name", table_name="characters")
    op.drop_table("characters")
    op.drop_table("creation_drafts")
    op.drop_table("accounts")
