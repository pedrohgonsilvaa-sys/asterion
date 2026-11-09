"""Duelo and Arena da Vigília (GDD v1.6.0 §13, §14, §39, §44, §49.14).

Lock order (every write follows it, which rules out deadlocks):
server advisory lock -> Characters in ascending id order -> PvpMatch -> ArenaProfiles
in ascending character id order. A path may skip a level but never go back up.
The advisory lock serialises the queue: pairing, entry, exit and the return of a
player to the queue after a cancelled Confirmation.

The Combat Configuration lock is the shared GameActivity row, read by
``combat_configuration_guard``. The Arena takes it on queue entry; the Duelo takes
it only when both sides have accepted. A match never writes ``Character.hp``, so
the world state is intact when it ends.

Linked accounts are only flagged (§36); nothing here blocks them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.active_arts import load_active_art_configuration
from asterion.application.campaign_coop import campaign_action_intent
from asterion.application.combat_configuration_guard import find_combat_configuration_blocker
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.prologue import CombatView
from asterion.application.social_graph import blocked_between, record_recent_contacts
from asterion.domain.arena import (
    AFK_CONSECUTIVE_TIMEOUTS,
    AFK_TOTAL_TIMEOUTS,
    ARENA_MIN_LEVEL,
    CONFIRMATION_TTL,
    DECAY_INACTIVITY,
    DECAY_MIN_RENOME,
    DODGE_WINDOW,
    DUEL_INVITE_TTL,
    DUEL_MIN_LEVEL,
    INITIAL_MMR,
    PLACEMENT_MATCHES,
    RECENT_REMATCH,
    SURRENDER_MIN_ROUND,
    TURN_TTL,
    decayed_renome,
    dodge_cooldown,
    elo_for,
    is_arena_window_open,
    is_pairing_compatible,
    latest_decay_boundary,
    mmr_after_match,
    placement_renome,
    renome_after_match,
)
from asterion.domain.combat import Combat, act, active_player_key, pass_turn
from asterion.domain.road import (
    RULESET,
    PlayerCombatantSpec,
    create_player_versus_player_combat,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    ArenaDodge,
    ArenaProfile,
    ArenaQueueEntry,
    Character,
    GameActivity,
    PvpMatch,
    PvpMatchMember,
)

ARENA_QUEUE_CONTENT = "arena_queue"
PVP_MATCH_CONTENT = "pvp_match"
_PVP_CONTENTS = (ARENA_QUEUE_CONTENT, PVP_MATCH_CONTENT)
# A turn overdue by more than this means the service itself was down (§43):
# the deadline is renewed instead of charging a timeout to the player.
DOWNTIME_GRACE = timedelta(seconds=60)
_SCORES = {"win": Decimal(1), "loss": Decimal(0), "draw": Decimal("0.5")}


class PvpError(ValueError):
    """A PvP action is invalid for the current, revalidated state."""

    def __init__(self, code: str, until: datetime | None = None):
        self.code = code
        self.until = until
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class DuelInviteView:
    match_id: UUID
    incoming: bool
    opponent_name: str
    opponent_level: int
    opponent_class: str
    seconds_left: int


@dataclass(frozen=True, slots=True)
class PvpHubView:
    name: str
    level: int
    renome: int
    elo: str | None
    placement_played: int
    wins: int
    losses: int
    draws: int
    window_open: bool
    blocked_until: datetime | None
    invite: DuelInviteView | None


@dataclass(frozen=True, slots=True)
class DuelPreviewView:
    character_id: UUID
    name: str
    level: int
    character_class: str


@dataclass(frozen=True, slots=True)
class QueueView:
    waited_seconds: int


@dataclass(frozen=True, slots=True)
class ConfirmationView:
    match_id: UUID
    accepted: bool
    seconds_left: int


@dataclass(frozen=True, slots=True)
class PvpCombatView:
    battle: CombatView
    match_id: UUID
    kind: str
    my_turn: bool
    seconds_left: int
    can_surrender: bool


@dataclass(frozen=True, slots=True)
class PvpResultView:
    kind: str
    outcome: str
    reason: str
    name: str
    opponent: str
    renome_before: int | None = None
    renome_after: int | None = None
    placed_before: bool | None = None
    placed_after: bool | None = None
    placement_played: int | None = None


@dataclass(frozen=True, slots=True)
class PvpMessageView:
    code: str
    until: datetime | None = None
    name: str | None = None


PvpView = (
    PvpHubView
    | DuelPreviewView
    | DuelInviteView
    | QueueView
    | ConfirmationView
    | PvpCombatView
    | PvpResultView
    | PvpMessageView
)


@dataclass(frozen=True, slots=True)
class PvpNotice:
    telegram_id: int
    view: PvpView


@dataclass(frozen=True, slots=True)
class PvpOutcome:
    view: PvpView
    notices: tuple[PvpNotice, ...] = ()


@dataclass(frozen=True, slots=True)
class RankingRow:
    position: int
    name: str
    elo: str
    renome: int


@dataclass(frozen=True, slots=True)
class RankingView:
    highlights: tuple[RankingRow, ...]
    own: RankingRow | None
    own_placement_played: int


def _utcnow(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _seconds_left(deadline: datetime | None, now: datetime) -> int:
    return 0 if deadline is None else max(0, int((deadline - now).total_seconds()))


def _is_placed(profile: ArenaProfile) -> bool:
    return profile.placement_played >= PLACEMENT_MATCHES


class PvpService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    # ----------------------------------------------------------------- views

    async def foreground(self, actor: int, *, now: datetime | None = None) -> PvpView | None:
        """The PvP activity that must be resumed, for /start and /menu (§39.4)."""
        now = _utcnow(now)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._foreground_view(session, character, now)

    async def resume(self, actor: int, *, now: datetime | None = None) -> PvpView:
        now = _utcnow(now)
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            view = await self._foreground_view(session, character, now)
            return view if view is not None else await self._hub(session, character, now)

    async def ranking(self, actor: int) -> RankingView:
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            rows = (
                await session.execute(
                    select(ArenaProfile, Character.name)
                    .join(Character, Character.id == ArenaProfile.character_id)
                    .where(
                        ArenaProfile.server_id == self.server_id,
                        ArenaProfile.placement_played >= PLACEMENT_MATCHES,
                    )
                    .order_by(ArenaProfile.renome.desc(), ArenaProfile.character_id)
                    .limit(3)
                )
            ).all()
            highlights = tuple(
                RankingRow(index, name, elo_for(profile.renome), profile.renome)
                for index, (profile, name) in enumerate(rows, start=1)
            )
            mine = await session.get(ArenaProfile, character.id)
            if mine is None or not _is_placed(mine):
                played = 0 if mine is None else mine.placement_played
                return RankingView(highlights, None, played)
            ahead = await session.scalar(
                select(func.count())
                .select_from(ArenaProfile)
                .where(
                    ArenaProfile.server_id == self.server_id,
                    ArenaProfile.placement_played >= PLACEMENT_MATCHES,
                    ArenaProfile.renome > mine.renome,
                )
            )
            return RankingView(
                highlights,
                RankingRow(int(ahead or 0) + 1, character.name, elo_for(mine.renome), mine.renome),
                mine.placement_played,
            )

    async def _hub(self, session, character: Character, now: datetime) -> PvpHubView:
        profile = await session.get(ArenaProfile, character.id)
        placed = profile is not None and _is_placed(profile)
        blocked = profile.queue_blocked_until if profile is not None else None
        return PvpHubView(
            name=character.name,
            level=character.level,
            renome=profile.renome if profile is not None else 0,
            elo=elo_for(profile.renome) if placed else None,
            placement_played=profile.placement_played if profile is not None else 0,
            wins=profile.wins if profile is not None else 0,
            losses=profile.losses if profile is not None else 0,
            draws=profile.draws if profile is not None else 0,
            window_open=is_arena_window_open(now),
            blocked_until=blocked if blocked is not None and blocked > now else None,
            invite=await self._open_invite(session, character, now),
        )

    async def _open_invite(
        self, session, character: Character, now: datetime
    ) -> DuelInviteView | None:
        row = (
            await session.execute(
                select(PvpMatch, PvpMatchMember)
                .join(PvpMatchMember, PvpMatchMember.match_id == PvpMatch.id)
                .where(
                    PvpMatchMember.character_id == character.id,
                    PvpMatch.kind == "duel",
                    PvpMatch.status == "invited",
                    PvpMatch.deadline_at > now,
                )
                .limit(1)
            )
        ).first()
        if row is None:
            return None
        match, member = row
        opponent = await session.scalar(
            select(Character)
            .join(PvpMatchMember, PvpMatchMember.character_id == Character.id)
            .where(PvpMatchMember.match_id == match.id, Character.id != character.id)
        )
        if opponent is None:
            return None
        return self._invite_view(match, not member.is_challenger, opponent, now)

    @staticmethod
    def _invite_view(
        match: PvpMatch, incoming: bool, opponent: Character, now: datetime
    ) -> DuelInviteView:
        return DuelInviteView(
            match.id,
            incoming,
            opponent.name,
            opponent.level,
            opponent.character_class,
            _seconds_left(match.deadline_at, now),
        )

    async def _foreground_view(self, session, character: Character, now: datetime):
        activity = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
                GameActivity.content_id.in_(_PVP_CONTENTS),
            )
        )
        if activity is None:
            return None
        row = (
            await session.execute(
                select(PvpMatch, PvpMatchMember)
                .join(PvpMatchMember, PvpMatchMember.match_id == PvpMatch.id)
                .where(
                    PvpMatchMember.game_activity_id == activity.id,
                    PvpMatch.status.in_(("confirming", "active")),
                )
                .limit(1)
            )
        ).first()
        if row is None:
            entry = await session.scalar(
                select(ArenaQueueEntry).where(
                    ArenaQueueEntry.game_activity_id == activity.id,
                    ArenaQueueEntry.status == "waiting",
                )
            )
            waited = 0 if entry is None else int((now - entry.entered_at).total_seconds())
            return QueueView(max(0, waited))
        match, member = row
        if match.status == "confirming":
            return ConfirmationView(
                match.id, member.accepted_at is not None, _seconds_left(match.deadline_at, now)
            )
        return self._combat_view(character, activity.id, match, member, self._decode(match), now)

    @staticmethod
    def _decode(match: PvpMatch) -> Combat:
        return decode(
            match.combat_snapshot, match.combat_id, match.ruleset_version, match.state_version
        )

    @staticmethod
    def _combat_view(
        character: Character,
        activity_id: UUID,
        match: PvpMatch,
        member: PvpMatchMember,
        combat: Combat,
        now: datetime,
    ) -> PvpCombatView:
        battle = CombatView(
            activity_id,
            match.id,
            character.id,
            combat,
            "pvp",
            0,
            context=f"pvp_{match.kind}",
            combat_actor_key=member.actor_key,
        )
        return PvpCombatView(
            battle,
            match.id,
            match.kind,
            active_player_key(combat) == member.actor_key,
            _seconds_left(match.deadline_at, now),
            combat.round >= SURRENDER_MIN_ROUND,
        )

    # ----------------------------------------------------------------- arena

    async def enter_queue(self, actor: int, *, now: datetime | None = None) -> PvpOutcome:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            await self._queue_lock(session)
            character = await self._lock_actor(session, actor)
            current = await self._foreground_view(session, character, now)
            if current is not None:
                return PvpOutcome(current)
            if character.level < ARENA_MIN_LEVEL:
                raise PvpError("arena_level")
            if not is_arena_window_open(now):
                raise PvpError("window_closed")
            profile = await self._profile(session, character)
            if profile.queue_blocked_until is not None and profile.queue_blocked_until > now:
                raise PvpError("queue_blocked", profile.queue_blocked_until)
            if await find_combat_configuration_blocker(session, character.id) is not None:
                raise PvpError("busy")
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            activity = self._new_activity(character, ARENA_QUEUE_CONTENT, now)
            session.add(activity)
            await session.flush()
            entry = ArenaQueueEntry(
                id=uuid4(),
                server_id=self.server_id,
                character_id=character.id,
                account_id=character.telegram_id,
                game_activity_id=activity.id,
                level=character.level,
                mmr=profile.mmr,
                configuration_snapshot=equipment.to_data(RULESET)
                | {"active_arts": [slot.to_data() for slot in arts.slots]},
                status="waiting",
                entered_at=now,
            )
            session.add(entry)
            await session.flush()
            notices = await self._pair_waiting(session, now)
            view = await self._foreground_view(session, character, now)
            return PvpOutcome(
                view,
                tuple(item for item in notices if item.telegram_id != actor),
            )

    async def leave_queue(self, actor: int, *, now: datetime | None = None) -> PvpOutcome:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            await self._queue_lock(session)
            character = await self._require_character(session, actor)
            entry = await session.scalar(
                select(ArenaQueueEntry)
                .where(
                    ArenaQueueEntry.character_id == character.id,
                    ArenaQueueEntry.status == "waiting",
                )
                .with_for_update()
            )
            if entry is not None:
                await self._close_entry(session, entry, "left", now)
            view = await self._foreground_view(session, character, now)
            if view is None:
                view = await self._hub(session, character, now)
            return PvpOutcome(view)

    async def accept(
        self, actor: int, match_id: UUID, *, now: datetime | None = None
    ) -> PvpOutcome:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character_ids = list(
                (
                    await session.scalars(
                        select(PvpMatchMember.character_id)
                        .where(PvpMatchMember.match_id == match_id)
                        .order_by(PvpMatchMember.character_id)
                    )
                ).all()
            )
            characters = await self._lock_characters(session, character_ids)
            match = await self._lock_match(session, match_id)
            character = next((row for row in characters if row.telegram_id == actor), None)
            if match is None or character is None:
                raise PvpError("not_found")
            members = await self._members(session, match.id)
            member = next(row for row in members if row.character_id == character.id)
            if match.status == "invited" and match.kind == "duel" and not member.is_challenger:
                if await blocked_between(
                    session, characters[0].id, characters[-1].id
                ):
                    raise PvpError("expired")
                return await self._accept_duel(session, match, members, characters, character, now)
            if match.status != "confirming":
                raise PvpError("expired")
            if match.deadline_at is not None and now >= match.deadline_at:
                raise PvpError("expired")
            member.accepted_at = member.accepted_at or now
            if all(row.accepted_at is not None for row in members):
                return await self._start_match(session, match, members, characters, now, actor)
            await session.flush()
            view = await self._foreground_view(session, character, now)
            return PvpOutcome(view)

    async def decline(
        self, actor: int, match_id: UUID, *, now: datetime | None = None
    ) -> PvpOutcome:
        """Refuse or cancel a Duelo invite, or refuse an Entry Confirmation."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            await self._queue_lock(session)
            character = await self._require_character(session, actor)
            match = await self._lock_match(session, match_id)
            if match is None:
                raise PvpError("not_found")
            members = await self._members(session, match.id)
            member = next((row for row in members if row.character_id == character.id), None)
            if member is None:
                raise PvpError("not_found")
            if match.status == "invited":
                other = next(row for row in members if row.character_id != character.id)
                match.status = "cancelled"
                match.finished_at = now
                match.deadline_at = None
                return PvpOutcome(
                    await self._hub(session, character, now),
                    (
                        PvpNotice(
                            other.account_id, PvpMessageView("duel_declined", name=character.name)
                        ),
                    ),
                )
            if match.status != "confirming":
                raise PvpError("expired")
            notices = await self._cancel_confirmation(session, match, members, {character.id}, now)
            notices += await self._pair_waiting(session, now)
            own = next((item for item in notices if item.telegram_id == actor), None)
            view = own.view if own is not None else await self._hub(session, character, now)
            return PvpOutcome(view, tuple(item for item in notices if item.telegram_id != actor))

    async def _pair_waiting(self, session, now: datetime) -> list[PvpNotice]:
        if not is_arena_window_open(now):
            return []
        entries = list(
            (
                await session.scalars(
                    select(ArenaQueueEntry)
                    .where(
                        ArenaQueueEntry.server_id == self.server_id,
                        ArenaQueueEntry.status == "waiting",
                    )
                    .order_by(ArenaQueueEntry.entered_at, ArenaQueueEntry.id)
                    .with_for_update()
                )
            ).all()
        )
        if len(entries) < 2:
            return []
        recent = await self._recent_pairs(session, now)
        used: set[UUID] = set()
        notices: list[PvpNotice] = []
        for index, first in enumerate(entries):
            if first.id in used:
                continue
            waited = (now - first.entered_at).total_seconds()
            candidates = [
                second
                for second in entries[index + 1 :]
                if second.id not in used
                and second.account_id != first.account_id
                and is_pairing_compatible(
                    waited_seconds=waited,
                    first_mmr=first.mmr,
                    first_level=first.level,
                    second_mmr=second.mmr,
                    second_level=second.level,
                )
            ]
            if not candidates:
                continue
            best = min(
                candidates,
                key=lambda second: (
                    frozenset((first.account_id, second.account_id)) in recent,
                    abs(first.mmr - second.mmr),
                    abs(first.level - second.level),
                    second.entered_at,
                ),
            )
            used.update((first.id, best.id))
            notices.extend(await self._open_confirmation(session, first, best, now))
        return notices

    async def _recent_pairs(self, session, now: datetime) -> set[frozenset[int]]:
        rows = (
            await session.execute(
                select(PvpMatchMember.match_id, PvpMatchMember.account_id)
                .join(PvpMatch, PvpMatch.id == PvpMatchMember.match_id)
                .where(
                    PvpMatch.server_id == self.server_id,
                    PvpMatch.kind == "arena",
                    PvpMatch.status == "finished",
                    PvpMatch.finished_at > now - RECENT_REMATCH,
                )
            )
        ).all()
        by_match: dict[UUID, list[int]] = {}
        for match_id, account_id in rows:
            by_match.setdefault(match_id, []).append(account_id)
        return {frozenset(accounts) for accounts in by_match.values()}

    async def _open_confirmation(
        self, session, first: ArenaQueueEntry, second: ArenaQueueEntry, now: datetime
    ) -> list[PvpNotice]:
        match = PvpMatch(
            id=uuid4(),
            server_id=self.server_id,
            kind="arena",
            status="confirming",
            deadline_at=now + CONFIRMATION_TTL,
            created_at=now,
            state_version=0,
        )
        session.add(match)
        await session.flush()
        notices = []
        for side, entry in (("a", first), ("b", second)):
            entry.status = "matched"
            session.add(
                PvpMatchMember(
                    match_id=match.id,
                    character_id=entry.character_id,
                    account_id=entry.account_id,
                    side=side,
                    actor_key=f"{side}1",
                    is_challenger=False,
                    game_activity_id=entry.game_activity_id,
                    queue_entry_id=entry.id,
                    consecutive_timeouts=0,
                    total_timeouts=0,
                )
            )
            notices.append(
                PvpNotice(
                    entry.account_id,
                    ConfirmationView(match.id, False, int(CONFIRMATION_TTL.total_seconds())),
                )
            )
        await session.flush()
        return notices

    async def _cancel_confirmation(
        self, session, match, members, dodgers: set[UUID], now: datetime
    ) -> list[PvpNotice]:
        """Dissolve a pairing. Whoever did not dodge goes back to the queue."""
        match.status = "cancelled"
        match.finished_at = now
        match.deadline_at = None
        notices: list[PvpNotice] = []
        window_open = is_arena_window_open(now)
        for member in sorted(members, key=lambda row: row.character_id):
            entry = await session.get(ArenaQueueEntry, member.queue_entry_id)
            if entry is None:
                continue
            if member.character_id in dodgers:
                session.add(
                    ArenaDodge(
                        id=uuid4(),
                        character_id=member.character_id,
                        match_id=match.id,
                        occurred_at=now,
                    )
                )
                await session.flush()
                count = await session.scalar(
                    select(func.count())
                    .select_from(ArenaDodge)
                    .where(
                        ArenaDodge.character_id == member.character_id,
                        ArenaDodge.occurred_at > now - DODGE_WINDOW,
                    )
                )
                until = None
                cooldown = dodge_cooldown(int(count or 1))
                if cooldown > timedelta(0):
                    until = now + cooldown
                    profile = await self._lock_profile(session, member.character_id)
                    if profile is not None:
                        profile.queue_blocked_until = until
                await self._close_entry(session, entry, "left", now)
                notices.append(PvpNotice(member.account_id, PvpMessageView("dodged", until)))
            elif window_open:
                entry.status = "waiting"
                notices.append(PvpNotice(member.account_id, PvpMessageView("requeued")))
            else:
                await self._close_entry(session, entry, "released", now)
                notices.append(PvpNotice(member.account_id, PvpMessageView("queue_released")))
        return notices

    async def _close_entry(
        self, session, entry: ArenaQueueEntry, status: str, now: datetime
    ) -> None:
        entry.status = status
        entry.resolved_at = now
        activity = await session.get(GameActivity, entry.game_activity_id)
        if activity is not None and activity.status == "active":
            activity.status = "completed"
            activity.last_valid_action_at = now

    # ----------------------------------------------------------------- duelo

    async def duel_preview(self, actor: int, target_name: str) -> DuelPreviewView:
        """Show level and Class before the challenge is sent (§14.2)."""
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            target = await self._find_by_name(session, target_name)
            if target is None:
                raise PvpError("target_not_found")
            self._check_duel_pair(character, target)
            return DuelPreviewView(target.id, target.name, target.level, target.character_class)

    async def challenge(
        self, actor: int, target_id: UUID, *, now: datetime | None = None
    ) -> PvpOutcome:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            actor_id = await session.scalar(
                select(Character.id).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if actor_id is None:
                raise PvpError("no_character")
            characters = await self._lock_characters(session, sorted({actor_id, target_id}))
            by_id = {row.id: row for row in characters}
            character, target = by_id[actor_id], by_id.get(target_id)
            if target is None or target.server_id != self.server_id:
                raise PvpError("target_not_found")
            self._check_duel_pair(character, target)
            # Author decision 2026-11-08: a Duel challenge is a direct invite.
            if await blocked_between(session, character.id, target.id):
                raise PvpError("opponent_busy")
            if await find_combat_configuration_blocker(session, character.id) is not None:
                raise PvpError("busy")
            if await find_combat_configuration_blocker(session, target.id) is not None:
                raise PvpError("opponent_busy")
            for row in (character, target):
                if await self._open_invite(session, row, now) is not None:
                    raise PvpError("invite_open" if row is character else "opponent_busy")
            match = PvpMatch(
                id=uuid4(),
                server_id=self.server_id,
                kind="duel",
                status="invited",
                deadline_at=now + DUEL_INVITE_TTL,
                created_at=now,
                state_version=0,
            )
            session.add(match)
            await session.flush()
            for side, row, challenger in (("a", character, True), ("b", target, False)):
                session.add(
                    PvpMatchMember(
                        match_id=match.id,
                        character_id=row.id,
                        account_id=row.telegram_id,
                        side=side,
                        actor_key=f"{side}1",
                        is_challenger=challenger,
                        consecutive_timeouts=0,
                        total_timeouts=0,
                    )
                )
            await session.flush()
            return PvpOutcome(
                self._invite_view(match, False, target, now),
                (PvpNotice(target.telegram_id, self._invite_view(match, True, character, now)),),
            )

    @staticmethod
    def _check_duel_pair(character: Character, target: Character) -> None:
        if character.id == target.id or character.telegram_id == target.telegram_id:
            raise PvpError("duel_self")
        if character.level < DUEL_MIN_LEVEL:
            raise PvpError("duel_level")
        if target.level < DUEL_MIN_LEVEL:
            raise PvpError("opponent_level")

    async def _accept_duel(self, session, match, members, characters, character, now):
        if match.deadline_at is not None and now >= match.deadline_at:
            raise PvpError("expired")
        for row in characters:
            if await find_combat_configuration_blocker(session, row.id) is not None:
                raise PvpError("busy" if row is character else "opponent_busy")
        for member in members:
            row = next(item for item in characters if item.id == member.character_id)
            activity = self._new_activity(row, PVP_MATCH_CONTENT, now)
            session.add(activity)
            await session.flush()
            member.game_activity_id = activity.id
            member.accepted_at = now
        return await self._start_match(
            session, match, members, characters, now, character.telegram_id
        )

    # ---------------------------------------------------------------- combat

    async def _start_match(self, session, match, members, characters, now, actor) -> PvpOutcome:
        by_id = {row.id: row for row in characters}
        specs: dict[str, PlayerCombatantSpec] = {}
        for member in members:
            character = by_id[member.character_id]
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            specs[member.side] = PlayerCombatantSpec(
                fighter_key=member.actor_key,
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
        combat = create_player_versus_player_combat(
            uuid4(),
            (specs["a"],),
            (specs["b"],),
            ruleset_version=RULESET,
            flavor="",
            opening_log="⚔️ O combate começa.",
            full_hp=True,
        )
        match.status = "active"
        match.combat_id = combat.id
        match.ruleset_version = RULESET
        match.started_at = now
        self._store_combat(match, combat, now)
        await session.flush()
        await self._sync_activities(session, match, members, combat, now, content=True)
        await record_recent_contacts(session, [row.id for row in characters], now)
        await record_linked_cooccurrence(
            session,
            server_id=self.server_id,
            activity_kind="arena_match" if match.kind == "arena" else "duel",
            activity_reference=f"pvp:{match.id.hex}",
            characters=characters,
            now=now,
        )
        return self._combat_outcome(match, members, by_id, combat, now, actor)

    @staticmethod
    def _store_combat(match: PvpMatch, combat: Combat, now: datetime) -> None:
        match.combat_snapshot = encode(combat)
        match.state_version = combat.version
        match.deadline_at = now + TURN_TTL

    async def _sync_activities(self, session, match, members, combat, now, *, content=False):
        for member in members:
            activity = await session.get(GameActivity, member.game_activity_id)
            if activity is None:
                continue
            activity.state_version = combat.version
            activity.last_valid_action_at = now
            if content:
                activity.content_id = PVP_MATCH_CONTENT
                activity.ruleset_version = match.ruleset_version

    def _combat_outcome(self, match, members, by_id, combat, now, actor) -> PvpOutcome:
        views = {
            member.account_id: self._combat_view(
                by_id[member.character_id],
                member.game_activity_id,
                match,
                member,
                combat,
                now,
            )
            for member in members
        }
        notices = tuple(
            PvpNotice(telegram_id, view)
            for telegram_id, view in views.items()
            if telegram_id != actor
        )
        return PvpOutcome(views.get(actor, next(iter(views.values()))), notices)

    async def action(
        self,
        actor: int,
        match_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
        *,
        now: datetime | None = None,
    ) -> PvpOutcome:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            match, members, by_id, member, character = await self._match_context(
                session, actor, match_id
            )
            if match.status != "active" or member is None:
                return PvpOutcome(await self._after_match(session, character, now))
            combat = self._decode(match)
            current = PvpOutcome(
                self._combat_view(character, member.game_activity_id, match, member, combat, now)
            )
            if version != match.state_version or active_player_key(combat) != member.actor_key:
                return current
            intent = campaign_action_intent(combat, member.actor_key, action_index, target_code)
            if intent is None:
                return current
            chosen, target = intent
            updated = act(combat, chosen, target_id=target, actor_key=member.actor_key)
            if updated.version == combat.version:
                return current
            member.consecutive_timeouts = 0
            return await self._advance(session, match, members, by_id, updated, now, actor)

    async def _advance(self, session, match, members, by_id, combat, now, actor) -> PvpOutcome:
        self._store_combat(match, combat, now)
        await self._sync_activities(session, match, members, combat, now)
        if combat.result:
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
            return await self._settle(session, match, members, by_id, winner, "combat", now, actor)
        return self._combat_outcome(match, members, by_id, combat, now, actor)

    async def surrender(
        self, actor: int, match_id: UUID, *, now: datetime | None = None
    ) -> PvpOutcome:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            match, members, by_id, member, character = await self._match_context(
                session, actor, match_id
            )
            if match.status != "active" or member is None:
                return PvpOutcome(await self._after_match(session, character, now))
            if self._decode(match).round < SURRENDER_MIN_ROUND:
                raise PvpError("surrender_round")
            winner = "b" if member.side == "a" else "a"
            return await self._settle(
                session, match, members, by_id, winner, "surrender", now, actor
            )

    async def _match_context(self, session, actor, match_id):
        match = await self._lock_match(session, match_id)
        character = await self._require_character(session, actor)
        if match is None:
            raise PvpError("not_found")
        members = await self._members(session, match.id)
        by_id = {
            row.id: row
            for row in (
                await session.scalars(
                    select(Character).where(
                        Character.id.in_([member.character_id for member in members])
                    )
                )
            ).all()
        }
        member = next((row for row in members if row.character_id == character.id), None)
        return match, members, by_id, member, character

    async def _after_match(self, session, character, now):
        view = await self._foreground_view(session, character, now)
        return view if view is not None else await self._hub(session, character, now)

    async def _settle(self, session, match, members, by_id, winner, reason, now, actor=None):
        match.status = "finished"
        match.winner_side = winner
        match.end_reason = reason
        match.finished_at = now
        match.deadline_at = None
        for member in members:
            activity = await session.get(GameActivity, member.game_activity_id)
            if activity is not None:
                activity.status = "completed"
                activity.last_valid_action_at = now
            if member.queue_entry_id is not None:
                entry = await session.get(ArenaQueueEntry, member.queue_entry_id)
                if entry is not None:
                    entry.status = "released"
                    entry.resolved_at = now
        if match.kind == "arena":
            await self._apply_ratings(session, members, winner, now)
        await session.flush()
        results = {
            member.account_id: self._result_view(match, member, members, by_id, reason)
            for member in members
        }
        own = results.get(actor) if actor is not None else None
        notices = tuple(
            PvpNotice(telegram_id, view)
            for telegram_id, view in results.items()
            if telegram_id != actor
        )
        return PvpOutcome(own if own is not None else next(iter(results.values())), notices)

    async def _apply_ratings(self, session, members, winner, now) -> None:
        ordered = sorted(members, key=lambda row: row.character_id)
        profiles = {}
        for member in ordered:
            profile = await self._lock_profile(session, member.character_id)
            if profile is None:
                profile = ArenaProfile(
                    character_id=member.character_id,
                    server_id=self.server_id,
                    renome=0,
                    mmr=INITIAL_MMR,
                    placement_played=0,
                    placement_wins=0,
                    matches_played=0,
                    wins=0,
                    losses=0,
                    draws=0,
                )
                session.add(profile)
                await session.flush()
            profiles[member.character_id] = profile
        before = {
            character_id: (
                profile.renome if _is_placed(profile) else placement_renome(profile.placement_wins),
                profile.mmr,
            )
            for character_id, profile in profiles.items()
        }
        for member in ordered:
            profile = profiles[member.character_id]
            other = next(row for row in ordered if row.character_id != member.character_id)
            opponent_renome, opponent_mmr = before[other.character_id]
            result = "draw" if winner is None else "win" if winner == member.side else "loss"
            score = _SCORES[result]
            placed = _is_placed(profile)
            member.renome_before = profile.renome
            member.placed_before = placed
            if placed:
                profile.renome = renome_after_match(profile.renome, opponent_renome, score)
            else:
                profile.placement_played += 1
                profile.placement_wins += 1 if result == "win" else 0
                if _is_placed(profile):
                    profile.renome = placement_renome(profile.placement_wins)
            profile.mmr = mmr_after_match(
                before[member.character_id][1], opponent_mmr, score, profile.matches_played
            )
            profile.matches_played += 1
            profile.wins += 1 if result == "win" else 0
            profile.losses += 1 if result == "loss" else 0
            profile.draws += 1 if result == "draw" else 0
            profile.last_match_at = now
            member.renome_after = profile.renome
            member.placed_after = _is_placed(profile)
            member.placement_played_after = profile.placement_played

    @staticmethod
    def _result_view(match, member, members, by_id, reason) -> PvpResultView:
        other = next(row for row in members if row.character_id != member.character_id)
        outcome = (
            "draw"
            if match.winner_side is None
            else "win"
            if match.winner_side == member.side
            else "loss"
        )
        return PvpResultView(
            kind=match.kind,
            outcome=outcome,
            reason=reason,
            name=by_id[member.character_id].name,
            opponent=by_id[other.character_id].name,
            renome_before=member.renome_before,
            renome_after=member.renome_after,
            placed_before=member.placed_before,
            placed_after=member.placed_after,
            placement_played=member.placement_played_after,
        )

    # ----------------------------------------------------------------- sweep

    async def run_maintenance(
        self, *, now: datetime | None = None, limit: int = 100
    ) -> list[PvpNotice]:
        """Expire deadlines, release the queue, pair and apply decay."""
        now = _utcnow(now)
        notices: list[PvpNotice] = []
        for status, handler in (
            ("invited", self._expire_invite),
            ("confirming", self._expire_confirmation),
            ("active", self._resolve_turn_timeout),
        ):
            async with self.sessions() as session:
                due = (
                    await session.scalars(
                        select(PvpMatch.id)
                        .where(
                            PvpMatch.server_id == self.server_id,
                            PvpMatch.status == status,
                            PvpMatch.deadline_at <= now,
                        )
                        .order_by(PvpMatch.deadline_at)
                        .limit(limit)
                    )
                ).all()
            for match_id in due:
                notices.extend(await handler(match_id, now))
        async with self.sessions.begin() as session:
            await self._queue_lock(session)
            if is_arena_window_open(now):
                notices.extend(await self._pair_waiting(session, now))
            else:
                notices.extend(await self._release_queue(session, now))
        await self._apply_decay(now, limit)
        return notices

    async def _expire_invite(self, match_id: UUID, now: datetime) -> list[PvpNotice]:
        async with self.sessions.begin() as session:
            match = await self._lock_match(session, match_id)
            if match is None or match.status != "invited" or match.deadline_at > now:
                return []
            match.status = "cancelled"
            match.finished_at = now
            match.deadline_at = None
            members = await self._members(session, match.id)
            return [
                PvpNotice(member.account_id, PvpMessageView("duel_expired")) for member in members
            ]

    async def _expire_confirmation(self, match_id: UUID, now: datetime) -> list[PvpNotice]:
        async with self.sessions.begin() as session:
            await self._queue_lock(session)
            match = await self._lock_match(session, match_id)
            if match is None or match.status != "confirming" or match.deadline_at > now:
                return []
            members = await self._members(session, match.id)
            dodgers = {row.character_id for row in members if row.accepted_at is None}
            return await self._cancel_confirmation(session, match, members, dodgers, now)

    async def _resolve_turn_timeout(self, match_id: UUID, now: datetime) -> list[PvpNotice]:
        async with self.sessions.begin() as session:
            match = await self._lock_match(session, match_id)
            if match is None or match.status != "active" or match.deadline_at > now:
                return []
            if now - match.deadline_at > DOWNTIME_GRACE:
                match.deadline_at = now + TURN_TTL
                return []
            members = await self._members(session, match.id)
            by_id = {
                row.id: row
                for row in (
                    await session.scalars(
                        select(Character).where(
                            Character.id.in_([member.character_id for member in members])
                        )
                    )
                ).all()
            }
            combat = self._decode(match)
            actor_key = active_player_key(combat)
            member = next((row for row in members if row.actor_key == actor_key), None)
            if member is None:
                return []
            member.consecutive_timeouts += 1
            member.total_timeouts += 1
            if (
                member.consecutive_timeouts >= AFK_CONSECUTIVE_TIMEOUTS
                or member.total_timeouts >= AFK_TOTAL_TIMEOUTS
            ):
                winner = "b" if member.side == "a" else "a"
                outcome = await self._settle(session, match, members, by_id, winner, "afk", now)
            else:
                outcome = await self._advance(
                    session, match, members, by_id, pass_turn(combat, member.actor_key), now, None
                )
            return list(outcome.notices)

    async def _release_queue(self, session, now: datetime) -> list[PvpNotice]:
        """Window closed: unmatched queue leaves with no penalty (§14.3)."""
        entries = (
            await session.scalars(
                select(ArenaQueueEntry)
                .where(
                    ArenaQueueEntry.server_id == self.server_id,
                    ArenaQueueEntry.status == "waiting",
                )
                .order_by(ArenaQueueEntry.id)
                .with_for_update()
            )
        ).all()
        notices = []
        for entry in entries:
            await self._close_entry(session, entry, "released", now)
            notices.append(PvpNotice(entry.account_id, PvpMessageView("queue_released")))
        return notices

    async def _apply_decay(self, now: datetime, limit: int) -> int:
        boundary = latest_decay_boundary(now)
        async with self.sessions.begin() as session:
            profiles = (
                await session.scalars(
                    select(ArenaProfile)
                    .where(
                        ArenaProfile.server_id == self.server_id,
                        ArenaProfile.renome >= DECAY_MIN_RENOME,
                        ArenaProfile.last_match_at <= boundary - DECAY_INACTIVITY,
                        (ArenaProfile.last_decay_at.is_(None))
                        | (ArenaProfile.last_decay_at < boundary),
                    )
                    .order_by(ArenaProfile.character_id)
                    .limit(limit)
                    .with_for_update()
                )
            ).all()
            for profile in profiles:
                profile.renome = decayed_renome(profile.renome)
                profile.last_decay_at = now
            return len(profiles)

    # --------------------------------------------------------------- helpers

    def _new_activity(self, character: Character, content: str, now: datetime) -> GameActivity:
        return GameActivity(
            id=uuid4(),
            character_id=character.id,
            content_id=content,
            status="active",
            state_version=0,
            ruleset_version=RULESET,
            last_valid_action_at=now,
        )

    async def _queue_lock(self, session) -> None:
        raw = int.from_bytes(sha256(f"arena:{self.server_id}".encode()).digest()[:8], "big")
        key = raw - (1 << 64) if raw >= (1 << 63) else raw
        await session.execute(select(func.pg_advisory_xact_lock(key)))

    async def _character(self, session, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _require_character(self, session, actor: int) -> Character:
        character = await self._character(session, actor)
        if character is None:
            raise PvpError("no_character")
        return character

    async def _lock_actor(self, session, actor: int) -> Character:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if character is None:
            raise PvpError("no_character")
        return character

    async def _lock_characters(self, session, character_ids) -> list[Character]:
        if not character_ids:
            return []
        return list(
            (
                await session.scalars(
                    select(Character)
                    .where(Character.id.in_(list(character_ids)))
                    .order_by(Character.id)
                    .with_for_update()
                )
            ).all()
        )

    async def _lock_match(self, session, match_id: UUID) -> PvpMatch | None:
        return await session.scalar(
            select(PvpMatch)
            .where(PvpMatch.id == match_id, PvpMatch.server_id == self.server_id)
            .with_for_update()
        )

    async def _members(self, session, match_id: UUID) -> list[PvpMatchMember]:
        return list(
            (
                await session.scalars(
                    select(PvpMatchMember)
                    .where(PvpMatchMember.match_id == match_id)
                    .order_by(PvpMatchMember.character_id)
                    .with_for_update()
                )
            ).all()
        )

    async def _lock_profile(self, session, character_id: UUID) -> ArenaProfile | None:
        return await session.scalar(
            select(ArenaProfile).where(ArenaProfile.character_id == character_id).with_for_update()
        )

    async def _profile(self, session, character: Character) -> ArenaProfile:
        profile = await self._lock_profile(session, character.id)
        if profile is None:
            profile = ArenaProfile(
                character_id=character.id,
                server_id=self.server_id,
                renome=0,
                mmr=INITIAL_MMR,
                placement_played=0,
                placement_wins=0,
                matches_played=0,
                wins=0,
                losses=0,
                draws=0,
            )
            session.add(profile)
            await session.flush()
        return profile

    async def _find_by_name(self, session, name: str) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.server_id == self.server_id,
                func.lower(Character.name) == name.strip().casefold(),
            )
        )
