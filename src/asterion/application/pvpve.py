"""Persistent two-stage PvPvE matchmaking and settlement for open-world Hunts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.campaign_coop import campaign_action_intent
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.road import (
    BRAZIER_DETAILS,
    BRAZIER_FOR_LOCATION,
    GROUP_HUNT_CONTENT,
    HUNT_CONTENT,
    PVPVE_CONTENT,
    PVPVE_QUEUE_CONTENT,
    RoadView,
    _location_label,
)
from asterion.domain.combat import (
    act,
    action_target_ids,
    active_player_key,
    allowed_actions,
    player_actions_for,
)
from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.road import (
    RULESET,
    PlayerCombatantSpec,
    create_player_versus_player_combat,
    material_for,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    GameActivity,
    GroupActivityParticipant,
    GroupActivityProposal,
    PvpveAccountCooldown,
    PvpveAccountPair,
    PvpveCollision,
    PvpveCollisionMember,
    PvpveDomainGrant,
    PvpveQueue,
    PvpveQueueMember,
    WorldState,
)

PVP_COOLDOWN = timedelta(minutes=3)
REMATCH_COOLDOWN = timedelta(minutes=10)
DOMAIN_COOLDOWN = timedelta(minutes=30)
MANUAL_QUEUE_TTL = timedelta(minutes=20)
ROUND_QUEUE_TTL = timedelta(minutes=75)
PVPVE_CONTENT_ID = PVPVE_CONTENT
PVPVE_QUEUE_CONTENT_ID = PVPVE_QUEUE_CONTENT


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _lock_key(server_id: str, local_id: str, roster_size: int) -> int:
    raw = int.from_bytes(
        sha256(f"pvpve:{server_id}:{local_id}:{roster_size}".encode()).digest()[:8],
        "big",
    )
    return raw - (1 << 64) if raw >= (1 << 63) else raw


class PvpveService:
    """Owns queues, PVP collisions, Domain rewards, and their idempotency."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str, road) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.road = road

    async def queue_round_hunt(
        self, session, character, world, profile, round_state, activity, *, now
    ) -> bool:
        """Offer one safe Ronda frontier to the approved solo PvPvE queue."""
        existing = await session.scalar(
            select(PvpveQueueMember).where(
                PvpveQueueMember.game_activity_id == activity.id,
                PvpveQueueMember.character_id == character.id,
            )
        )
        if existing is not None:
            return True
        await self._match_lock(session, profile.local_id, 1)
        queue = PvpveQueue(
            id=uuid4(),
            server_id=self.server_id,
            local_id=profile.local_id,
            roster_size=1,
            source_type="round",
            roster_snapshot=[character.id.hex],
            created_at=now,
            expires_at=now + ROUND_QUEUE_TTL,
        )
        session.add(queue)
        await session.flush()
        session.add(
            PvpveQueueMember(
                queue_id=queue.id,
                character_id=character.id,
                account_id=character.telegram_id,
                game_activity_id=activity.id,
                actor_key="q1",
                ordinal=1,
            )
        )
        round_state.config_snapshot = {
            **(round_state.config_snapshot or {}),
            "pvpve_checked_for": round_state.completed_encounters + 1,
        }
        round_state.next_resolution_at = queue.expires_at
        round_state.state_version += 1
        activity.content_id = PVPVE_QUEUE_CONTENT_ID
        activity.state_version = round_state.state_version
        activity.last_valid_action_at = now
        await session.flush()
        await self._try_match(session, queue, now=now)
        return True

    async def queue_manual_hunt(self, session, character, world, profile) -> RoadView:
        now = _utcnow()
        await self._match_lock(session, profile.local_id, 1)
        queue = PvpveQueue(
            id=uuid4(),
            server_id=self.server_id,
            local_id=profile.local_id,
            roster_size=1,
            source_type="manual",
            roster_snapshot=[character.id.hex],
            created_at=now,
            expires_at=now + MANUAL_QUEUE_TTL,
        )
        session.add(queue)
        await session.flush()
        activity = GameActivity(
            id=uuid4(),
            character_id=character.id,
            content_id=PVPVE_QUEUE_CONTENT_ID,
            status="active",
            state_version=0,
            ruleset_version=RULESET,
            last_valid_action_at=now,
        )
        session.add(activity)
        await session.flush()
        session.add(
            PvpveQueueMember(
                queue_id=queue.id,
                character_id=character.id,
                account_id=character.telegram_id,
                game_activity_id=activity.id,
                actor_key="q1",
                ordinal=1,
            )
        )
        await session.flush()
        matched = await self._try_match(session, queue, now=now)
        if matched:
            await session.refresh(activity)
            return await self.view_for_activity(session, character, activity)
        return self._queue_view(character, world.location, activity, queue, now)

    async def queue_group_hunt(
        self, session, proposal: GroupActivityProposal, characters
    ) -> str:
        if not 2 <= len(characters) <= 4:
            raise ValueError("group PvPvE rosters require two to four participants")
        if len({item.telegram_id for item in characters}) != len(characters):
            raise ValueError("a PvPvE roster cannot contain two characters from one account")
        context = proposal.context_payload or {}
        local_id = context.get("local_id")
        if not isinstance(local_id, str) or not local_id:
            raise ValueError("group Hunt is missing its frozen Local")
        now = _utcnow()
        await self._match_lock(session, local_id, len(characters))
        queue = PvpveQueue(
            id=uuid4(),
            server_id=self.server_id,
            local_id=local_id,
            roster_size=len(characters),
            source_type="group",
            group_id=proposal.group_id,
            proposal_id=proposal.id,
            roster_snapshot=[item.id.hex for item in characters],
            created_at=now,
            expires_at=now + MANUAL_QUEUE_TTL,
        )
        session.add(queue)
        await session.flush()
        for ordinal, character in enumerate(characters, start=1):
            activity = GameActivity(
                id=uuid4(),
                character_id=character.id,
                content_id=PVPVE_QUEUE_CONTENT_ID,
                status="active",
                state_version=0,
                ruleset_version=RULESET,
                last_valid_action_at=now,
            )
            session.add(activity)
            await session.flush()
            session.add(
                PvpveQueueMember(
                    queue_id=queue.id,
                    character_id=character.id,
                    account_id=character.telegram_id,
                    game_activity_id=activity.id,
                    actor_key=f"q{ordinal}",
                    ordinal=ordinal,
                )
            )
        await session.flush()
        await self._try_match(session, queue, now=now)
        return queue.id.hex

    async def refresh_queue(self, actor: int, activity_id: UUID) -> bool:
        """Refresh one queue without first locking its viewer's Character row."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return False
            seed = await session.scalar(
                select(PvpveQueueMember).where(
                    PvpveQueueMember.character_id == character.id,
                    PvpveQueueMember.game_activity_id == activity_id,
                )
            )
            if seed is None:
                return False
            queue_hint = await session.get(PvpveQueue, seed.queue_id)
            activity = await session.scalar(
                select(GameActivity).where(GameActivity.id == activity_id)
            )
            if (
                queue_hint is None
                or activity is None
                or activity.content_id != PVPVE_QUEUE_CONTENT_ID
            ):
                return False
            await self._match_lock(session, queue_hint.local_id, queue_hint.roster_size)
            queue = await session.scalar(
                select(PvpveQueue)
                .where(PvpveQueue.id == seed.queue_id)
                .with_for_update()
            )
            if queue is None:
                return False
            members, characters, activities = await self._lock_queue_roster(session, queue.id)
            if not members or len(members) != queue.roster_size:
                await self._cancel_queue(session, queue, members, activities, _utcnow())
                return False
            now = _utcnow()
            if queue.status == "waiting":
                matched = await self._try_match(session, queue, now=now)
                if not matched and now >= queue.expires_at:
                    await self._materialize_queue_pve(
                        session, queue, members, characters, activities, now=now
                    )
            await session.flush()
            return True

    async def cancel_queue(self, actor: int, activity_id: UUID) -> RoadView | None:
        """Cancel a waiting queue before any PvP encounter or Vigor cost exists."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            seed = await session.scalar(
                select(PvpveQueueMember).where(
                    PvpveQueueMember.character_id == character.id,
                    PvpveQueueMember.game_activity_id == activity_id,
                )
            )
            if seed is None:
                return None
            queue_hint = await session.get(PvpveQueue, seed.queue_id)
            activity = await session.get(GameActivity, activity_id)
            if queue_hint is None or activity is None:
                return None
            if (
                queue_hint.status != "waiting"
                or activity.content_id != PVPVE_QUEUE_CONTENT_ID
            ):
                return await self.view_for_activity(session, character, activity)
            await self._match_lock(session, queue_hint.local_id, queue_hint.roster_size)
            queue = await session.scalar(
                select(PvpveQueue)
                .where(PvpveQueue.id == seed.queue_id)
                .with_for_update()
            )
            if queue is None:
                return None
            members, _characters, activities = await self._lock_queue_roster(
                session, queue.id
            )
            now = _utcnow()
            if queue.status == "waiting":
                if queue.source_type == "round":
                    queue.status = "cancelled"
                    queue.resolved_at = now
                    round_activity = next(
                        (row for row in activities if row.id == activity_id), None
                    )
                    if round_activity is not None:
                        await self.road.continue_round_after_queue(
                            session,
                            queue,
                            character,
                            round_activity,
                            anchor=now,
                        )
                else:
                    await self._cancel_queue(session, queue, members, activities, now)
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id)
            )
            blocking = await self.road._road_blocking_view(session, character)
            if blocking is not None:
                return blocking
            return await self.road._view_for_world(session, character, world) if world else None

    async def view_for_activity(self, session, character, activity) -> RoadView | None:
        if activity.content_id == PVPVE_QUEUE_CONTENT_ID:
            member = await session.scalar(
                select(PvpveQueueMember).where(
                    PvpveQueueMember.game_activity_id == activity.id,
                    PvpveQueueMember.character_id == character.id,
                )
            )
            if member is None:
                return None
            queue = await session.get(PvpveQueue, member.queue_id)
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id)
            )
            if queue is None or queue.status != "waiting":
                refreshed = await session.get(GameActivity, activity.id, populate_existing=True)
                if refreshed is not None and refreshed.content_id != PVPVE_QUEUE_CONTENT_ID:
                    return await self._route_activity(session, character, refreshed)
                return await self.road._view_for_world(session, character, world) if world else None
            if _utcnow() >= queue.expires_at:
                return RoadView(
                    "hunt_queue",
                    character.id,
                    _location_label(queue.local_id),
                    activity_id=activity.id,
                    state_version=activity.state_version,
                    name=character.name,
                    hp=character.hp,
                    max_hp=character.max_hp,
                    result_text="Busca expirada · Atualize para continuar como Caçada PvE.",
                    pvpve_round_queue=queue.source_type == "round",
                )
            return self._queue_view(
                character,
                world.location if world else queue.local_id,
                activity,
                queue,
                _utcnow(),
            )
        if activity.content_id == PVPVE_CONTENT_ID:
            return await self._collision_view_for_activity(session, character, activity)
        return None

    async def handle_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None = None,
        *,
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
        action_index: int | None = None,
        target_code: str | None = None,
    ) -> tuple[bool, RoadView | None]:
        async with self.sessions.begin() as session:
            seed_character = await self._character(session, actor)
            if seed_character is None:
                return False, None
            seed_activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == seed_character.id,
                )
            )
            if seed_activity is None or seed_activity.content_id != PVPVE_CONTENT_ID:
                return False, None
            seed_member = await session.scalar(
                select(PvpveCollisionMember).where(
                    PvpveCollisionMember.character_id == seed_character.id,
                    PvpveCollisionMember.game_activity_id == activity_id,
                )
            )
            if seed_member is None:
                return False, None
            collision = await session.scalar(
                select(PvpveCollision)
                .where(PvpveCollision.id == seed_member.collision_id)
                .with_for_update()
            )
            if collision is None:
                return True, None
            members = list(
                (
                    await session.scalars(
                        select(PvpveCollisionMember)
                        .where(PvpveCollisionMember.collision_id == collision.id)
                        .order_by(PvpveCollisionMember.character_id)
                        .with_for_update()
                    )
                ).all()
            )
            characters = await self._lock_characters(
                session, [row.character_id for row in members]
            )
            activities = list(
                (
                    await session.scalars(
                        select(GameActivity)
                        .where(GameActivity.id.in_([row.game_activity_id for row in members]))
                        .order_by(GameActivity.id)
                        .with_for_update()
                    )
                ).all()
            )
            char_by_id = {row.id: row for row in characters}
            activity_by_id = {row.id: row for row in activities}
            member_by_activity = {row.game_activity_id: row for row in members}
            member = member_by_activity.get(activity_id)
            character = char_by_id.get(seed_character.id)
            activity = activity_by_id.get(activity_id)
            if member is None or character is None or activity is None:
                return True, None
            if collision.status != "active" or activity.status != "active":
                return True, await self._collision_view_for_activity(session, character, activity)
            combat = decode(
                collision.combat_snapshot,
                collision.combat_id,
                collision.ruleset_version,
                collision.state_version,
            )
            if (
                activity.state_version != version
                or collision.state_version != version
                or active_player_key(combat) != member.actor_key
            ):
                return True, await self._combat_view(
                    session, character, activity, collision, member, combat
                )
            own_queue_id = (
                collision.queue_a_id if member.side == "a" else collision.queue_b_id
            )
            own_queue = await session.get(PvpveQueue, own_queue_id)
            if (
                own_queue is not None
                and own_queue.source_type == "round"
                and not member.round_takeover
            ):
                now = _utcnow()
                updated = await self._advance_round_ai(
                    session,
                    collision,
                    members,
                    char_by_id,
                    activity_by_id,
                    combat,
                )
                if updated.version != combat.version:
                    collision.combat_snapshot = encode(updated)
                    collision.state_version = updated.version
                    for row in members:
                        fighter = updated.fighters.get(row.actor_key)
                        if fighter is not None:
                            char_by_id[row.character_id].hp = fighter.hp
                        roster_activity = activity_by_id[row.game_activity_id]
                        roster_activity.state_version = updated.version
                        roster_activity.last_valid_action_at = now
                if updated.result:
                    await self._resolve_collision(
                        session,
                        collision,
                        members,
                        char_by_id,
                        activity_by_id,
                        updated,
                        now=now,
                    )
                await session.flush()
                return True, await self._view_after_resolution(
                    session,
                    char_by_id[seed_character.id],
                    activity_by_id[activity_id],
                )
            actor_action = action
            resolved_target = target_id
            if action_index is not None:
                intent = campaign_action_intent(
                    combat, member.actor_key, action_index, target_code or "x"
                )
                if intent is None:
                    return True, await self._combat_view(
                        session, character, activity, collision, member, combat
                    )
                actor_action, resolved_target = intent
            if consumable_id is None:
                if actor_action is None:
                    return True, await self._combat_view(
                        session, character, activity, collision, member, combat
                    )
                updated = act(
                    combat,
                    actor_action,
                    target_id=resolved_target,
                    actor_key=member.actor_key,
                )
            else:
                # The authoritative TDO rules explicitly prohibit external
                # consumables in PvP; inventory is never touched here.
                return True, await self._combat_view(
                    session, character, activity, collision, member, combat
                )
            if updated.version == combat.version:
                return True, await self._combat_view(
                    session, character, activity, collision, member, combat
                )
            now = _utcnow()
            if actor_action != "hold":
                member.contributed = True
            if not updated.result:
                updated = await self._advance_round_ai(
                    session,
                    collision,
                    members,
                    char_by_id,
                    activity_by_id,
                    updated,
                )
            collision.combat_snapshot = encode(updated)
            collision.state_version = updated.version
            for row in members:
                fighter = updated.fighters.get(row.actor_key)
                if fighter is not None:
                    char_by_id[row.character_id].hp = fighter.hp
                roster_activity = activity_by_id[row.game_activity_id]
                roster_activity.state_version = updated.version
                roster_activity.last_valid_action_at = now
            if updated.result:
                await self._resolve_collision(
                    session,
                    collision,
                    members,
                    char_by_id,
                    activity_by_id,
                    updated,
                    now=now,
                )
                await session.flush()
                return True, await self._view_after_resolution(
                    session, char_by_id[seed_character.id], activity_by_id[activity_id]
                )
            await session.flush()
            return True, await self._combat_view(
                session, character, activity, collision, member, updated
            )

    async def action_intent(
        self, actor: int, activity_id: UUID, version: int, action_index: int, target_code: str
    ) -> RoadView | None:
        handled, view = await self.handle_action(
            actor,
            activity_id,
            version,
            action_index=action_index,
            target_code=target_code,
        )
        return view if handled else None

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, **_kwargs
    ) -> RoadView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == PVPVE_CONTENT_ID,
                )
            )
            if activity is None:
                return None
            view = await self._collision_view_for_activity(session, character, activity)
            if view is None or view.kind != "combat":
                return view
            return view

    async def acknowledge_defeat(self, session, character) -> bool:
        member = await session.scalar(
            select(PvpveCollisionMember)
            .join(PvpveCollision, PvpveCollisionMember.collision_id == PvpveCollision.id)
            .where(
                PvpveCollisionMember.character_id == character.id,
                PvpveCollisionMember.status == "defeated",
                PvpveCollisionMember.result_acknowledged.is_(False),
            )
            .order_by(PvpveCollision.created_at.desc(), PvpveCollision.id.desc())
            .limit(1)
            .with_for_update()
        )
        if member is None:
            return False
        member.result_acknowledged = True
        return True

    async def settle_domain(
        self, session, character, activity, context, event, components, *, paid
    ):
        collision_id = context.pvpve_collision_id
        if collision_id is None or not context.pvpve_domain_eligible:
            return
        collision = await session.scalar(
            select(PvpveCollision)
            .where(PvpveCollision.id == collision_id)
            .with_for_update()
        )
        existing = await session.get(PvpveDomainGrant, (collision_id, character.id))
        if existing is not None:
            return
        member = await session.get(PvpveCollisionMember, (collision_id, character.id))
        if member is None or collision is None or member.status != "prey":
            return
        if not paid:
            session.add(
                PvpveDomainGrant(
                    collision_id=collision_id,
                    character_id=character.id,
                    crowns=0,
                    material_id=None,
                    status="no_economic_reward",
                )
            )
            return
        opposing_accounts = list(
            (
                await session.scalars(
                    select(PvpveCollisionMember.account_id)
                    .where(
                        PvpveCollisionMember.collision_id == collision_id,
                        PvpveCollisionMember.side != member.side,
                    )
                    .order_by(PvpveCollisionMember.account_id)
                )
            ).all()
        )
        pairs = sorted(
            {
                (min(member.account_id, account_id), max(member.account_id, account_id))
                for account_id in opposing_accounts
                if account_id != member.account_id
            }
        )
        if not pairs:
            session.add(
                PvpveDomainGrant(
                    collision_id=collision_id,
                    character_id=character.id,
                    crowns=0,
                    material_id=None,
                    status="no_opponent",
                )
            )
            return
        await session.execute(
            insert(PvpveAccountPair)
            .values([{"account_a": a, "account_b": b} for a, b in pairs])
            .on_conflict_do_nothing(index_elements=["account_a", "account_b"])
        )
        pair_rows = list(
            (
                await session.scalars(
                    select(PvpveAccountPair)
                    .where(
                        tuple_(PvpveAccountPair.account_a, PvpveAccountPair.account_b).in_(
                            pairs
                        )
                    )
                    .order_by(PvpveAccountPair.account_a, PvpveAccountPair.account_b)
                    .with_for_update()
                )
            ).all()
        )
        now = _utcnow()
        if any(row.domain_until is not None and row.domain_until > now for row in pair_rows):
            session.add(
                PvpveDomainGrant(
                    collision_id=collision_id,
                    character_id=character.id,
                    crowns=0,
                    material_id=None,
                    status="locked",
                )
            )
            return
        reference = context.pvpve_reference_level or context.enemy_level
        bonus_crowns = round_10(crowns_per_level(reference) * Decimal("0.05"))
        material_id = material_for(
            context.creature_id,
            f"pvpve-domain:{collision_id.hex}:{character.id.hex}",
        )
        character.crowns += bonus_crowns
        await self.road._deliver_material(
            session,
            character,
            material_id,
            1,
            f"pvpvd:{collision_id.hex}:{character.id.hex}:m",
        )
        session.add(
            PvpveDomainGrant(
                collision_id=collision_id,
                character_id=character.id,
                crowns=bonus_crowns,
                material_id=material_id,
                status="granted",
            )
        )
        components.extend(
            [
                ("crowns", None, bonus_crowns, {"source": "dominio_do_rastro"}),
                (
                    "material",
                    material_id,
                    1,
                    {"material_id": material_id, "bound": False, "source": "dominio_do_rastro"},
                ),
            ]
        )
        until = now + DOMAIN_COOLDOWN
        for row in pair_rows:
            row.domain_until = max(row.domain_until or until, until)

    async def finish_prey(self, session, collision_id: UUID, *, victory: bool) -> None:
        collision = await session.scalar(
            select(PvpveCollision)
            .where(PvpveCollision.id == collision_id)
            .with_for_update()
        )
        if collision is None or collision.status in {"completed", "failed"}:
            return
        members = list(
            (
                await session.scalars(
                    select(PvpveCollisionMember)
                    .where(
                        PvpveCollisionMember.collision_id == collision_id,
                        PvpveCollisionMember.status == "prey",
                    )
                    .with_for_update()
                )
            ).all()
        )
        now = _utcnow()
        for member in members:
            member.status = "settled"
            member.prey_result = "victory" if victory else "defeat"
            member.settled_at = now
        collision.status = "completed" if victory else "failed"
        collision.resolved_at = now
        await self._finish_group_proposals(session, collision, now, victory=victory)
        await session.flush()

    async def finish_prey_member(
        self,
        session,
        collision_id: UUID,
        character_id: UUID,
        *,
        victory: bool,
    ) -> None:
        collision = await session.scalar(
            select(PvpveCollision)
            .where(PvpveCollision.id == collision_id)
            .with_for_update()
        )
        if collision is None or collision.status in {"completed", "failed"}:
            return
        member = await session.scalar(
            select(PvpveCollisionMember)
            .where(
                PvpveCollisionMember.collision_id == collision_id,
                PvpveCollisionMember.character_id == character_id,
            )
            .with_for_update()
        )
        if member is None or member.status != "prey":
            return
        member.status = "settled"
        member.prey_result = "victory" if victory else "defeat"
        member.settled_at = _utcnow()
        remaining = await session.scalar(
            select(func.count(PvpveCollisionMember.character_id)).where(
                PvpveCollisionMember.collision_id == collision_id,
                PvpveCollisionMember.status == "prey",
            )
        )
        if not remaining:
            await self.finish_prey(session, collision_id, victory=victory)

    async def _route_activity(self, session, character, activity):
        if activity.content_id == GROUP_HUNT_CONTENT:
            return await self.road.group_hunts.view_for_activity(session, character, activity)
        if activity.content_id == HUNT_CONTENT:
            return await self.road._combat_view(session, character, activity)
        if activity.content_id == PVPVE_CONTENT_ID:
            return await self._collision_view_for_activity(session, character, activity)
        return None

    async def _collision_view_for_activity(self, session, character, activity):
        member = await session.scalar(
            select(PvpveCollisionMember).where(
                PvpveCollisionMember.game_activity_id == activity.id,
                PvpveCollisionMember.character_id == character.id,
            )
        )
        if member is None:
            return None
        if member.status == "defeated" and not member.result_acknowledged:
            return await self._defeat_view(session, character, activity, member)
        if member.status != "active":
            return None
        collision = await session.get(PvpveCollision, member.collision_id)
        if collision is None or collision.status != "active":
            return None
        combat = decode(
            collision.combat_snapshot,
            collision.combat_id,
            collision.ruleset_version,
            collision.state_version,
        )
        return await self._combat_view(
            session, character, activity, collision, member, combat
        )

    async def _combat_view(self, session, character, activity, collision, member, combat):
        queue_id = collision.queue_a_id if member.side == "a" else collision.queue_b_id
        queue = await session.get(PvpveQueue, queue_id)
        return RoadView(
            "combat",
            character.id,
            _location_label(collision.local_id),
            activity.id,
            collision.id,
            collision.combat_id,
            combat,
            state_version=collision.state_version,
            vigor=character.vigor,
            max_vigor=character.max_vigor,
            name=character.name,
            hp=character.hp,
            max_hp=character.max_hp,
            consumable_options=(),
            consumable_quantities=(),
            consumable_budget_limit=0,
            combat_context="pvpve",
            combat_actor_key=member.actor_key,
            pvpve_round_ai=bool(
                queue is not None
                and queue.source_type == "round"
                and not member.round_takeover
            ),
            pvpve_round_takeover=bool(
                queue is not None
                and queue.source_type == "round"
                and member.round_takeover
            ),
        )

    async def assume_round_control(self, actor: int, activity_id: UUID) -> RoadView | None:
        """Persist a Ronda PvPvE takeover for the member's next opportunity."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == PVPVE_CONTENT_ID,
                )
            )
            if activity is None:
                return None
            member = await session.scalar(
                select(PvpveCollisionMember)
                .where(
                    PvpveCollisionMember.game_activity_id == activity.id,
                    PvpveCollisionMember.character_id == character.id,
                )
            )
            if member is None:
                return None
            collision = await session.scalar(
                select(PvpveCollision)
                .where(PvpveCollision.id == member.collision_id)
                .with_for_update()
            )
            if collision is None or collision.status != "active":
                activity = await session.scalar(
                    select(GameActivity).where(GameActivity.id == activity_id)
                )
                if activity is None:
                    return None
                return await self._collision_view_for_activity(
                    session, character, activity
                )
            member = await session.scalar(
                select(PvpveCollisionMember)
                .where(
                    PvpveCollisionMember.collision_id == collision.id,
                    PvpveCollisionMember.character_id == character.id,
                )
                .with_for_update()
            )
            activity = await session.scalar(
                select(GameActivity)
                .where(GameActivity.id == activity_id)
                .with_for_update()
            )
            if member is None or activity is None:
                return None
            queue_id = collision.queue_a_id if member.side == "a" else collision.queue_b_id
            queue = await session.get(PvpveQueue, queue_id)
            if queue is None or queue.source_type != "round":
                return await self._collision_view_for_activity(
                    session, character, activity
                )
            member.round_takeover = True
            return await self._collision_view_for_activity(
                session, character, activity
            )

    async def _defeat_view(self, session, character, activity, member):
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        recovery_location = world.location if world is not None else None
        recovery_brazier = None
        if recovery_location in BRAZIER_FOR_LOCATION:
            brazier_id = BRAZIER_FOR_LOCATION[recovery_location]
            recovery_brazier = BRAZIER_DETAILS[brazier_id][1]
        return RoadView(
            "hunt_defeat",
            character.id,
            _location_label(
                await session.scalar(
                    select(PvpveCollision.local_id).where(
                        PvpveCollision.id == member.collision_id
                    )
                )
            ),
            activity_id=activity.id,
            name=character.name,
            hp=character.hp,
            max_hp=character.max_hp,
            recovery_brazier=recovery_brazier,
            recovery_location=recovery_location,
            combat_context="pvpve",
            result_text="O confronto terminou. A perseguição foi encerrada.",
        )

    async def _view_after_resolution(self, session, character, activity):
        if activity.content_id == PVPVE_CONTENT_ID and activity.status == "failed":
            return await self._collision_view_for_activity(session, character, activity)
        return await self._route_activity(session, character, activity)

    async def _try_match(self, session, current, *, now) -> bool:
        if current.status != "waiting" or current.expires_at <= now:
            return False
        candidates = list(
            (
                await session.scalars(
                    select(PvpveQueue)
                    .where(
                        PvpveQueue.server_id == current.server_id,
                        PvpveQueue.local_id == current.local_id,
                        PvpveQueue.roster_size == current.roster_size,
                        PvpveQueue.status == "waiting",
                        PvpveQueue.expires_at > now,
                        PvpveQueue.id != current.id,
                    )
                    .order_by(PvpveQueue.created_at, PvpveQueue.id)
                    .with_for_update()
                )
            ).all()
        )
        current_members = list(
            (
                await session.scalars(
                    select(PvpveQueueMember)
                    .where(PvpveQueueMember.queue_id == current.id)
                    .order_by(PvpveQueueMember.ordinal)
                )
            ).all()
        )
        if len(current_members) != current.roster_size:
            return False
        current_accounts = {row.account_id for row in current_members}
        for candidate in candidates:
            if (
                current.group_id is not None
                and candidate.group_id == current.group_id
            ):
                continue
            candidate_members = list(
                (
                    await session.scalars(
                        select(PvpveQueueMember)
                        .where(PvpveQueueMember.queue_id == candidate.id)
                        .order_by(PvpveQueueMember.ordinal)
                    )
                ).all()
            )
            if len(candidate_members) != candidate.roster_size:
                continue
            candidate_accounts = {row.account_id for row in candidate_members}
            if current_accounts.intersection(candidate_accounts):
                continue
            if not await self._pairing_available(
                session, current_accounts, candidate_accounts, now
            ):
                continue
            if not await self._queue_roster_valid(
                session, current, current_members
            ) or not await self._queue_roster_valid(
                session, candidate, candidate_members
            ):
                continue
            await self._create_collision(
                session,
                current,
                current_members,
                candidate,
                candidate_members,
                now=now,
            )
            return True
        return False

    async def _queue_roster_valid(self, session, queue, members) -> bool:
        char_ids = [row.character_id for row in members]
        characters = list(
            (
                await session.scalars(
                    select(Character).where(Character.id.in_(char_ids))
                )
            ).all()
        )
        by_id = {row.id: row for row in characters}
        activities = list(
            (
                await session.scalars(
                    select(GameActivity).where(
                        GameActivity.id.in_([member.game_activity_id for member in members])
                    )
                )
            ).all()
        )
        activity_by_id = {row.id: row for row in activities}
        if len(characters) != queue.roster_size or len(activities) != queue.roster_size:
            return False
        for member in members:
            character = by_id.get(member.character_id)
            activity = activity_by_id.get(member.game_activity_id)
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == member.character_id)
            )
            profile = (
                await self.road._available_local_profile(session, character, world, "hunt")
                if character is not None
                else None
            )
            if (
                character is None
                or activity is None
                or activity.status != "active"
                or activity.content_id != PVPVE_QUEUE_CONTENT_ID
                or character.hp <= 0
                or character.delivery_blocked
                or world is None
                or profile is None
                or profile.local_id != queue.local_id
            ):
                return False
        return True

    async def _pairing_available(self, session, accounts_a, accounts_b, now) -> bool:
        accounts = sorted(accounts_a | accounts_b)
        if accounts:
            await session.execute(
                insert(PvpveAccountCooldown)
                .values([{"account_id": account_id} for account_id in accounts])
                .on_conflict_do_nothing(index_elements=["account_id"])
            )
            cooldowns = list(
                (
                    await session.scalars(
                        select(PvpveAccountCooldown)
                        .where(PvpveAccountCooldown.account_id.in_(accounts))
                        .order_by(PvpveAccountCooldown.account_id)
                        .with_for_update()
                    )
                ).all()
            )
            if any(
                row.pvp_until is not None and row.pvp_until > now
                for row in cooldowns
            ):
                return False
        active_accounts = set(
            (
                await session.scalars(
                    select(PvpveCollisionMember.account_id)
                    .join(
                        PvpveCollision,
                        PvpveCollision.id == PvpveCollisionMember.collision_id,
                    )
                    .where(
                        PvpveCollisionMember.account_id.in_(accounts),
                        PvpveCollision.status.in_(("active", "prey")),
                    )
                )
            ).all()
        )
        if active_accounts:
            return False
        pairs = sorted(
            {
                (min(a, b), max(a, b))
                for a in accounts_a
                for b in accounts_b
                if a != b
            }
        )
        rows = list(
            (
                await session.scalars(
                    select(PvpveAccountPair).where(
                        tuple_(PvpveAccountPair.account_a, PvpveAccountPair.account_b).in_(
                            pairs
                        )
                    )
                )
            ).all()
        )
        return not any(
            row.last_match_at is not None
            and row.last_match_at + REMATCH_COOLDOWN > now
            for row in rows
        )

    async def _create_collision(
        self, session, queue_a, members_a, queue_b, members_b, *, now
    ) -> None:
        collision_id = uuid4()
        member_specs = []
        characters_by_id = {
            row.id: row
            for row in (
                await session.scalars(
                    select(Character)
                    .where(
                        Character.id.in_(
                            [member.character_id for member in (*members_a, *members_b)]
                        )
                    )
                    .order_by(Character.id)
                )
            ).all()
        }
        for side, members in (("a", members_a), ("b", members_b)):
            for index, queued in enumerate(members, start=1):
                character = characters_by_id[queued.character_id]
                equipment = await load_equipment_configuration(session, character)
                arts = await load_active_art_configuration(session, character)
                reconcile_character_hp(character, equipment)
                member_specs.append(
                    (
                        queued,
                        character,
                        side,
                        PlayerCombatantSpec(
                            fighter_key=f"{side}{index}",
                            character_id=character.id.hex,
                            name=character.name,
                            character_class=character.character_class,
                            race=character.race,
                            level=character.level,
                            hp=character.hp,
                            equipment_configuration=equipment,
                            active_art_ids=arts.art_ids,
                            active_art_snapshots=tuple(
                                slot.to_data() for slot in arts.slots
                            ),
                        ),
                    )
                )
        left = tuple(row[3] for row in member_specs if row[2] == "a")
        right = tuple(row[3] for row in member_specs if row[2] == "b")
        combat = create_player_versus_player_combat(
            uuid4(),
            left,
            right,
            ruleset_version=RULESET,
            flavor="Um grupo rival cruza a trilha.",
            opening_log="⚔️ O confronto pela trilha começa.",
        )
        collision = PvpveCollision(
            id=collision_id,
            server_id=queue_a.server_id,
            local_id=queue_a.local_id,
            roster_size=queue_a.roster_size,
            queue_a_id=queue_a.id,
            queue_b_id=queue_b.id,
            combat_id=combat.id,
            ruleset_version=RULESET,
            state_version=combat.version,
            combat_snapshot=encode(combat),
            status="active",
            created_at=now,
        )
        session.add(collision)
        await session.flush()
        queue_a.status = "matched"
        queue_b.status = "matched"
        queue_a.resolved_at = now
        queue_b.resolved_at = now
        activity_by_id = {}
        for queued, character, side, spec in member_specs:
            activity = await session.get(GameActivity, queued.game_activity_id)
            if activity is None:
                continue
            activity.content_id = PVPVE_CONTENT_ID
            activity.state_version = combat.version
            activity.ruleset_version = RULESET
            activity.last_valid_action_at = now
            activity_by_id[activity.id] = activity
            session.add(
                PvpveCollisionMember(
                    collision_id=collision.id,
                    character_id=character.id,
                    account_id=character.telegram_id,
                    game_activity_id=activity.id,
                    actor_key=spec.fighter_key,
                    side=side,
                    status="active",
                )
            )
        await session.flush()

        members = list(
            (
                await session.scalars(
                    select(PvpveCollisionMember)
                    .where(PvpveCollisionMember.collision_id == collision.id)
                    .order_by(PvpveCollisionMember.character_id)
                )
            ).all()
        )
        combat = await self._advance_round_ai(
            session,
            collision,
            members,
            characters_by_id,
            activity_by_id,
            combat,
        )
        if combat.version != collision.state_version:
            collision.combat_snapshot = encode(combat)
            collision.state_version = combat.version
            for row in members:
                fighter = combat.fighters.get(row.actor_key)
                character = characters_by_id.get(row.character_id)
                activity = activity_by_id.get(row.game_activity_id)
                if fighter is not None and character is not None:
                    character.hp = fighter.hp
                if activity is not None:
                    activity.state_version = combat.version
                    activity.last_valid_action_at = now
        if combat.result:
            await self._resolve_collision(
                session,
                collision,
                members,
                characters_by_id,
                activity_by_id,
                combat,
                now=now,
            )

    async def _advance_round_ai(
        self, session, collision, members, characters, activities, combat
    ):
        queues = {
            "a": await session.get(PvpveQueue, collision.queue_a_id),
            "b": await session.get(PvpveQueue, collision.queue_b_id),
        }
        member_by_actor = {row.actor_key: row for row in members}
        steps = 0
        while combat.result is None and steps < 64:
            actor_key = active_player_key(combat)
            member = member_by_actor.get(actor_key)
            queue = queues.get(member.side) if member is not None else None
            if (
                member is None
                or queue is None
                or queue.source_type != "round"
                or member.round_takeover
            ):
                break
            available = player_actions_for(combat, actor_key)
            candidates = []
            fighter = combat.fighters[actor_key]
            for action_id in allowed_actions(combat, actor_key):
                if action_id == "defend":
                    candidates.append((Decimal("-1"), action_id, None))
                    continue
                action = available.get(action_id)
                targets = action_target_ids(combat, action_id, actor_key=actor_key)
                if action is None or not targets:
                    continue
                score = action.coefficient * action.hit_count
                missing_hp = max(Decimal(0), fighter.stats.hp - fighter.hp)
                if missing_hp and action.heal_coefficient > 0:
                    score += action.heal_coefficient * min(
                        Decimal(1), missing_hp / fighter.stats.hp
                    )
                if action.self_barrier_coefficient > 0 and not fighter.barriers:
                    score += action.self_barrier_coefficient * Decimal("0.5")
                candidates.append((score, action_id, targets[0]))
            if not candidates:
                break
            _score, action_id, target_id = max(
                candidates, key=lambda candidate: (candidate[0], candidate[1])
            )
            updated = act(
                combat,
                action_id,
                target_id=target_id,
                actor_key=actor_key,
            )
            if updated.version == combat.version:
                break
            if action_id != "hold":
                member.contributed = True
            combat = updated
            steps += 1
        return combat

    async def _resolve_collision(
        self, session, collision, members, characters, activities, combat, *, now
    ) -> None:
        alive_a = any(
            fighter.hp > 0 and fighter.side == "player" for fighter in combat.fighters.values()
        )
        alive_b = any(
            fighter.hp > 0 and fighter.side == "enemy" for fighter in combat.fighters.values()
        )
        winner = "a" if alive_a and not alive_b else "b" if alive_b and not alive_a else None
        collision.winner_side = winner
        collision.resolved_at = now
        collision.status = "prey" if winner is not None else "failed"
        await self._record_match_history(session, members, now)
        queues = {
            "a": await session.get(PvpveQueue, collision.queue_a_id),
            "b": await session.get(PvpveQueue, collision.queue_b_id),
        }
        sides: dict[str, list[PvpveCollisionMember]] = {"a": [], "b": []}
        for member in members:
            sides[member.side].append(member)
            character = characters[member.character_id]
            activity = activities[member.game_activity_id]
            fighter = combat.fighters.get(member.actor_key)
            if winner == member.side and fighter is not None and fighter.hp > 0:
                member.status = "prey"
                member.domain_eligible = member.contributed
                continue
            member.status = "defeated"
            member.domain_eligible = False
            member.settled_at = now
            source_queue = queues.get(member.side)
            world = await session.scalar(
                select(WorldState)
                .where(WorldState.character_id == character.id)
                .with_for_update()
            )
            ended_round = False
            if source_queue is not None and source_queue.source_type == "round":
                ended_round = await self.road.finish_round_after_pvp_defeat(
                    session,
                    member,
                    character,
                    activity,
                    local_id=collision.local_id,
                    world=world,
                    now=now,
                )
            if not ended_round:
                activity.status = "failed"
                await self.road._recover_normal_pve_defeat(
                    session, character, collision.local_id, world
                )
        if winner is None:
            for queue in queues.values():
                if queue is not None:
                    await self._finish_one_group_proposal(session, queue, now, victory=False)
            return
        queue = queues[winner]
        if queue is not None:
            await session.scalar(
                select(PvpveQueue)
                .where(PvpveQueue.id == queue.id)
                .with_for_update()
            )
        survivors = sorted(sides[winner], key=lambda row: row.actor_key)
        if queue is None:
            collision.status = "failed"
            return
        await self._materialize_survivor_prey(
            session,
            collision,
            queue,
            survivors,
            characters,
            activities,
            now=now,
        )
        losing_queue_id = collision.queue_b_id if winner == "a" else collision.queue_a_id
        losing_queue = await session.get(PvpveQueue, losing_queue_id)
        if losing_queue is not None:
            await self._finish_one_group_proposal(
                session, losing_queue, now, victory=False
            )

    async def _materialize_survivor_prey(
        self, session, collision, queue, survivors, characters, activities, *, now
    ) -> None:
        survivors = [
            member
            for member in survivors
            if characters[member.character_id].hp > 0
            and activities[member.game_activity_id].status == "active"
        ]
        if not survivors:
            collision.status = "failed"
            return
        survivor_characters = [characters[member.character_id] for member in survivors]
        reference_level = max(character.level for character in survivor_characters)
        collision.prey_reference_level = reference_level
        prey_seed = sha256(f"pvpve-prey:{collision.id.hex}".encode()).hexdigest()
        if queue.source_type == "round":
            member = survivors[0]
            character = characters[member.character_id]
            activity = activities[member.game_activity_id]
            continued = await self.road.continue_round_after_pvp(
                session,
                collision,
                queue,
                member,
                character,
                activity,
                reference_level=reference_level,
                anchor=now,
            )
            if not continued:
                # PvP is already resolved. If the normal Ronda preflight ends
                # the batch (for example, insufficient Vigor), close this
                # collision without leaving an orphaned active prey member.
                collision.status = "completed"
                member.status = "settled"
                member.result_acknowledged = True
                member.domain_eligible = False
                member.settled_at = now
                if activity.status == "active":
                    activity.status = "failed"
                return
        elif queue.source_type == "group" and len(survivors) >= 2:
            proposal = await session.scalar(
                select(GroupActivityProposal)
                .where(GroupActivityProposal.id == queue.proposal_id)
                .with_for_update()
            )
            if proposal is None:
                for member in survivors:
                    activity = activities[member.game_activity_id]
                    activity.status = "failed"
                    member.status = "defeated"
                    member.domain_eligible = False
                    await self.road._recover_normal_pve_defeat(
                        session, characters[member.character_id], collision.local_id
                    )
                collision.status = "failed"
                return
            encounter_id = await self.road.group_hunts.materialize_queued_pve(
                session,
                proposal,
                survivor_characters,
                [activities[member.game_activity_id] for member in survivors],
                collision_id=collision.id,
                domain_eligible={
                    member.character_id: member.domain_eligible for member in survivors
                },
                reference_level=reference_level,
                seed=prey_seed,
            )
            proposal.activity_reference = encounter_id
        else:
            member = survivors[0]
            character = characters[member.character_id]
            activity = activities[member.game_activity_id]
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id)
            )
            profile = await self.road._available_local_profile(
                session, character, world, "hunt"
            )
            if profile is None or profile.local_id != collision.local_id:
                activity.status = "failed"
                member.status = "defeated"
                member.domain_eligible = False
                await self.road._recover_normal_pve_defeat(
                    session, character, collision.local_id, world
                )
                collision.status = "failed"
                return
            await self.road._materialize_manual_hunt(
                session,
                character,
                world,
                profile,
                activity=activity,
                collision_id=collision.id,
                domain_eligible=member.domain_eligible,
                reference_level=reference_level,
                seed=prey_seed,
            )
            if queue.proposal_id is not None:
                await self._release_proposal_reservations(session, queue.proposal_id)
        collision.status = "prey"
        for member in survivors:
            member.status = "prey"
            activities[member.game_activity_id].last_valid_action_at = now

    async def _materialize_queue_pve(
        self, session, queue, members, characters, activities, *, now
    ) -> None:
        by_character = {row.id: row for row in characters}
        activity_by_character = {row.character_id: row for row in activities}
        roster = [by_character.get(row.character_id) for row in members]
        if (
            len(roster) != queue.roster_size
            or any(item is None for item in roster)
            or len(activity_by_character) != queue.roster_size
        ):
            await self._cancel_queue(session, queue, members, activities, now)
            return
        roster = [item for item in roster if item is not None]
        if any(
            item.hp <= 0
            or activity_by_character[item.id].status != "active"
            or activity_by_character[item.id].content_id != PVPVE_QUEUE_CONTENT_ID
            for item in roster
        ):
            await self._cancel_queue(session, queue, members, activities, now)
            return
        worlds = list(
            (
                await session.scalars(
                    select(WorldState).where(
                        WorldState.character_id.in_([item.id for item in roster])
                    )
                )
            ).all()
        )
        world_by_character = {row.character_id: row for row in worlds}
        if len(world_by_character) != len(roster):
            await self._cancel_queue(session, queue, members, activities, now)
            return
        first_location = world_by_character[roster[0].id].location
        profiles = [
            await self.road._available_local_profile(
                session, item, world_by_character.get(item.id), "hunt"
            )
            for item in roster
        ]
        if any(
            profile is None
            or profile.local_id != queue.local_id
            or world_by_character[item.id].location != first_location
            for item, profile in zip(roster, profiles, strict=True)
        ):
            await self._cancel_queue(session, queue, members, activities, now)
            return
        queue.status = "expired"
        queue.resolved_at = now
        if queue.source_type == "group":
            proposal = await session.scalar(
                select(GroupActivityProposal)
                .where(GroupActivityProposal.id == queue.proposal_id)
                .with_for_update()
            )
            if proposal is None:
                await self._cancel_queue(session, queue, members, activities, now)
                return
            encounter_id = await self.road.group_hunts.materialize_queued_pve(
                session,
                proposal,
                roster,
                [activity_by_character[item.id] for item in roster],
            )
            proposal.activity_reference = encounter_id
        elif queue.source_type == "round":
            character = roster[0]
            await self.road.continue_round_after_queue(
                session,
                queue,
                character,
                activity_by_character[character.id],
                anchor=queue.expires_at,
            )
        else:
            character = roster[0]
            await self.road._materialize_manual_hunt(
                session,
                character,
                world_by_character[character.id],
                profiles[0],
                activity=activity_by_character[character.id],
            )

    async def _cancel_queue(self, session, queue, members, activities, now) -> None:
        queue.status = "cancelled"
        queue.resolved_at = now
        if queue.source_type == "round":
            queue_members = members or list(
                (
                    await session.scalars(
                        select(PvpveQueueMember).where(
                            PvpveQueueMember.queue_id == queue.id
                        )
                    )
                ).all()
            )
            activity_by_id = {row.id: row for row in activities}
            for member in queue_members:
                activity = activity_by_id.get(member.game_activity_id)
                if activity is None:
                    activity = await session.get(GameActivity, member.game_activity_id)
                if activity is not None:
                    await self.road.finish_round_after_queue_invalid(
                        session, activity, now=now
                    )
        for activity in activities:
            if activity.status == "active" and activity.content_id == PVPVE_QUEUE_CONTENT_ID:
                activity.status = "completed"
                activity.last_valid_action_at = now
        if queue.proposal_id is not None:
            proposal = await session.get(
                GroupActivityProposal, queue.proposal_id, with_for_update=True
            )
            if proposal is not None and proposal.status == "started":
                proposal.status = "cancelled"
                proposal.cancel_reason = "pvpve_context_changed"
                proposal.finished_at = now
                proposal.revision += 1
                await self._release_proposal_reservations(session, proposal.id)

    async def _record_match_history(self, session, members, now) -> None:
        accounts_by_side = {
            side: {row.account_id for row in members if row.side == side}
            for side in ("a", "b")
        }
        pairs = sorted(
            {
                (min(a, b), max(a, b))
                for a in accounts_by_side["a"]
                for b in accounts_by_side["b"]
                if a != b
            }
        )
        accounts = sorted(accounts_by_side["a"] | accounts_by_side["b"])
        if accounts:
            await session.execute(
                insert(PvpveAccountCooldown)
                .values(
                    [
                        {"account_id": account_id, "pvp_until": now + PVP_COOLDOWN}
                        for account_id in accounts
                    ]
                )
                .on_conflict_do_nothing(index_elements=["account_id"])
            )
            cooldowns = list(
                (
                    await session.scalars(
                        select(PvpveAccountCooldown)
                        .where(PvpveAccountCooldown.account_id.in_(accounts))
                        .order_by(PvpveAccountCooldown.account_id)
                        .with_for_update()
                    )
                ).all()
            )
            for row in cooldowns:
                row.pvp_until = max(row.pvp_until or now, now + PVP_COOLDOWN)
        if pairs:
            await session.execute(
                insert(PvpveAccountPair)
                .values([{"account_a": a, "account_b": b, "last_match_at": now} for a, b in pairs])
                .on_conflict_do_nothing(index_elements=["account_a", "account_b"])
            )
            pair_rows = list(
                (
                    await session.scalars(
                        select(PvpveAccountPair)
                        .where(
                            tuple_(
                                PvpveAccountPair.account_a,
                                PvpveAccountPair.account_b,
                            ).in_(pairs)
                        )
                        .order_by(PvpveAccountPair.account_a, PvpveAccountPair.account_b)
                        .with_for_update()
                    )
                ).all()
            )
            for row in pair_rows:
                row.last_match_at = now

    async def _finish_one_group_proposal(
        self, session, queue, now, *, victory: bool
    ) -> None:
        if queue.proposal_id is None:
            return
        proposal = await session.scalar(
            select(GroupActivityProposal)
            .where(GroupActivityProposal.id == queue.proposal_id)
            .with_for_update()
        )
        if proposal is not None and proposal.status == "started":
            proposal.status = "completed" if victory else "failed"
            proposal.finished_at = now
            proposal.revision += 1
        await self._release_proposal_reservations(session, queue.proposal_id)

    async def _finish_group_proposals(
        self, session, collision, now, *, victory: bool
    ) -> None:
        for queue_id in (collision.queue_a_id, collision.queue_b_id):
            queue = await session.get(PvpveQueue, queue_id)
            if queue is not None and queue.proposal_id is not None:
                await self._finish_one_group_proposal(
                    session, queue, now, victory=victory
                )

    async def _release_proposal_reservations(self, session, proposal_id: UUID) -> None:
        rows = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == proposal_id)
                    .with_for_update()
                )
            ).all()
        )
        for row in rows:
            row.reservation_state = "released"

    async def _lock_queue_roster(self, session, queue_id):
        members = list(
            (
                await session.scalars(
                    select(PvpveQueueMember)
                    .where(PvpveQueueMember.queue_id == queue_id)
                    .order_by(PvpveQueueMember.character_id)
                    .with_for_update()
                )
            ).all()
        )
        characters = await self._lock_characters(
            session, [row.character_id for row in members]
        )
        activities = list(
            (
                await session.scalars(
                    select(GameActivity)
                    .where(GameActivity.id.in_([row.game_activity_id for row in members]))
                    .order_by(GameActivity.id)
                    .with_for_update()
                )
            ).all()
        )
        return members, characters, activities

    async def _lock_characters(self, session, character_ids):
        if not character_ids:
            return []
        return list(
            (
                await session.scalars(
                    select(Character)
                    .where(Character.id.in_(character_ids))
                    .order_by(Character.id)
                    .with_for_update()
                )
            ).all()
        )

    async def _match_lock(self, session, local_id: str, roster_size: int) -> None:
        key = _lock_key(self.server_id, local_id, roster_size)
        await session.execute(select(func.pg_advisory_xact_lock(key)))

    async def _character(self, session, actor: int):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    def _queue_view(self, character, location, activity, queue, now) -> RoadView:
        remaining = max(0, int((queue.expires_at - now).total_seconds() + 0.999999))
        minutes, seconds = divmod(remaining, 60)
        return RoadView(
            "hunt_queue",
            character.id,
            _location_label(queue.local_id),
            activity_id=activity.id,
            state_version=activity.state_version,
            vigor=character.vigor,
            max_vigor=character.max_vigor,
            name=character.name,
            hp=character.hp,
            max_hp=character.max_hp,
            result_text=f"Busca por grupo rival · até {minutes:02d}:{seconds:02d}",
            pvpve_round_queue=queue.source_type == "round",
        )
