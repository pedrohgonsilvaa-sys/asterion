"""Add persistent social groups and shared-activity confirmations."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261008_0022"
down_revision = "20261005_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("leader_character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('active','disbanded')", name="ck_social_group_status"),
        sa.CheckConstraint("revision >= 0", name="ck_social_group_revision"),
        sa.ForeignKeyConstraint(
            ["leader_character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "social_group_members",
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["social_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("character_id"),
    )
    op.create_index(
        "ix_social_group_members_group_joined",
        "social_group_members",
        ["group_id", "joined_at", "character_id"],
    )
    op.create_table(
        "social_group_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inviter_character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invitee_character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','accepted','declined','cancelled','expired')",
            name="ck_social_group_invite_status",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_social_group_invite_revision"),
        sa.ForeignKeyConstraint(["group_id"], ["social_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["inviter_character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["invitee_character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_pending_social_group_invite",
        "social_group_invites",
        ["group_id", "invitee_character_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_social_group_invites_inbox",
        "social_group_invites",
        ["invitee_character_id", "status", "expires_at"],
    )
    op.create_table(
        "group_activity_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", sa.String(32), nullable=False),
        sa.Column("proposer_character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "journey_reference_character_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "context_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cancel_reason", sa.String(48), nullable=True),
        sa.Column("activity_reference", sa.String(96), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','ready','declined','expired','cancelled','started',"
            "'completed','failed')",
            name="ck_group_activity_proposal_status",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_group_activity_proposal_revision"),
        sa.CheckConstraint("expires_at > created_at", name="ck_group_activity_proposal_expiry"),
        sa.CheckConstraint(
            "jsonb_typeof(context_payload) = 'object'",
            name="ck_group_activity_context_object",
        ),
        sa.CheckConstraint("activity_type <> ''", name="ck_group_activity_type_nonempty"),
        sa.ForeignKeyConstraint(
            ["group_id"], ["social_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["proposer_character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["journey_reference_character_id"], ["characters.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_group_activity_proposal_group_status",
        "group_activity_proposals",
        ["group_id", "status", "created_at"],
    )
    op.create_index(
        "ix_group_activity_proposal_expiry",
        "group_activity_proposals",
        ["status", "expires_at"],
    )
    op.create_table(
        "group_activity_participants",
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("eligibility", sa.String(16), nullable=False),
        sa.Column("eligibility_fingerprint", sa.String(64), nullable=True),
        sa.Column(
            "eligibility_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("response", sa.String(16), nullable=False),
        sa.Column("reservation_state", sa.String(16), server_default="active", nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "eligibility IN ('eligible','helper','ineligible')",
            name="ck_group_activity_participant_eligibility",
        ),
        sa.CheckConstraint(
            "response IN ('pending','accepted','declined','not_required')",
            name="ck_group_activity_participant_response",
        ),
        sa.CheckConstraint(
            "reservation_state IN ('active','released')",
            name="ck_group_activity_participant_reservation",
        ),
        sa.CheckConstraint(
            "eligibility != 'ineligible' OR response = 'not_required'",
            name="ck_group_activity_ineligible_response",
        ),
        sa.CheckConstraint(
            "eligibility = 'ineligible' OR response != 'not_required'",
            name="ck_group_activity_eligible_response",
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_group_activity_participant_ordinal"),
        sa.CheckConstraint(
            "jsonb_typeof(eligibility_snapshot) = 'object'",
            name="ck_group_activity_eligibility_snapshot_object",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["group_activity_proposals.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("proposal_id", "character_id"),
    )
    op.create_index(
        "uq_character_active_group_proposal",
        "group_activity_participants",
        ["character_id"],
        unique=True,
        postgresql_where=sa.text("reservation_state = 'active'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "group_activity_participants",
        "group_activity_proposals",
        "social_group_invites",
        "social_group_members",
        "social_groups",
    ):
        bind.execute(sa.text(f'LOCK TABLE "{table}" IN ACCESS EXCLUSIVE MODE'))
        if bind.execute(sa.text(f'SELECT EXISTS (SELECT 1 FROM "{table}")')).scalar_one():
            raise RuntimeError(f"Refusing to drop populated MMO group table {table}.")
    op.drop_index(
        "uq_character_active_group_proposal", table_name="group_activity_participants"
    )
    op.drop_table("group_activity_participants")
    op.drop_index(
        "ix_group_activity_proposal_expiry", table_name="group_activity_proposals"
    )
    op.drop_index(
        "ix_group_activity_proposal_group_status", table_name="group_activity_proposals"
    )
    op.drop_table("group_activity_proposals")
    op.drop_index("ix_social_group_invites_inbox", table_name="social_group_invites")
    op.drop_index("uq_pending_social_group_invite", table_name="social_group_invites")
    op.drop_table("social_group_invites")
    op.drop_index("ix_social_group_members_group_joined", table_name="social_group_members")
    op.drop_table("social_group_members")
    op.drop_table("social_groups")
