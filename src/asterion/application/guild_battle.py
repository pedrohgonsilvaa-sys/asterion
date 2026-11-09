"""Batalha de Guildas (GDD v1.6.0 §15, §36, §39, §44, §49.14).

Flow: Inscrição (Leader, 24h before until 20:30) -> pairing at 20:30 -> Entry
Confirmation until 20:50 (a reserve may replace an unconfirmed combatant) -> both
Fronts at 21:00 -> on a tie, the Champion 1v1 -> ratings and standings.

Lock order (every write follows it, which rules out deadlocks):
server advisory lock -> Guilds in ascending id order -> Characters in ascending id
order -> registrations -> GuildBattleFight -> GuildBattle -> profiles in ascending
Guild id order. A path may skip a level but never go back up. The Guild service
locks Guild before Character too, so leaving a Guild serialises with pairing and
confirmation.

The Combat Configuration lock is a GameActivity row created by the Entry
Confirmation. It stays active for the whole valid participation: a combatant keeps
it until their Front ends, the Champion keeps it until the battle ends, so the
configuration confirmed for the Front is the one used for the Champion. A fight
never writes ``Character.hp``.

Linked accounts in one fight are only flagged (§36); nothing here blocks them.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account import notification_enabled
from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.active_arts import load_active_art_configuration
from asterion.application.campaign_coop import campaign_action_intent
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.guild_battle_locks import (
    OPEN_REGISTRATION as _OPEN_REGISTRATION,
)
from asterion.application.prologue import CombatView
from asterion.domain.arena import AFK_CONSECUTIVE_TIMEOUTS, AFK_TOTAL_TIMEOUTS
from asterion.domain.combat import Combat, act, active_player_key, pass_turn, withdraw_fighter
from asterion.domain.guild_battle import (
    COMBATANTS,
    FRONT_SIZES,
    FRONTS,
    GUILD_BATTLE_MIN_LEVEL,
    INITIAL_RATING,
    MAX_RESERVES,
    TURN_TTL,
    FightKind,
    PairingCandidate,
    StandingCandidate,
    battle_score,
    classification_points,
    front_points,
    individual_reward_eligible,
    next_battle_start,
    no_show_winner,
    open_registration,
    order_standings,
    pair_guilds,
    rating_after_battle,
    reward_eligible,
    schedule_for,
)
from asterion.domain.guilds import GuildRole
from asterion.domain.road import (
    RULESET,
    PlayerCombatantSpec,
    create_player_versus_player_combat,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    GameActivity,
    Guild,
    GuildBattle,
    GuildBattleFight,
    GuildBattleFightMember,
    GuildBattleProfile,
    GuildBattleRegistration,
    GuildBattleRosterEntry,
    GuildMember,
)

GUILD_BATTLE_CONTENT = "guild_battle"
# A turn overdue by more than this means the service itself was down (§43):
# the deadline is renewed instead of charging a timeout to the player.
DOWNTIME_GRACE = timedelta(seconds=60)
_SIDES = ("a", "b")


class GuildBattleError(ValueError):
    """A Batalha de Guildas action is invalid for the current, revalidated state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class RosterSlotView:
    character_id: UUID
    name: str
    slot: str
    is_champion: bool
    confirmed: bool
    replaced: bool = False


@dataclass(frozen=True, slots=True)
class RegistrationView:
    guild_name: str
    starts_at: datetime
    status: str
    roster: tuple[RosterSlotView, ...]
    opponent_name: str | None


@dataclass(frozen=True, slots=True)
class MemberOption:
    character_id: UUID
    name: str
    level: int


@dataclass(frozen=True, slots=True)
class GuildBattleHubView:
    """Entry screen: the viewer's Guild, the next battle and its current entry."""

    guild_name: str
    character_id: UUID
    is_leader: bool
    next_starts_at: datetime
    registration_open: bool
    registration: RegistrationView | None
    # Members at the current Nv.30 or more, by name; only filled for the Leader.
    candidates: tuple[MemberOption, ...]
    in_fight: bool


@dataclass(frozen=True, slots=True)
class GuildBattleFightView:
    battle: CombatView
    fight_id: UUID
    kind: str
    my_turn: bool
    seconds_left: int


@dataclass(frozen=True, slots=True)
class GuildBattleResultView:
    """Battle settled: ``outcome`` is win, loss or draw from the viewer's Guild."""

    battle_id: UUID
    outcome: str
    guild_name: str
    opponent_name: str
    points: Decimal
    opponent_points: Decimal
    rating_before: int
    rating_after: int


@dataclass(frozen=True, slots=True)
class GuildBattleMessageView:
    code: str
    fight_kind: str | None = None


GuildBattleView = GuildBattleFightView | GuildBattleResultView | GuildBattleMessageView


@dataclass(frozen=True, slots=True)
class GuildBattleNotice:
    telegram_id: int
    view: GuildBattleView


def notice_category(view: GuildBattleView) -> str:
    """Notification category (UI: Essenciais vs PvP/Batalha de Guildas).

    Author decision 2026-11-09: what asks for an action (the pairing that opens
    the Entry Confirmation, and the live fight turns) is Essential; bye, end of a
    Front and the result follow the competitive category.
    """
    if isinstance(view, GuildBattleFightView):
        return "essentials"
    if isinstance(view, GuildBattleMessageView) and view.code == "paired":
        return "essentials"
    return "competitive"


@dataclass(frozen=True, slots=True)
class GuildBattleOutcome:
    view: GuildBattleView
    notices: tuple[GuildBattleNotice, ...] = ()


@dataclass(frozen=True, slots=True)
class StandingRow:
    position: int
    guild_id: UUID
    guild_name: str
    points: int
    rating: int
    real_battles: int
    wins: int
    draws: int
    losses: int
    byes: int
    reward_eligible: bool


def _utcnow(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _seconds_left(deadline: datetime | None, now: datetime) -> int:
    return 0 if deadline is None else max(0, int((deadline - now).total_seconds()))


async def individual_participations(session: AsyncSession, character_id: UUID) -> int:
    """Real battles a character fought in; the Champion counts once per battle."""
    count = await session.scalar(
        select(func.count(func.distinct(GuildBattleFight.battle_id)))
        .join(GuildBattleFightMember, GuildBattleFightMember.fight_id == GuildBattleFight.id)
        .join(GuildBattle, GuildBattle.id == GuildBattleFight.battle_id)
        .where(
            GuildBattleFightMember.character_id == character_id,
            GuildBattle.status == "finished",
        )
    )
    return int(count or 0)


class GuildBattleService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    # ------------------------------------------------------------ Inscrição

    async def register(
        self,
        actor: int,
        *,
        front_1: tuple[UUID, ...],
        front_2: tuple[UUID, ...],
        champion: UUID,
        reserves: tuple[UUID, ...] = (),
        now: datetime | None = None,
    ) -> RegistrationView:
        """The Leader registers or replaces the roster while Inscrição is open."""
        now = _utcnow(now)
        schedule = open_registration(now)
        if schedule is None:
            raise GuildBattleError("registration_closed")
        combatants = (*front_1, *front_2)
        everyone = (*combatants, *reserves)
        if (
            len(front_1) != FRONT_SIZES[FightKind.FRONT_I]
            or len(front_2) != FRONT_SIZES[FightKind.FRONT_II]
            or len(combatants) != COMBATANTS
            or len(reserves) > MAX_RESERVES
            or len(set(everyone)) != len(everyone)
            or champion not in combatants
        ):
            raise GuildBattleError("invalid_roster")
        async with self.sessions.begin() as session:
            await self._advisory_lock(session)
            character, guild = await self._leader_guild(session, actor)
            if guild.dissolution_due_at is not None:
                raise GuildBattleError("guild_dissolving")
            members = await self._eligible_members(session, guild.id, everyone)
            if len(members) != len(everyone):
                raise GuildBattleError("member_ineligible")
            registration = await session.scalar(
                select(GuildBattleRegistration)
                .where(
                    GuildBattleRegistration.guild_id == guild.id,
                    GuildBattleRegistration.starts_at == schedule.starts_at,
                )
                .with_for_update()
            )
            if registration is None:
                registration = GuildBattleRegistration(
                    id=uuid4(),
                    server_id=self.server_id,
                    guild_id=guild.id,
                    starts_at=schedule.starts_at,
                    created_at=now,
                )
                session.add(registration)
            elif registration.status not in ("registered", "cancelled"):
                raise GuildBattleError("registration_closed")
            else:
                await self._clear_roster(session, registration.id)
                registration.revision += 1
            registration.status = "registered"
            registration.registered_by = character.id
            registration.updated_at = now
            await session.flush()
            slots = {
                **{item: FightKind.FRONT_I.value for item in front_1},
                **{item: FightKind.FRONT_II.value for item in front_2},
                **{item: "reserve" for item in reserves},
            }
            for character_id in everyone:
                session.add(
                    GuildBattleRosterEntry(
                        registration_id=registration.id,
                        character_id=character_id,
                        account_id=members[character_id].telegram_id,
                        slot=slots[character_id],
                        is_champion=character_id == champion,
                        status="registered",
                    )
                )
            await session.flush()
            return await self._registration_view(session, registration, guild)

    async def cancel_registration(self, actor: int, *, now: datetime | None = None) -> None:
        now = _utcnow(now)
        schedule = open_registration(now)
        if schedule is None:
            raise GuildBattleError("registration_closed")
        async with self.sessions.begin() as session:
            await self._advisory_lock(session)
            _character, guild = await self._leader_guild(session, actor)
            registration = await session.scalar(
                select(GuildBattleRegistration)
                .where(
                    GuildBattleRegistration.guild_id == guild.id,
                    GuildBattleRegistration.starts_at == schedule.starts_at,
                    GuildBattleRegistration.status == "registered",
                )
                .with_for_update()
            )
            if registration is None:
                raise GuildBattleError("not_registered")
            await self._clear_roster(session, registration.id)
            registration.status = "cancelled"
            registration.revision += 1
            registration.updated_at = now

    async def hub(self, actor: int, *, now: datetime | None = None) -> GuildBattleHubView:
        now = _utcnow(now)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                raise GuildBattleError("no_character")
            membership = await session.get(GuildMember, character.id)
            if membership is None:
                raise GuildBattleError("not_in_guild")
            guild = await session.get(Guild, membership.guild_id)
            if guild is None or guild.status != "active":
                raise GuildBattleError("not_in_guild")
            is_leader = membership.role == GuildRole.LEADER.value
            candidates: tuple[MemberOption, ...] = ()
            if is_leader:
                rows = (
                    await session.scalars(
                        select(Character)
                        .join(GuildMember, GuildMember.character_id == Character.id)
                        .where(
                            GuildMember.guild_id == guild.id,
                            Character.server_id == self.server_id,
                            Character.level >= GUILD_BATTLE_MIN_LEVEL,
                        )
                        .order_by(Character.name, Character.id)
                    )
                ).all()
                candidates = tuple(MemberOption(row.id, row.name, row.level) for row in rows)
            in_fight = await session.scalar(
                select(GuildBattleFightMember.fight_id)
                .join(GuildBattleFight, GuildBattleFight.id == GuildBattleFightMember.fight_id)
                .where(
                    GuildBattleFightMember.character_id == character.id,
                    GuildBattleFight.status == "active",
                )
                .limit(1)
            )
        registration = await self.registration(actor)
        return GuildBattleHubView(
            guild.name,
            character.id,
            is_leader,
            next_battle_start(now),
            open_registration(now) is not None,
            registration,
            candidates,
            in_fight is not None,
        )

    async def deliverable(
        self, notices: Sequence[GuildBattleNotice]
    ) -> list[GuildBattleNotice]:
        """Drop notices whose category the player switched off (GDD §37.3 Notificações)."""
        if not notices:
            return []
        allowed: dict[tuple[int, str], bool] = {}
        async with self.sessions() as session:
            for notice in notices:
                key = (notice.telegram_id, notice_category(notice.view))
                if key not in allowed:
                    character = await self._character(session, notice.telegram_id)
                    allowed[key] = character is not None and await notification_enabled(
                        session, character.id, key[1]
                    )
        return [item for item in notices if allowed[(item.telegram_id, notice_category(item.view))]]

    async def registration(self, actor: int) -> RegistrationView | None:
        """The actor's Guild entry for the next battle that is not settled yet."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            membership = await session.get(GuildMember, character.id)
            if membership is None:
                return None
            registration = await session.scalar(
                select(GuildBattleRegistration)
                .where(
                    GuildBattleRegistration.guild_id == membership.guild_id,
                    GuildBattleRegistration.status.in_((*_OPEN_REGISTRATION, "bye")),
                )
                .order_by(GuildBattleRegistration.starts_at.desc())
                .limit(1)
            )
            if registration is None:
                return None
            guild = await session.get(Guild, membership.guild_id)
            assert guild is not None
            return await self._registration_view(session, registration, guild)

    # ------------------------------------------------- confirmation & reserves

    async def confirm(self, actor: int, *, now: datetime | None = None) -> RegistrationView:
        """Entry Confirmation: records and locks the full Combat Configuration (§39)."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            await self._advisory_lock(session)
            character = await self._character(session, actor)
            if character is None:
                raise GuildBattleError("no_character")
            entry, registration = await self._paired_entry(session, character.id)
            if entry is None or entry.slot == "reserve" or entry.status == "replaced":
                raise GuildBattleError("not_in_roster")
            if entry.status == "confirmed":
                guild = await session.get(Guild, registration.guild_id)
                assert guild is not None
                return await self._registration_view(session, registration, guild)
            if now >= schedule_for(registration.starts_at).confirmation_closes_at:
                raise GuildBattleError("confirmation_closed")
            guild = await self._lock_guild(session, registration.guild_id)
            locked = await self._lock_character(session, character.id)
            if not await self._eligible(session, guild.id, locked):
                raise GuildBattleError("member_ineligible")
            if await session.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == locked.id, GameActivity.status == "active"
                )
            ):
                raise GuildBattleError("busy")
            activity = GameActivity(
                id=uuid4(),
                character_id=locked.id,
                content_id=GUILD_BATTLE_CONTENT,
                status="active",
                state_version=0,
                ruleset_version=RULESET,
                last_valid_action_at=now,
            )
            session.add(activity)
            await session.flush()
            entry.status = "confirmed"
            entry.confirmed_at = now
            entry.game_activity_id = activity.id
            await session.flush()
            return await self._registration_view(session, registration, guild)

    async def substitute(
        self,
        actor: int,
        replaced_character_id: UUID,
        reserve_character_id: UUID,
        *,
        now: datetime | None = None,
    ) -> RegistrationView:
        """A reserve takes the place of an unconfirmed combatant until 20:50."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            await self._advisory_lock(session)
            _character, guild = await self._leader_guild(session, actor)
            registration = await session.scalar(
                select(GuildBattleRegistration)
                .where(
                    GuildBattleRegistration.guild_id == guild.id,
                    GuildBattleRegistration.status == "paired",
                )
                .with_for_update()
            )
            if registration is None:
                raise GuildBattleError("not_paired")
            if now >= schedule_for(registration.starts_at).confirmation_closes_at:
                raise GuildBattleError("confirmation_closed")
            entries = {
                row.character_id: row for row in await self._roster(session, registration.id)
            }
            replaced = entries.get(replaced_character_id)
            reserve = entries.get(reserve_character_id)
            if (
                replaced is None
                or reserve is None
                or replaced.slot == "reserve"
                or replaced.status != "registered"
                or reserve.slot != "reserve"
                or reserve.status != "registered"
            ):
                raise GuildBattleError("invalid_substitution")
            if not await self._eligible_members(session, guild.id, (reserve_character_id,)):
                raise GuildBattleError("member_ineligible")
            reserve.slot, replaced.slot = replaced.slot, "reserve"
            reserve.is_champion, replaced.is_champion = replaced.is_champion, False
            replaced.status = "replaced"
            registration.revision += 1
            registration.updated_at = now
            await session.flush()
            return await self._registration_view(session, registration, guild)

    # --------------------------------------------------------------- combat

    async def foreground(
        self, actor: int, *, now: datetime | None = None
    ) -> GuildBattleFightView | None:
        now = _utcnow(now)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            row = (
                await session.execute(
                    select(GuildBattleFight, GuildBattleFightMember)
                    .join(
                        GuildBattleFightMember,
                        GuildBattleFightMember.fight_id == GuildBattleFight.id,
                    )
                    .where(
                        GuildBattleFightMember.character_id == character.id,
                        GuildBattleFight.status == "active",
                    )
                    .limit(1)
                )
            ).first()
            if row is None:
                return None
            fight, member = row
            return self._fight_view(character, fight, member, self._decode(fight), now)

    async def action(
        self,
        actor: int,
        fight_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
        *,
        now: datetime | None = None,
    ) -> GuildBattleOutcome:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                raise GuildBattleError("no_character")
            fight = await self._lock_fight(session, fight_id)
            if fight is None:
                raise GuildBattleError("not_found")
            members = await self._fight_members(session, fight.id)
            member = next((row for row in members if row.character_id == character.id), None)
            if member is None:
                raise GuildBattleError("not_found")
            if fight.status != "active":
                return GuildBattleOutcome(GuildBattleMessageView("fight_over", fight.kind))
            combat = self._decode(fight)
            current = GuildBattleOutcome(self._fight_view(character, fight, member, combat, now))
            if (
                member.withdrawn_at is not None
                or version != fight.state_version
                or active_player_key(combat) != member.actor_key
            ):
                return current
            intent = campaign_action_intent(combat, member.actor_key, action_index, target_code)
            if intent is None:
                return current
            chosen, target = intent
            updated = act(combat, chosen, target_id=target, actor_key=member.actor_key)
            if updated.version == combat.version:
                return current
            member.consecutive_timeouts = 0
            notices = await self._advance(session, fight, members, updated, now)
            own = next((item.view for item in notices if item.telegram_id == actor), None)
            rest = tuple(item for item in notices if item.telegram_id != actor)
            if own is None:
                own = self._fight_view(character, fight, member, updated, now)
            return GuildBattleOutcome(own, rest)

    # ---------------------------------------------------------- maintenance

    async def run_maintenance(
        self, *, now: datetime | None = None, limit: int = 100
    ) -> list[GuildBattleNotice]:
        """Pair at 20:30, start at 21:00 and resolve turn timeouts. Idempotent."""
        now = _utcnow(now)
        notices: list[GuildBattleNotice] = []
        notices.extend(await self._pair_due(now))
        async with self.sessions() as session:
            due_battles = (
                await session.scalars(
                    select(GuildBattle.id)
                    .where(
                        GuildBattle.server_id == self.server_id,
                        GuildBattle.status == "confirming",
                        GuildBattle.starts_at <= now,
                    )
                    .order_by(GuildBattle.starts_at, GuildBattle.id)
                    .limit(limit)
                )
            ).all()
        for battle_id in due_battles:
            notices.extend(await self._start_battle(battle_id, now))
        async with self.sessions() as session:
            due_fights = (
                await session.scalars(
                    select(GuildBattleFight.id)
                    .join(GuildBattle, GuildBattle.id == GuildBattleFight.battle_id)
                    .where(
                        GuildBattle.server_id == self.server_id,
                        GuildBattleFight.status == "active",
                        GuildBattleFight.deadline_at <= now,
                    )
                    .order_by(GuildBattleFight.deadline_at)
                    .limit(limit)
                )
            ).all()
        for fight_id in due_fights:
            notices.extend(await self._resolve_turn_timeout(fight_id, now))
        return notices

    async def _pair_due(self, now: datetime) -> list[GuildBattleNotice]:
        async with self.sessions.begin() as session:
            await self._advisory_lock(session)
            due = (
                await session.scalars(
                    select(GuildBattleRegistration)
                    .where(
                        GuildBattleRegistration.server_id == self.server_id,
                        GuildBattleRegistration.status == "registered",
                    )
                    .order_by(GuildBattleRegistration.guild_id)
                )
            ).all()
            by_slot: dict[datetime, list[GuildBattleRegistration]] = defaultdict(list)
            for registration in due:
                if schedule_for(registration.starts_at).registration_closes_at <= now:
                    by_slot[registration.starts_at].append(registration)
            notices: list[GuildBattleNotice] = []
            for starts_at in sorted(by_slot):
                notices.extend(await self._pair_slot(session, starts_at, by_slot[starts_at], now))
            return notices

    async def _pair_slot(self, session, starts_at, registrations, now):
        guilds = {
            guild.id: guild
            for guild in (
                await session.scalars(
                    select(Guild)
                    .where(Guild.id.in_([row.guild_id for row in registrations]))
                    .order_by(Guild.id)
                    .with_for_update()
                )
            ).all()
        }
        valid = []
        for registration in sorted(registrations, key=lambda row: row.guild_id):
            await session.refresh(registration, with_for_update=True)
            if registration.status != "registered":
                continue
            if guilds[registration.guild_id].status != "active":
                registration.status = "cancelled"
                registration.updated_at = now
                continue
            valid.append(registration)
        profiles = {row.guild_id: await self._lock_profile(session, row.guild_id) for row in valid}
        pairing = pair_guilds(
            [
                PairingCandidate(
                    row.guild_id, profiles[row.guild_id].rating, profiles[row.guild_id].byes
                )
                for row in valid
            ]
        )
        by_guild = {row.guild_id: row for row in valid}
        notices: list[GuildBattleNotice] = []
        if pairing.bye is not None:
            registration = by_guild[pairing.bye]
            registration.status = "bye"
            registration.updated_at = now
            profiles[pairing.bye].byes += 1
            for entry in await self._roster(session, registration.id):
                notices.append(GuildBattleNotice(entry.account_id, GuildBattleMessageView("bye")))
        for guild_a, guild_b in pairing.pairs:
            registration_a, registration_b = by_guild[guild_a], by_guild[guild_b]
            session.add(
                GuildBattle(
                    id=uuid4(),
                    server_id=self.server_id,
                    starts_at=starts_at,
                    registration_a_id=registration_a.id,
                    registration_b_id=registration_b.id,
                    guild_a_id=guild_a,
                    guild_b_id=guild_b,
                    status="confirming",
                    points_a=Decimal(0),
                    points_b=Decimal(0),
                    created_at=now,
                )
            )
            for registration in (registration_a, registration_b):
                registration.status = "paired"
                registration.updated_at = now
                for entry in await self._roster(session, registration.id):
                    notices.append(
                        GuildBattleNotice(entry.account_id, GuildBattleMessageView("paired"))
                    )
        await session.flush()
        return notices

    async def _start_battle(self, battle_id: UUID, now: datetime) -> list[GuildBattleNotice]:
        async with self.sessions.begin() as session:
            await self._advisory_lock(session)
            battle = await self._lock_battle(session, battle_id)
            if battle is None or battle.status != "confirming" or battle.starts_at > now:
                return []
            rosters = await self._battle_rosters(session, battle)
            battle.status = "fronts"
            notices: list[GuildBattleNotice] = []
            for kind in FRONTS:
                lineup = {
                    side: [row for row in rosters[side] if row.slot == kind.value]
                    for side in _SIDES
                }
                notices.extend(await self._open_fight(session, battle, kind, lineup, now))
            notices.extend(await self._progress_battle(session, battle, now))
            return notices

    async def _open_fight(self, session, battle, kind, lineup, now):
        """Create one fight; a side with an unconfirmed combatant is absent."""
        absent = {
            side: not lineup[side] or any(row.status != "confirmed" for row in lineup[side])
            for side in _SIDES
        }
        fight = GuildBattleFight(
            id=uuid4(),
            battle_id=battle.id,
            kind=kind.value,
            status="active",
            absent_a=absent["a"],
            absent_b=absent["b"],
            state_version=0,
        )
        session.add(fight)
        await session.flush()
        if absent["a"] or absent["b"]:
            return await self._finish_fight(
                session, battle, fight, no_show_winner(absent["a"], absent["b"]), "no_show", now
            )
        characters = {
            row.id: row
            for row in (
                await session.scalars(
                    select(Character).where(
                        Character.id.in_([e.character_id for side in _SIDES for e in lineup[side]])
                    )
                )
            ).all()
        }
        specs: dict[str, list[PlayerCombatantSpec]] = {"a": [], "b": []}
        members: list[GuildBattleFightMember] = []
        for side in _SIDES:
            for index, entry in enumerate(sorted(lineup[side], key=lambda row: row.character_id)):
                character = characters[entry.character_id]
                key = f"{side}{index + 1}"
                equipment = await load_equipment_configuration(session, character)
                arts = await load_active_art_configuration(session, character)
                specs[side].append(
                    PlayerCombatantSpec(
                        fighter_key=key,
                        character_id=character.id.hex,
                        name=character.name,
                        character_class=character.character_class,
                        race=character.race,
                        level=character.level,
                        hp=character.hp,
                        equipment_configuration=equipment,
                        active_art_ids=arts.art_ids,
                        active_art_snapshots=tuple(slot.to_data() for slot in arts.slots),
                    )
                )
                member = GuildBattleFightMember(
                    fight_id=fight.id,
                    character_id=character.id,
                    account_id=entry.account_id,
                    side=side,
                    actor_key=key,
                    game_activity_id=entry.game_activity_id,
                    consecutive_timeouts=0,
                    total_timeouts=0,
                )
                session.add(member)
                members.append(member)
        combat = create_player_versus_player_combat(
            uuid4(),
            tuple(specs["a"]),
            tuple(specs["b"]),
            ruleset_version=RULESET,
            flavor="",
            opening_log="⚔️ A frente começa.",
            full_hp=True,
        )
        fight.combat_id = combat.id
        fight.ruleset_version = RULESET
        fight.started_at = now
        self._store_combat(fight, combat, now)
        await session.flush()
        await self._sync_activities(session, members, combat, now)
        await record_linked_cooccurrence(
            session,
            server_id=self.server_id,
            activity_kind="guild_battle",
            activity_reference=f"guild_battle:{fight.id.hex}",
            characters=characters.values(),
            now=now,
        )
        return self._fight_notices(fight, members, characters, combat, now)

    async def _resolve_turn_timeout(self, fight_id: UUID, now: datetime) -> list[GuildBattleNotice]:
        async with self.sessions.begin() as session:
            fight = await self._lock_fight(session, fight_id)
            if fight is None or fight.status != "active" or fight.deadline_at > now:
                return []
            if now - fight.deadline_at > DOWNTIME_GRACE:
                fight.deadline_at = now + TURN_TTL
                return []
            members = await self._fight_members(session, fight.id)
            combat = self._decode(fight)
            member = next(
                (row for row in members if row.actor_key == active_player_key(combat)), None
            )
            if member is None:
                return []
            member.consecutive_timeouts += 1
            member.total_timeouts += 1
            if (
                member.consecutive_timeouts >= AFK_CONSECUTIVE_TIMEOUTS
                or member.total_timeouts >= AFK_TOTAL_TIMEOUTS
            ):
                member.withdrawn_at = now
                updated = withdraw_fighter(combat, member.actor_key)
            else:
                updated = pass_turn(combat, member.actor_key)
            return await self._advance(session, fight, members, updated, now)

    async def _advance(self, session, fight, members, combat, now) -> list[GuildBattleNotice]:
        self._store_combat(fight, combat, now)
        await self._sync_activities(session, members, combat, now)
        if not combat.result:
            characters = await self._characters(session, [row.character_id for row in members])
            return self._fight_notices(fight, members, characters, combat, now)
        alive = {
            side: any(
                fighter.hp > 0 and fighter.side == side for fighter in combat.fighters.values()
            )
            for side in ("player", "enemy")
        }
        winner = (
            "a"
            if alive["player"] and not alive["enemy"]
            else "b"
            if alive["enemy"] and not alive["player"]
            else None
        )
        battle = await self._lock_battle(session, fight.battle_id)
        assert battle is not None
        reason = "afk" if any(row.withdrawn_at is not None for row in members) else "combat"
        return await self._finish_fight(session, battle, fight, winner, reason, now)

    async def _finish_fight(self, session, battle, fight, winner, reason, now):
        fight.status = "finished"
        fight.winner_side = winner
        fight.end_reason = reason
        fight.finished_at = now
        fight.deadline_at = None
        rosters = await self._battle_rosters(session, battle)
        notices = []
        for side in _SIDES:
            for entry in rosters[side]:
                if fight.kind == FightKind.CHAMPION.value:
                    in_fight = entry.is_champion
                else:
                    in_fight = entry.slot == fight.kind
                if not in_fight:
                    continue
                if fight.kind != FightKind.CHAMPION.value and not entry.is_champion:
                    await self._release(session, entry, now)
                notices.append(
                    GuildBattleNotice(
                        entry.account_id, GuildBattleMessageView("fight_over", fight.kind)
                    )
                )
        await session.flush()
        notices.extend(await self._progress_battle(session, battle, now))
        return notices

    async def _progress_battle(self, session, battle, now) -> list[GuildBattleNotice]:
        fights = {
            row.kind: row
            for row in (
                await session.scalars(
                    select(GuildBattleFight).where(GuildBattleFight.battle_id == battle.id)
                )
            ).all()
        }
        if battle.status == "finished":
            return []
        champion = fights.get(FightKind.CHAMPION.value)
        if champion is not None:
            if champion.status != "finished":
                return []
            return await self._finish_battle(session, battle, champion.winner_side, now)
        if any(
            kind.value not in fights or fights[kind.value].status != "finished" for kind in FRONTS
        ):
            return []
        points_a = points_b = Decimal(0)
        for kind in FRONTS:
            fight = fights[kind.value]
            a, b = front_points(fight.winner_side, absent_a=fight.absent_a, absent_b=fight.absent_b)
            points_a += a
            points_b += b
        battle.points_a, battle.points_b = points_a, points_b
        if points_a != points_b:
            return await self._finish_battle(
                session, battle, "a" if points_a > points_b else "b", now
            )
        battle.status = "champion"
        rosters = await self._battle_rosters(session, battle)
        lineup = {side: [row for row in rosters[side] if row.is_champion] for side in _SIDES}
        return await self._open_fight(session, battle, FightKind.CHAMPION, lineup, now)

    async def _finish_battle(self, session, battle, winner, now) -> list[GuildBattleNotice]:
        battle.status = "finished"
        battle.winner_side = winner
        battle.finished_at = now
        rosters = await self._battle_rosters(session, battle)
        for side in _SIDES:
            for entry in rosters[side]:
                await self._release(session, entry, now)
        for registration_id in (battle.registration_a_id, battle.registration_b_id):
            registration = await session.get(GuildBattleRegistration, registration_id)
            assert registration is not None
            registration.status = "finished"
            registration.updated_at = now
        first, second = sorted((battle.guild_a_id, battle.guild_b_id))
        profiles = {
            first: await self._lock_profile(session, first),
            second: await self._lock_profile(session, second),
        }
        profile_a, profile_b = profiles[battle.guild_a_id], profiles[battle.guild_b_id]
        score_a, score_b = battle_score(winner)
        battle.rating_a_before, battle.rating_b_before = profile_a.rating, profile_b.rating
        new_a = rating_after_battle(
            profile_a.rating, profile_b.rating, score_a, profile_a.real_battles
        )
        new_b = rating_after_battle(
            profile_b.rating, profile_a.rating, score_b, profile_b.real_battles
        )
        for profile, score, rating in ((profile_a, score_a, new_a), (profile_b, score_b, new_b)):
            profile.rating = rating
            profile.real_battles += 1
            profile.points += classification_points(score)
            if score == 1:
                profile.wins += 1
            elif score == 0:
                profile.losses += 1
            else:
                profile.draws += 1
            profile.last_battle_at = now
        battle.rating_a_after, battle.rating_b_after = new_a, new_b
        await session.flush()
        names = {
            row.id: row.name
            for row in (
                await session.scalars(
                    select(Guild).where(Guild.id.in_([battle.guild_a_id, battle.guild_b_id]))
                )
            ).all()
        }
        notices = []
        for side in _SIDES:
            mine = side == "a"
            score = score_a if mine else score_b
            view = GuildBattleResultView(
                battle.id,
                "win" if score == 1 else "loss" if score == 0 else "draw",
                names[battle.guild_a_id if mine else battle.guild_b_id],
                names[battle.guild_b_id if mine else battle.guild_a_id],
                battle.points_a if mine else battle.points_b,
                battle.points_b if mine else battle.points_a,
                battle.rating_a_before if mine else battle.rating_b_before,
                new_a if mine else new_b,
            )
            notices.extend(
                GuildBattleNotice(entry.account_id, view)
                for entry in rosters[side]
                if entry.status != "replaced"
            )
        return notices

    # ------------------------------------------------------------- standings

    async def standings(self) -> tuple[StandingRow, ...]:
        async with self.sessions() as session:
            rows = (
                await session.execute(
                    select(GuildBattleProfile, Guild.name)
                    .join(Guild, Guild.id == GuildBattleProfile.guild_id)
                    .where(
                        GuildBattleProfile.server_id == self.server_id,
                        Guild.status == "active",
                    )
                )
            ).all()
        by_id = {profile.guild_id: (profile, name) for profile, name in rows}
        ordered = order_standings(
            [StandingCandidate(p.guild_id, p.points, p.rating) for p, _ in rows]
        )
        result = []
        for position, item in enumerate(ordered, start=1):
            profile, name = by_id[item.guild_id]
            result.append(
                StandingRow(
                    position,
                    profile.guild_id,
                    name,
                    profile.points,
                    profile.rating,
                    profile.real_battles,
                    profile.wins,
                    profile.draws,
                    profile.losses,
                    profile.byes,
                    reward_eligible(profile.real_battles),
                )
            )
        return tuple(result)

    async def individual_reward_eligible(self, actor: int) -> bool:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return False
            return individual_reward_eligible(
                await individual_participations(session, character.id)
            )

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _decode(fight: GuildBattleFight) -> Combat:
        return decode(
            fight.combat_snapshot, fight.combat_id, fight.ruleset_version, fight.state_version
        )

    @staticmethod
    def _store_combat(fight: GuildBattleFight, combat: Combat, now: datetime) -> None:
        fight.combat_snapshot = encode(combat)
        fight.state_version = combat.version
        fight.deadline_at = now + TURN_TTL

    @staticmethod
    async def _sync_activities(session, members, combat, now) -> None:
        for member in members:
            if member.game_activity_id is None:
                continue
            activity = await session.get(GameActivity, member.game_activity_id)
            if activity is None:
                continue
            activity.state_version = combat.version
            activity.last_valid_action_at = now

    @staticmethod
    async def _release(session, entry: GuildBattleRosterEntry, now: datetime) -> None:
        """End one participation: the configuration lock goes with it."""
        if entry.game_activity_id is None:
            return
        activity = await session.get(GameActivity, entry.game_activity_id)
        if activity is not None and activity.status == "active":
            activity.status = "completed"
            activity.last_valid_action_at = now

    @staticmethod
    def _fight_view(character, fight, member, combat, now) -> GuildBattleFightView:
        battle = CombatView(
            member.game_activity_id or fight.id,
            fight.id,
            character.id,
            combat,
            "pvp",
            0,
            context=GUILD_BATTLE_CONTENT,
            combat_actor_key=member.actor_key,
        )
        return GuildBattleFightView(
            battle,
            fight.id,
            fight.kind,
            member.withdrawn_at is None and active_player_key(combat) == member.actor_key,
            _seconds_left(fight.deadline_at, now),
        )

    def _fight_notices(self, fight, members, characters, combat, now):
        return [
            GuildBattleNotice(
                member.account_id,
                self._fight_view(characters[member.character_id], fight, member, combat, now),
            )
            for member in members
            if member.withdrawn_at is None
        ]

    async def _registration_view(self, session, registration, guild) -> RegistrationView:
        entries = await self._roster(session, registration.id)
        characters = await self._characters(session, [row.character_id for row in entries])
        order = {FightKind.FRONT_I.value: 0, FightKind.FRONT_II.value: 1, "reserve": 2}
        roster = tuple(
            RosterSlotView(
                row.character_id,
                characters[row.character_id].name,
                row.slot,
                row.is_champion,
                row.status == "confirmed",
                row.status == "replaced",
            )
            for row in sorted(
                entries, key=lambda row: (order[row.slot], characters[row.character_id].name)
            )
        )
        opponent_name = None
        if registration.status in ("paired", "finished"):
            battle = await session.scalar(
                select(GuildBattle).where(
                    (GuildBattle.registration_a_id == registration.id)
                    | (GuildBattle.registration_b_id == registration.id)
                )
            )
            if battle is not None:
                other_id = battle.guild_b_id if battle.guild_a_id == guild.id else battle.guild_a_id
                other = await session.get(Guild, other_id)
                opponent_name = other.name if other is not None else None
        return RegistrationView(
            guild.name, registration.starts_at, registration.status, roster, opponent_name
        )

    async def _advisory_lock(self, session) -> None:
        raw = int.from_bytes(sha256(f"guild_battle:{self.server_id}".encode()).digest()[:8], "big")
        key = raw - (1 << 64) if raw >= (1 << 63) else raw
        await session.execute(select(func.pg_advisory_xact_lock(key)))

    async def _character(self, session, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    @staticmethod
    async def _characters(session, ids) -> dict[UUID, Character]:
        if not ids:
            return {}
        return {
            row.id: row
            for row in (
                await session.scalars(select(Character).where(Character.id.in_(list(ids))))
            ).all()
        }

    @staticmethod
    async def _lock_character(session, character_id: UUID) -> Character:
        character = await session.scalar(
            select(Character)
            .where(Character.id == character_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if character is None:
            raise GuildBattleError("no_character")
        return character

    @staticmethod
    async def _lock_guild(session, guild_id: UUID) -> Guild:
        guild = await session.scalar(
            select(Guild)
            .where(Guild.id == guild_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if guild is None or guild.status != "active":
            raise GuildBattleError("not_in_guild")
        return guild

    async def _leader_guild(self, session, actor: int) -> tuple[Character, Guild]:
        character = await self._character(session, actor)
        if character is None:
            raise GuildBattleError("no_character")
        seed = await session.get(GuildMember, character.id)
        if seed is None:
            raise GuildBattleError("not_in_guild")
        guild = await self._lock_guild(session, seed.guild_id)
        membership = await session.scalar(
            select(GuildMember)
            .where(GuildMember.character_id == character.id)
            .execution_options(populate_existing=True)
        )
        if membership is None or membership.guild_id != guild.id:
            raise GuildBattleError("not_in_guild")
        if membership.role != GuildRole.LEADER.value:
            raise GuildBattleError("no_permission")
        return character, guild

    async def _eligible_members(self, session, guild_id, character_ids) -> dict[UUID, Character]:
        """Members of this Guild, on this server, at the current Nv.30 or more."""
        rows = (
            await session.scalars(
                select(Character)
                .join(GuildMember, GuildMember.character_id == Character.id)
                .where(
                    Character.id.in_(list(character_ids)),
                    Character.server_id == self.server_id,
                    Character.level >= GUILD_BATTLE_MIN_LEVEL,
                    GuildMember.guild_id == guild_id,
                )
            )
        ).all()
        return {row.id: row for row in rows}

    async def _eligible(self, session, guild_id, character: Character) -> bool:
        return bool(await self._eligible_members(session, guild_id, (character.id,)))

    async def _paired_entry(self, session, character_id: UUID):
        row = (
            await session.execute(
                select(GuildBattleRosterEntry, GuildBattleRegistration)
                .join(
                    GuildBattleRegistration,
                    GuildBattleRegistration.id == GuildBattleRosterEntry.registration_id,
                )
                .where(
                    GuildBattleRosterEntry.character_id == character_id,
                    GuildBattleRegistration.status == "paired",
                )
                .limit(1)
            )
        ).first()
        return (None, None) if row is None else (row[0], row[1])

    @staticmethod
    async def _roster(session, registration_id: UUID) -> list[GuildBattleRosterEntry]:
        return list(
            (
                await session.scalars(
                    select(GuildBattleRosterEntry)
                    .where(GuildBattleRosterEntry.registration_id == registration_id)
                    .order_by(GuildBattleRosterEntry.character_id)
                )
            ).all()
        )

    @staticmethod
    async def _clear_roster(session, registration_id: UUID) -> None:
        for entry in await GuildBattleService._roster(session, registration_id):
            await session.delete(entry)
        await session.flush()

    async def _battle_rosters(self, session, battle) -> dict[str, list[GuildBattleRosterEntry]]:
        return {
            "a": await self._roster(session, battle.registration_a_id),
            "b": await self._roster(session, battle.registration_b_id),
        }

    @staticmethod
    async def _lock_battle(session, battle_id: UUID) -> GuildBattle | None:
        return await session.scalar(
            select(GuildBattle)
            .where(GuildBattle.id == battle_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    @staticmethod
    async def _lock_fight(session, fight_id: UUID) -> GuildBattleFight | None:
        return await session.scalar(
            select(GuildBattleFight)
            .where(GuildBattleFight.id == fight_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    @staticmethod
    async def _fight_members(session, fight_id: UUID) -> list[GuildBattleFightMember]:
        return list(
            (
                await session.scalars(
                    select(GuildBattleFightMember)
                    .where(GuildBattleFightMember.fight_id == fight_id)
                    .order_by(GuildBattleFightMember.actor_key)
                    .with_for_update()
                )
            ).all()
        )

    async def _lock_profile(self, session, guild_id: UUID) -> GuildBattleProfile:
        profile = await session.scalar(
            select(GuildBattleProfile)
            .where(GuildBattleProfile.guild_id == guild_id)
            .with_for_update()
        )
        if profile is None:
            profile = GuildBattleProfile(
                guild_id=guild_id,
                server_id=self.server_id,
                rating=INITIAL_RATING,
                real_battles=0,
                wins=0,
                draws=0,
                losses=0,
                byes=0,
                points=0,
            )
            session.add(profile)
            await session.flush()
        return profile
