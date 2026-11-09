"""Juramento da Guilda (GDD v1.6.0 §22.1, §49.15).

Lock order (every write follows it, which rules out deadlocks):
Character -> OathGuildProgress -> OathMember on the way in;
OathAttempt -> OathAttemptMember -> OathGuildProgress -> OathMember during a combat.
The start never holds an attempt, and a combat never takes a Character lock.

A Provação keeps its own HP per participant, like the Arena: it never writes
``Character.hp``. Each member's ``GameActivity`` stays active across the three
combats, which is what holds the Combat Configuration lock (§22.1).

Paying a whole Guild inside one click would break that order, so a finished cycle
is settled apart, one Character per transaction, by the maintenance job.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.campaign_coop import campaign_action_intent
from asterion.application.combat_configuration_guard import find_combat_configuration_blocker
from asterion.application.engagement import grant_bundle
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.groups import ActivityEligibility
from asterion.application.guild_upkeep import record_treasury
from asterion.application.item_escrow import return_to_owner
from asterion.application.prologue import CombatView
from asterion.domain.combat import (
    Combat,
    act,
    active_player_key,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import ConsumableFamily, consumable_limit
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.engagement import material_name
from asterion.domain.equipment_stats import equipment_configuration_from_data
from asterion.domain.oaths import (
    ATTEMPT_INACTIVITY,
    GRACE,
    OATH_TRIAL_CATALOG,
    PROVACOES_PER_CYCLE,
    RULESET,
    STAGE_COUNT,
    WINDOW,
    OathTrialDefinition,
    cycle_key,
    definition_for_opening,
    encounter_stats,
    enemy_level,
    engine_multipliers,
    is_eligible,
    latest_opening,
    next_opening,
    next_threshold,
    region_for_level,
    reward_bundle,
    reward_catalyst_id,
    reward_catalysts,
    stage_milestones,
    tier_for,
    treasury_reward,
)
from asterion.domain.road import RULESET as COMBAT_RULESET
from asterion.domain.road import (
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    ConsumableStack,
    GameActivity,
    GroupActivityParticipant,
    GroupActivityProposal,
    Guild,
    GuildMember,
    OathAttempt,
    OathAttemptMember,
    OathCycle,
    OathGuildProgress,
    OathMember,
    OathMilestone,
    SocialGroupMember,
)

OATH_ACTIVITY_PREFIX = "oath_trial:"
OATH_ACTIVITY_TYPE = "oath_trial"
_OATH_CONTEXT = "oath_trial"
_ENEMY_KEY = "enemy"
_SOLO_KEY = "player"
ZERO = Decimal(0)


class OathError(ValueError):
    """A Juramento action is invalid for the current, revalidated state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class OathHubView:
    catalog_empty: bool = False
    guild_name: str | None = None
    window: str = "closed"  # closed | open | grace
    deadline: datetime | None = None
    next_opening: datetime | None = None
    trial_name: str | None = None
    provacoes_left: int = 0
    individual: int = 0
    collective: int = 0
    tier: int = 0
    next_threshold: int | None = None
    bound_elsewhere: bool = False
    bound: bool = False
    can_start: bool = False
    has_group: bool = False
    active_attempt_id: UUID | None = None
    can_abandon: bool = False
    has_last_result: bool = False
    notice: str | None = None


@dataclass(frozen=True, slots=True)
class OathRewardItem:
    name: str
    quantity: int


@dataclass(frozen=True, slots=True)
class OathAttemptResultView:
    """End of one Provação (UI §48.6)."""

    outcome: str
    guild_name: str
    flavor: str
    points: int
    cycle_total: int


@dataclass(frozen=True, slots=True)
class OathCycleResultView:
    """End of a cycle (UI §48.6)."""

    guild_name: str
    tier: int
    contribution: int
    participated: bool
    eligible: bool
    treasury: int
    crowns: int = 0
    items: tuple[OathRewardItem, ...] = ()


@dataclass(frozen=True, slots=True)
class OathTurnNotice:
    """Pushed to a roster member whose turn has come."""

    title: str
    started: bool = False


OathView = OathHubView | OathAttemptResultView | OathCycleResultView | CombatView


@dataclass(frozen=True, slots=True)
class OathNotice:
    telegram_id: int
    view: OathAttemptResultView | OathCycleResultView | OathTurnNotice


Notifier = Callable[[Sequence[OathNotice]], Awaitable[None]]


def _utcnow(now: datetime | None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return current.astimezone(UTC)


class OathService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        catalog: tuple[OathTrialDefinition, ...] = OATH_TRIAL_CATALOG,
        notifier: Notifier | None = None,
    ):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id
        self.catalog = catalog
        self.notifier = notifier
        self._by_id = {definition.trial_id: definition for definition in catalog}

    # ---------------------------------------------------------------- reading

    async def hub(
        self, actor: int, *, now: datetime | None = None, notice: str | None = None
    ) -> OathHubView:
        now = _utcnow(now)
        await self._ensure_cycle(now)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return await self._hub_view(session, character, now, notice)

    async def foreground(self, actor: int) -> CombatView | None:
        """The Provação to resume on /start; ``None`` lets other routers answer."""
        async with self.sessions() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if character is None:
                return None
            attempt, member = await self._active_attempt(session, character.id)
            if attempt is None:
                return None
            combat = self._decode(attempt)
            return await self._combat_view(session, character, attempt, member, combat)

    async def last_result(self, actor: int) -> OathCycleResultView | OathHubView:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            found = (
                await session.execute(
                    select(OathMember, OathGuildProgress)
                    .join(
                        OathGuildProgress,
                        (OathGuildProgress.cycle_id == OathMember.cycle_id)
                        & (OathGuildProgress.guild_id == OathMember.guild_id),
                    )
                    .where(
                        OathMember.character_id == character.id,
                        OathMember.settled_at.is_not(None),
                    )
                    .order_by(OathMember.settled_at.desc())
                    .limit(1)
                )
            ).first()
            if found is not None:
                guild = await session.get(Guild, found[0].guild_id)
                return self._cycle_result(found[0], found[1], guild.name)
            # §22.1: without a valid Provação one can only see the collective result.
            membership = await session.get(GuildMember, character.id)
            if membership is not None:
                progress = await session.scalar(
                    select(OathGuildProgress)
                    .where(
                        OathGuildProgress.guild_id == membership.guild_id,
                        OathGuildProgress.finalized_at.is_not(None),
                    )
                    .order_by(OathGuildProgress.finalized_at.desc())
                    .limit(1)
                )
                if progress is not None:
                    guild = await session.get(Guild, membership.guild_id)
                    return OathCycleResultView(
                        guild.name, progress.tier or 0, 0, False, False, progress.treasury_crowns
                    )
            return await self._hub_view(
                session, character, _utcnow(None), "Ainda não há resultado de Juramento."
            )

    # ---------------------------------------------------------------- starting

    async def start_solo(self, actor: int, *, now: datetime | None = None) -> OathView:
        now = _utcnow(now)
        await self._ensure_cycle(now)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            cycle, guild_id = await self._start_context(session, character, now)
            reason = await self._ineligibility(session, character, cycle, guild_id)
            if reason is not None:
                raise OathError(reason)
            attempt = await self._create_attempt(session, cycle, guild_id, [character], None, now)
            member = await session.get(OathAttemptMember, (attempt.id, character.id))
            combat = self._decode(attempt)
            return await self._combat_view(session, character, attempt, member, combat)

    async def group_proposal(self, actor: int) -> dict:
        """Context for the Group's Entry Confirmation (§22.1)."""
        now = _utcnow(None)
        await self._ensure_cycle(now)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            cycle, guild_id = await self._start_context(session, character, now)
            return {
                "cycle_id": cycle.id.hex,
                "guild_id": guild_id.hex,
                "title": "Provação do Juramento",
            }

    async def eligibility(
        self, session: AsyncSession, character: Character, payload: dict
    ) -> ActivityEligibility:
        cycle = await session.get(OathCycle, UUID(hex=payload["cycle_id"]))
        guild_id = UUID(hex=payload["guild_id"])
        reason = (
            "closed"
            if cycle is None or not self._start_open(cycle, _utcnow(None))
            else await self._ineligibility(session, character, cycle, guild_id)
        )
        if reason is not None:
            return ActivityEligibility("ineligible")
        facts = {
            "character": character.id.hex,
            "cycle": cycle.id.hex,
            "guild": guild_id.hex,
            "level": character.level,
        }
        fingerprint = sha256(repr(sorted(facts.items())).encode()).hexdigest()
        return ActivityEligibility("eligible", fingerprint, facts)

    async def create_activity(
        self,
        session: AsyncSession,
        proposal: GroupActivityProposal,
        characters: Sequence[Character],
    ) -> str:
        """Called by the Group with every participant's Character already locked."""
        now = _utcnow(None)
        cycle = await session.get(OathCycle, UUID(hex=proposal.context_payload["cycle_id"]))
        if cycle is None or not self._start_open(cycle, now):
            raise OathError("closed")
        attempt = await self._create_attempt(
            session,
            cycle,
            UUID(hex=proposal.context_payload["guild_id"]),
            characters,
            proposal.id,
            now,
        )
        return attempt.id.hex

    async def announce_start(self, attempt_reference: str, starter: int) -> None:
        """Tell the rest of the roster that the Provação has begun."""
        async with self.sessions() as session:
            attempt = await session.get(OathAttempt, UUID(hex=attempt_reference))
            if attempt is None:
                return
            telegrams = await self._roster_telegrams(session, attempt.id)
            definition = self._by_id.get(attempt.trial_id)
            title = definition.name if definition is not None else "Provação"
        await self._notify(
            [
                OathNotice(telegram, OathTurnNotice(title, started=True))
                for telegram in telegrams
                if telegram != starter
            ]
        )

    async def _create_attempt(
        self,
        session: AsyncSession,
        cycle: OathCycle,
        guild_id: UUID,
        characters: Sequence[Character],
        proposal_id: UUID | None,
        now: datetime,
    ) -> OathAttempt:
        definition = self._by_id.get(cycle.trial_id)
        if definition is None:
            raise OathError("closed")
        ordered = sorted(characters, key=lambda row: row.id.hex)
        await session.execute(
            insert(OathGuildProgress)
            .values(cycle_id=cycle.id, guild_id=guild_id, contribution=0, treasury_crowns=0)
            .on_conflict_do_nothing()
        )
        await self._lock_progress(session, cycle.id, guild_id)
        for character in ordered:
            await session.execute(
                insert(OathMember)
                .values(
                    cycle_id=cycle.id,
                    character_id=character.id,
                    guild_id=guild_id,
                    reference_level=character.level,
                    provacoes_used=0,
                    contribution=0,
                    bound_at=now,
                )
                .on_conflict_do_nothing()
            )
            binding = await session.scalar(
                select(OathMember)
                .where(OathMember.cycle_id == cycle.id, OathMember.character_id == character.id)
                .with_for_update()
            )
            if binding.guild_id != guild_id:
                raise OathError("bound_elsewhere")
            if binding.provacoes_used >= PROVACOES_PER_CYCLE:
                raise OathError("no_provacoes")
            binding.provacoes_used += 1
        roster = list(characters)
        solo = len(roster) == 1
        attempt_id = uuid4()
        rows: list[tuple[Character, OathAttemptMember]] = []
        for ordinal, character in enumerate(roster):
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            rows.append(
                (
                    character,
                    OathAttemptMember(
                        attempt_id=attempt_id,
                        character_id=character.id,
                        actor_key=_SOLO_KEY if solo else f"p{ordinal + 1}",
                        ordinal=ordinal,
                        level=character.level,
                        hp=ZERO,
                        combat_configuration=equipment.to_data(COMBAT_RULESET) | arts.to_data(),
                        consumable_uses=0,
                        acted_stages=[],
                        contribution=0,
                    ),
                )
            )
        reference_level = enemy_level(tuple(row.level for row in roster))
        combat = self._build_combat(definition, 1, reference_level, rows, first=True)
        attempt = OathAttempt(
            id=attempt_id,
            cycle_id=cycle.id,
            guild_id=guild_id,
            trial_id=definition.trial_id,
            proposal_id=proposal_id,
            status="active",
            stage=1,
            roster_size=len(roster),
            reference_level=reference_level,
            points=0,
            combat_id=combat.id,
            combat_snapshot=encode(combat),
            state_version=combat.version,
            ruleset_version=COMBAT_RULESET,
            started_at=now,
            last_action_at=now,
        )
        session.add(attempt)
        await session.flush()
        for character, member in rows:
            activity = GameActivity(
                id=uuid4(),
                character_id=character.id,
                content_id=f"{OATH_ACTIVITY_PREFIX}{attempt.id.hex}",
                status="active",
                state_version=combat.version,
                ruleset_version=COMBAT_RULESET,
                last_valid_action_at=now,
            )
            session.add(activity)
            await session.flush()
            member.game_activity_id = activity.id
            member.hp = combat.fighters[member.actor_key].hp
            session.add(member)
        await session.flush()
        return attempt

    def _build_combat(
        self,
        definition: OathTrialDefinition,
        stage: int,
        reference_level: int,
        rows: Sequence[tuple[Character, OathAttemptMember]],
        *,
        first: bool = False,
    ) -> Combat:
        """§22.1: the first combat is clean; later ones carry the HP of the last."""
        encounter = definition.encounter(stage)
        roster_size = len(rows)
        lead_character, lead_member = rows[0]
        enemy = CreatureCombatantSpec(
            encounter.creature,
            reference_level,
            _ENEMY_KEY,
            stat_multipliers=engine_multipliers(encounter.creature, roster_size),
        )
        party = None
        if roster_size > 1:
            party = tuple(
                PlayerCombatantSpec(
                    fighter_key=member.actor_key,
                    character_id=str(character.id),
                    name=character.name,
                    character_class=character.character_class,
                    race=character.race,
                    level=member.level,
                    hp=Decimal(character.max_hp) if first else Decimal(member.hp),
                    equipment_configuration=equipment_configuration_from_data(
                        member.combat_configuration
                    ),
                    active_art_ids=self._art_ids(member),
                    active=first or Decimal(member.hp) > 0,
                    active_art_snapshots=tuple(member.combat_configuration.get("active_arts", ())),
                )
                for character, member in rows
            )
        combat = create_creature_party_combat(
            uuid4(),
            lead_character.name,
            lead_character.character_class,
            lead_character.race,
            Decimal(lead_character.max_hp) if first else Decimal(lead_member.hp),
            (enemy,),
            player_level=lead_member.level,
            equipment_configuration=equipment_configuration_from_data(
                lead_member.combat_configuration
            ),
            ruleset_version=COMBAT_RULESET,
            flavor=encounter.flavor,
            opening_log=encounter.flavor,
            active_art_ids=self._art_ids(lead_member) if party is None else None,
            party=party,
        )
        boss = combat.fighters[_ENEMY_KEY]
        boss.stats = encounter_stats(encounter.creature, reference_level, roster_size)
        boss.hp = boss.stats.hp
        for _, member in rows:
            fighter = combat.fighters[member.actor_key]
            fighter.hp = fighter.stats.hp if first else min(Decimal(member.hp), fighter.stats.hp)
        return combat

    @staticmethod
    def _art_ids(member: OathAttemptMember) -> tuple[str, ...]:
        return tuple(
            str(entry["art_id"])
            for entry in member.combat_configuration.get("active_arts", ())
            if isinstance(entry, dict) and entry.get("art_id")
        )

    # ---------------------------------------------------------------- combat

    async def action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
        *,
        now: datetime | None = None,
    ) -> OathView:
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
    ) -> OathView | None:
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
                target_id
                if item.family == ConsumableFamily.DISPELLER and target_id
                else current.combat_actor_key
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

    async def abandon(self, actor: int, *, now: datetime | None = None) -> OathView:
        """Only whoever opened the Provação ends it for the roster; it stays consumed."""
        now = _utcnow(now)
        notices: list[OathNotice] = []
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            attempt_id = await session.scalar(
                select(OathAttemptMember.attempt_id)
                .join(OathAttempt, OathAttempt.id == OathAttemptMember.attempt_id)
                .where(
                    OathAttemptMember.character_id == character.id,
                    OathAttempt.status == "active",
                )
            )
            if attempt_id is None:
                raise OathError("no_active")
            attempt = await self._lock_attempt(session, attempt_id)
            members = await self._lock_members(session, attempt.id)
            member = next(row for row in members if row.character_id == character.id)
            if attempt.status != "active":
                raise OathError("no_active")
            if member.ordinal != 0:
                raise OathError("not_opener")
            await self._finish(session, attempt, members, "abandoned", now)
            view = await self._attempt_result(session, attempt, character.id)
            notices = await self._ending_notices(session, attempt, character.telegram_id)
        await self._notify(notices)
        return view

    async def _apply(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        now: datetime | None,
        action: tuple[int, str] | None = None,
        consumable: tuple[str, str, str | None] | None = None,
    ) -> OathView:
        now = _utcnow(now)
        notices: list[OathNotice] = []
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            attempt_id = await session.scalar(
                select(OathAttemptMember.attempt_id).where(
                    OathAttemptMember.character_id == character.id,
                    OathAttemptMember.game_activity_id == activity_id,
                )
            )
            if attempt_id is None:
                return await self._hub_view(session, character, now, None)
            attempt = await self._lock_attempt(session, attempt_id)
            members = await self._lock_members(session, attempt.id)
            member = next(row for row in members if row.character_id == character.id)
            if attempt.status != "active":
                return await self._attempt_result(session, attempt, character.id)
            cycle = await session.get(OathCycle, attempt.cycle_id)
            if now >= cycle.grace_ends_at or now - attempt.last_action_at > ATTEMPT_INACTIVITY:
                status = "expired" if now >= cycle.grace_ends_at else "abandoned"
                await self._finish(session, attempt, members, status, now)
                view = await self._attempt_result(session, attempt, character.id)
                notices = await self._ending_notices(session, attempt, character.telegram_id)
            else:
                view, notices = await self._play(
                    session, character, attempt, members, member, version, action, consumable, now
                )
        await self._notify(notices)
        return view

    async def _play(
        self, session, character, attempt, members, member, version, action, consumable, now
    ) -> tuple[OathView, list[OathNotice]]:
        combat = self._decode(attempt)
        current = await self._combat_view(session, character, attempt, member, combat)
        if version != attempt.state_version or active_player_key(combat) != member.actor_key:
            return current, []
        stack = None
        if consumable is not None:
            item_id, target_id, effect_id = consumable
            remaining = consumable_limit("oath_trial") - member.consumable_uses
            if remaining <= 0:
                return current, []
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
                return current, []
            updated = use_combat_consumable(
                combat,
                item_id,
                target_id=target_id,
                effect_id=effect_id,
                budget_limit=remaining,
                actor_key=member.actor_key,
            )
        else:
            action_index, target_code = action
            intent = campaign_action_intent(combat, member.actor_key, action_index, target_code)
            if intent is None:
                return current, []
            chosen, target = intent
            updated = act(combat, chosen, target_id=target, actor_key=member.actor_key)
        if updated.version == combat.version:
            return current, []
        if stack is not None:
            stack.quantity -= 1
            member.consumable_uses += 1
        self._mark_acted(member, combat, updated, attempt.stage)
        for row in members:
            row.hp = updated.fighters[row.actor_key].hp
        attempt.last_action_at = now
        if updated.result == "victory":
            return await self._stage_won(session, character, attempt, members, member, updated, now)
        if updated.result == "defeat" or all(row.hp <= 0 for row in members):
            self._store(attempt, updated)
            await self._finish(session, attempt, members, "failed", now)
            view = await self._attempt_result(session, attempt, character.id)
            return view, await self._ending_notices(session, attempt, character.telegram_id)
        self._store(attempt, updated)
        await self._sync_activities(session, members, updated.version, now)
        return (
            await self._combat_view(session, character, attempt, member, updated),
            await self._turn_notices(session, attempt, members, member, updated),
        )

    async def _stage_won(self, session, character, attempt, members, member, combat, now):
        progress = await self._lock_progress(session, attempt.cycle_id, attempt.guild_id)
        bindings = await self._lock_bindings(session, attempt.cycle_id, members)
        stage = attempt.stage
        for milestone, points in stage_milestones(stage):
            inserted = await session.execute(
                insert(OathMilestone)
                .values(attempt_id=attempt.id, milestone=milestone, points=points, recorded_at=now)
                .on_conflict_do_nothing()
                .returning(OathMilestone.milestone)
            )
            if inserted.first() is None:
                continue
            # §22.1: collective once per Provação, never multiplied by the roster.
            progress.contribution += points
            attempt.points += points
            for row in members:
                # §22.1: presence alone earns nothing.
                if stage in row.acted_stages:
                    row.contribution += points
                    bindings[row.character_id].contribution += points
        self._store(attempt, combat)
        if stage == STAGE_COUNT:
            await self._finish(session, attempt, members, "completed", now)
            view = await self._attempt_result(session, attempt, character.id)
            return view, await self._ending_notices(session, attempt, character.telegram_id)
        definition = self._by_id.get(attempt.trial_id)
        if definition is None:
            await self._finish(session, attempt, members, "failed", now)
            view = await self._attempt_result(session, attempt, character.id)
            return view, await self._ending_notices(session, attempt, character.telegram_id)
        rows = await self._member_rows(session, members)
        attempt.stage = stage + 1
        following = self._build_combat(definition, attempt.stage, attempt.reference_level, rows)
        # Keeps growing across combats, so an old button can never match a new turn.
        following.version = combat.version + 1
        attempt.combat_id = following.id
        self._store(attempt, following)
        for row in members:
            row.hp = following.fighters[row.actor_key].hp
        await self._sync_activities(session, members, following.version, now)
        return (
            await self._combat_view(session, character, attempt, member, following),
            await self._turn_notices(session, attempt, members, member, following),
        )

    @staticmethod
    def _store(attempt: OathAttempt, combat: Combat) -> None:
        attempt.combat_snapshot = encode(combat)
        attempt.state_version = combat.version

    @staticmethod
    def _mark_acted(member, before: Combat, updated: Combat, stage: int) -> None:
        """Dealing damage, healing or granting a Barrier counts; Defender does not."""
        useful = any(
            event.actor == member.actor_key
            and not event.internal
            and (
                max(event.effective_damage, event.damage) > 0
                or event.healed > 0
                or event.barrier_value > 0
            )
            for event in updated.events[len(before.events) :]
        )
        if useful and stage not in member.acted_stages:
            member.acted_stages = [*member.acted_stages, stage]

    async def _sync_activities(self, session, members, version: int, now: datetime) -> None:
        await session.execute(
            update(GameActivity)
            .where(GameActivity.id.in_([row.game_activity_id for row in members]))
            .values(state_version=version, last_valid_action_at=now)
            .execution_options(synchronize_session=False)
        )

    async def _finish(self, session, attempt, members, status: str, now: datetime) -> None:
        attempt.status = status
        attempt.finished_at = now
        await session.execute(
            update(GameActivity)
            .where(
                GameActivity.id.in_([row.game_activity_id for row in members]),
                GameActivity.status == "active",
            )
            .values(status="completed" if status == "completed" else "failed")
            .execution_options(synchronize_session=False)
        )
        if attempt.proposal_id is None:
            return
        proposal = await session.get(
            GroupActivityProposal, attempt.proposal_id, with_for_update=True
        )
        if proposal is not None and proposal.status == "started":
            proposal.status = "completed" if status == "completed" else "failed"
            proposal.finished_at = now
            proposal.revision += 1
        await session.execute(
            update(GroupActivityParticipant)
            .where(GroupActivityParticipant.proposal_id == attempt.proposal_id)
            .values(reservation_state="released")
            .execution_options(synchronize_session=False)
        )

    # ------------------------------------------------------------- maintenance

    async def run_maintenance(self, *, now: datetime | None = None) -> list[OathNotice]:
        now = _utcnow(now)
        await self._ensure_cycle(now)
        notices = await self._close_stale_attempts(now)
        async with self.sessions() as session:
            cycles = list(
                (
                    await session.scalars(
                        select(OathCycle.id).where(
                            OathCycle.server_id == self.server_id,
                            OathCycle.status.in_(("open", "finalizing")),
                            OathCycle.grace_ends_at <= now,
                        )
                    )
                ).all()
            )
        for cycle_id in cycles:
            notices.extend(await self._finalize(cycle_id, now))
        return notices

    async def _close_stale_attempts(self, now: datetime) -> list[OathNotice]:
        async with self.sessions() as session:
            stale = (
                await session.execute(
                    select(OathAttempt.id, OathCycle.grace_ends_at)
                    .join(OathCycle, OathCycle.id == OathAttempt.cycle_id)
                    .where(
                        OathCycle.server_id == self.server_id,
                        OathAttempt.status == "active",
                        (OathCycle.grace_ends_at <= now)
                        | (OathAttempt.last_action_at < now - ATTEMPT_INACTIVITY),
                    )
                )
            ).all()
        notices: list[OathNotice] = []
        for attempt_id, grace_ends_at in stale:
            async with self.sessions.begin() as session:
                attempt = await self._lock_attempt(session, attempt_id)
                if attempt.status != "active":
                    continue
                members = await self._lock_members(session, attempt.id)
                status = "expired" if now >= grace_ends_at else "abandoned"
                await self._finish(session, attempt, members, status, now)
                notices.extend(await self._ending_notices(session, attempt, None))
        return notices

    async def _finalize(self, cycle_id: UUID, now: datetime) -> list[OathNotice]:
        """§22.1: idempotent; a restart resumes where it stopped."""
        async with self.sessions.begin() as session:
            cycle = await session.scalar(
                select(OathCycle).where(OathCycle.id == cycle_id).with_for_update()
            )
            still_active = await session.scalar(
                select(func.count())
                .select_from(OathAttempt)
                .where(OathAttempt.cycle_id == cycle_id, OathAttempt.status == "active")
            )
            if cycle is None or cycle.status == "closed" or still_active:
                return []
            cycle.status = "finalizing"
        async with self.sessions() as session:
            guild_ids = sorted(
                (
                    await session.scalars(
                        select(OathGuildProgress.guild_id).where(
                            OathGuildProgress.cycle_id == cycle_id,
                            OathGuildProgress.finalized_at.is_(None),
                        )
                    )
                ).all(),
                key=str,
            )
        for guild_id in guild_ids:
            async with self.sessions.begin() as session:
                await self._freeze_guild(session, cycle_id, guild_id, now)
        async with self.sessions() as session:
            character_ids = sorted(
                (
                    await session.scalars(
                        select(OathMember.character_id).where(
                            OathMember.cycle_id == cycle_id, OathMember.settled_at.is_(None)
                        )
                    )
                ).all(),
                key=str,
            )
        notices = []
        for character_id in character_ids:
            notice = await self._settle_one(cycle_id, character_id, now)
            if notice is not None:
                notices.append(notice)
        async with self.sessions.begin() as session:
            cycle = await session.scalar(
                select(OathCycle).where(OathCycle.id == cycle_id).with_for_update()
            )
            if cycle.status != "closed":
                cycle.status = "closed"
                cycle.closed_at = now
        return notices

    async def _freeze_guild(self, session, cycle_id, guild_id, now) -> None:
        # Guilds lock first everywhere (see guild_upkeep).
        guild = await session.scalar(select(Guild).where(Guild.id == guild_id).with_for_update())
        progress = await self._lock_progress(session, cycle_id, guild_id)
        if progress.finalized_at is not None:
            return
        progress.tier = tier_for(progress.contribution)
        if progress.tier and guild is not None and guild.status == "active":
            progress.treasury_crowns = treasury_reward(progress.tier)
            record_treasury(session, guild, "oath", progress.treasury_crowns, now)
        progress.finalized_at = now

    async def _settle_one(
        self, cycle_id: UUID, character_id: UUID, now: datetime
    ) -> OathNotice | None:
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character).where(Character.id == character_id).with_for_update()
            )
            binding = await session.scalar(
                select(OathMember)
                .where(OathMember.cycle_id == cycle_id, OathMember.character_id == character_id)
                .with_for_update()
            )
            if character is None or binding is None or binding.settled_at is not None:
                return None
            progress = await session.get(OathGuildProgress, (cycle_id, binding.guild_id))
            eligible = bool(progress.tier) and is_eligible(binding.contribution)
            reward: dict = {}
            if eligible:
                reward = await self._grant(session, character, binding, progress.tier)
            binding.eligible = eligible
            binding.reward = reward
            binding.settled_at = now
            guild = await session.get(Guild, binding.guild_id)
            return OathNotice(
                character.telegram_id, self._cycle_result(binding, progress, guild.name)
            )

    async def _grant(self, session, character, binding, tier: int) -> dict:
        """§22.1: the source key keeps a repeated job from delivering twice."""
        level = binding.reference_level
        key = f"oath:{binding.cycle_id.hex}:{binding.guild_id.hex}:{character.id.hex}:individual"
        granted = await grant_bundle(
            session,
            character,
            reward_bundle(level, tier),
            key,
            region=region_for_level(level),
        )
        items = [{"name": item.name, "quantity": item.quantity} for item in granted.items]
        catalysts = reward_catalysts(tier)
        if catalysts:
            material_id = reward_catalyst_id(level)
            await return_to_owner(
                session,
                character,
                "material",
                {"material_id": material_id, "bound": True},
                catalysts,
                f"{key}:{material_id}",
            )
            items.append({"name": material_name(material_id), "quantity": catalysts})
        return {"crowns": granted.crowns, "items": items}

    # ----------------------------------------------------------------- helpers

    async def _ensure_cycle(self, now: datetime) -> None:
        """A restart or a second process lands on the same row."""
        opening = latest_opening(now)
        definition = definition_for_opening(self.catalog, opening)
        if definition is None:
            return
        opens_at = opening.astimezone(UTC)
        if now >= opens_at + WINDOW + GRACE:
            return
        async with self.sessions.begin() as session:
            await session.execute(
                insert(OathCycle)
                .values(
                    id=uuid4(),
                    server_id=self.server_id,
                    cycle_key=cycle_key(opening),
                    trial_id=definition.trial_id,
                    status="open",
                    opens_at=opens_at,
                    deadline_at=opens_at + WINDOW,
                    grace_ends_at=opens_at + WINDOW + GRACE,
                    ruleset_version=RULESET,
                )
                .on_conflict_do_nothing(constraint="uq_oath_cycle")
            )

    async def _current_cycle(self, session, now: datetime) -> OathCycle | None:
        return await session.scalar(
            select(OathCycle)
            .where(
                OathCycle.server_id == self.server_id,
                OathCycle.status == "open",
                OathCycle.opens_at <= now,
                OathCycle.grace_ends_at > now,
            )
            .order_by(OathCycle.opens_at.desc())
            .limit(1)
        )

    @staticmethod
    def _start_open(cycle: OathCycle, now: datetime) -> bool:
        return cycle.status == "open" and cycle.opens_at <= now < cycle.deadline_at

    async def _start_context(self, session, character, now) -> tuple[OathCycle, UUID]:
        cycle = await self._current_cycle(session, now)
        if cycle is None or not self._start_open(cycle, now):
            raise OathError("closed")
        membership = await session.get(GuildMember, character.id)
        if membership is None:
            raise OathError("no_guild")
        return cycle, membership.guild_id

    async def _ineligibility(self, session, character, cycle, guild_id) -> str | None:
        membership = await session.get(GuildMember, character.id)
        if membership is None or membership.guild_id != guild_id:
            return "no_guild"
        binding = await session.get(OathMember, (cycle.id, character.id))
        if binding is not None:
            if binding.guild_id != guild_id:
                return "bound_elsewhere"
            if binding.provacoes_used >= PROVACOES_PER_CYCLE:
                return "no_provacoes"
        if await find_combat_configuration_blocker(session, character.id) is not None:
            return "busy"
        return None

    async def _hub_view(self, session, character, now: datetime, notice) -> OathHubView:
        if not self.catalog:
            return OathHubView(catalog_empty=True, notice=notice)
        membership = await session.get(GuildMember, character.id)
        cycle = await self._current_cycle(session, now)
        upcoming = next_opening(now).astimezone(UTC)
        has_last = (
            await session.scalar(
                select(OathMember.cycle_id)
                .where(
                    OathMember.character_id == character.id,
                    OathMember.settled_at.is_not(None),
                )
                .limit(1)
            )
            is not None
        )
        if membership is None and cycle is None:
            return OathHubView(next_opening=upcoming, has_last_result=has_last, notice=notice)
        guild = await session.get(Guild, membership.guild_id) if membership is not None else None
        if cycle is None:
            return OathHubView(
                guild_name=guild.name if guild is not None else None,
                next_opening=upcoming,
                has_last_result=has_last,
                notice=notice,
            )
        definition = self._by_id.get(cycle.trial_id)
        window = "open" if now < cycle.deadline_at else "grace"
        binding = await session.get(OathMember, (cycle.id, character.id))
        guild_id = membership.guild_id if membership is not None else None
        bound_elsewhere = binding is not None and binding.guild_id != guild_id
        progress_guild = binding.guild_id if binding is not None else guild_id
        progress = (
            await session.get(OathGuildProgress, (cycle.id, progress_guild))
            if progress_guild is not None
            else None
        )
        collective = progress.contribution if progress is not None else 0
        attempt, member = await self._active_attempt(session, character.id)
        used = binding.provacoes_used if binding is not None else 0
        left = max(0, PROVACOES_PER_CYCLE - used)
        blocker = await find_combat_configuration_blocker(session, character.id)
        return OathHubView(
            guild_name=guild.name if guild is not None else None,
            window=window,
            deadline=cycle.deadline_at,
            next_opening=upcoming,
            trial_name=definition.name if definition is not None else None,
            provacoes_left=left,
            individual=binding.contribution if binding is not None else 0,
            collective=collective,
            tier=tier_for(collective),
            next_threshold=next_threshold(collective),
            bound_elsewhere=bound_elsewhere,
            bound=binding is not None and not bound_elsewhere,
            can_start=(
                window == "open"
                and membership is not None
                and not bound_elsewhere
                and left > 0
                and blocker is None
            ),
            active_attempt_id=attempt.id if attempt is not None else None,
            has_group=await session.get(SocialGroupMember, character.id) is not None,
            can_abandon=member is not None and member.ordinal == 0,
            has_last_result=has_last,
            notice=notice,
        )

    async def _combat_view(self, session, character, attempt, member, combat) -> CombatView:
        definition = self._by_id.get(attempt.trial_id)
        name = definition.name if definition is not None else "Provação"
        quantities: tuple[tuple[str, int], ...] = ()
        options = ()
        remaining = max(0, consumable_limit("oath_trial") - member.consumable_uses)
        if active_player_key(combat) == member.actor_key:
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
            options = combat_consumable_options(
                combat,
                tuple(item for item, _ in quantities),
                budget_limit=remaining,
                actor_key=member.actor_key,
            )
        return CombatView(
            member.game_activity_id,
            attempt.combat_id,
            character.id,
            combat,
            f"{name} · Combate {attempt.stage}/{STAGE_COUNT}",
            0,
            context=_OATH_CONTEXT,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=remaining,
            combat_actor_key=member.actor_key,
        )

    async def _attempt_result(self, session, attempt, character_id) -> OathAttemptResultView:
        guild = await session.get(Guild, attempt.guild_id)
        binding = await session.get(OathMember, (attempt.cycle_id, character_id))
        definition = self._by_id.get(attempt.trial_id)
        member = await session.get(OathAttemptMember, (attempt.id, character_id))
        return OathAttemptResultView(
            outcome=attempt.status,
            guild_name=guild.name,
            flavor=(
                definition.conclusion_flavor
                if definition is not None and attempt.status == "completed"
                else ""
            ),
            points=member.contribution if member is not None else 0,
            cycle_total=binding.contribution if binding is not None else 0,
        )

    async def _ending_notices(self, session, attempt, skip: int | None) -> list[OathNotice]:
        rows = (
            await session.execute(
                select(Character.id, Character.telegram_id)
                .join(OathAttemptMember, OathAttemptMember.character_id == Character.id)
                .where(OathAttemptMember.attempt_id == attempt.id)
            )
        ).all()
        await session.flush()
        notices = []
        for character_id, telegram in rows:
            if telegram == skip:
                continue
            view = await self._attempt_result(session, attempt, character_id)
            notices.append(OathNotice(telegram, view))
        return notices

    async def _turn_notices(self, session, attempt, members, member, combat) -> list[OathNotice]:
        """Group play is asynchronous here: whoever is next must be told."""
        next_key = active_player_key(combat)
        if next_key is None or next_key == member.actor_key:
            return []
        next_member = next((row for row in members if row.actor_key == next_key), None)
        if next_member is None:
            return []
        telegram = await session.scalar(
            select(Character.telegram_id).where(Character.id == next_member.character_id)
        )
        definition = self._by_id.get(attempt.trial_id)
        return [OathNotice(telegram, OathTurnNotice(definition.name if definition else "Provação"))]

    async def _notify(self, notices: Sequence[OathNotice]) -> None:
        if notices and self.notifier is not None:
            await self.notifier(notices)

    @staticmethod
    def _cycle_result(binding, progress, guild_name: str) -> OathCycleResultView:
        reward = binding.reward or {}
        return OathCycleResultView(
            guild_name=guild_name,
            tier=progress.tier or 0,
            contribution=binding.contribution,
            participated=binding.provacoes_used > 0,
            eligible=bool(binding.eligible),
            treasury=progress.treasury_crowns,
            crowns=int(reward.get("crowns", 0)),
            items=tuple(
                OathRewardItem(str(item["name"]), int(item["quantity"]))
                for item in reward.get("items", ())
            ),
        )

    @staticmethod
    def _decode(attempt: OathAttempt) -> Combat:
        return decode(
            attempt.combat_snapshot,
            attempt.combat_id,
            attempt.ruleset_version,
            attempt.state_version,
        )

    async def _member_rows(self, session, members):
        by_id = {
            row.id: row
            for row in (
                await session.scalars(
                    select(Character).where(Character.id.in_([m.character_id for m in members]))
                )
            ).all()
        }
        ordered = sorted(members, key=lambda row: row.ordinal)
        return [(by_id[row.character_id], row) for row in ordered]

    async def _active_attempt(self, session, character_id: UUID):
        row = (
            await session.execute(
                select(OathAttempt, OathAttemptMember)
                .join(OathAttemptMember, OathAttemptMember.attempt_id == OathAttempt.id)
                .where(
                    OathAttemptMember.character_id == character_id,
                    OathAttempt.status == "active",
                )
                .limit(1)
            )
        ).first()
        return (row[0], row[1]) if row is not None else (None, None)

    async def _roster_telegrams(self, session, attempt_id: UUID) -> list[int]:
        return list(
            (
                await session.scalars(
                    select(Character.telegram_id)
                    .join(OathAttemptMember, OathAttemptMember.character_id == Character.id)
                    .where(OathAttemptMember.attempt_id == attempt_id)
                )
            ).all()
        )

    async def _owns_activity(self, actor: int, activity_id: UUID) -> bool:
        async with self.sessions() as session:
            found = await session.scalar(
                select(OathAttemptMember.attempt_id)
                .join(Character, Character.id == OathAttemptMember.character_id)
                .where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                    OathAttemptMember.game_activity_id == activity_id,
                )
            )
            return found is not None

    async def _character(self, session, actor: int) -> Character:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )
        if character is None:
            raise OathError("no_character")
        return character

    async def _lock_character(self, session, actor: int) -> Character:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if character is None:
            raise OathError("no_character")
        return character

    async def _lock_attempt(self, session, attempt_id: UUID) -> OathAttempt:
        return await session.scalar(
            select(OathAttempt).where(OathAttempt.id == attempt_id).with_for_update()
        )

    async def _lock_members(self, session, attempt_id: UUID) -> list[OathAttemptMember]:
        return list(
            (
                await session.scalars(
                    select(OathAttemptMember)
                    .where(OathAttemptMember.attempt_id == attempt_id)
                    .order_by(OathAttemptMember.character_id)
                    .with_for_update()
                )
            ).all()
        )

    async def _lock_progress(self, session, cycle_id, guild_id) -> OathGuildProgress:
        return await session.scalar(
            select(OathGuildProgress)
            .where(OathGuildProgress.cycle_id == cycle_id, OathGuildProgress.guild_id == guild_id)
            .with_for_update()
        )

    async def _lock_bindings(self, session, cycle_id, members) -> dict[UUID, OathMember]:
        rows = (
            await session.scalars(
                select(OathMember)
                .where(
                    OathMember.cycle_id == cycle_id,
                    OathMember.character_id.in_([row.character_id for row in members]),
                )
                .order_by(OathMember.character_id)
                .with_for_update()
            )
        ).all()
        return {row.character_id: row for row in rows}
