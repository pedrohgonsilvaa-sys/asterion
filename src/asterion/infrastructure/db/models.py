from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

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
        CheckConstraint("level BETWEEN 1 AND 60 AND xp >= 0", name="ck_character_progress"),
        CheckConstraint("hp >= 0 AND hp <= max_hp AND max_hp > 0", name="ck_character_hp"),
        CheckConstraint(
            "vigor BETWEEN 0 AND max_vigor AND max_vigor = 100", name="ck_character_vigor"
        ),
        CheckConstraint("crowns >= 0", name="ck_character_crowns"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(ForeignKey("accounts.telegram_id"), nullable=False)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(16), nullable=False)
    race: Mapped[str] = mapped_column(String(24), nullable=False)
    character_class: Mapped[str] = mapped_column(String(24), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(48), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    xp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    hp: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    max_hp: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    vigor: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    max_vigor: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
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


class MaterialStack(Base):
    __tablename__ = "material_stacks"
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 0 AND 999", name="ck_material_quantity"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    material_id: Mapped[str] = mapped_column(String(96), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    bound: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


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
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
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
    creature_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    enemy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    variant: Mapped[str | None] = mapped_column(String(24))
    seed: Mapped[str] = mapped_column(String(128), nullable=False)
    local_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Estrada das Cinzas",
        server_default=text("'Estrada das Cinzas'"),
    )
    loot_profile: Mapped[str] = mapped_column(String(32), nullable=False, default="hunt")
    result_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
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
    local_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Estrada das Cinzas",
        server_default=text("'Estrada das Cinzas'"),
    )
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
