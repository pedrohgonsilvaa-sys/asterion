from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from asterion.domain.equipment import EQUIPMENT_SLOT_VALUES
from asterion.infrastructure.db.base import Base


class Account(Base):
    __tablename__ = "accounts"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)


class CreationDraft(Base):
    __tablename__ = "creation_drafts"
    __table_args__ = (
        UniqueConstraint("telegram_id", "server_id", name="uq_draft_actor_server"),
        CheckConstraint("version >= 0", name="ck_draft_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(ForeignKey("accounts.telegram_id"), nullable=False)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step: Mapped[str] = mapped_column(String(48), nullable=False, default="name")
    name: Mapped[str | None] = mapped_column(String(16))
    race: Mapped[str | None] = mapped_column(String(24))
    character_class: Mapped[str | None] = mapped_column(String(24))
    editing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(String(24))
    rejected_name: Mapped[str | None] = mapped_column(String(16))


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (
        UniqueConstraint("telegram_id", "server_id", name="uq_character_actor_server"),
        Index("uq_character_server_name", "server_id", text("lower(name)"), unique=True),
        CheckConstraint("name ~ '^[A-Z][a-z]{2,15}$'", name="ck_character_name"),
        CheckConstraint(
            "race IN ('remanescente','velado','cinereo','hemario','alvorano')",
            name="ck_character_race",
        ),
        CheckConstraint(
            "character_class IN ('sentinela','errante','vigia','tecelao','oraculo','luminar')",
            name="ck_character_class",
        ),
        CheckConstraint(
            "selected_path IS NULL OR selected_path IN ('bastiao','devastador','carrasco',"
            "'sabotador','atirador','rastreador','conjurador','runico','agoureiro',"
            "'invocador','guardiao','inquisidor')",
            name="ck_character_selected_path",
        ),
        CheckConstraint("level BETWEEN 1 AND 60 AND xp >= 0", name="ck_character_progress"),
        CheckConstraint("legacy_level BETWEEN 0 AND 5", name="ck_character_legacy_level"),
        CheckConstraint("hp >= 0 AND hp <= max_hp AND max_hp > 0", name="ck_character_hp"),
        CheckConstraint(
            "vigor BETWEEN 0 AND max_vigor AND max_vigor = 100", name="ck_character_vigor"
        ),
        CheckConstraint("crowns >= 0", name="ck_character_crowns"),
        CheckConstraint(
            "combat_configuration_version >= 0",
            name="ck_character_combat_configuration_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(ForeignKey("accounts.telegram_id"), nullable=False)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(16), nullable=False)
    race: Mapped[str] = mapped_column(String(24), nullable=False)
    character_class: Mapped[str] = mapped_column(String(24), nullable=False)
    selected_path: Mapped[str | None] = mapped_column(String(24))
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    xp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    legacy_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    hp: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    max_hp: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    vigor: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    vigor_regen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    max_vigor: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
    )
    # NULL on characters older than this column: they cannot become Chamado recruits.
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    crowns: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    elite_equipment_pity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    elite_legendary_pity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    delivery_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    tracked_secondary_quest_id: Mapped[str | None] = mapped_column(String(32))
    vigor_consumable_cycle: Mapped[date | None] = mapped_column(Date)
    combat_configuration_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class LegacyAscensionRecord(Base):
    """Immutable audit entry for a committed Legacy transition."""

    __tablename__ = "legacy_ascensions"
    __table_args__ = (
        UniqueConstraint(
            "character_id", "legacy_level_after", name="uq_legacy_level_per_character"
        ),
        UniqueConstraint("operation_key", name="uq_legacy_ascension_operation"),
        CheckConstraint("legacy_level_after BETWEEN 1 AND 5", name="ck_legacy_ascension_level"),
        CheckConstraint("character_level_before = 60", name="ck_legacy_ascension_level_before"),
        CheckConstraint("xp_before >= 0", name="ck_legacy_ascension_xp_before"),
        CheckConstraint(
            "configuration_version_before >= 0",
            name="ck_legacy_ascension_config_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    legacy_level_after: Mapped[int] = mapped_column(Integer, nullable=False)
    character_level_before: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_before: Mapped[int] = mapped_column(BigInteger, nullable=False)
    campaign_quest_id: Mapped[str] = mapped_column(String(32), nullable=False)
    operation_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    configuration_version_before: Mapped[int] = mapped_column(Integer, nullable=False)
    ascended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LegacyAscensionConfirmation(Base):
    """One current, stale-safe explicit confirmation for a character."""

    __tablename__ = "legacy_ascension_confirmations"
    __table_args__ = (
        UniqueConstraint("confirmation_key", name="uq_legacy_confirmation_key"),
        CheckConstraint(
            "expected_configuration_version >= 0",
            name="ck_legacy_confirmation_config_version",
        ),
        CheckConstraint("expires_at > created_at", name="ck_legacy_confirmation_expiry"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    confirmation_key: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    expected_configuration_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SocialGroup(Base):
    """Persistent social group; activity rosters are stored separately."""

    __tablename__ = "social_groups"
    __table_args__ = (
        CheckConstraint("status IN ('active','disbanded')", name="ck_social_group_status"),
        CheckConstraint("revision >= 0", name="ck_social_group_revision"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    leader_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SocialGroupMember(Base):
    """One-character membership; a character can be in only one social group."""

    __tablename__ = "social_group_members"
    __table_args__ = (
        Index("ix_social_group_members_group_joined", "group_id", "joined_at", "character_id"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_groups.id", ondelete="CASCADE"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SocialGroupInvite(Base):
    """Targeted, persistent invitation that expires ten minutes after creation."""

    __tablename__ = "social_group_invites"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','declined','cancelled','expired')",
            name="ck_social_group_invite_status",
        ),
        CheckConstraint("revision >= 0", name="ck_social_group_invite_revision"),
        Index(
            "uq_pending_social_group_invite",
            "group_id",
            "invitee_character_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_social_group_invites_inbox", "invitee_character_id", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_groups.id", ondelete="CASCADE"), nullable=False
    )
    inviter_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    invitee_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GroupActivityProposal(Base):
    """A durable 60-second confirmation before any shared activity is created."""

    __tablename__ = "group_activity_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','ready','declined','expired','cancelled','started',"
            "'completed','failed')",
            name="ck_group_activity_proposal_status",
        ),
        CheckConstraint("revision >= 0", name="ck_group_activity_proposal_revision"),
        CheckConstraint("expires_at > created_at", name="ck_group_activity_proposal_expiry"),
        CheckConstraint(
            "context_payload IS NULL OR jsonb_typeof(context_payload) = 'object'",
            name="ck_group_activity_context_object",
        ),
        CheckConstraint("activity_type <> ''", name="ck_group_activity_type_nonempty"),
        Index("ix_group_activity_proposal_group_status", "group_id", "status", "created_at"),
        Index("ix_group_activity_proposal_expiry", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_groups.id", ondelete="CASCADE"), nullable=False
    )
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    proposer_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    journey_reference_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    context_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cancel_reason: Mapped[str | None] = mapped_column(String(48))
    activity_reference: Mapped[str | None] = mapped_column(String(96))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GroupActivityParticipant(Base):
    """Candidate status and immutable consent record for a group activity."""

    __tablename__ = "group_activity_participants"
    __table_args__ = (
        PrimaryKeyConstraint("proposal_id", "character_id"),
        CheckConstraint(
            "eligibility IN ('eligible','helper','ineligible')",
            name="ck_group_activity_participant_eligibility",
        ),
        CheckConstraint(
            "response IN ('pending','accepted','declined','not_required')",
            name="ck_group_activity_participant_response",
        ),
        CheckConstraint(
            "reservation_state IN ('active','released')",
            name="ck_group_activity_participant_reservation",
        ),
        CheckConstraint(
            "eligibility != 'ineligible' OR response = 'not_required'",
            name="ck_group_activity_ineligible_response",
        ),
        CheckConstraint(
            "eligibility = 'ineligible' OR response != 'not_required'",
            name="ck_group_activity_eligible_response",
        ),
        CheckConstraint("ordinal >= 0", name="ck_group_activity_participant_ordinal"),
        CheckConstraint(
            "eligibility_snapshot IS NULL OR jsonb_typeof(eligibility_snapshot) = 'object'",
            name="ck_group_activity_eligibility_snapshot_object",
        ),
        Index(
            "uq_character_active_group_proposal",
            "character_id",
            unique=True,
            postgresql_where=text("reservation_state = 'active'"),
        ),
    )

    proposal_id: Mapped[UUID] = mapped_column(
        ForeignKey("group_activity_proposals.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    eligibility: Mapped[str] = mapped_column(String(16), nullable=False)
    eligibility_fingerprint: Mapped[str | None] = mapped_column(String(64))
    eligibility_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    response: Mapped[str] = mapped_column(String(16), nullable=False)
    reservation_state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignJourney(Base):
    """Persistent campaign context; character Quest rows remain authoritative."""

    __tablename__ = "campaign_journeys"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','paused','completed','cancelled')",
            name="ck_campaign_journey_status",
        ),
        CheckConstraint("revision >= 0", name="ck_campaign_journey_revision"),
        CheckConstraint(
            "context_payload IS NULL OR jsonb_typeof(context_payload) = 'object'",
            name="ck_campaign_journey_context_object",
        ),
        Index("ix_campaign_journeys_group_status", "group_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_groups.id", ondelete="CASCADE"), nullable=False
    )
    quest_id: Mapped[str] = mapped_column(String(32), nullable=False)
    checkpoint: Mapped[str] = mapped_column(String(96), nullable=False)
    journey_reference_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    technical_host_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="RESTRICT"), nullable=False
    )
    context_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CampaignJourneyMember(Base):
    """Membership snapshot for one cooperative campaign journey."""

    __tablename__ = "campaign_journey_members"
    __table_args__ = (
        PrimaryKeyConstraint("journey_id", "character_id"),
        CheckConstraint("role IN ('eligible','helper')", name="ck_campaign_journey_member_role"),
        CheckConstraint(
            "status IN ('active','left','completed')",
            name="ck_campaign_journey_member_status",
        ),
        Index("ix_campaign_journey_member_character", "character_id", "status"),
    )

    journey_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaign_journeys.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    checkpoint_snapshot: Mapped[str] = mapped_column(String(96), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignSharedEncounter(Base):
    """One frozen, reconnectable combat shared by an activity roster."""

    __tablename__ = "campaign_shared_encounters"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','completed','failed','paused')",
            name="ck_campaign_shared_encounter_status",
        ),
        CheckConstraint(
            "roster_size BETWEEN 1 AND 4", name="ck_campaign_shared_encounter_roster_size"
        ),
        CheckConstraint("state_version >= 0", name="ck_campaign_shared_encounter_version"),
        CheckConstraint(
            "scaling_snapshot IS NULL OR jsonb_typeof(scaling_snapshot) = 'object'",
            name="ck_campaign_shared_encounter_scaling_object",
        ),
        CheckConstraint(
            "combat_snapshot IS NULL OR jsonb_typeof(combat_snapshot) = 'object'",
            name="ck_campaign_shared_encounter_combat_object",
        ),
        UniqueConstraint("proposal_id", name="uq_campaign_shared_encounter_proposal"),
        Index("ix_campaign_shared_encounters_journey_status", "journey_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    journey_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaign_journeys.id", ondelete="SET NULL")
    )
    proposal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("group_activity_proposals.id", ondelete="SET NULL")
    )
    quest_id: Mapped[str] = mapped_column(String(32), nullable=False)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    journey_reference_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    technical_host_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="RESTRICT"), nullable=False
    )
    roster_size: Mapped[int] = mapped_column(Integer, nullable=False)
    scaling_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    state_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    combat_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignSharedEncounterMember(Base):
    """Per-character foreground lease and idempotent result state for shared combat."""

    __tablename__ = "campaign_shared_encounter_members"
    __table_args__ = (
        PrimaryKeyConstraint("shared_encounter_id", "character_id"),
        UniqueConstraint("game_activity_id", name="uq_campaign_shared_member_activity"),
        UniqueConstraint(
            "shared_encounter_id", "actor_key", name="uq_campaign_shared_member_actor"
        ),
        CheckConstraint("role IN ('eligible','helper')", name="ck_campaign_shared_member_role"),
        CheckConstraint(
            "settlement_state IN ('pending','settled')",
            name="ck_campaign_shared_member_settlement",
        ),
        Index("ix_campaign_shared_member_character", "character_id", "shared_encounter_id"),
    )

    shared_encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaign_shared_encounters.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    game_activity_id: Mapped[UUID] = mapped_column(
        ForeignKey("game_activities.id", ondelete="CASCADE"), nullable=False
    )
    actor_key: Mapped[str] = mapped_column(String(16), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    checkpoint_snapshot: Mapped[str] = mapped_column(String(96), nullable=False)
    settlement_state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    result: Mapped[str | None] = mapped_column(String(16))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignObjectiveCredit(Base):
    """Idempotent evidence record for a shared objective credited per character."""

    __tablename__ = "campaign_objective_credits"
    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "quest_id",
            "objective_id",
            "source_key",
            name="uq_campaign_objective_credit",
        ),
        Index("ix_campaign_objective_credit_source", "source_key", "quest_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    journey_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaign_journeys.id", ondelete="SET NULL")
    )
    quest_id: Mapped[str] = mapped_column(String(32), nullable=False)
    objective_id: Mapped[str] = mapped_column(String(96), nullable=False)
    source_key: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CharacterProfile(Base):
    """Optional player-authored character history and pending Telegram input."""

    __tablename__ = "character_profiles"
    __table_args__ = (
        CheckConstraint("revision >= 0", name="ck_character_profile_revision"),
        CheckConstraint(
            "history IS NULL OR char_length(history) <= 1200",
            name="ck_character_profile_history_length",
        ),
        CheckConstraint(
            "history_prompt_message_id IS NULL OR history_prompt_message_id > 0",
            name="ck_character_profile_prompt_message_id",
        ),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    history: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    history_prompt_message_id: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CharacterNotificationPreference(Base):
    """Sparse per-character notification overrides; absent rows mean enabled."""

    __tablename__ = "character_notification_preferences"
    __table_args__ = (
        CheckConstraint(
            "category IN ('essentials','events','competitive','guild','market','chronicle')",
            name="ck_character_notification_category",
        ),
        CheckConstraint("revision >= 0", name="ck_character_notification_revision"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(16), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CharacterNameReservation(Base):
    """Normalized names kept unavailable after rename or deletion."""

    __tablename__ = "character_name_reservations"
    __table_args__ = (
        CheckConstraint("normalized_name ~ '^[a-z]{3,16}$'", name="ck_name_reservation_name"),
        CheckConstraint("source IN ('rename','deletion')", name="ck_name_reservation_source"),
        Index("ix_name_reservation_expiry", "reserved_until"),
    )

    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    normalized_name: Mapped[str] = mapped_column(String(16), primary_key=True)
    reserved_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    origin_character_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CharacterRenameHistory(Base):
    """Administrative identity history retained after character deletion."""

    __tablename__ = "character_rename_history"
    __table_args__ = (
        CheckConstraint("origin IN ('player')", name="ck_character_rename_origin"),
        Index("ix_character_rename_history", "character_id", "renamed_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    old_name: Mapped[str] = mapped_column(String(16), nullable=False)
    new_name: Mapped[str] = mapped_column(String(16), nullable=False)
    renamed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="player")


class CharacterDeletionRequest(Base):
    """Deletion workflow history is retained after its Character row is purged."""

    __tablename__ = "character_deletion_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('preview','pending','cancelled','completed')",
            name="ck_character_deletion_status",
        ),
        CheckConstraint("revision >= 0", name="ck_character_deletion_revision"),
        CheckConstraint("due_at > requested_at", name="ck_character_deletion_due"),
        Index(
            "uq_open_character_deletion",
            "character_id",
            unique=True,
            postgresql_where=text("status IN ('preview','pending')"),
        ),
        Index(
            "ix_due_character_deletions",
            "due_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name_at_request: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class CharacterAccountInput(Base):
    """Durable, versioned state for an uncommitted character rename input."""

    __tablename__ = "character_account_inputs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting','preview','invalid','unavailable')",
            name="ck_character_account_input_status",
        ),
        CheckConstraint("revision >= 0", name="ck_character_account_input_revision"),
        CheckConstraint("prompt_message_id > 0", name="ck_character_account_input_prompt"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    prompt_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_name: Mapped[str] = mapped_column(String(16), nullable=False)
    new_name: Mapped[str | None] = mapped_column(String(16))
    last_update_id: Mapped[int | None] = mapped_column(BigInteger)
    error: Mapped[str | None] = mapped_column(String(16))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CharacterPendingInput(Base):
    """One persistent Telegram free-text prompt may be active per character."""

    __tablename__ = "character_pending_inputs"
    __table_args__ = (
        CheckConstraint(
            "input_kind IN ('history','doctrine_name','rename')",
            name="ck_character_pending_input_kind",
        ),
        CheckConstraint("prompt_message_id > 0", name="ck_character_pending_input_prompt"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    input_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    prompt_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Brazier(Base):
    __tablename__ = "braziers"
    __table_args__ = (UniqueConstraint("character_id", "brazier_id", name="uq_character_brazier"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    brazier_id: Mapped[str] = mapped_column(String(64), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Achievement(Base):
    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("character_id", "achievement_id", name="uq_character_achievement"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    achievement_id: Mapped[str] = mapped_column(String(64), nullable=False)


class CharacterCosmetic(Base):
    """A permanent cosmetic entitlement earned by one character."""

    __tablename__ = "character_cosmetics"
    __table_args__ = (
        PrimaryKeyConstraint("character_id", "cosmetic_id", name="pk_character_cosmetics"),
        UniqueConstraint(
            "character_id",
            "cosmetic_type",
            "cosmetic_id",
            name="uq_character_cosmetic_type_id",
        ),
        CheckConstraint(
            "cosmetic_type IN ('appearance','title','emblem','frame','banner')",
            name="ck_character_cosmetic_type",
        ),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    cosmetic_id: Mapped[str] = mapped_column(String(96), nullable=False)
    cosmetic_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_achievement_id: Mapped[str] = mapped_column(String(64), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CharacterCosmeticSelection(Base):
    """At most one owned cosmetic selected for each presentation category."""

    __tablename__ = "character_cosmetic_selections"
    __table_args__ = (
        PrimaryKeyConstraint(
            "character_id", "cosmetic_type", name="pk_character_cosmetic_selection"
        ),
        ForeignKeyConstraint(
            ["character_id", "cosmetic_type", "cosmetic_id"],
            [
                "character_cosmetics.character_id",
                "character_cosmetics.cosmetic_type",
                "character_cosmetics.cosmetic_id",
            ],
            ondelete="CASCADE",
            name="fk_character_cosmetic_selection_owned",
        ),
        CheckConstraint(
            "cosmetic_type IN ('appearance','title','emblem','frame','banner')",
            name="ck_character_cosmetic_selection_type",
        ),
    )

    character_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    cosmetic_type: Mapped[str] = mapped_column(String(16), nullable=False)
    cosmetic_id: Mapped[str] = mapped_column(String(96), nullable=False)


class CharacterDoctrine(Base):
    """A saved reference-based character combat configuration."""

    __tablename__ = "character_doctrines"
    __table_args__ = (
        UniqueConstraint("id", "character_id", name="uq_character_doctrine_owner"),
        Index(
            "uq_character_doctrine_name",
            "character_id",
            text("lower(name)"),
            unique=True,
        ),
        CheckConstraint("char_length(name) BETWEEN 1 AND 40", name="ck_doctrine_name_length"),
        CheckConstraint("revision >= 0", name="ck_doctrine_revision"),
        CheckConstraint(
            "jsonb_typeof(configuration) = 'object'",
            name="ck_doctrine_configuration_object",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CharacterDoctrineInput(Base):
    """Durable, stale-safe Telegram name input for Doctrine creation/rename."""

    __tablename__ = "character_doctrine_inputs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["doctrine_id", "character_id"],
            ["character_doctrines.id", "character_doctrines.character_id"],
            ondelete="CASCADE",
            name="fk_character_doctrine_input_target",
        ),
        CheckConstraint("action IN ('create','rename')", name="ck_doctrine_input_action"),
        CheckConstraint(
            "(action = 'create' AND doctrine_id IS NULL) OR "
            "(action = 'rename' AND doctrine_id IS NOT NULL)",
            name="ck_doctrine_input_target",
        ),
        CheckConstraint("expected_revision >= 0", name="ck_doctrine_input_revision"),
        CheckConstraint(
            "expected_configuration_version >= 0", name="ck_doctrine_input_config_version"
        ),
        CheckConstraint("prompt_message_id > 0", name="ck_doctrine_input_prompt"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    doctrine_id: Mapped[UUID | None] = mapped_column(Uuid)
    expected_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_configuration_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Quest(Base):
    __tablename__ = "quests"
    __table_args__ = (
        UniqueConstraint("character_id", "quest_id", name="uq_character_quest"),
        CheckConstraint("status IN ('active','completed','abandoned')", name="ck_quest_status"),
        CheckConstraint("step >= 1", name="ck_quest_step"),
        CheckConstraint("state_version >= 0", name="ck_quest_state_version"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    quest_id: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="tdo-1.0.2", server_default="tdo-1.0.2"
    )
    state_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    progress: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class LocationDiscovery(Base):
    __tablename__ = "location_discoveries"
    __table_args__ = (
        UniqueConstraint("character_id", "location_id", name="uq_character_location"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    location_id: Mapped[str] = mapped_column(String(64), nullable=False)


class CodexEntry(Base):
    __tablename__ = "codex_entries"
    __table_args__ = (UniqueConstraint("character_id", "entry_id", name="uq_character_codex"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    entry_id: Mapped[str] = mapped_column(String(96), nullable=False)


class Unlock(Base):
    __tablename__ = "unlocks"
    __table_args__ = (UniqueConstraint("character_id", "unlock_id", name="uq_character_unlock"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    unlock_id: Mapped[str] = mapped_column(String(96), nullable=False)


class ClassTrialState(Base):
    """Durable shared progression state for a character's one Class Trial."""

    __tablename__ = "class_trial_states"
    __table_args__ = (
        CheckConstraint(
            "character_class IN ('sentinela','errante','vigia','tecelao','oraculo','luminar')",
            name="ck_class_trial_class",
        ),
        CheckConstraint("status IN ('ready','active','completed')", name="ck_class_trial_status"),
        CheckConstraint("current_stage BETWEEN 1 AND 3", name="ck_class_trial_stage"),
        CheckConstraint("state_version >= 0", name="ck_class_trial_state_version"),
        CheckConstraint(
            "(status = 'active') = (current_attempt_id IS NOT NULL)",
            name="ck_class_trial_attempt_status",
        ),
        CheckConstraint(
            "(status = 'active') = (attempt_state IS NOT NULL)",
            name="ck_class_trial_attempt_snapshot",
        ),
        CheckConstraint(
            "jsonb_typeof(completed_stages) = 'array'",
            name="ck_class_trial_checkpoints_array",
        ),
        CheckConstraint(
            "stage_definition IS NULL OR jsonb_typeof(stage_definition) = 'object'",
            name="ck_class_trial_stage_definition_object",
        ),
        CheckConstraint(
            "attempt_state IS NULL OR jsonb_typeof(attempt_state) = 'object'",
            name="ck_class_trial_attempt_state_object",
        ),
        CheckConstraint(
            "context IN ('circle','refuge')",
            name="ck_class_trial_context",
        ),
        CheckConstraint(
            "status != 'completed' OR completed_stages = '[1,2,3]'::jsonb",
            name="ck_class_trial_complete_checkpoints",
        ),
        ForeignKeyConstraint(
            ["current_attempt_id", "character_id"],
            ["game_activities.id", "game_activities.character_id"],
            name="fk_class_trial_attempt_character_activity",
        ),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    character_class: Mapped[str] = mapped_column(String(24), nullable=False)
    trial_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ready", server_default="ready"
    )
    current_stage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    completed_stages: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    state_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    context: Mapped[str] = mapped_column(
        String(16), nullable=False, default="circle", server_default="circle"
    )
    current_attempt_id: Mapped[UUID | None] = mapped_column(Uuid, unique=True)
    stage_definition: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    attempt_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))


class MaterialStack(Base):
    __tablename__ = "material_stacks"
    __table_args__ = (CheckConstraint("quantity BETWEEN 0 AND 999", name="ck_material_quantity"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    material_id: Mapped[str] = mapped_column(String(96), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    bound: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


class WarehouseMaterialStack(Base):
    """A material stack kept in the character's canonical 100-slot Warehouse."""

    __tablename__ = "warehouse_material_stacks"
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 999", name="ck_warehouse_material_quantity"),
        Index("ix_warehouse_material_character", "character_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    material_id: Mapped[str] = mapped_column(String(96), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    bound: Mapped[bool] = mapped_column(Boolean, nullable=False)


class RewardEvent(Base):
    __tablename__ = "reward_events"
    __table_args__ = (
        UniqueConstraint("character_id", "source_id", name="uq_character_reward_source"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(96), nullable=False)


class RewardComponent(Base):
    __tablename__ = "reward_components"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reward_event_id: Mapped[UUID] = mapped_column(ForeignKey("reward_events.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    item_id: Mapped[str | None] = mapped_column(String(96))
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class WorldState(Base):
    __tablename__ = "world_states"
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), primary_key=True)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    location: Mapped[str] = mapped_column(String(64), nullable=False)


class GameActivity(Base):
    __tablename__ = "game_activities"
    __table_args__ = (
        UniqueConstraint("id", "character_id", name="uq_activity_character"),
        Index(
            "uq_active_foreground",
            "character_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "uq_first_combat_occurrence",
            "character_id",
            "content_id",
            unique=True,
            postgresql_where=text("content_id = 'prologue_first_combat'"),
        ),
        CheckConstraint("status IN ('active','completed','failed')", name="ck_activity_status"),
        CheckConstraint("state_version >= 0", name="ck_activity_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    last_valid_action_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    game_activity_id: Mapped[UUID] = mapped_column(
        ForeignKey("game_activities.id"),
        nullable=False,
        unique=True,
    )


class CombatRecord(Base):
    __tablename__ = "combats"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id"), nullable=False, unique=True
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class RewardGrant(Base):
    __tablename__ = "reward_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["game_activity_id", "character_id"],
            ["game_activities.id", "game_activities.character_id"],
            name="fk_grant_activity_character",
        ),
        CheckConstraint("xp >= 0", name="ck_grant_xp"),
    )

    game_activity_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id"), nullable=False, index=True
    )
    xp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DungeonRun(Base):
    """Durable, multiplayer-capable state for one dungeon expedition."""

    __tablename__ = "dungeon_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','completed','failed','expired')",
            name="ck_dungeon_run_status",
        ),
        CheckConstraint(
            "difficulty IN ('stable','fractured','rupture')",
            name="ck_dungeon_run_difficulty",
        ),
        CheckConstraint("initial_group_size BETWEEN 1 AND 4", name="ck_dungeon_run_group_size"),
        CheckConstraint("current_encounter_ordinal >= 1", name="ck_dungeon_run_ordinal"),
        CheckConstraint("state_version >= 0", name="ck_dungeon_run_state_version"),
        CheckConstraint(
            "active_checkpoint_encounter IS NULL OR active_checkpoint_encounter >= 1",
            name="ck_dungeon_run_checkpoint",
        ),
        CheckConstraint("jsonb_typeof(progress) = 'object'", name="ck_dungeon_run_progress"),
        Index(
            "ix_dungeon_runs_active_updated",
            "last_activity_at",
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dungeon_family_id: Mapped[str] = mapped_column(String(96), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    content_version: Mapped[str] = mapped_column(String(48), nullable=False)
    reference_level: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_group_size: Mapped[int] = mapped_column(Integer, nullable=False)
    current_encounter_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    seed: Mapped[str] = mapped_column(String(128), nullable=False)
    has_brazier: Mapped[bool] = mapped_column(Boolean, nullable=False)
    brazier_activated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    brazier_after_encounter: Mapped[int | None] = mapped_column(Integer)
    active_checkpoint_encounter: Mapped[int | None] = mapped_column(Integer)
    progress: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DungeonRunMember(Base):
    """Run participant record; D1 creates one participant, D2 may add up to four."""

    __tablename__ = "dungeon_run_members"
    __table_args__ = (
        PrimaryKeyConstraint("run_id", "character_id", name="pk_dungeon_run_members"),
        UniqueConstraint("run_id", "position", name="uq_dungeon_run_member_position"),
        CheckConstraint("position BETWEEN 1 AND 4", name="ck_dungeon_run_member_position"),
        CheckConstraint(
            "status IN ('active','defeated','left')",
            name="ck_dungeon_run_member_status",
        ),
        CheckConstraint("vigor_reserved >= 0", name="ck_dungeon_run_member_vigor"),
        CheckConstraint("consumable_uses >= 0", name="ck_dungeon_run_member_consumables"),
        CheckConstraint("hp >= 0 AND max_hp > 0 AND hp <= max_hp", name="ck_dungeon_run_member_hp"),
        CheckConstraint(
            "jsonb_typeof(combat_configuration) = 'object'",
            name="ck_dungeon_run_member_config",
        ),
        CheckConstraint("jsonb_typeof(run_state) = 'object'", name="ck_dungeon_run_member_state"),
        CheckConstraint(
            "jsonb_typeof(contribution) = 'object'",
            name="ck_dungeon_run_member_contribution",
        ),
        Index(
            "uq_dungeon_active_member",
            "character_id",
            unique=True,
            postgresql_where=text("status IN ('active','defeated')"),
        ),
    )

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("dungeon_runs.id", ondelete="CASCADE"), nullable=False
    )
    foreground_activity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_activities.id", ondelete="SET NULL"), unique=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    vigor_reserved: Mapped[int] = mapped_column(Integer, nullable=False)
    vigor_refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consumable_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    combat_configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    hp: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    max_hp: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    run_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    contribution: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class DungeonRunEncounter(Base):
    """One stable encounter slot, with its latest retry activity reference."""

    __tablename__ = "dungeon_run_encounters"
    __table_args__ = (
        PrimaryKeyConstraint("run_id", "encounter_ordinal", name="pk_dungeon_run_encounters"),
        CheckConstraint("encounter_ordinal >= 1", name="ck_dungeon_encounter_ordinal"),
        CheckConstraint(
            "status IN ('pending','active','completed')",
            name="ck_dungeon_encounter_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_dungeon_encounter_attempt_count"),
        CheckConstraint("jsonb_typeof(progress) = 'object'", name="ck_dungeon_encounter_progress"),
        ForeignKeyConstraint(
            ["activity_id"], ["game_activities.id"], name="fk_dungeon_encounter_activity"
        ),
        UniqueConstraint("activity_id", name="uq_dungeon_encounter_activity"),
    )

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("dungeon_runs.id", ondelete="CASCADE"), nullable=False
    )
    encounter_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_id: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    activity_id: Mapped[UUID | None] = mapped_column(Uuid)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    reward_settled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DungeonPityState(Base):
    __tablename__ = "dungeon_pity_states"
    __table_args__ = (
        CheckConstraint("legendary_plus_points >= 0", name="ck_dungeon_pity_legendary_points"),
        CheckConstraint("mythic_points >= 0", name="ck_dungeon_pity_mythic_points"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    legendary_plus_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mythic_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DungeonLobby(Base):
    """Durable group-formation and ready-check state for dungeon runs."""

    __tablename__ = "dungeon_lobbies"
    __table_args__ = (
        CheckConstraint("mode IN ('invite','matchmaking')", name="ck_dungeon_lobby_mode"),
        CheckConstraint(
            "status IN ('forming','confirming','started','cancelled','expired')",
            name="ck_dungeon_lobby_status",
        ),
        CheckConstraint("state_version >= 0", name="ck_dungeon_lobby_state_version"),
        Index(
            "ix_dungeon_lobbies_open",
            "dungeon_family_id",
            "difficulty",
            "created_at",
            postgresql_where=text("status IN ('forming','confirming')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dungeon_family_id: Mapped[str] = mapped_column(String(96), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="forming")
    leader_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmation_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("dungeon_runs.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DungeonLobbyMember(Base):
    """One participant's durable state in a lobby/ready check."""

    __tablename__ = "dungeon_lobby_members"
    __table_args__ = (
        PrimaryKeyConstraint("lobby_id", "character_id", name="pk_dungeon_lobby_members"),
        UniqueConstraint("lobby_id", "position", name="uq_dungeon_lobby_position"),
        CheckConstraint("position BETWEEN 1 AND 4", name="ck_dungeon_lobby_position"),
        CheckConstraint(
            "status IN ('invited','joined','queued','matched','confirmed','declined','left')",
            name="ck_dungeon_lobby_member_status",
        ),
        Index(
            "uq_dungeon_open_lobby_member",
            "character_id",
            unique=True,
            postgresql_where=text("status IN ('invited','joined','queued','matched','confirmed')"),
        ),
    )

    lobby_id: Mapped[UUID] = mapped_column(
        ForeignKey("dungeon_lobbies.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    foreground_activity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_activities.id", ondelete="SET NULL"), unique=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="joined")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DungeonInvite(Base):
    """Persistent, cancellable, expiring invite with no resource reservation."""

    __tablename__ = "dungeon_invites"
    __table_args__ = (
        UniqueConstraint("lobby_id", "invitee_character_id", name="uq_dungeon_invite_target"),
        CheckConstraint(
            "status IN ('pending','accepted','declined','cancelled','expired')",
            name="ck_dungeon_invite_status",
        ),
        CheckConstraint("state_version >= 0", name="ck_dungeon_invite_version"),
        Index(
            "ix_dungeon_invites_pending",
            "invitee_character_id",
            "expires_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    lobby_id: Mapped[UUID] = mapped_column(
        ForeignKey("dungeon_lobbies.id", ondelete="CASCADE"), nullable=False
    )
    inviter_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    invitee_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DungeonMatchQueue(Base):
    """One active matchmaking request per character."""

    __tablename__ = "dungeon_match_queue"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','matched','cancelled','expired')",
            name="ck_dungeon_match_queue_status",
        ),
        Index(
            "ix_dungeon_match_queue_grouping",
            "dungeon_family_id",
            "difficulty",
            "created_at",
            postgresql_where=text("status = 'queued'"),
        ),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    dungeon_family_id: Mapped[str] = mapped_column(String(96), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    lobby_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("dungeon_lobbies.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CreationInput(Base):
    """Durable Telegram update deduplication, including text input across step changes."""

    __tablename__ = "creation_inputs"

    telegram_id: Mapped[int] = mapped_column(ForeignKey("accounts.telegram_id"), primary_key=True)
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    aggregate_key: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class HuntContext(Base):
    """Materialized, repeatable hunt facts attached to a foreground activity."""

    __tablename__ = "hunt_contexts"
    __table_args__ = (
        UniqueConstraint("game_activity_id", name="uq_hunt_activity"),
        CheckConstraint("enemy_level >= 1", name="ck_hunt_enemy_level"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    game_activity_id: Mapped[UUID] = mapped_column(ForeignKey("game_activities.id"), nullable=False)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    local_id: Mapped[str] = mapped_column(String(64), nullable=False)
    creature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    enemy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    variant: Mapped[str | None] = mapped_column(String(24))
    seed: Mapped[str] = mapped_column(String(128), nullable=False)
    loot_profile: Mapped[str] = mapped_column(String(32), nullable=False, default="hunt")
    pvpve_collision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pvpve_collisions.id", ondelete="SET NULL")
    )
    pvpve_reference_level: Mapped[int | None] = mapped_column(Integer)
    pvpve_domain_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    result_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class GroupHuntEncounter(Base):
    """One frozen PvE encounter shared by an individual activity roster."""

    __tablename__ = "group_hunt_encounters"
    __table_args__ = (
        CheckConstraint("roster_size BETWEEN 2 AND 4", name="ck_group_hunt_roster_size"),
        CheckConstraint("enemy_level >= 1", name="ck_group_hunt_enemy_level"),
        CheckConstraint("reference_level >= 1", name="ck_group_hunt_reference_level"),
        CheckConstraint("state_version >= 0", name="ck_group_hunt_version"),
        CheckConstraint(
            "status IN ('active','completed','failed')", name="ck_group_hunt_status"
        ),
        CheckConstraint(
            "jsonb_typeof(scaling_snapshot) = 'object'",
            name="ck_group_hunt_scaling_object",
        ),
        CheckConstraint(
            "jsonb_typeof(combat_snapshot) = 'object'",
            name="ck_group_hunt_combat_object",
        ),
        UniqueConstraint("proposal_id", name="uq_group_hunt_proposal"),
        Index("ix_group_hunt_group_status", "group_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_groups.id", ondelete="CASCADE"), nullable=False
    )
    proposal_id: Mapped[UUID] = mapped_column(
        ForeignKey("group_activity_proposals.id", ondelete="RESTRICT"), nullable=False
    )
    local_id: Mapped[str] = mapped_column(String(64), nullable=False)
    creature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    enemy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_level: Mapped[int] = mapped_column(Integer, nullable=False)
    variant: Mapped[str | None] = mapped_column(String(24))
    seed: Mapped[str] = mapped_column(String(128), nullable=False)
    roster_size: Mapped[int] = mapped_column(Integer, nullable=False)
    scaling_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    combat_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True)
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    combat_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GroupHuntMember(Base):
    """Individual activity lease, turn identity and reward seed in a Group Hunt."""

    __tablename__ = "group_hunt_members"
    __table_args__ = (
        PrimaryKeyConstraint("group_hunt_encounter_id", "character_id"),
        UniqueConstraint("game_activity_id", name="uq_group_hunt_member_activity"),
        UniqueConstraint("group_hunt_encounter_id", "actor_key", name="uq_group_hunt_member_actor"),
        CheckConstraint("ordinal BETWEEN 1 AND 4", name="ck_group_hunt_member_ordinal"),
        CheckConstraint("consumable_uses >= 0", name="ck_group_hunt_member_consumables"),
        CheckConstraint(
            "settlement_state IN ('pending','settled')",
            name="ck_group_hunt_member_settlement",
        ),
        Index("ix_group_hunt_member_character", "character_id", "group_hunt_encounter_id"),
    )

    group_hunt_encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("group_hunt_encounters.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    game_activity_id: Mapped[UUID] = mapped_column(
        ForeignKey("game_activities.id", ondelete="CASCADE"), nullable=False
    )
    actor_key: Mapped[str] = mapped_column(String(16), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    loot_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    consumable_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    settlement_state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    result: Mapped[str | None] = mapped_column(String(16))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PvpveQueue(Base):
    """A short-lived hunt intent, matched only before a prey is materialized."""

    __tablename__ = "pvpve_queues"
    __table_args__ = (
        CheckConstraint("roster_size BETWEEN 1 AND 4", name="ck_pvpve_queue_roster_size"),
        CheckConstraint("source_type IN ('manual','group','round')", name="ck_pvpve_queue_source"),
        CheckConstraint(
            "status IN ('waiting','matched','expired','cancelled')",
            name="ck_pvpve_queue_status",
        ),
        CheckConstraint("jsonb_typeof(roster_snapshot) = 'array'", name="ck_pvpve_queue_roster"),
        UniqueConstraint("proposal_id", name="uq_pvpve_queue_proposal"),
        Index(
            "ix_pvpve_queue_match",
            "server_id",
            "local_id",
            "roster_size",
            "status",
            "created_at",
        ),
        Index(
            "uq_pvpve_queue_waiting_group",
            "group_id",
            unique=True,
            postgresql_where=text("status = 'waiting' AND group_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    local_id: Mapped[str] = mapped_column(String(64), nullable=False)
    roster_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("social_groups.id", ondelete="SET NULL")
    )
    proposal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("group_activity_proposals.id", ondelete="SET NULL")
    )
    roster_snapshot: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="waiting", server_default="waiting"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PvpveQueueMember(Base):
    __tablename__ = "pvpve_queue_members"
    __table_args__ = (
        PrimaryKeyConstraint("queue_id", "character_id"),
        CheckConstraint("ordinal BETWEEN 1 AND 4", name="ck_pvpve_queue_ordinal"),
        Index("ix_pvpve_queue_member_character", "character_id", "queue_id"),
        Index("ix_pvpve_queue_member_activity", "game_activity_id", "character_id"),
    )

    queue_id: Mapped[UUID] = mapped_column(
        ForeignKey("pvpve_queues.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), nullable=False
    )
    game_activity_id: Mapped[UUID] = mapped_column(
        ForeignKey("game_activities.id", ondelete="CASCADE"), nullable=False
    )
    actor_key: Mapped[str] = mapped_column(String(16), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)


class PvpveCollision(Base):
    __tablename__ = "pvpve_collisions"
    __table_args__ = (
        CheckConstraint("roster_size BETWEEN 1 AND 4", name="ck_pvpve_collision_roster"),
        CheckConstraint("state_version >= 0", name="ck_pvpve_collision_version"),
        CheckConstraint(
            "status IN ('active','prey','completed','failed')", name="ck_pvpve_collision_status"
        ),
        CheckConstraint(
            "winner_side IS NULL OR winner_side IN ('a','b')",
            name="ck_pvpve_collision_winner",
        ),
        CheckConstraint(
            "jsonb_typeof(combat_snapshot) = 'object'",
            name="ck_pvpve_collision_snapshot",
        ),
        UniqueConstraint("queue_a_id", name="uq_pvpve_collision_queue_a"),
        UniqueConstraint("queue_b_id", name="uq_pvpve_collision_queue_b"),
        UniqueConstraint("combat_id", name="uq_pvpve_collision_combat"),
        Index("ix_pvpve_collision_local_created", "local_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    local_id: Mapped[str] = mapped_column(String(64), nullable=False)
    roster_size: Mapped[int] = mapped_column(Integer, nullable=False)
    queue_a_id: Mapped[UUID] = mapped_column(
        ForeignKey("pvpve_queues.id", ondelete="RESTRICT"), nullable=False
    )
    queue_b_id: Mapped[UUID] = mapped_column(
        ForeignKey("pvpve_queues.id", ondelete="RESTRICT"), nullable=False
    )
    combat_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    combat_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    winner_side: Mapped[str | None] = mapped_column(String(1))
    prey_reference_level: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PvpveCollisionMember(Base):
    __tablename__ = "pvpve_collision_members"
    __table_args__ = (
        PrimaryKeyConstraint("collision_id", "character_id"),
        UniqueConstraint("game_activity_id", name="uq_pvpve_collision_member_activity"),
        UniqueConstraint("collision_id", "actor_key", name="uq_pvpve_collision_member_actor"),
        CheckConstraint("side IN ('a','b')", name="ck_pvpve_collision_member_side"),
        CheckConstraint(
            "status IN ('active','prey','defeated','settled')",
            name="ck_pvpve_collision_member_status",
        ),
        CheckConstraint(
            "prey_result IS NULL OR prey_result IN ('victory','defeat')",
            name="ck_pvpve_collision_member_prey_result",
        ),
        Index("ix_pvpve_collision_member_account", "account_id", "collision_id"),
    )

    collision_id: Mapped[UUID] = mapped_column(
        ForeignKey("pvpve_collisions.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), nullable=False
    )
    game_activity_id: Mapped[UUID] = mapped_column(
        ForeignKey("game_activities.id", ondelete="CASCADE"), nullable=False
    )
    actor_key: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(1), nullable=False)
    contributed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    domain_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    round_takeover: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    result_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    prey_result: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PvpveAccountPair(Base):
    __tablename__ = "pvpve_account_pairs"
    __table_args__ = (
        CheckConstraint("account_a < account_b", name="ck_pvpve_account_pair_order"),
    )

    account_a: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    account_b: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    last_match_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    domain_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PvpveAccountCooldown(Base):
    __tablename__ = "pvpve_account_cooldowns"

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    pvp_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PvpveDomainGrant(Base):
    __tablename__ = "pvpve_domain_grants"
    __table_args__ = (
        PrimaryKeyConstraint("collision_id", "character_id"),
        CheckConstraint("crowns >= 0", name="ck_pvpve_domain_crowns"),
        CheckConstraint(
            "status IN ('granted','locked','no_economic_reward','no_opponent')",
            name="ck_pvpve_domain_status",
        ),
    )

    collision_id: Mapped[UUID] = mapped_column(
        ForeignKey("pvpve_collisions.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    crowns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    material_id: Mapped[str | None] = mapped_column(String(96))
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="granted", server_default="granted"
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class HuntRound(Base):
    """Authoritative Ronda de Caça batch state."""

    __tablename__ = "hunt_rounds"
    __table_args__ = (
        CheckConstraint("batch_size IN (5, 10, 20)", name="ck_hunt_round_batch"),
        CheckConstraint("completed_encounters >= 0", name="ck_hunt_round_completed"),
        CheckConstraint("state_version >= 0", name="ck_hunt_round_version"),
        CheckConstraint(
            "status IN ('preparing','active','completed','cancelled',"
            "'defeated','ended','interrupted')",
            name="ck_hunt_round_status",
        ),
        Index(
            "uq_open_hunt_round",
            "character_id",
            unique=True,
            postgresql_where=text("status IN ('preparing','active','interrupted')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    activity_id: Mapped[UUID | None] = mapped_column(ForeignKey("game_activities.id"), unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="preparing")
    end_reason: Mapped[str | None] = mapped_column(String(32))
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_encounters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    seed: Mapped[str] = mapped_column(String(128), nullable=False)
    prepared_heal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    prepared_purify: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    next_resolution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    elite_engaged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class HuntRoundEncounter(Base):
    """One persisted materialized encounter within a Ronda batch."""

    __tablename__ = "hunt_round_encounters"
    __table_args__ = (
        UniqueConstraint("round_id", "ordinal", name="uq_hunt_round_ordinal"),
        CheckConstraint("ordinal >= 1", name="ck_hunt_round_encounter_ordinal"),
        CheckConstraint("enemy_level >= 1", name="ck_hunt_round_enemy_level"),
        CheckConstraint(
            "status IN ('materialized','completed','defeated','interrupted','elite_combat')",
            name="ck_hunt_round_encounter_status",
        ),
        CheckConstraint("state_version >= 0", name="ck_hunt_round_encounter_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    round_id: Mapped[UUID] = mapped_column(ForeignKey("hunt_rounds.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_id: Mapped[UUID | None] = mapped_column(ForeignKey("game_activities.id"), unique=True)
    combat_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True)
    seed: Mapped[str] = mapped_column(String(160), nullable=False)
    creature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    enemy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    variant: Mapped[str | None] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="materialized")
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    combat_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExplorationAttempt(Base):
    __tablename__ = "exploration_attempts"
    __table_args__ = (
        UniqueConstraint("character_id", "id", name="uq_exploration_character"),
        CheckConstraint("state_version >= 0", name="ck_exploration_version"),
        CheckConstraint("status IN ('active','completed','failed')", name="ck_exploration_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    local_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    seed: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    result_id: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    state_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    progress: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    activity_id: Mapped[UUID | None] = mapped_column(ForeignKey("game_activities.id"))
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class BestiaryEntry(Base):
    __tablename__ = "bestiary_entries"
    __table_args__ = (
        UniqueConstraint("character_id", "creature_id", name="uq_character_bestiary"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    creature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    bkp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="observed", server_default="observed"
    )
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class BestiaryEvidence(Base):
    __tablename__ = "bestiary_evidence"
    __table_args__ = (
        UniqueConstraint("character_id", "creature_id", "evidence_id", name="uq_bestiary_evidence"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    creature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String(96), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)


class CodexFragment(Base):
    __tablename__ = "codex_fragments"
    __table_args__ = (
        UniqueConstraint("character_id", "fragment_id", name="uq_character_fragment"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    entry_id: Mapped[str] = mapped_column(String(96), nullable=False)
    fragment_id: Mapped[str] = mapped_column(String(96), nullable=False)


class EquipmentItem(Base):
    __tablename__ = "equipment_items"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rarity: Mapped[str] = mapped_column(String(16), nullable=False)
    slot: Mapped[str] = mapped_column(String(24), nullable=False)
    item_level: Mapped[int] = mapped_column(Integer, nullable=False)
    bound: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class WarehouseEquipmentItem(Base):
    """Exact equipment instance while unavailable from Inventory and combat builds."""

    __tablename__ = "warehouse_equipment_items"
    __table_args__ = (
        UniqueConstraint("character_id", "source_key", name="uq_warehouse_equipment_source"),
        Index("ix_warehouse_equipment_character", "character_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rarity: Mapped[str] = mapped_column(String(16), nullable=False)
    slot: Mapped[str] = mapped_column(String(24), nullable=False)
    item_level: Mapped[int] = mapped_column(Integer, nullable=False)
    bound: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CharacterEquipmentSlot(Base):
    __tablename__ = "character_equipment_slots"
    __table_args__ = (
        PrimaryKeyConstraint("character_id", "slot", name="pk_character_equipment_slots"),
        UniqueConstraint("equipment_item_id", name="uq_equipment_slot_item"),
        CheckConstraint(
            "slot IN (" + ", ".join(f"'{slot}'" for slot in EQUIPMENT_SLOT_VALUES) + ")",
            name="ck_character_equipment_slots_slot",
        ),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    slot: Mapped[str] = mapped_column(String(24), nullable=False)
    equipment_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("equipment_items.id", ondelete="RESTRICT"), nullable=False
    )


class CharacterActiveArtSlot(Base):
    __tablename__ = "character_active_art_slots"
    __table_args__ = (
        PrimaryKeyConstraint("character_id", "slot", name="pk_character_active_art_slots"),
        UniqueConstraint("character_id", "art_id", name="uq_character_active_art"),
        CheckConstraint("slot BETWEEN 1 AND 3", name="ck_character_active_art_slot"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    art_id: Mapped[str] = mapped_column(String(96), nullable=False)


class CharacterTalentChoice(Base):
    __tablename__ = "character_talent_choices"
    __table_args__ = (
        PrimaryKeyConstraint("character_id", "point_slot", name="pk_character_talent_choices"),
        UniqueConstraint("character_id", "talent_id", name="uq_character_talent_choice"),
        CheckConstraint("point_slot BETWEEN 1 AND 12", name="ck_character_talent_point_slot"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    point_slot: Mapped[int] = mapped_column(Integer, nullable=False)
    talent_id: Mapped[str] = mapped_column(String(96), nullable=False)
    publicly_acquired: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


class CharacterProfession(Base):
    """The two active profession slots; abandoned progress is deliberately deleted."""

    __tablename__ = "character_professions"
    __table_args__ = (
        PrimaryKeyConstraint("character_id", "slot", name="pk_character_professions"),
        UniqueConstraint("character_id", "profession_id", name="uq_character_profession"),
        CheckConstraint("slot IN ('primary','secondary')", name="ck_character_profession_slot"),
        CheckConstraint(
            "profession_id IN ('blacksmith','artificer','alchemist','leatherworker','jeweler')",
            name="ck_character_profession_id",
        ),
        CheckConstraint("level BETWEEN 1 AND 30", name="ck_character_profession_level"),
        CheckConstraint(
            "slot != 'secondary' OR level <= 15",
            name="ck_character_profession_secondary_cap",
        ),
        CheckConstraint("pxp >= 0", name="ck_character_profession_pxp"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    slot: Mapped[str] = mapped_column(String(12), nullable=False)
    profession_id: Mapped[str] = mapped_column(String(24), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    pxp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")


class CraftingReceipt(Base):
    """Durable preview/commit receipt that prevents craft output rerolls and dupes."""

    __tablename__ = "crafting_receipts"
    __table_args__ = (
        UniqueConstraint("character_id", "source_key", name="uq_character_craft_source"),
        Index("ix_crafting_receipts_character_status", "character_id", "status"),
        CheckConstraint(
            "status IN ('preview','committed','cancelled','expired')",
            name="ck_crafting_receipt_status",
        ),
        CheckConstraint(
            "output_payload IS NULL OR jsonb_typeof(output_payload) = 'object'",
            name="ck_crafting_receipt_payload",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[str] = mapped_column(String(96), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="preview", server_default="preview"
    )
    preview_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    seed: Mapped[str] = mapped_column(String(128), nullable=False)
    output_kind: Mapped[str | None] = mapped_column(String(24))
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuneStack(Base):
    __tablename__ = "rune_stacks"
    __table_args__ = (
        UniqueConstraint(
            "character_id", "family", "rarity", "grade", "bound", name="uq_character_rune"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    family: Mapped[str] = mapped_column(String(32), nullable=False)
    rarity: Mapped[str] = mapped_column(String(16), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    potency: Mapped[str] = mapped_column(String(24), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    bound: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class ConsumableStack(Base):
    __tablename__ = "consumable_stacks"
    __table_args__ = (
        UniqueConstraint("character_id", "consumable_id", name="uq_character_consumable"),
        CheckConstraint("quantity BETWEEN 0 AND 99", name="ck_consumable_quantity"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    consumable_id: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class WarehouseRuneStack(Base):
    """A Rune stack kept in the character's canonical 100-slot Warehouse."""

    __tablename__ = "warehouse_rune_stacks"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_warehouse_rune_quantity"),
        Index("ix_warehouse_rune_character", "character_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    family: Mapped[str] = mapped_column(String(32), nullable=False)
    rarity: Mapped[str] = mapped_column(String(16), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    potency: Mapped[str] = mapped_column(String(24), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    bound: Mapped[bool] = mapped_column(Boolean, nullable=False)


class WarehouseConsumableStack(Base):
    """A Consumable stack kept in the character's canonical 100-slot Warehouse."""

    __tablename__ = "warehouse_consumable_stacks"
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 99", name="ck_warehouse_consumable_quantity"),
        Index("ix_warehouse_consumable_character", "character_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    consumable_id: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class PendingItem(Base):
    __tablename__ = "pending_items"
    __table_args__ = (
        UniqueConstraint("character_id", "source_key", name="uq_character_pending_source"),
        CheckConstraint("quantity > 0", name="ck_pending_quantity"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class WarehouseOperation(Base):
    """Durable preview/commit token for idempotent Inventory/Warehouse transfers."""

    __tablename__ = "warehouse_operations"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('deposit','withdraw','claim_pending')",
            name="ck_warehouse_operation_direction",
        ),
        CheckConstraint(
            "kind IN ('equipment','material','rune','consumable')",
            name="ck_warehouse_operation_kind",
        ),
        CheckConstraint(
            "status IN ('preview','committed','cancelled','stale','expired')",
            name="ck_warehouse_operation_status",
        ),
        CheckConstraint("quantity > 0", name="ck_warehouse_operation_quantity"),
        Index("ix_warehouse_operation_character_status", "character_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key: Mapped[str | None] = mapped_column(String(160))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="preview", server_default="preview"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BlockedDelivery(Base):
    """Durable delivery hold used when both Inventory and Pending are full."""

    __tablename__ = "blocked_deliveries"
    __table_args__ = (
        CheckConstraint("status IN ('pending','resolved')", name="ck_blocked_delivery_status"),
        CheckConstraint("quantity > 0", name="ck_blocked_delivery_quantity"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Guild(Base):
    """Server-bound Guild (GDD v1.6.0 §30). Never hard-deleted."""

    __tablename__ = "guilds"
    __table_args__ = (
        CheckConstraint("name ~ '^[A-Za-z]{3,16}$'", name="ck_guild_name"),
        CheckConstraint("tag ~ '^[A-Z]{3}$'", name="ck_guild_tag"),
        CheckConstraint("status IN ('active','dissolved')", name="ck_guild_status"),
        CheckConstraint("recruitment IN ('open','closed')", name="ck_guild_recruitment"),
        CheckConstraint("lodging_level BETWEEN 0 AND 5", name="ck_guild_lodging_level"),
        CheckConstraint("revision >= 0", name="ck_guild_revision"),
        CheckConstraint("treasury_crowns >= 0", name="ck_guild_treasury"),
        CheckConstraint(
            "(dissolution_requested_at IS NULL) = (dissolution_due_at IS NULL)",
            name="ck_guild_dissolution_pair",
        ),
        CheckConstraint(
            "(status = 'dissolved') = (dissolved_at IS NOT NULL)", name="ck_guild_dissolved_at"
        ),
        Index(
            "uq_guild_server_name",
            "server_id",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "uq_guild_server_tag",
            "server_id",
            "tag",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_guild_recruiting", "server_id", "status", "recruitment", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(16), nullable=False)
    tag: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    recruitment: Mapped[str] = mapped_column(
        String(8), nullable=False, default="closed", server_default="closed"
    )
    lodging_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    treasury_crowns: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    last_renamed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dissolution_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dissolution_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dissolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuildMember(Base):
    """One Guild per character; the character row already fixes the server."""

    __tablename__ = "guild_members"
    __table_args__ = (
        CheckConstraint("role IN ('leader','officer','member')", name="ck_guild_member_role"),
        Index(
            "uq_guild_single_leader",
            "guild_id",
            unique=True,
            postgresql_where=text("role = 'leader'"),
        ),
        Index("ix_guild_members_guild", "guild_id", "joined_at", "character_id"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(8), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    role_since: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Last authenticated activity, used by the 168h Leader succession (§30.3).
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GuildInvite(Base):
    """Direct invite; valid until answered, cancelled or made unusable (§55.5)."""

    __tablename__ = "guild_invites"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','declined','cancelled','invalidated')",
            name="ck_guild_invite_status",
        ),
        CheckConstraint("revision >= 0", name="ck_guild_invite_revision"),
        Index(
            "uq_pending_guild_invite",
            "guild_id",
            "invitee_character_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_guild_invites_inbox", "invitee_character_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    inviter_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    invitee_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuildApplication(Base):
    """Guild application (Inscrição, §30.1). Resolved rows stay as audit history."""

    __tablename__ = "guild_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected','cancelled')",
            name="ck_guild_application_status",
        ),
        CheckConstraint(
            "(status = 'cancelled') = (closed_by IS NOT NULL)",
            name="ck_guild_application_cancel_origin",
        ),
        CheckConstraint(
            "closed_by IS NULL OR closed_by IN ('player','system')",
            name="ck_guild_application_closed_by",
        ),
        CheckConstraint("revision >= 0", name="ck_guild_application_revision"),
        Index(
            "uq_pending_guild_application",
            "guild_id",
            "character_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_guild_applications_character", "character_id", "created_at"),
        Index("ix_guild_applications_guild", "guild_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    closed_by: Mapped[str | None] = mapped_column(String(8))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )


class GuildSwitchCooldown(Base):
    """Last Guild exit per account + server, so recreating a character never resets it."""

    __tablename__ = "guild_switch_cooldowns"

    telegram_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id"), primary_key=True, autoincrement=False
    )
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_exit_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GuildAuditEntry(Base):
    """Append-only log of relevant Guild administration (§30)."""

    __tablename__ = "guild_audit_log"
    __table_args__ = (
        CheckConstraint("action <> ''", name="ck_guild_audit_action"),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="ck_guild_audit_details"),
        Index("ix_guild_audit_guild", "guild_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    target_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GuildProject(Base):
    """One level of one Obra: Financiamento -> Construção -> concluída (§30.2)."""

    __tablename__ = "guild_projects"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('lodging','forge','veil_altar','treasury','veil_archive',"
            "'hunters_post','war_hall')",
            name="ck_guild_project_kind",
        ),
        CheckConstraint("level BETWEEN 1 AND 5", name="ck_guild_project_level"),
        CheckConstraint(
            "status IN ('funding','building','completed','cancelled')",
            name="ck_guild_project_status",
        ),
        CheckConstraint("cost > 0 AND funded BETWEEN 0 AND cost", name="ck_guild_project_funds"),
        CheckConstraint(
            "status NOT IN ('building','completed') OR funded = cost",
            name="ck_guild_project_funded_before_build",
        ),
        CheckConstraint(
            "(status = 'building') <= (completes_at IS NOT NULL)",
            name="ck_guild_project_build_end",
        ),
        CheckConstraint("revision >= 0", name="ck_guild_project_revision"),
        Index(
            "uq_guild_project_level",
            "guild_id",
            "kind",
            "level",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
        Index(
            "uq_guild_project_active_kind",
            "guild_id",
            "kind",
            unique=True,
            postgresql_where=text("status IN ('funding','building')"),
        ),
        Index("ix_guild_projects_due", "status", "completes_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    cost: Mapped[int] = mapped_column(BigInteger, nullable=False)
    funded: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    funded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuildProjectContribution(Base):
    """Final, non-refundable contribution to an Obra, from a wallet or the Treasury."""

    __tablename__ = "guild_project_contributions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_guild_contribution_amount"),
        CheckConstraint("source IN ('wallet','treasury')", name="ck_guild_contribution_source"),
        Index("ix_guild_contributions_project", "project_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("guild_projects.id"), nullable=False)
    character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    source: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GuildTreasuryEntry(Base):
    """Treasury ledger. `amount` is signed and `balance_after` never goes negative."""

    __tablename__ = "guild_treasury_ledger"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('deposit','project_funding','rename','forfeit','oath','expedition')",
            name="ck_guild_treasury_kind",
        ),
        CheckConstraint("amount <> 0", name="ck_guild_treasury_amount"),
        CheckConstraint("balance_after >= 0", name="ck_guild_treasury_balance"),
        Index("ix_guild_treasury_guild", "guild_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("guild_projects.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GuildNameHistory(Base):
    """Rename history; the old Name/TAG stays reserved until `reserved_until`."""

    __tablename__ = "guild_name_history"
    __table_args__ = (
        Index("ix_guild_name_history_name", "server_id", text("lower(old_name)")),
        Index("ix_guild_name_history_tag", "server_id", "old_tag"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    old_name: Mapped[str] = mapped_column(String(16), nullable=False)
    old_tag: Mapped[str] = mapped_column(String(3), nullable=False)
    new_name: Mapped[str] = mapped_column(String(16), nullable=False)
    new_tag: Mapped[str] = mapped_column(String(3), nullable=False)
    actor_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    renamed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reserved_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccountLink(Base):
    """Admin-declared association between two Telegram accounts (GDD §36).

    Association alone is never proof of guilt: it only makes co-occurrence of
    the two accounts in the same activity produce a flag for human review.
    """

    __tablename__ = "account_links"
    __table_args__ = (CheckConstraint("account_a < account_b", name="ck_account_link_order"),)

    account_a: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    account_b: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AccountRiskFlag(Base):
    """One review item: two linked accounts were seen in the same activity (GDD §36)."""

    __tablename__ = "account_risk_flags"
    __table_args__ = (
        CheckConstraint("account_a < account_b", name="ck_account_risk_flag_order"),
        CheckConstraint(
            "status IN ('open','reviewed','dismissed')", name="ck_account_risk_flag_status"
        ),
        UniqueConstraint(
            "activity_kind",
            "activity_reference",
            "account_a",
            "account_b",
            name="uq_account_risk_flag_activity_pair",
        ),
        Index("ix_account_risk_flags_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    account_a: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), nullable=False
    )
    account_b: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_reference: Mapped[str] = mapped_column(String(96), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open")
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlayerShop(Base):
    """§28.2 Personal Shop. The row outlives its owner so a Code is never reused."""

    __tablename__ = "player_shops"
    __table_args__ = (UniqueConstraint("code", name="uq_player_shop_code"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL"), unique=True
    )
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    public_name: Mapped[str | None] = mapped_column(String(36))
    description: Mapped[str | None] = mapped_column(String(240))
    last_promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketListing(Base):
    """§28.10 offer. While active, its item exists only in `item_snapshot` (escrow)."""

    __tablename__ = "market_listings"
    __table_args__ = (
        CheckConstraint("unit_price > 0", name="ck_market_listing_price"),
        CheckConstraint(
            "remaining_quantity >= 0 AND remaining_quantity <= initial_quantity",
            name="ck_market_listing_quantity",
        ),
        CheckConstraint(
            "status IN ('active','sold_out','removed','expired','closed')",
            name="ck_market_listing_status",
        ),
        CheckConstraint(
            "item_kind IN ('equipment','material','consumable','rune')",
            name="ck_market_listing_kind",
        ),
        CheckConstraint("fee_bps BETWEEN 0 AND 500", name="ck_market_listing_fee_bps"),
        Index("ix_market_listing_shop_status", "shop_id", "status"),
        Index(
            "ix_market_listing_active_expiry",
            "expires_at",
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(ForeignKey("player_shops.id"), nullable=False)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    item_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    rarity: Mapped[str | None] = mapped_column(String(16))
    item_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    initial_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    terms_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    gross_sold_total: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    fee_charged_total: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    # Fee in basis points, fixed at creation (Tesouraria Obra, domain/guild_works.py).
    fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, server_default="500")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MarketPriceChange(Base):
    """§28.15 internal price history."""

    __tablename__ = "market_price_changes"
    __table_args__ = (Index("ix_market_price_change_listing", "listing_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("market_listings.id"), nullable=False)
    owner_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    old_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    new_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    terms_version: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketPurchase(Base):
    """§28.11 confirmation reference; once committed it is the sale record."""

    __tablename__ = "market_purchases"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_market_purchase_quantity"),
        CheckConstraint("status IN ('preview','committed')", name="ck_market_purchase_status"),
        Index("ix_market_purchase_listing", "listing_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("market_listings.id"), nullable=False)
    buyer_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    seller_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    terms_version: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    gross: Mapped[int | None] = mapped_column(BigInteger)
    fee: Mapped[int | None] = mapped_column(BigInteger)
    net: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="preview")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ShopSearchAttempt(Base):
    """§49.18 Buscar Loja rate limit; survives a bot restart."""

    __tablename__ = "shop_search_attempts"
    __table_args__ = (Index("ix_shop_search_character_time", "character_id", "attempted_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TradeSession(Base):
    """§29 Direct Trade between two characters of one server."""

    __tablename__ = "trade_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('invited','open','committed','cancelled','expired','declined')",
            name="ck_trade_session_status",
        ),
        Index(
            "ix_trade_session_live",
            "status",
            "last_activity_at",
            postgresql_where=text("status IN ('invited','open')"),
        ),
        Index("ix_trade_session_initiator", "initiator_character_id"),
        Index("ix_trade_session_partner", "partner_character_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    initiator_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    partner_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    initiator_steps: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    partner_steps: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(String(32))


class TradeItem(Base):
    """An offered item in Direct Trade escrow; kept afterwards as the §29 log."""

    __tablename__ = "trade_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_trade_item_quantity"),
        CheckConstraint(
            "status IN ('escrow','delivered','returned','withdrawn','discarded')",
            name="ck_trade_item_status",
        ),
        CheckConstraint(
            "item_kind IN ('equipment','material','consumable','rune')",
            name="ck_trade_item_kind",
        ),
        Index("ix_trade_item_trade", "trade_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    trade_id: Mapped[UUID] = mapped_column(ForeignKey("trade_sessions.id"), nullable=False)
    owner_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    item_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    rarity: Mapped[str | None] = mapped_column(String(16))
    item_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="escrow")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArenaProfile(Base):
    """Career of one character in the Arena; Legado never resets it."""

    __tablename__ = "arena_profiles"
    __table_args__ = (
        CheckConstraint("renome >= 0", name="ck_arena_profile_renome"),
        CheckConstraint(
            "placement_played BETWEEN 0 AND 5 AND placement_wins BETWEEN 0 AND placement_played",
            name="ck_arena_profile_placement",
        ),
        Index("ix_arena_profiles_ranking", "server_id", "renome"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    renome: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mmr: Mapped[int] = mapped_column(Integer, nullable=False, default=1500)
    placement_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    placement_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queue_blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_match_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_decay_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Arena matches of the current competitive cycle (Crônica); reset at finalization.
    cycle_matches: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class ArenaQueueEntry(Base):
    """One entry in the competitive queue; it owns the Combat Configuration lock."""

    __tablename__ = "arena_queue_entries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('waiting','matched','left','released')",
            name="ck_arena_queue_status",
        ),
        Index(
            "uq_arena_queue_open_character",
            "character_id",
            unique=True,
            postgresql_where=text("status IN ('waiting','matched')"),
        ),
        Index("ix_arena_queue_waiting", "server_id", "status", "entered_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    game_activity_id: Mapped[UUID] = mapped_column(ForeignKey("game_activities.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    mmr: Mapped[int] = mapped_column(Integer, nullable=False)
    configuration_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="waiting")
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PvpMatch(Base):
    """One Duelo or Arena match, from invite or pairing until the settlement."""

    __tablename__ = "pvp_matches"
    __table_args__ = (
        CheckConstraint("kind IN ('duel','arena')", name="ck_pvp_match_kind"),
        CheckConstraint(
            "status IN ('invited','confirming','active','finished','cancelled')",
            name="ck_pvp_match_status",
        ),
        CheckConstraint(
            "winner_side IS NULL OR winner_side IN ('a','b')", name="ck_pvp_match_winner"
        ),
        Index("ix_pvp_matches_due", "server_id", "status", "deadline_at"),
        Index("ix_pvp_matches_finished", "server_id", "kind", "finished_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    # Invite, Entry Confirmation or current turn, according to the status.
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    combat_id: Mapped[UUID | None] = mapped_column(Uuid)
    ruleset_version: Mapped[str | None] = mapped_column(String(48))
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    combat_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    winner_side: Mapped[str | None] = mapped_column(String(1))
    end_reason: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PvpMatchMember(Base):
    __tablename__ = "pvp_match_members"
    __table_args__ = (
        CheckConstraint("side IN ('a','b')", name="ck_pvp_member_side"),
        UniqueConstraint("match_id", "side", name="uq_pvp_member_side"),
        Index("ix_pvp_member_character", "character_id"),
    )

    match_id: Mapped[UUID] = mapped_column(
        ForeignKey("pvp_matches.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    side: Mapped[str] = mapped_column(String(1), nullable=False)
    actor_key: Mapped[str] = mapped_column(String(8), nullable=False)
    is_challenger: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    game_activity_id: Mapped[UUID | None] = mapped_column(ForeignKey("game_activities.id"))
    queue_entry_id: Mapped[UUID | None] = mapped_column(ForeignKey("arena_queue_entries.id"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_timeouts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_timeouts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    renome_before: Mapped[int | None] = mapped_column(Integer)
    renome_after: Mapped[int | None] = mapped_column(Integer)
    placed_before: Mapped[bool | None] = mapped_column(Boolean)
    placed_after: Mapped[bool | None] = mapped_column(Boolean)
    placement_played_after: Mapped[int | None] = mapped_column(Integer)


class ArenaDodge(Base):
    """Refused or expired Entry Confirmation, read in a rolling 60 minutes."""

    __tablename__ = "arena_dodges"
    __table_args__ = (Index("ix_arena_dodges_character_at", "character_id", "occurred_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[UUID] = mapped_column(
        ForeignKey("pvp_matches.id", ondelete="CASCADE"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FriendRequest(Base):
    """§31 pending friend request. A resolved request simply stops existing."""

    __tablename__ = "friend_requests"
    __table_args__ = (
        UniqueConstraint(
            "sender_character_id", "recipient_character_id", name="uq_friend_request_pair"
        ),
        CheckConstraint(
            "sender_character_id <> recipient_character_id", name="ck_friend_request_not_self"
        ),
        Index("ix_friend_requests_recipient", "recipient_character_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sender_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    recipient_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Friendship(Base):
    """§31 mutual friendship, stored once with character_a < character_b."""

    __tablename__ = "friendships"
    __table_args__ = (
        CheckConstraint("character_a < character_b", name="ck_friendship_order"),
        Index("ix_friendships_character_b", "character_b"),
    )

    character_a: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    character_b: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterBlock(Base):
    """§31 one-directional block; it restricts both sides of direct interactions."""

    __tablename__ = "character_blocks"
    __table_args__ = (
        CheckConstraint(
            "blocker_character_id <> blocked_character_id", name="ck_character_block_not_self"
        ),
        Index("ix_character_blocks_blocked", "blocked_character_id"),
    )

    blocker_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecentContact(Base):
    """§31 Recentes: someone this character shared a Grupo, Masmorra, PvP or Troca with."""

    __tablename__ = "recent_contacts"
    __table_args__ = (
        CheckConstraint(
            "character_id <> other_character_id", name="ck_recent_contact_not_self"
        ),
        Index("ix_recent_contacts_character_seen", "character_id", "last_seen_at"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    other_character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlayerSearchAttempt(Base):
    """§49.18 Busca de jogador rate limit; survives a bot restart."""

    __tablename__ = "player_search_attempts"
    __table_args__ = (Index("ix_player_search_character_time", "character_id", "attempted_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Relato(Base):
    """§31.1 snapshot of a História published to the official Relatos topic."""

    __tablename__ = "relatos"
    __table_args__ = (
        CheckConstraint("status IN ('published','removed')", name="ck_relato_status"),
        Index("ix_relatos_character_created", "character_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    author_name: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContentReport(Base):
    """§31.1 report of a História or Relato, resolved by an operator."""

    __tablename__ = "content_reports"
    __table_args__ = (
        CheckConstraint("kind IN ('history','relato')", name="ck_content_report_kind"),
        CheckConstraint(
            "status IN ('open','upheld','dismissed')", name="ck_content_report_status"
        ),
        Index(
            "uq_content_report_open",
            "reporter_character_id",
            "target_key",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index("ix_content_reports_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    target_key: Mapped[str] = mapped_column(String(48), nullable=False)
    reporter_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    target_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    relato_id: Mapped[UUID | None] = mapped_column(ForeignKey("relatos.id", ondelete="SET NULL"))
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)


class DailyGiftClaim(Base):
    """§32.1 one claim per account, server and daily cycle (the primary key)."""

    __tablename__ = "daily_gift_claims"
    __table_args__ = (
        CheckConstraint("claim_day BETWEEN 1 AND 7", name="ck_daily_gift_claim_day"),
    )

    telegram_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    cycle_date: Mapped[date] = mapped_column(Date, primary_key=True)
    claim_day: Mapped[int] = mapped_column(Integer, nullable=False)
    character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecruitmentCode(Base):
    """§32.2 the personal Chamado code of one account on one server."""

    __tablename__ = "recruitment_codes"
    __table_args__ = (UniqueConstraint("server_id", "code", name="uq_recruitment_code"),)

    telegram_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecruitmentInvite(Base):
    """A Chamado deep link opened before the newcomer has a character."""

    __tablename__ = "recruitment_invites"

    telegram_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecruitmentLink(Base):
    """§32.2 one recruit per account and server; it survives character deletion."""

    __tablename__ = "recruitment_links"
    __table_args__ = (
        CheckConstraint(
            "recruit_telegram_id <> recruiter_telegram_id", name="ck_recruitment_not_self"
        ),
        CheckConstraint("peak_level BETWEEN 1 AND 60", name="ck_recruitment_peak_level"),
        Index("ix_recruitment_links_recruiter", "server_id", "recruiter_telegram_id", "linked_at"),
    )

    recruit_telegram_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    recruiter_telegram_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), nullable=False
    )
    peak_level: Mapped[int] = mapped_column(Integer, nullable=False)
    # §49.19: only the first 10 valid recruits pay the recruiter in Coroas.
    pays_recruiter: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecruitmentClaim(Base):
    """§49.19 a milestone payment already taken by one side of a recruitment."""

    __tablename__ = "recruitment_claims"
    __table_args__ = (
        CheckConstraint("milestone IN (10,30,60)", name="ck_recruitment_claim_milestone"),
        CheckConstraint("side IN ('recruit','recruiter')", name="ck_recruitment_claim_side"),
    )

    recruit_telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    milestone: Mapped[int] = mapped_column(Integer, primary_key=True)
    side: Mapped[str] = mapped_column(String(16), primary_key=True)
    character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    crowns: Mapped[int] = mapped_column(Integer, nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PromoCode(Base):
    """§32.4 Código de Asterion, created by an operator."""

    __tablename__ = "promo_codes"
    __table_args__ = (
        UniqueConstraint("server_id", "code", name="uq_promo_code"),
        CheckConstraint("scope IN ('account','character')", name="ck_promo_code_scope"),
        CheckConstraint("uses_per_account >= 1", name="ck_promo_code_uses_per_account"),
        CheckConstraint(
            "global_limit IS NULL OR global_limit >= 1", name="ck_promo_code_global_limit"
        ),
        CheckConstraint("redeemed_count >= 0", name="ck_promo_code_redeemed"),
        CheckConstraint("expires_at > starts_at", name="ck_promo_code_window"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(24), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    global_limit: Mapped[int | None] = mapped_column(Integer)
    uses_per_account: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    # A list of {"weight", "c_multiplier", "basics", "fragments"}; one entry is a fixed prize.
    reward_table: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    redeemed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PromoRedemption(Base):
    """§32.4 one redemption; the prize drawn is stored once and never redrawn."""

    __tablename__ = "promo_redemptions"
    __table_args__ = (
        Index("ix_promo_redemptions_code_account", "code_id", "telegram_id"),
        Index("ix_promo_redemptions_code_character", "code_id", "character_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code_id: Mapped[UUID] = mapped_column(
        ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False
    )
    telegram_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    entry_index: Mapped[int] = mapped_column(Integer, nullable=False)
    crowns: Mapped[int] = mapped_column(Integer, nullable=False)
    basics: Mapped[int] = mapped_column(Integer, nullable=False)
    fragments: Mapped[int] = mapped_column(Integer, nullable=False)
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PromoAttempt(Base):
    """§49.19 attempt rate limit per account; survives a bot restart."""

    __tablename__ = "promo_attempts"
    __table_args__ = (Index("ix_promo_attempts_account_time", "telegram_id", "attempted_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.telegram_id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorldEventOccurrence(Base):
    """One scheduled opening of a World Event (GDD §21); unique per opening."""

    __tablename__ = "world_event_occurrences"
    __table_args__ = (
        CheckConstraint(
            "status IN ('gathering','active','completed','failed')",
            name="ck_world_event_occurrence_status",
        ),
        UniqueConstraint("server_id", "occurrence_key", name="uq_world_event_occurrence"),
        Index("ix_world_event_occurrence_status", "server_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    occurrence_key: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    phase: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    phase_one_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    phase_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    participants_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    boss_hp: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    boss_max_hp: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ruleset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorldEventParticipation(Base):
    """Contribution per occurrence and character (§21); re-entering never duplicates it."""

    __tablename__ = "world_event_participations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','withdrawn','settled')",
            name="ck_world_event_participation_status",
        ),
        Index(
            "uq_world_event_active_participation",
            "character_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    occurrence_id: Mapped[UUID] = mapped_column(
        ForeignKey("world_event_occurrences.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    combat_configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    hp: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    reentry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_activities.id", ondelete="SET NULL")
    )
    combat_phase: Mapped[int | None] = mapped_column(Integer)
    vigor_reserved: Mapped[int] = mapped_column(Integer, nullable=False)
    vigor_refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consumable_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    significant_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    major_contributions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    phases: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    damage_dealt: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eligible: Mapped[bool | None] = mapped_column(Boolean)
    reward: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OathCycle(Base):
    """One weekly Juramento window (GDD §22.1); unique per opening."""

    __tablename__ = "oath_cycles"
    __table_args__ = (
        CheckConstraint("status IN ('open','finalizing','closed')", name="ck_oath_cycle_status"),
        UniqueConstraint("server_id", "cycle_key", name="uq_oath_cycle"),
        Index("ix_oath_cycle_status", "server_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    cycle_key: Mapped[str] = mapped_column(String(16), nullable=False)
    trial_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    grace_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ruleset_version: Mapped[str] = mapped_column(String(64), nullable=False)


class OathGuildProgress(Base):
    """Collective contribution of one Guild in one cycle (§22.1)."""

    __tablename__ = "oath_guild_progress"
    __table_args__ = (
        CheckConstraint("contribution >= 0", name="ck_oath_guild_contribution"),
        CheckConstraint("tier IS NULL OR tier BETWEEN 0 AND 4", name="ck_oath_guild_tier"),
        Index("ix_oath_guild_progress_guild", "guild_id", "finalized_at"),
    )

    cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("oath_cycles.id", ondelete="CASCADE"), primary_key=True
    )
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), primary_key=True)
    contribution: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tier: Mapped[int | None] = mapped_column(Integer)
    treasury_crowns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OathMember(Base):
    """A character's binding to ``guild_id + cycle_id`` (§22.1): one Guild per cycle."""

    __tablename__ = "oath_members"
    __table_args__ = (
        CheckConstraint("provacoes_used BETWEEN 0 AND 3", name="ck_oath_member_provacoes"),
        CheckConstraint("contribution BETWEEN 0 AND 180", name="ck_oath_member_contribution"),
        Index("ix_oath_members_guild", "cycle_id", "guild_id"),
    )

    cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("oath_cycles.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    reference_level: Mapped[int] = mapped_column(Integer, nullable=False)
    provacoes_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contribution: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eligible: Mapped[bool | None] = mapped_column(Boolean)
    reward: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OathAttempt(Base):
    """One Provação: the shared combat of its roster (§22.1)."""

    __tablename__ = "oath_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','completed','failed','abandoned','expired')",
            name="ck_oath_attempt_status",
        ),
        CheckConstraint("stage BETWEEN 1 AND 3", name="ck_oath_attempt_stage"),
        CheckConstraint("roster_size BETWEEN 1 AND 4", name="ck_oath_attempt_roster"),
        Index("ix_oath_attempts_status", "cycle_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("oath_cycles.id", ondelete="CASCADE"), nullable=False
    )
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    trial_id: Mapped[str] = mapped_column(String(64), nullable=False)
    proposal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("group_activity_proposals.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    stage: Mapped[int] = mapped_column(Integer, nullable=False)
    roster_size: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_level: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    combat_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    combat_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ruleset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_action_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OathAttemptMember(Base):
    """A participant of one Provação, with its own HP: never writes ``Character.hp``."""

    __tablename__ = "oath_attempt_members"
    __table_args__ = (
        Index("ix_oath_attempt_members_activity", "game_activity_id"),
    )

    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("oath_attempts.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    game_activity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_activities.id", ondelete="SET NULL")
    )
    actor_key: Mapped[str] = mapped_column(String(16), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    hp: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    combat_configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    consumable_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acted_stages: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    contribution: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class OathMilestone(Base):
    """Authoritative, idempotent record of a milestone won in a Provação (§22.1)."""

    __tablename__ = "oath_milestones"

    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("oath_attempts.id", ondelete="CASCADE"), primary_key=True
    )
    milestone: Mapped[str] = mapped_column(String(16), primary_key=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Expedition(Base):
    """One weekly Expedição of a Guild (GDD §22.2); a Background Commitment."""

    __tablename__ = "expeditions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('forming','active','completed','cancelled')",
            name="ck_expedition_status",
        ),
        CheckConstraint("resolved_stages BETWEEN 0 AND 3", name="ck_expedition_stages"),
        CheckConstraint("score IS NULL OR score BETWEEN 0 AND 300", name="ck_expedition_score"),
        UniqueConstraint("guild_id", "week_key", name="uq_expedition_guild_week"),
        Index("ix_expedition_status", "server_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    week_key: Mapped[str] = mapped_column(String(16), nullable=False)
    route_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_stages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[str | None] = mapped_column(String(16))
    treasury_crowns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ruleset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExpeditionMember(Base):
    """Roster row, frozen when the Expedição starts (§22.2)."""

    __tablename__ = "expedition_members"

    expedition_id: Mapped[UUID] = mapped_column(
        ForeignKey("expeditions.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_level: Mapped[int | None] = mapped_column(Integer)
    active_stages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible: Mapped[bool | None] = mapped_column(Boolean)
    reward: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExpeditionChoice(Base):
    """One choice per member and stage (§49.15), active or the explicit default."""

    __tablename__ = "expedition_choices"
    __table_args__ = (
        CheckConstraint("stage BETWEEN 1 AND 3", name="ck_expedition_choice_stage"),
    )

    expedition_id: Mapped[UUID] = mapped_column(
        ForeignKey("expeditions.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    stage: Mapped[int] = mapped_column(Integer, primary_key=True)
    option_id: Mapped[str | None] = mapped_column(String(64))
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False)
    chosen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GuildBattleProfile(Base):
    """Technical Guild rating and standings (§15, §49.14); persists between Crônicas."""

    __tablename__ = "guild_battle_profiles"
    __table_args__ = (
        CheckConstraint(
            "real_battles >= 0 AND wins >= 0 AND draws >= 0 AND losses >= 0 AND byes >= 0"
            " AND points >= 0",
            name="ck_guild_battle_profile_counts",
        ),
        Index("ix_guild_battle_profiles_server", "server_id", "points", "rating"),
    )

    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), primary_key=True)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=1500)
    # Standings below belong to the current Crônica and reset at its finalization;
    # the rating and ``career_real_battles`` (its K factor) persist (§49.14).
    career_real_battles: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    real_battles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    byes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_battle_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuildBattleRegistration(Base):
    """One Guild entered in one Batalha de Guildas, from Inscrição to the result."""

    __tablename__ = "guild_battle_registrations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('registered','paired','bye','finished','cancelled')",
            name="ck_guild_battle_registration_status",
        ),
        UniqueConstraint("guild_id", "starts_at", name="uq_guild_battle_registration_slot"),
        Index("ix_guild_battle_registrations_due", "server_id", "status", "starts_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    guild_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    registered_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GuildBattleRosterEntry(Base):
    """A registered combatant or reserve; confirmation takes the configuration lock."""

    __tablename__ = "guild_battle_roster"
    __table_args__ = (
        CheckConstraint(
            "slot IN ('front_1','front_2','reserve')", name="ck_guild_battle_roster_slot"
        ),
        CheckConstraint(
            "status IN ('registered','confirmed','replaced')",
            name="ck_guild_battle_roster_status",
        ),
        CheckConstraint(
            "NOT is_champion OR slot <> 'reserve'", name="ck_guild_battle_roster_champion"
        ),
        Index("ix_guild_battle_roster_character", "character_id"),
    )

    registration_id: Mapped[UUID] = mapped_column(
        ForeignKey("guild_battle_registrations.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    slot: Mapped[str] = mapped_column(String(8), nullable=False)
    is_champion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    game_activity_id: Mapped[UUID | None] = mapped_column(ForeignKey("game_activities.id"))


class GuildBattle(Base):
    """Two paired Guilds: Frente I, Frente II and, on a tie, the Champion."""

    __tablename__ = "guild_battles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('confirming','fronts','champion','finished')",
            name="ck_guild_battle_status",
        ),
        CheckConstraint(
            "winner_side IS NULL OR winner_side IN ('a','b')", name="ck_guild_battle_winner"
        ),
        UniqueConstraint("registration_a_id", name="uq_guild_battle_registration_a"),
        UniqueConstraint("registration_b_id", name="uq_guild_battle_registration_b"),
        Index("ix_guild_battles_due", "server_id", "status", "starts_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_a_id: Mapped[UUID] = mapped_column(
        ForeignKey("guild_battle_registrations.id"), nullable=False
    )
    registration_b_id: Mapped[UUID] = mapped_column(
        ForeignKey("guild_battle_registrations.id"), nullable=False
    )
    guild_a_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    guild_b_id: Mapped[UUID] = mapped_column(ForeignKey("guilds.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    points_a: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False, default=0)
    points_b: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False, default=0)
    winner_side: Mapped[str | None] = mapped_column(String(1))
    rating_a_before: Mapped[int | None] = mapped_column(Integer)
    rating_a_after: Mapped[int | None] = mapped_column(Integer)
    rating_b_before: Mapped[int | None] = mapped_column(Integer)
    rating_b_after: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuildBattleFight(Base):
    """One combat of a Batalha de Guildas: a Front or the Champion duel."""

    __tablename__ = "guild_battle_fights"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('front_1','front_2','champion')", name="ck_guild_battle_fight_kind"
        ),
        CheckConstraint("status IN ('active','finished')", name="ck_guild_battle_fight_status"),
        CheckConstraint(
            "winner_side IS NULL OR winner_side IN ('a','b')",
            name="ck_guild_battle_fight_winner",
        ),
        UniqueConstraint("battle_id", "kind", name="uq_guild_battle_fight_kind"),
        Index("ix_guild_battle_fights_due", "status", "deadline_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    battle_id: Mapped[UUID] = mapped_column(
        ForeignKey("guild_battles.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    absent_a: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    absent_b: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    winner_side: Mapped[str | None] = mapped_column(String(1))
    end_reason: Mapped[str | None] = mapped_column(String(16))
    combat_id: Mapped[UUID | None] = mapped_column(Uuid)
    ruleset_version: Mapped[str | None] = mapped_column(String(48))
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    combat_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuildBattleFightMember(Base):
    __tablename__ = "guild_battle_fight_members"
    __table_args__ = (
        CheckConstraint("side IN ('a','b')", name="ck_guild_battle_fight_member_side"),
        UniqueConstraint("fight_id", "actor_key", name="uq_guild_battle_fight_member_key"),
        Index("ix_guild_battle_fight_member_character", "character_id"),
    )

    fight_id: Mapped[UUID] = mapped_column(
        ForeignKey("guild_battle_fights.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    side: Mapped[str] = mapped_column(String(1), nullable=False)
    actor_key: Mapped[str] = mapped_column(String(8), nullable=False)
    game_activity_id: Mapped[UUID | None] = mapped_column(ForeignKey("game_activities.id"))
    consecutive_timeouts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_timeouts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ------------------------------------------------------------------ Crônica (§5, §49.16)


class ChronicleCycle(Base):
    """One Crônica on one server. Day 1 is set by the operator; T derives from it."""

    __tablename__ = "chronicle_cycles"
    __table_args__ = (
        CheckConstraint(
            "outcome IS NULL OR outcome IN "
            "('selar','estabilizar','herdeiros','destruir','em_espera')",
            name="ck_chronicle_cycle_outcome",
        ),
        CheckConstraint("revision >= 0", name="ck_chronicle_cycle_revision"),
    )

    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chronicle_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    day1: Mapped[date] = mapped_column(Date, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vote_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    runoff_options: Mapped[list[str] | None] = mapped_column(JSONB)
    runoff_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(16))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    liquidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChronicleCycleLog(Base):
    """Every Day 1 change and every exceptional extension of T (§5.3)."""

    __tablename__ = "chronicle_cycle_logs"
    __table_args__ = (
        CheckConstraint("action IN ('set_day1','extend')", name="ck_chronicle_log_action"),
        Index("ix_chronicle_cycle_logs_cycle", "server_id", "chronicle_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chronicle_id: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChronicleAccount(Base):
    """Trilha progress per ``conta + servidor + Crônica`` (§5.4); also the account lock."""

    __tablename__ = "chronicle_accounts"
    __table_args__ = (
        CheckConstraint(
            "points >= 0 AND repeatable_points >= 0 AND repeatable_points <= points",
            name="ck_chronicle_account_points",
        ),
    )

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chronicle_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repeatable_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    premium_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    premium_source: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChronicleCompletion(Base):
    """A completed objective or chapter conclusion of one character (narrative state)."""

    __tablename__ = "chronicle_completions"
    __table_args__ = (
        Index("ix_chronicle_completions_account", "account_id", "server_id", "chronicle_id"),
    )

    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )
    chronicle_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    objective_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChroniclePointGrant(Base):
    """One idempotent Trilha grant; ``source_key`` is unique per account (§5.4)."""

    __tablename__ = "chronicle_point_grants"
    __table_args__ = (
        CheckConstraint("points > 0", name="ck_chronicle_grant_points"),
        Index(
            "ix_chronicle_grants_daily",
            "account_id",
            "server_id",
            "chronicle_id",
            "source_id",
            "cycle_date",
        ),
    )

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chronicle_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    source_key: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(48), nullable=False)
    repeatable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    cycle_date: Mapped[date] = mapped_column(Date, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChronicleClaim(Base):
    """One delivered Marco reward; claim and liquidation never duplicate it."""

    __tablename__ = "chronicle_claims"
    __table_args__ = (
        CheckConstraint("track IN ('free','premium')", name="ck_chronicle_claim_track"),
        CheckConstraint("milestone BETWEEN 1 AND 40", name="ck_chronicle_claim_milestone"),
        CheckConstraint("via IN ('claim','liquidation')", name="ck_chronicle_claim_via"),
    )

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chronicle_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    track: Mapped[str] = mapped_column(String(8), primary_key=True)
    milestone: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    via: Mapped[str] = mapped_column(String(16), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChronicleVote(Base):
    """The single active vote of an account in one round (§5.1)."""

    __tablename__ = "chronicle_votes"
    __table_args__ = (
        CheckConstraint("round IN ('main','runoff')", name="ck_chronicle_vote_round"),
        CheckConstraint(
            "option IN ('selar','estabilizar','herdeiros','destruir')",
            name="ck_chronicle_vote_option",
        ),
    )

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chronicle_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    round: Mapped[str] = mapped_column(String(8), primary_key=True)
    option: Mapped[str] = mapped_column(String(16), nullable=False)
    character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChronicleElector(Base):
    """Electorate frozen when the main vote closes; the runoff uses only it."""

    __tablename__ = "chronicle_electorate"

    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chronicle_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VigilHallEntry(Base):
    """Salão da Vigília: what the Classificação showed when a Crônica was finalized."""

    __tablename__ = "vigil_hall_entries"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('arena','guild_battle','guild_battle_member')",
            name="ck_vigil_hall_kind",
        ),
        UniqueConstraint(
            "server_id", "chronicle_id", "kind", "subject_id", name="uq_vigil_hall_subject"
        ),
        Index("ix_vigil_hall_position", "server_id", "chronicle_id", "kind", "position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chronicle_id: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    account_id: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    elo: Mapped[str | None] = mapped_column(String(24))
    matches: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reward_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reward_tier: Mapped[str | None] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
