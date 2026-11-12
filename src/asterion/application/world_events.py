"""Eventos Mundiais (GDD v1.6.0 §21, §21.1, §49.15).

Lock order (every write follows it, which rules out deadlocks):
Character -> WorldEventOccurrence -> WorldEventParticipation -> ConsumableStack.
A path may skip a level but never go back up. The occurrence row serialises the
shared Chefe: HP is only read and written under it, so the Chefe dies once.

Paying 200 participants inside one click would break that order, so a finished
occurrence is settled apart, one Character per transaction, by the maintenance job.

Each participant fights an own instance of the phase; the instance always starts
its turn from the shared HP. A participation has its own HP, like the Arena: it
never writes ``Character.hp``. Only the combat itself is Foreground; the Combat
Configuration lock lasts the whole participation (``combat_configuration_guard``).

Linked accounts are only flagged (§36); nothing here blocks them.

During Crônica I every slot runs O Compasso, one occurrence per Region version
(``domain/chronicle_events.py``). A character joins at most one version per slot, of a
Region where Desbravar is already released; when several occurrences share the slot
their locks are taken in id order.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.active_arts import load_active_art_configuration
from asterion.application.campaign_coop import campaign_action_intent
from asterion.application.chronicle import calendar_of, load_cycle
from asterion.application.chronicle_activities import (
    LatestLocal,
    record_world_event,
    region_accessible,
)
from asterion.application.combat_configuration_guard import find_combat_configuration_blocker
from asterion.application.engagement import grant_bundle
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.progression import consolidate_character_level, level_xp
from asterion.application.prologue import CombatView
from asterion.application.vigor import add_vigor_state, reconcile_character_vigor
from asterion.domain.chronicle_events import ALL_DEFINITIONS as CHRONICLE_DEFINITIONS
from asterion.domain.chronicle_events import (
    configure_compasso,
    definitions_for_slot,
    next_chronicle_slot,
)
from asterion.domain.chronicle_events import enemy_specs as chronicle_enemy_specs
from asterion.domain.combat import (
    Combat,
    act,
    active_player_key,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import ConsumableFamily, consumable_limit
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.equipment_stats import equipment_configuration_from_data
from asterion.domain.road import RULESET as COMBAT_RULESET
from asterion.domain.road import CreatureCombatantSpec, create_creature_party_combat
from asterion.domain.world_events import (
    DEADLINE,
    ENTRY_WINDOW,
    GATHERING_WINDOW,
    PHASE_COUNT,
    REENTRY_DELAY,
    RULESET,
    VIGOR_COST,
    WORLD_EVENT_CATALOG,
    WorldEventDefinition,
    attuned_equipment,
    attuned_level,
    boss_engine_multipliers,
    boss_stats,
    definition_for_slot,
    is_eligible,
    latest_slot,
    next_slot,
    occurrence_key,
    reward_bundle,
    reward_xp,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    AccountLink,
    Character,
    ConsumableStack,
    GameActivity,
    WorldEventOccurrence,
    WorldEventParticipation,
)

WORLD_EVENT_ACTIVITY_PREFIX = "world_event:"
_OPEN_STATUSES = ("gathering", "active")
_FINAL_STATUSES = ("completed", "failed")
_ACTOR_KEY = "player"
_ENEMY_KEY = "enemy"
_WORLD_EVENT_CONTEXT = "world_event"


class WorldEventError(ValueError):
    """An Event action is invalid for the current, revalidated state."""

    def __init__(self, code: str, seconds: int = 0):
        self.code = code
        self.seconds = seconds
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class WorldEventStatus:
    occurrence_id: UUID
    name: str
    region: str
    flavor: str
    status: str
    phase: int
    boss_name: str | None
    boss_hp: Decimal
    boss_max_hp: Decimal
    participants: int
    seconds_to_start: int
    can_enter: bool
    joined: bool
    withdrawn: bool
    in_combat: bool
    reentry_seconds: int
    significant_actions: int
    phases_done: int
    eligible: bool
    consumables_left: int


@dataclass(frozen=True, slots=True)
class WorldEventVersion:
    """One version of a multi-version slot the character may join (Crônica)."""

    occurrence_id: UUID
    name: str
    region: str
    level: int
    participants: int


@dataclass(frozen=True, slots=True)
class WorldEventHubView:
    status: WorldEventStatus | None
    next_opening: datetime | None
    has_last_result: bool = False
    notice: str | None = None
    versions: tuple[WorldEventVersion, ...] = ()  # choose one; ``status`` is None then
    seconds_to_start: int = 0


@dataclass(frozen=True, slots=True)
class WorldEventRewardItem:
    name: str
    quantity: int


@dataclass(frozen=True, slots=True)
class WorldEventResultView:
    name: str
    region: str
    flavor: str
    completed: bool
    eligible: bool
    crowns: int = 0
    xp: int = 0
    items: tuple[WorldEventRewardItem, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldEventNotice:
    telegram_id: int
    view: WorldEventResultView


WorldEventView = WorldEventHubView | WorldEventResultView | CombatView


def _utcnow(now: datetime | None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return current.astimezone(UTC)


def _seconds_left(deadline: datetime | None, now: datetime) -> int:
    if deadline is None:
        return 0
    return max(0, int((deadline - now).total_seconds()))


class WorldEventService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        catalog: tuple[WorldEventDefinition, ...] = WORLD_EVENT_CATALOG,
        latest_local: LatestLocal | None = None,
    ):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id
        self.catalog = catalog
        # Without it no Crônica version can be joined (maintenance needs none).
        self.latest_local = latest_local
        self._by_id = {
            definition.event_id: definition for definition in (*catalog, *CHRONICLE_DEFINITIONS)
        }

    # ---------------------------------------------------------------- reading

    async def hub(
        self, actor: int, *, now: datetime | None = None, notice: str | None = None
    ) -> WorldEventHubView:
        now = _utcnow(now)
        await self._ensure_occurrence(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            occurrences = await self._slot_occurrences(session, lock=True)
            for occurrence in occurrences:
                await self._tick(session, occurrence, now)
            occurrence = await self._chosen(session, character, occurrences)
            if occurrence is None and len(occurrences) > 1:
                return await self._versions_view(session, character, occurrences, now, notice)
            return await self._hub_view(session, character, occurrence, now, notice)

    async def foreground(self, actor: int, *, now: datetime | None = None) -> CombatView | None:
        """The Event combat to resume on /start; ``None`` lets other routers answer."""
        now = _utcnow(now)
        async with self.sessions() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if character is None:
                return None
            participation = await session.scalar(
                select(WorldEventParticipation).where(
                    WorldEventParticipation.character_id == character.id,
                    WorldEventParticipation.status == "active",
                    WorldEventParticipation.activity_id.is_not(None),
                )
            )
            if participation is None:
                return None
            occurrence = await session.get(WorldEventOccurrence, participation.occurrence_id)
            activity = await session.get(GameActivity, participation.activity_id)
            if (
                occurrence is None
                or activity is None
                or activity.status != "active"
                or now >= occurrence.deadline_at
            ):
                return None
            combat, record = await self._load_combat(session, activity)
            return await self._combat_view(
                session, character, occurrence, participation, activity, record, combat
            )

    async def last_result(self, actor: int) -> WorldEventResultView | WorldEventHubView:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            row = await session.execute(
                select(WorldEventParticipation, WorldEventOccurrence)
                .join(
                    WorldEventOccurrence,
                    WorldEventOccurrence.id == WorldEventParticipation.occurrence_id,
                )
                .where(
                    WorldEventParticipation.character_id == character.id,
                    WorldEventParticipation.settled_at.is_not(None),
                )
                .order_by(WorldEventParticipation.settled_at.desc())
                .limit(1)
            )
            found = row.first()
            if found is None:
                return WorldEventHubView(None, await self._next_opening(session, datetime.now(UTC)))
            return self._result_view(found[1], found[0])

    # ---------------------------------------------------------------- actions

    async def enter(
        self, actor: int, occurrence_id: UUID, *, now: datetime | None = None
    ) -> WorldEventView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            occurrence = await self._lock_occurrence(session, occurrence_id)
            await self._tick(session, occurrence, now)
            existing = await self._participation(session, occurrence.id, character.id, lock=True)
            if existing is not None:
                if existing.status == "withdrawn":
                    raise WorldEventError("withdrawn")
                return await self._hub_view(session, character, occurrence, now, None)
            if not self._entry_open(occurrence, now):
                raise WorldEventError("entry_closed")
            definition = self._definition(occurrence)
            if definition is not None and definition.family:
                await self._check_version(session, character, occurrence, definition)
            if await find_combat_configuration_blocker(session, character.id) is not None:
                raise WorldEventError("busy")
            if character.hp <= 0:
                raise WorldEventError("no_hp")
            await reconcile_character_vigor(session, character, now=now)
            if character.vigor < VIGOR_COST:
                raise WorldEventError("vigor")
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            character.vigor -= VIGOR_COST
            session.add(
                WorldEventParticipation(
                    occurrence_id=occurrence.id,
                    character_id=character.id,
                    status="active",
                    combat_configuration=equipment.to_data(COMBAT_RULESET) | arts.to_data(),
                    hp=character.hp,
                    vigor_reserved=VIGOR_COST,
                    vigor_refunded=False,
                    consumable_uses=0,
                    significant_actions=0,
                    major_contributions=0,
                    phases=[],
                    damage_dealt=Decimal(0),
                    joined_at=now,
                )
            )
            await session.flush()
            return await self._hub_view(session, character, occurrence, now, None)

    async def fight(
        self, actor: int, occurrence_id: UUID, *, now: datetime | None = None
    ) -> WorldEventView:
        """Open or resume the combat of the current phase."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            occurrence = await self._lock_occurrence(session, occurrence_id)
            await self._tick(session, occurrence, now)
            participation = await self._participation(
                session, occurrence.id, character.id, lock=True
            )
            if participation is None or participation.status != "active":
                raise WorldEventError("not_joined")
            if occurrence.status == "gathering":
                raise WorldEventError("gathering", _seconds_left(occurrence.phase_one_at, now))
            if occurrence.status != "active":
                return await self._hub_view(session, character, occurrence, now, None)
            if participation.activity_id is not None:
                activity = await session.get(GameActivity, participation.activity_id)
                if activity is not None and activity.status == "active":
                    combat, record = await self._load_combat(session, activity)
                    return await self._combat_view(
                        session, character, occurrence, participation, activity, record, combat
                    )
            if participation.reentry_at is not None and now < participation.reentry_at:
                raise WorldEventError("reentry_wait", _seconds_left(participation.reentry_at, now))
            busy = await session.scalar(
                select(GameActivity.id)
                .where(GameActivity.character_id == character.id, GameActivity.status == "active")
                .with_for_update()
            )
            if busy is not None:
                raise WorldEventError("busy")
            definition = self._definition(occurrence)
            if definition is None:
                raise WorldEventError("not_found")
            # One content id per phase: it tells a first instance of the phase from a reentry.
            content_id = f"{WORLD_EVENT_ACTIVITY_PREFIX}{occurrence.id.hex}:{occurrence.phase}"
            first_instance = (
                await session.scalar(
                    select(GameActivity.id)
                    .where(
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == content_id,
                    )
                    .limit(1)
                )
                is None
            )
            combat = self._new_combat(
                character, definition, occurrence, participation, first_instance=first_instance
            )
            activity, _, record = await CombatRepository(session).create(
                character, content_id, combat
            )
            participation.activity_id = activity.id
            participation.combat_phase = occurrence.phase
            participation.reentry_at = None
            participation.hp = combat.fighters[_ACTOR_KEY].hp
            return await self._combat_view(
                session, character, occurrence, participation, activity, record, combat
            )

    async def action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
        *,
        now: datetime | None = None,
    ) -> WorldEventView:
        return await self._apply(
            actor, activity_id, version, now=now, action=(action_index, target_code)
        )

    async def consume_for_activity(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        item_id: str,
        target_id: str,
        effect_id: str | None,
        now: datetime | None = None,
    ) -> WorldEventView | None:
        if not await self._owns_activity(actor, activity_id):
            return None
        return await self._apply(
            actor, activity_id, version, now=now, consumable=(item_id, target_id, effect_id)
        )

    async def consumable_selection(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        screen: str = "items",
        item_id: str | None = None,
        target_id: str | None = None,
        parent: str = "items",
    ) -> CombatView | None:
        if not await self._owns_activity(actor, activity_id):
            return None
        current = await self.foreground(actor)
        if current is None or current.activity_id != activity_id:
            return None
        if current.combat.version != version:
            return replace(current, consumable_notice="⚠️ Consumível · A tela ficou desatualizada.")
        if screen == "combat":
            return current
        if screen == "items":
            return (
                replace(current, consumable_screen="items")
                if current.consumable_options
                else current
            )
        item = consumable_definition(item_id or "")
        options = tuple(
            option for option in current.consumable_options if option.item_id == item_id
        )
        if item is None or not options:
            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Não está disponível.",
            )
        if screen in {"choose_item", "choose_target"}:
            chosen = (
                target_id if item.family == ConsumableFamily.DISPELLER and target_id else _ACTOR_KEY
            )
            selected = tuple(option for option in options if option.target_id == chosen)
            if len(selected) == 1:
                return replace(current, ready_consumable_option=selected[0])
            if selected:
                return replace(
                    current,
                    consumable_screen="effects",
                    selected_consumable_id=item.id,
                    selected_target_id=chosen,
                    selection_parent="items",
                )
        return replace(
            current,
            consumable_screen="items",
            consumable_notice="⚠️ Consumível · Não está disponível.",
        )

    async def withdraw(
        self, actor: int, occurrence_id: UUID, *, now: datetime | None = None
    ) -> WorldEventHubView:
        """§21: ends the participation for good, releasing the Configuration lock."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            occurrence = await self._lock_occurrence(session, occurrence_id)
            await self._tick(session, occurrence, now)
            participation = await self._participation(
                session, occurrence.id, character.id, lock=True
            )
            if participation is None or participation.status != "active":
                raise WorldEventError("not_joined")
            if participation.activity_id is not None:
                activity = await session.get(GameActivity, participation.activity_id)
                if activity is not None and activity.status == "active":
                    activity.status = "completed"
                participation.activity_id = None
                participation.combat_phase = None
            participation.status = "withdrawn"
            return await self._hub_view(session, character, occurrence, now, None)

    async def _apply(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        now: datetime | None,
        action: tuple[int, str] | None = None,
        consumable: tuple[str, str, str | None] | None = None,
    ) -> WorldEventView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            occurrence_id = await session.scalar(
                select(WorldEventParticipation.occurrence_id).where(
                    WorldEventParticipation.character_id == character.id,
                    WorldEventParticipation.activity_id == activity_id,
                )
            )
            if occurrence_id is None:
                return await self._stale_hub(session, character, now)
            occurrence = await self._lock_occurrence(session, occurrence_id)
            await self._tick(session, occurrence, now)
            participation = await self._participation(
                session, occurrence.id, character.id, lock=True
            )
            # The tick above may have ended the phase and released this instance.
            if (
                participation is None
                or participation.status != "active"
                or participation.activity_id != activity_id
                or occurrence.status != "active"
                or participation.combat_phase != occurrence.phase
            ):
                return await self._hub_view(
                    session, character, occurrence, now, "A fase mudou. Entre de novo."
                )
            activity = await session.get(GameActivity, activity_id)
            if activity is None or activity.status != "active":
                return await self._hub_view(session, character, occurrence, now, None)
            combat, record = await self._load_combat(session, activity)
            # §21: the instance always plays from the shared HP.
            shared_before = Decimal(occurrence.boss_hp)
            combat.fighters[_ENEMY_KEY].hp = shared_before
            current = self._combat_view(
                session, character, occurrence, participation, activity, record, combat
            )
            if version != activity.state_version or active_player_key(combat) != _ACTOR_KEY:
                return await current
            stack = None
            if consumable is not None:
                item_id, target_id, effect_id = consumable
                remaining = consumable_limit("world_event") - participation.consumable_uses
                if remaining <= 0:
                    return await current
                stack = await session.scalar(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == character.id,
                        ConsumableStack.consumable_id == item_id,
                        ConsumableStack.quantity > 0,
                    )
                    .with_for_update()
                )
                if stack is None:
                    return await current
                updated = use_combat_consumable(
                    combat,
                    item_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=remaining,
                    actor_key=_ACTOR_KEY,
                )
            else:
                action_index, target_code = action
                intent = campaign_action_intent(combat, _ACTOR_KEY, action_index, target_code)
                if intent is None:
                    return await current
                chosen, target = intent
                updated = act(combat, chosen, target_id=target, actor_key=_ACTOR_KEY)
            if updated.version == combat.version:
                return await current
            if stack is not None:
                stack.quantity -= 1
                participation.consumable_uses += 1
            return await self._after_action(
                session,
                character,
                occurrence,
                participation,
                activity,
                record,
                combat,
                updated,
                shared_before,
                now,
            )

    async def _after_action(
        self,
        session,
        character,
        occurrence,
        participation,
        activity,
        record,
        before: Combat,
        updated: Combat,
        shared_before: Decimal,
        now: datetime,
    ) -> WorldEventView:
        enemy = updated.fighters[_ENEMY_KEY]
        # Never below zero: overkill does not carry over (§21). A Chefe's self-heal
        # stays inside the instance and never restores the shared bar.
        damage = max(Decimal(0), shared_before - Decimal(enemy.hp))
        occurrence.boss_hp = max(Decimal(0), shared_before - damage)
        enemy.hp = occurrence.boss_hp
        participation.damage_dealt = Decimal(participation.damage_dealt) + damage
        player = updated.fighters[_ACTOR_KEY]
        participation.hp = player.hp
        self._count_significant(participation, before, updated, occurrence.phase)
        record.snapshot = encode(updated)
        activity.state_version = updated.version
        activity.last_valid_action_at = now
        if occurrence.boss_hp <= 0:
            participation.major_contributions += 1
            activity.status = "completed"
            return await self._phase_cleared(session, character, occurrence, participation, now)
        if updated.result == "defeat" or player.hp <= 0:
            activity.status = "failed"
            participation.activity_id = None
            participation.combat_phase = None
            participation.hp = Decimal(0)
            participation.reentry_at = now + REENTRY_DELAY
            return await self._hub_view(
                session, character, occurrence, now, "💀 Você caiu. A reentrada abre em 2 minutos."
            )
        return await self._combat_view(
            session, character, occurrence, participation, activity, record, updated
        )

    async def _phase_cleared(
        self, session, character, occurrence, participation, now: datetime
    ) -> WorldEventHubView:
        participation.activity_id = None
        participation.combat_phase = None
        definition = self._definition(occurrence)
        await self._release_instances(session, occurrence)
        if definition is None or occurrence.phase >= PHASE_COUNT:
            occurrence.status = "completed" if definition is not None else "failed"
            occurrence.finished_at = now
            occurrence.state_version += 1
            return await self._hub_view(
                session,
                character,
                occurrence,
                now,
                "🏆 O Chefe caiu. O resultado chega em instantes.",
            )
        await self._start_phase(session, occurrence, definition, occurrence.phase + 1, now)
        return await self._hub_view(session, character, occurrence, now, "Fase concluída.")

    @staticmethod
    def _count_significant(participation, before: Combat, updated: Combat, phase: int) -> None:
        """An Ação Significativa deals damage, heals or grants a Barrier; Defender does not."""
        new_events = updated.events[len(before.events) :]
        useful = any(
            event.actor == _ACTOR_KEY
            and not event.internal
            and (
                max(event.effective_damage, event.damage) > 0
                or event.healed > 0
                or event.barrier_value > 0
            )
            for event in new_events
        )
        if not useful:
            return
        participation.significant_actions += 1
        if phase not in participation.phases:
            participation.phases = [*participation.phases, phase]

    # ------------------------------------------------------------- maintenance

    async def run_maintenance(self, *, now: datetime | None = None) -> list[WorldEventNotice]:
        now = _utcnow(now)
        await self._ensure_occurrence(now)
        async with self.sessions() as session:
            pending = list(
                (
                    await session.scalars(
                        select(WorldEventOccurrence.id).where(
                            WorldEventOccurrence.server_id == self.server_id,
                            WorldEventOccurrence.settled_at.is_(None),
                        )
                    )
                ).all()
            )
        notices: list[WorldEventNotice] = []
        for occurrence_id in pending:
            async with self.sessions.begin() as session:
                occurrence = await self._lock_occurrence(session, occurrence_id)
                await self._tick(session, occurrence, now)
                final = occurrence.status in _FINAL_STATUSES
            if final:
                notices.extend(await self._settle(occurrence_id, now))
        return notices

    async def _settle(self, occurrence_id: UUID, now: datetime) -> list[WorldEventNotice]:
        async with self.sessions() as session:
            character_ids = sorted(
                (
                    await session.scalars(
                        select(WorldEventParticipation.character_id).where(
                            WorldEventParticipation.occurrence_id == occurrence_id,
                            WorldEventParticipation.settled_at.is_(None),
                        )
                    )
                ).all()
            )
        notices = []
        for character_id in character_ids:
            notice = await self._settle_one(occurrence_id, character_id, now)
            if notice is not None:
                notices.append(notice)
        async with self.sessions.begin() as session:
            occurrence = await self._lock_occurrence(session, occurrence_id)
            if occurrence.settled_at is None:
                await self._flag_linked_accounts(session, occurrence, now)
                occurrence.settled_at = now
        return notices

    async def _settle_one(
        self, occurrence_id: UUID, character_id: UUID, now: datetime
    ) -> WorldEventNotice | None:
        """Idempotent per participation, so a restart resumes where it stopped."""
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character).where(Character.id == character_id).with_for_update()
            )
            participation = await self._participation(
                session, occurrence_id, character_id, lock=True
            )
            if character is None or participation is None or participation.settled_at is not None:
                return None
            occurrence = await session.get(WorldEventOccurrence, occurrence_id)
            definition = self._definition(occurrence)
            reward: dict = {}
            eligible = (
                occurrence.status == "completed"
                and definition is not None
                and is_eligible(
                    len(participation.phases),
                    participation.significant_actions,
                    participation.major_contributions,
                )
            )
            if eligible:
                granted = await grant_bundle(
                    session,
                    character,
                    reward_bundle(definition.reference_level),
                    f"world_event:{occurrence.id.hex}:{character.id.hex}",
                    region=definition.region,
                )
                xp = reward_xp(level_xp(definition.reference_level))
                character.xp += xp
                await consolidate_character_level(session, character)
                if definition.family:
                    # §0.3.8 and §8: the same occurrence counts for objective and Trilha.
                    await record_world_event(
                        session,
                        character,
                        definition.family,
                        occurrence.id.hex,
                        now=now,
                        started_at=occurrence.opened_at,
                    )
                reward = {
                    "crowns": granted.crowns,
                    "xp": xp,
                    "items": [
                        {"name": item.name, "quantity": item.quantity} for item in granted.items
                    ],
                }
            elif not participation.vigor_refunded and participation.vigor_reserved > 0:
                await reconcile_character_vigor(session, character, now=now)
                add_vigor_state(character, participation.vigor_reserved, now=now)
                participation.vigor_refunded = True
            participation.reward = reward
            participation.eligible = eligible
            participation.settled_at = now
            if participation.status == "active":
                participation.status = "settled"
            return WorldEventNotice(
                character.telegram_id, self._result_view(occurrence, participation)
            )

    async def _flag_linked_accounts(self, session, occurrence, now: datetime) -> None:
        """§36. Pre-filtered: 200 accounts would exceed the driver's parameter limit."""
        characters = list(
            (
                await session.scalars(
                    select(Character)
                    .join(
                        WorldEventParticipation,
                        WorldEventParticipation.character_id == Character.id,
                    )
                    .where(WorldEventParticipation.occurrence_id == occurrence.id)
                )
            ).all()
        )
        accounts = {character.telegram_id for character in characters}
        if len(accounts) < 2:
            return
        links = await session.execute(
            select(AccountLink.account_a, AccountLink.account_b).where(
                AccountLink.account_a.in_(accounts), AccountLink.account_b.in_(accounts)
            )
        )
        linked = {account for row in links.all() for account in row}
        if not linked:
            return
        await record_linked_cooccurrence(
            session,
            server_id=self.server_id,
            activity_kind="world_event",
            activity_reference=str(occurrence.id),
            characters=[row for row in characters if row.telegram_id in linked],
            now=now,
        )

    # ----------------------------------------------------------------- helpers

    async def _ensure_occurrence(self, now: datetime) -> None:
        """A restart or a second process lands on the same row (§21)."""
        slot = latest_slot(now)
        if slot is None:
            return
        opened_at = slot.astimezone(UTC)
        if now >= opened_at + DEADLINE:
            return
        async with self.sessions.begin() as session:
            cycle = await load_cycle(session, self.server_id)
            # During the Crônica every slot is O Compasso (author decision, 2026-11-11).
            definitions = definitions_for_slot(calendar_of(cycle), slot) if cycle else ()
            if not definitions:
                definition = definition_for_slot(self.catalog, slot)
                definitions = (definition,) if definition is not None else ()
            for definition in definitions:
                await self._insert_occurrence(session, definition, slot, opened_at)

    async def _insert_occurrence(self, session, definition, slot, opened_at) -> None:
        await session.execute(
            insert(WorldEventOccurrence)
            .values(
                id=uuid4(),
                server_id=self.server_id,
                event_id=definition.event_id,
                occurrence_key=occurrence_key(slot, definition.version),
                status="gathering",
                phase=0,
                opened_at=opened_at,
                phase_one_at=opened_at + GATHERING_WINDOW,
                entry_closes_at=opened_at + ENTRY_WINDOW,
                deadline_at=opened_at + DEADLINE,
                participants_snapshot=0,
                boss_hp=Decimal(0),
                boss_max_hp=Decimal(0),
                state_version=0,
                ruleset_version=RULESET,
            )
            .on_conflict_do_nothing(constraint="uq_world_event_occurrence")
        )

    async def _tick(self, session, occurrence, now: datetime) -> None:
        """Time-driven transitions. The caller holds the occurrence lock."""
        if occurrence.status not in _OPEN_STATUSES:
            return
        definition = self._definition(occurrence)
        if definition is None or now >= occurrence.deadline_at:
            await self._release_instances(session, occurrence)
            occurrence.status = "failed"
            occurrence.finished_at = now
            occurrence.state_version += 1
            return
        if occurrence.status == "gathering" and now >= occurrence.phase_one_at:
            await self._start_phase(session, occurrence, definition, 1, now)

    async def _start_phase(self, session, occurrence, definition, number: int, now) -> None:
        """§21: frozen for the phase; a new phase restores nobody's HP."""
        participants = await session.scalar(
            select(func.count())
            .select_from(WorldEventParticipation)
            .where(
                WorldEventParticipation.occurrence_id == occurrence.id,
                WorldEventParticipation.status == "active",
            )
        )
        phase_definition = definition.phase(number)
        stats = boss_stats(
            phase_definition.creature,
            definition.reference_level,
            participants,
            phase_definition.variant,
        )
        occurrence.status = "active"
        occurrence.phase = number
        occurrence.participants_snapshot = participants
        occurrence.boss_hp = stats.hp
        occurrence.boss_max_hp = stats.hp
        occurrence.phase_started_at = now
        occurrence.state_version += 1

    async def _release_instances(self, session, occurrence) -> None:
        """Lock order: the occurrence is already held; instances sync on the next click."""
        activity_ids = select(WorldEventParticipation.activity_id).where(
            WorldEventParticipation.occurrence_id == occurrence.id,
            WorldEventParticipation.activity_id.is_not(None),
        )
        await session.execute(
            update(GameActivity)
            .where(GameActivity.id.in_(activity_ids), GameActivity.status == "active")
            .values(status="completed")
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            update(WorldEventParticipation)
            .where(
                WorldEventParticipation.occurrence_id == occurrence.id,
                WorldEventParticipation.activity_id.is_not(None),
            )
            .values(activity_id=None, combat_phase=None)
            .execution_options(synchronize_session=False)
        )

    def _new_combat(
        self, character, definition, occurrence, participation, *, first_instance: bool = True
    ) -> Combat:
        configuration = participation.combat_configuration
        equipment = equipment_configuration_from_data(configuration)
        level = character.level
        if definition.attuned:
            level = attuned_level(character.level, definition.reference_level)
            equipment = attuned_equipment(equipment, level)
        art_ids = tuple(
            str(entry["art_id"])
            for entry in configuration.get("active_arts", ())
            if isinstance(entry, dict) and entry.get("art_id")
        )
        phase = definition.phase(occurrence.phase)
        boss = CreatureCombatantSpec(
            phase.creature,
            definition.reference_level,
            _ENEMY_KEY,
            stat_multipliers=boss_engine_multipliers(occurrence.participants_snapshot),
        )
        enemies = (boss,)
        configure = None
        if definition.family:
            enemies = chronicle_enemy_specs(definition, occurrence.phase, boss)
            number = occurrence.phase

            def configure(state: Combat) -> None:
                configure_compasso(state, number, resonance=first_instance)

        combat = create_creature_party_combat(
            uuid4(),
            character.name,
            character.character_class,
            character.race,
            Decimal(participation.hp) if participation.hp > 0 else Decimal(character.max_hp),
            enemies,
            player_level=level,
            equipment_configuration=equipment,
            ruleset_version=COMBAT_RULESET,
            flavor=phase.flavor,
            opening_log=phase.flavor,
            active_art_ids=art_ids,
            configure_combat=configure,
        )
        enemy = combat.fighters[_ENEMY_KEY]
        enemy.stats = boss_stats(
            phase.creature,
            definition.reference_level,
            occurrence.participants_snapshot,
            phase.variant,
        )
        enemy.hp = Decimal(occurrence.boss_hp)
        player = combat.fighters[_ACTOR_KEY]
        player.hp = (
            min(Decimal(participation.hp), player.stats.hp)
            if participation.hp > 0
            else player.stats.hp
        )
        return combat

    async def _load_combat(self, session, activity):
        _, record = await CombatRepository(session).combat(activity)
        return (
            decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version),
            record,
        )

    async def _combat_view(
        self, session, character, occurrence, participation, activity, record, combat
    ) -> CombatView:
        # Display only: a resumed instance must show the shared bar (§21).
        combat.fighters[_ENEMY_KEY].hp = Decimal(occurrence.boss_hp)
        definition = self._definition(occurrence)
        name = definition.name if definition is not None else ""
        quantities = tuple(
            (row.consumable_id, row.quantity)
            for row in (
                await session.scalars(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == character.id,
                        ConsumableStack.quantity > 0,
                    )
                    .order_by(ConsumableStack.consumable_id)
                )
            ).all()
        )
        remaining = max(0, consumable_limit("world_event") - participation.consumable_uses)
        return CombatView(
            activity.id,
            record.id,
            character.id,
            combat,
            f"{name} · Fase {occurrence.phase}/{PHASE_COUNT}",
            0,
            context=_WORLD_EVENT_CONTEXT,
            consumable_options=combat_consumable_options(
                combat,
                tuple(item for item, _ in quantities),
                budget_limit=remaining,
                actor_key=_ACTOR_KEY,
            ),
            consumable_quantities=quantities,
            consumable_budget_limit=remaining,
            combat_actor_key=_ACTOR_KEY,
        )

    async def _hub_view(
        self, session, character, occurrence, now: datetime, notice: str | None
    ) -> WorldEventHubView:
        has_last = (
            await session.scalar(
                select(WorldEventParticipation.occurrence_id)
                .where(
                    WorldEventParticipation.character_id == character.id,
                    WorldEventParticipation.settled_at.is_not(None),
                )
                .limit(1)
            )
            is not None
        )
        definition = self._definition(occurrence) if occurrence is not None else None
        if occurrence is None or definition is None or occurrence.status not in _OPEN_STATUSES:
            return WorldEventHubView(None, await self._next_opening(session, now), has_last, notice)
        participation = await self._participation(session, occurrence.id, character.id)
        count = await session.scalar(
            select(func.count())
            .select_from(WorldEventParticipation)
            .where(
                WorldEventParticipation.occurrence_id == occurrence.id,
                WorldEventParticipation.status == "active",
            )
        )
        joined = participation is not None and participation.status == "active"
        withdrawn = participation is not None and participation.status == "withdrawn"
        phase = definition.phase(occurrence.phase) if occurrence.phase else None
        return WorldEventHubView(
            WorldEventStatus(
                occurrence_id=occurrence.id,
                name=definition.name,
                region=definition.region,
                flavor=phase.flavor if phase is not None else "",
                status=occurrence.status,
                phase=occurrence.phase,
                boss_name=phase.creature.name if phase is not None else None,
                boss_hp=Decimal(occurrence.boss_hp),
                boss_max_hp=Decimal(occurrence.boss_max_hp),
                participants=count,
                seconds_to_start=_seconds_left(occurrence.phase_one_at, now),
                can_enter=participation is None and self._entry_open(occurrence, now),
                joined=joined,
                withdrawn=withdrawn,
                in_combat=joined and participation.activity_id is not None,
                reentry_seconds=(_seconds_left(participation.reentry_at, now) if joined else 0),
                significant_actions=(
                    participation.significant_actions if participation is not None else 0
                ),
                phases_done=len(participation.phases) if participation is not None else 0,
                eligible=(
                    participation is not None
                    and is_eligible(
                        len(participation.phases),
                        participation.significant_actions,
                        participation.major_contributions,
                    )
                ),
                consumables_left=(
                    max(0, consumable_limit("world_event") - participation.consumable_uses)
                    if participation is not None
                    else 0
                ),
            ),
            await self._next_opening(session, now),
            has_last,
            notice,
        )

    def _result_view(self, occurrence, participation) -> WorldEventResultView:
        definition = self._definition(occurrence)
        reward = participation.reward or {}
        return WorldEventResultView(
            name=definition.name if definition is not None else occurrence.event_id,
            region=definition.region if definition is not None else "",
            flavor=definition.conclusion_flavor if definition is not None else "",
            completed=occurrence.status == "completed",
            eligible=bool(participation.eligible),
            crowns=int(reward.get("crowns", 0)),
            xp=int(reward.get("xp", 0)),
            items=tuple(
                WorldEventRewardItem(str(item["name"]), int(item["quantity"]))
                for item in reward.get("items", ())
            ),
        )

    def _entry_open(self, occurrence, now: datetime) -> bool:
        """Whichever comes first: the 15-minute window or the final phase."""
        return (
            occurrence.status in _OPEN_STATUSES
            and now < occurrence.entry_closes_at
            and occurrence.phase < PHASE_COUNT
        )

    async def _next_opening(self, session, now: datetime) -> datetime | None:
        if self.catalog:
            return next_slot(now)
        cycle = await load_cycle(session, self.server_id)
        return next_chronicle_slot(calendar_of(cycle), now) if cycle is not None else None

    async def _has_last(self, session, character) -> bool:
        found = await session.scalar(
            select(WorldEventParticipation.occurrence_id)
            .where(
                WorldEventParticipation.character_id == character.id,
                WorldEventParticipation.settled_at.is_not(None),
            )
            .limit(1)
        )
        return found is not None

    async def _versions_view(
        self, session, character, occurrences, now: datetime, notice: str | None
    ) -> WorldEventHubView:
        """A multi-version slot the character has not joined: the versions open to them."""
        versions = []
        for occurrence in occurrences:
            definition = self._definition(occurrence)
            if definition is None or not self._entry_open(occurrence, now):
                continue
            if not await self._version_open(session, character, definition):
                continue
            count = await session.scalar(
                select(func.count())
                .select_from(WorldEventParticipation)
                .where(
                    WorldEventParticipation.occurrence_id == occurrence.id,
                    WorldEventParticipation.status == "active",
                )
            )
            versions.append(
                WorldEventVersion(
                    occurrence.id,
                    definition.name,
                    definition.region,
                    definition.reference_level,
                    count,
                )
            )
        versions.sort(key=lambda item: item.level)
        next_opening = await self._next_opening(session, now)
        has_last = await self._has_last(session, character)
        if not versions:
            if any(row.status in _OPEN_STATUSES for row in occurrences):
                notice = notice or "Nenhuma versão deste Evento está aberta para você agora."
            return WorldEventHubView(None, next_opening, has_last, notice)
        return WorldEventHubView(
            None,
            next_opening,
            has_last,
            notice,
            tuple(versions),
            _seconds_left(occurrences[0].phase_one_at, now),
        )

    async def _version_open(self, session, character, definition) -> bool:
        """§11.5: any version of a Region where Desbravar is already released."""
        if self.latest_local is None:
            return False
        return await region_accessible(session, character, definition.region, self.latest_local)

    async def _check_version(self, session, character, occurrence, definition) -> None:
        """One version per slot, of a Region the character already reached."""
        other = await session.scalar(
            select(WorldEventParticipation.occurrence_id)
            .join(
                WorldEventOccurrence,
                WorldEventOccurrence.id == WorldEventParticipation.occurrence_id,
            )
            .where(
                WorldEventParticipation.character_id == character.id,
                WorldEventOccurrence.server_id == self.server_id,
                WorldEventOccurrence.opened_at == occurrence.opened_at,
                WorldEventOccurrence.id != occurrence.id,
            )
            .limit(1)
        )
        if other is not None:
            raise WorldEventError("other_version")
        if not await self._version_open(session, character, definition):
            raise WorldEventError("region_locked")

    def _definition(self, occurrence) -> WorldEventDefinition | None:
        return self._by_id.get(occurrence.event_id)

    async def _owns_activity(self, actor: int, activity_id: UUID) -> bool:
        async with self.sessions() as session:
            found = await session.scalar(
                select(WorldEventParticipation.occurrence_id)
                .join(Character, Character.id == WorldEventParticipation.character_id)
                .where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                    WorldEventParticipation.activity_id == activity_id,
                )
            )
            return found is not None

    async def _stale_hub(self, session, character, now: datetime) -> WorldEventHubView:
        occurrences = await self._slot_occurrences(session)
        occurrence = await self._chosen(session, character, occurrences)
        if occurrence is None and len(occurrences) > 1:
            return await self._versions_view(session, character, occurrences, now, None)
        return await self._hub_view(session, character, occurrence, now, None)

    async def _slot_occurrences(self, session, *, lock: bool = False) -> list:
        """The occurrences of the latest unfinished slot, in id order (the lock order)."""
        latest = (
            select(func.max(WorldEventOccurrence.opened_at))
            .where(
                WorldEventOccurrence.server_id == self.server_id,
                or_(
                    WorldEventOccurrence.status.in_(_OPEN_STATUSES),
                    WorldEventOccurrence.settled_at.is_(None),
                ),
            )
            .scalar_subquery()
        )
        query = (
            select(WorldEventOccurrence)
            .where(
                WorldEventOccurrence.server_id == self.server_id,
                WorldEventOccurrence.opened_at == latest,
            )
            .order_by(WorldEventOccurrence.id)
        )
        return list((await session.scalars(query.with_for_update() if lock else query)).all())

    async def _chosen(self, session, character, occurrences: list):
        """The occurrence the character joined; the only one of a single-version slot."""
        if not occurrences:
            return None
        joined = await session.scalar(
            select(WorldEventParticipation.occurrence_id).where(
                WorldEventParticipation.character_id == character.id,
                WorldEventParticipation.occurrence_id.in_([row.id for row in occurrences]),
            )
        )
        for occurrence in occurrences:
            if occurrence.id == joined:
                return occurrence
        return occurrences[0] if len(occurrences) == 1 else None

    async def _character(self, session, actor: int) -> Character:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )
        if character is None:
            raise WorldEventError("no_character")
        return character

    async def _lock_character(self, session, actor: int) -> Character:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if character is None:
            raise WorldEventError("no_character")
        return character

    async def _lock_occurrence(self, session, occurrence_id: UUID) -> WorldEventOccurrence:
        occurrence = await session.scalar(
            select(WorldEventOccurrence)
            .where(
                WorldEventOccurrence.id == occurrence_id,
                WorldEventOccurrence.server_id == self.server_id,
            )
            .with_for_update()
        )
        if occurrence is None:
            raise WorldEventError("not_found")
        return occurrence

    async def _participation(
        self, session, occurrence_id: UUID, character_id: UUID, *, lock: bool = False
    ) -> WorldEventParticipation | None:
        query = select(WorldEventParticipation).where(
            WorldEventParticipation.occurrence_id == occurrence_id,
            WorldEventParticipation.character_id == character_id,
        )
        return await session.scalar(query.with_for_update() if lock else query)
