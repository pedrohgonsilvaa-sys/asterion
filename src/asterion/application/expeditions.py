"""Expedição assíncrona (GDD v1.6.0 §22.2, §49.15).

Background Commitment: it never creates a ``GameActivity`` and so never locks the
Combat Configuration (§22.2).

Lock order: Guild -> Expedition -> ExpeditionMember, and Character -> ExpeditionMember
when paying. A finished Expedição is settled one Character per transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.engagement import grant_bundle
from asterion.application.guild_upkeep import record_treasury
from asterion.domain.expeditions import (
    DEFAULT_POINTS,
    DURATION,
    EXPEDITION_ROUTE_CATALOG,
    QUALITY_POINTS,
    ROSTER_MAX,
    ROSTER_MIN,
    RULESET,
    STAGE_COUNT,
    ExpeditionResult,
    ExpeditionRoute,
    final_score,
    is_eligible,
    next_start,
    result_for,
    reward_bundle,
    route_for_start,
    stage_at,
    stage_ends_at,
    treasury_reward,
    week_key,
)
from asterion.domain.guilds import GuildRole
from asterion.domain.oaths import region_for_level
from asterion.infrastructure.db.models import (
    Character,
    Expedition,
    ExpeditionChoice,
    ExpeditionMember,
    Guild,
    GuildMember,
)


class ExpeditionError(ValueError):
    """An Expedição action is invalid for the current, revalidated state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ExpeditionRosterEntry:
    character_id: UUID
    name: str
    level: int
    selected: bool


@dataclass(frozen=True, slots=True)
class ExpeditionOptionView:
    index: int
    label: str
    chosen: bool
    description: str = ""


@dataclass(frozen=True, slots=True)
class ExpeditionHubView:
    catalog_empty: bool = False
    guild_name: str | None = None
    can_manage: bool = False
    status: str = "none"  # none | forming | active
    expedition_id: UUID | None = None
    route_name: str | None = None
    starts_at: datetime | None = None
    roster: tuple[ExpeditionRosterEntry, ...] = ()
    roster_count: int = 0
    in_roster: bool = False
    stage: int = 0
    stage_ends: datetime | None = None
    stage_flavor: str | None = None
    options: tuple[ExpeditionOptionView, ...] = ()
    answered: bool = False
    has_last_result: bool = False
    notice: str | None = None


@dataclass(frozen=True, slots=True)
class ExpeditionRewardItem:
    name: str
    quantity: int


@dataclass(frozen=True, slots=True)
class ExpeditionResultView:
    """UI §48.5."""

    route_name: str
    result: ExpeditionResult
    score: int
    flavor: str
    treasury: int
    in_roster: bool
    eligible: bool
    crowns: int = 0
    items: tuple[ExpeditionRewardItem, ...] = ()


@dataclass(frozen=True, slots=True)
class ExpeditionStageNotice:
    route_name: str
    stage: int


ExpeditionView = ExpeditionHubView | ExpeditionResultView


@dataclass(frozen=True, slots=True)
class ExpeditionNotice:
    telegram_id: int
    view: ExpeditionResultView | ExpeditionStageNotice


def _utcnow(now: datetime | None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return current.astimezone(UTC)


class ExpeditionService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        catalog: tuple[ExpeditionRoute, ...] = EXPEDITION_ROUTE_CATALOG,
    ):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id
        self.catalog = catalog
        self._by_id = {route.route_id: route for route in catalog}

    # ---------------------------------------------------------------- reading

    async def hub(
        self, actor: int, *, now: datetime | None = None, notice: str | None = None
    ) -> ExpeditionHubView:
        now = _utcnow(now)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return await self._hub_view(session, character, now, notice)

    async def last_result(self, actor: int) -> ExpeditionView:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            found = (
                await session.execute(
                    select(Expedition, ExpeditionMember)
                    .join(ExpeditionMember, ExpeditionMember.expedition_id == Expedition.id)
                    .where(
                        ExpeditionMember.character_id == character.id,
                        ExpeditionMember.settled_at.is_not(None),
                    )
                    .order_by(ExpeditionMember.settled_at.desc())
                    .limit(1)
                )
            ).first()
            if found is None:
                return await self._hub_view(
                    session, character, _utcnow(None), "Ainda não há resultado de Expedição."
                )
            return self._result_view(found[0], found[1])

    # ---------------------------------------------------------------- actions

    async def toggle_roster(
        self, actor: int, character_id: UUID, *, now: datetime | None = None
    ) -> ExpeditionHubView:
        """Leader or Officer adds or removes a member until Monday 18:00."""
        now = _utcnow(now)
        if not self.catalog:
            raise ExpeditionError("catalog_empty")
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            membership = await session.get(GuildMember, character.id)
            if membership is None:
                raise ExpeditionError("no_guild")
            if membership.role not in (GuildRole.LEADER.value, GuildRole.OFFICER.value):
                raise ExpeditionError("not_manager")
            guild = await self._lock_guild(session, membership.guild_id)
            if guild.status != "active" or guild.dissolution_due_at is not None:
                raise ExpeditionError("guild_dissolving")
            target = await session.get(GuildMember, character_id)
            if target is None or target.guild_id != guild.id:
                raise ExpeditionError("not_member")
            running = await self._active(session, guild.id)
            if running is not None:
                raise ExpeditionError("already_active")
            expedition = await self._forming(session, guild, now)
            row = await session.get(ExpeditionMember, (expedition.id, character_id))
            if row is not None:
                await session.delete(row)
            else:
                rows = await self._roster(session, expedition.id)
                if len(rows) >= ROSTER_MAX:
                    raise ExpeditionError("roster_full")
                session.add(
                    ExpeditionMember(
                        expedition_id=expedition.id,
                        character_id=character_id,
                        ordinal=max((item.ordinal for item in rows), default=-1) + 1,
                    )
                )
            await session.flush()
            return await self._hub_view(session, character, now, None)

    async def choose(
        self,
        actor: int,
        expedition_id: UUID,
        stage: int,
        option_index: int,
        *,
        now: datetime | None = None,
    ) -> ExpeditionHubView:
        """§49.15: one choice per member and stage; the first one stands."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            expedition = await session.get(Expedition, expedition_id)
            if expedition is None or expedition.server_id != self.server_id:
                raise ExpeditionError("not_found")
            member = await session.get(ExpeditionMember, (expedition.id, character.id))
            if member is None:
                raise ExpeditionError("not_in_roster")
            if expedition.status != "active" or stage_at(expedition.starts_at, now) != stage:
                raise ExpeditionError("stage_closed")
            route = self._by_id.get(expedition.route_id)
            if route is None or not 0 <= option_index < len(route.stage(stage).options):
                raise ExpeditionError("not_found")
            option = route.stage(stage).options[option_index]
            inserted = await session.execute(
                insert(ExpeditionChoice)
                .values(
                    expedition_id=expedition.id,
                    character_id=character.id,
                    stage=stage,
                    option_id=option.option_id,
                    points=QUALITY_POINTS[option.quality],
                    is_default=False,
                    chosen_at=now,
                )
                .on_conflict_do_nothing()
                .returning(ExpeditionChoice.stage)
            )
            if inserted.first() is None:
                raise ExpeditionError("already_chosen")
            return await self._hub_view(session, character, now, "Sua escolha foi registrada.")

    # ------------------------------------------------------------- maintenance

    async def run_maintenance(self, *, now: datetime | None = None) -> list[ExpeditionNotice]:
        now = _utcnow(now)
        async with self.sessions() as session:
            due_starts = list(
                (
                    await session.execute(
                        select(Expedition.id, Expedition.guild_id).where(
                            Expedition.server_id == self.server_id,
                            Expedition.status == "forming",
                            Expedition.starts_at <= now,
                        )
                    )
                ).all()
            )
        notices: list[ExpeditionNotice] = []
        for expedition_id, guild_id in due_starts:
            notices.extend(await self._start(expedition_id, guild_id, now))
        async with self.sessions() as session:
            running = list(
                (
                    await session.execute(
                        select(Expedition.id, Expedition.guild_id).where(
                            Expedition.server_id == self.server_id,
                            Expedition.status == "active",
                        )
                    )
                ).all()
            )
            pending = list(
                (
                    await session.scalars(
                        select(Expedition.id).where(
                            Expedition.server_id == self.server_id,
                            Expedition.status == "completed",
                            Expedition.settled_at.is_(None),
                        )
                    )
                ).all()
            )
        for expedition_id, guild_id in running:
            notices.extend(await self._advance(expedition_id, guild_id, now))
            pending.append(expedition_id)
        for expedition_id in dict.fromkeys(pending):
            notices.extend(await self._settle(expedition_id, now))
        return notices

    async def _start(self, expedition_id, guild_id, now) -> list[ExpeditionNotice]:
        """Freezes the roster (§22.2) or cancels below the minimum."""
        async with self.sessions.begin() as session:
            guild = await self._lock_guild(session, guild_id)
            expedition = await self._lock(session, expedition_id)
            if expedition.status != "forming":
                return []
            route = self._by_id.get(expedition.route_id)
            rows = await self._roster(session, expedition.id)
            valid: list[tuple[ExpeditionMember, Character]] = []
            for row in rows:
                membership = await session.get(GuildMember, row.character_id)
                character = await session.get(Character, row.character_id)
                if membership is not None and membership.guild_id == guild.id and character:
                    valid.append((row, character))
                else:
                    await session.delete(row)
            if (
                route is None
                or guild.status != "active"
                or guild.dissolution_due_at is not None
                or len(valid) < ROSTER_MIN
                or now >= expedition.ends_at
            ):
                expedition.status = "cancelled"
                return []
            for row, character in valid:
                row.reference_level = character.level
            expedition.status = "active"
            await session.flush()
            await record_linked_cooccurrence(
                session,
                server_id=self.server_id,
                activity_kind="expedition",
                activity_reference=str(expedition.id),
                characters=[character for _, character in valid],
                now=now,
            )
            return [
                ExpeditionNotice(character.telegram_id, ExpeditionStageNotice(route.name, 1))
                for _, character in valid
            ]

    async def _advance(self, expedition_id, guild_id, now) -> list[ExpeditionNotice]:
        """§22.2: never waits for a vote; closed stages take the default."""
        async with self.sessions.begin() as session:
            guild = await self._lock_guild(session, guild_id)
            expedition = await self._lock(session, expedition_id)
            if expedition.status != "active":
                return []
            rows = await self._roster(session, expedition.id)
            before = expedition.resolved_stages
            while (
                expedition.resolved_stages < STAGE_COUNT
                and stage_ends_at(expedition.starts_at, expedition.resolved_stages + 1) <= now
            ):
                expedition.resolved_stages += 1
                for row in rows:
                    await session.execute(
                        insert(ExpeditionChoice)
                        .values(
                            expedition_id=expedition.id,
                            character_id=row.character_id,
                            stage=expedition.resolved_stages,
                            option_id=None,
                            points=DEFAULT_POINTS,
                            is_default=True,
                            chosen_at=now,
                        )
                        .on_conflict_do_nothing()
                    )
            if expedition.resolved_stages == before:
                return []
            route = self._by_id.get(expedition.route_id)
            if expedition.resolved_stages >= STAGE_COUNT:
                await self._finalize(session, guild, expedition, rows, now)
                return []
            telegrams = await self._telegrams(session, rows)
            return [
                ExpeditionNotice(
                    telegram,
                    ExpeditionStageNotice(
                        route.name if route is not None else "",
                        expedition.resolved_stages + 1,
                    ),
                )
                for telegram in telegrams
            ]

    async def _finalize(self, session, guild, expedition, rows, now) -> None:
        choices = (
            await session.scalars(
                select(ExpeditionChoice).where(ExpeditionChoice.expedition_id == expedition.id)
            )
        ).all()
        by_stage: dict[int, list[int]] = {}
        active: dict[UUID, int] = {}
        for choice in choices:
            by_stage.setdefault(choice.stage, []).append(choice.points)
            if not choice.is_default:
                active[choice.character_id] = active.get(choice.character_id, 0) + 1
        score = final_score(by_stage[stage] for stage in sorted(by_stage))
        result = result_for(score)
        for row in rows:
            row.active_stages = active.get(row.character_id, 0)
        expedition.score = score
        expedition.result = result.value
        expedition.status = "completed"
        expedition.finalized_at = now
        crowns = treasury_reward(result)
        if crowns and guild.status == "active":
            expedition.treasury_crowns = crowns
            record_treasury(session, guild, "expedition", crowns, now)

    async def _settle(self, expedition_id, now) -> list[ExpeditionNotice]:
        async with self.sessions() as session:
            expedition = await session.get(Expedition, expedition_id)
            if expedition is None or expedition.status != "completed":
                return []
            character_ids = sorted(
                (
                    await session.scalars(
                        select(ExpeditionMember.character_id).where(
                            ExpeditionMember.expedition_id == expedition_id,
                            ExpeditionMember.settled_at.is_(None),
                        )
                    )
                ).all(),
                key=str,
            )
        notices = []
        for character_id in character_ids:
            notice = await self._settle_one(expedition_id, character_id, now)
            if notice is not None:
                notices.append(notice)
        async with self.sessions.begin() as session:
            expedition = await self._lock(session, expedition_id)
            if expedition.settled_at is None:
                expedition.settled_at = now
        return notices

    async def _settle_one(self, expedition_id, character_id, now) -> ExpeditionNotice | None:
        """Idempotent per member, so a restart resumes where it stopped."""
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character).where(Character.id == character_id).with_for_update()
            )
            member = await session.scalar(
                select(ExpeditionMember)
                .where(
                    ExpeditionMember.expedition_id == expedition_id,
                    ExpeditionMember.character_id == character_id,
                )
                .with_for_update()
            )
            if character is None or member is None or member.settled_at is not None:
                return None
            expedition = await session.get(Expedition, expedition_id)
            bundle = reward_bundle(member.reference_level, ExpeditionResult(expedition.result))
            eligible = bundle is not None and is_eligible(member.active_stages)
            reward: dict = {}
            if eligible:
                granted = await grant_bundle(
                    session,
                    character,
                    bundle,
                    f"expedition:{expedition.id.hex}:{character.id.hex}",
                    region=region_for_level(member.reference_level),
                )
                reward = {
                    "crowns": granted.crowns,
                    "items": [
                        {"name": item.name, "quantity": item.quantity} for item in granted.items
                    ],
                }
            member.eligible = eligible
            member.reward = reward
            member.settled_at = now
            return ExpeditionNotice(character.telegram_id, self._result_view(expedition, member))

    # ----------------------------------------------------------------- helpers

    async def _forming(self, session, guild, now) -> Expedition:
        start = next_start(now)
        key = week_key(start)
        expedition = await session.scalar(
            select(Expedition).where(Expedition.guild_id == guild.id, Expedition.week_key == key)
        )
        if expedition is not None:
            return expedition
        route = route_for_start(self.catalog, start)
        starts_at = start.astimezone(UTC)
        expedition = Expedition(
            id=uuid4(),
            server_id=self.server_id,
            guild_id=guild.id,
            week_key=key,
            route_id=route.route_id,
            status="forming",
            starts_at=starts_at,
            ends_at=starts_at + DURATION,
            resolved_stages=0,
            treasury_crowns=0,
            ruleset_version=RULESET,
        )
        session.add(expedition)
        await session.flush()
        return expedition

    async def _hub_view(self, session, character, now, notice) -> ExpeditionHubView:
        if not self.catalog:
            return ExpeditionHubView(catalog_empty=True, notice=notice)
        has_last = (
            await session.scalar(
                select(ExpeditionMember.expedition_id)
                .where(
                    ExpeditionMember.character_id == character.id,
                    ExpeditionMember.settled_at.is_not(None),
                )
                .limit(1)
            )
            is not None
        )
        membership = await session.get(GuildMember, character.id)
        if membership is None:
            # §22.2: leaving the Guild never removes a frozen roster seat.
            kept = await self._active_as_member(session, character.id)
            if kept is None:
                return ExpeditionHubView(has_last_result=has_last, notice=notice)
            return await self._active_view(
                session, kept, character, None, False, has_last, notice, now
            )
        guild = await session.get(Guild, membership.guild_id)
        can_manage = membership.role in (GuildRole.LEADER.value, GuildRole.OFFICER.value)
        running = await self._active(session, guild.id) or await self._active_as_member(
            session, character.id
        )
        if running is not None:
            return await self._active_view(
                session, running, character, guild.name, can_manage, has_last, notice, now
            )
        start = next_start(now)
        expedition = await session.scalar(
            select(Expedition).where(
                Expedition.guild_id == guild.id,
                Expedition.week_key == week_key(start),
                Expedition.status == "forming",
            )
        )
        rows = await self._roster(session, expedition.id) if expedition is not None else []
        selected = {row.character_id for row in rows}
        members = (
            await session.execute(
                select(GuildMember.character_id, Character.name, Character.level)
                .join(Character, Character.id == GuildMember.character_id)
                .where(GuildMember.guild_id == guild.id)
                .order_by(Character.name)
            )
        ).all()
        route = route_for_start(self.catalog, start)
        return ExpeditionHubView(
            guild_name=guild.name,
            can_manage=can_manage,
            status="forming",
            expedition_id=expedition.id if expedition is not None else None,
            route_name=route.name if route is not None else None,
            starts_at=start.astimezone(UTC),
            roster=tuple(
                ExpeditionRosterEntry(row[0], row[1], row[2], row[0] in selected) for row in members
            ),
            roster_count=len(selected),
            in_roster=character.id in selected,
            has_last_result=has_last,
            notice=notice,
        )

    async def _active_view(
        self, session, expedition, character, guild_name, can_manage, has_last, notice, now
    ) -> ExpeditionHubView:
        route = self._by_id.get(expedition.route_id)
        rows = await self._roster(session, expedition.id)
        member = next((row for row in rows if row.character_id == character.id), None)
        stage = min(stage_at(expedition.starts_at, now), STAGE_COUNT)
        stage_data = route.stage(stage) if route is not None and stage else None
        chosen = None
        if member is not None and stage:
            choice = await session.get(ExpeditionChoice, (expedition.id, character.id, stage))
            chosen = choice.option_id if choice is not None else None
        return ExpeditionHubView(
            guild_name=guild_name,
            can_manage=can_manage,
            status="active",
            expedition_id=expedition.id,
            route_name=route.name if route is not None else None,
            starts_at=expedition.starts_at,
            roster_count=len(rows),
            in_roster=member is not None,
            stage=stage,
            stage_ends=stage_ends_at(expedition.starts_at, stage) if stage else None,
            stage_flavor=stage_data.flavor if stage_data is not None else None,
            options=(
                tuple(
                    ExpeditionOptionView(
                        index, option.label, option.option_id == chosen, option.description
                    )
                    for index, option in enumerate(stage_data.options)
                )
                if stage_data is not None and member is not None
                else ()
            ),
            answered=chosen is not None,
            has_last_result=has_last,
            notice=notice,
        )

    def _result_view(self, expedition, member) -> ExpeditionResultView:
        route = self._by_id.get(expedition.route_id)
        reward = member.reward or {}
        return ExpeditionResultView(
            route_name=route.name if route is not None else expedition.route_id,
            result=ExpeditionResult(expedition.result),
            score=expedition.score or 0,
            flavor=route.return_flavor if route is not None else "",
            treasury=expedition.treasury_crowns,
            in_roster=True,
            eligible=bool(member.eligible),
            crowns=int(reward.get("crowns", 0)),
            items=tuple(
                ExpeditionRewardItem(str(item["name"]), int(item["quantity"]))
                for item in reward.get("items", ())
            ),
        )

    async def _active(self, session, guild_id: UUID) -> Expedition | None:
        return await session.scalar(
            select(Expedition)
            .where(Expedition.guild_id == guild_id, Expedition.status == "active")
            .limit(1)
        )

    async def _active_as_member(self, session, character_id: UUID) -> Expedition | None:
        return await session.scalar(
            select(Expedition)
            .join(ExpeditionMember, ExpeditionMember.expedition_id == Expedition.id)
            .where(ExpeditionMember.character_id == character_id, Expedition.status == "active")
            .limit(1)
        )

    async def _roster(self, session, expedition_id: UUID) -> list[ExpeditionMember]:
        return list(
            (
                await session.scalars(
                    select(ExpeditionMember)
                    .where(ExpeditionMember.expedition_id == expedition_id)
                    .order_by(ExpeditionMember.ordinal)
                )
            ).all()
        )

    async def _telegrams(self, session, rows) -> list[int]:
        return list(
            (
                await session.scalars(
                    select(Character.telegram_id).where(
                        Character.id.in_([row.character_id for row in rows])
                    )
                )
            ).all()
        )

    async def _lock(self, session, expedition_id: UUID) -> Expedition:
        return await session.scalar(
            select(Expedition).where(Expedition.id == expedition_id).with_for_update()
        )

    async def _lock_guild(self, session, guild_id: UUID) -> Guild:
        guild = await session.scalar(select(Guild).where(Guild.id == guild_id).with_for_update())
        if guild is None:
            raise ExpeditionError("not_found")
        return guild

    async def _character(self, session, actor: int) -> Character:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )
        if character is None:
            raise ExpeditionError("no_character")
        return character
