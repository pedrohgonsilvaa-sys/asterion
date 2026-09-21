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
    __table_args__ = (UniqueConstraint("character_id", "quest_id", name="uq_character_quest"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey("characters.id"), nullable=False)
    quest_id: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


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
