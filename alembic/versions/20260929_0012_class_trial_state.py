"""Persist the shared three-stage Class Trial state."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260929_0012"
down_revision = "20260926_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "class_trial_states",
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("character_class", sa.String(length=24), nullable=False),
        sa.Column("trial_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ready"),
        sa.Column("current_stage", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "completed_stages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("state_version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("context", sa.String(length=16), nullable=False, server_default="circle"),
        sa.Column("current_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("stage_definition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attempt_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "character_class IN ('sentinela','errante','vigia','tecelao','oraculo','luminar')",
            name="ck_class_trial_class",
        ),
        sa.CheckConstraint(
            "status IN ('ready','active','completed')", name="ck_class_trial_status"
        ),
        sa.CheckConstraint("current_stage BETWEEN 1 AND 3", name="ck_class_trial_stage"),
        sa.CheckConstraint("state_version >= 0", name="ck_class_trial_state_version"),
        sa.CheckConstraint(
            "(status = 'active') = (current_attempt_id IS NOT NULL)",
            name="ck_class_trial_attempt_status",
        ),
        sa.CheckConstraint(
            "(status = 'active') = (attempt_state IS NOT NULL)",
            name="ck_class_trial_attempt_snapshot",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(completed_stages) = 'array'",
            name="ck_class_trial_checkpoints_array",
        ),
        sa.CheckConstraint(
            "stage_definition IS NULL OR jsonb_typeof(stage_definition) = 'object'",
            name="ck_class_trial_stage_definition_object",
        ),
        sa.CheckConstraint(
            "attempt_state IS NULL OR jsonb_typeof(attempt_state) = 'object'",
            name="ck_class_trial_attempt_state_object",
        ),
        sa.CheckConstraint("context IN ('circle','refuge')", name="ck_class_trial_context"),
        sa.CheckConstraint(
            "status != 'completed' OR completed_stages = '[1,2,3]'::jsonb",
            name="ck_class_trial_complete_checkpoints",
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"],
            name="fk_class_trial_states_character_id_characters",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["current_attempt_id", "character_id"],
            ["game_activities.id", "game_activities.character_id"],
            name="fk_class_trial_attempt_character_activity",
        ),
        sa.PrimaryKeyConstraint("character_id", name="pk_class_trial_states"),
        sa.UniqueConstraint("current_attempt_id", name="uq_class_trial_current_attempt"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("LOCK TABLE class_trial_states IN SHARE ROW EXCLUSIVE MODE")
    if bind.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM class_trial_states)")):
        raise RuntimeError("Cannot downgrade while characters have Class Trial progress")
    op.drop_table("class_trial_states")
