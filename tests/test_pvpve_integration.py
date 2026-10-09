from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from asterion.application.groups import GroupService
from asterion.application.road import HUNT_CONTENT, RoadService
from asterion.bot.road_ui import render_road
from asterion.domain.combat import active_player_key
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CombatRecord,
    Encounter,
    GameActivity,
    HuntContext,
    PvpveAccountCooldown,
    PvpveAccountPair,
    PvpveCollision,
    PvpveCollisionMember,
    PvpveDomainGrant,
    PvpveQueue,
    PvpveQueueMember,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

ACTORS = tuple(range(995101, 995109))
NAMES = tuple(f"Rastro{letter}" for letter in "abcdefgh")


async def _seed_hunters(database, count: int = 2):
    sessions = database[1]
    characters = {}
    async with sessions.begin() as session:
        for index, actor in enumerate(ACTORS[:count]):
            character_id = uuid4()
            characters[actor] = character_id
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    id=character_id,
                    telegram_id=actor,
                    server_id="ocaso",
                    name=NAMES[index],
                    race="remanescente",
                    character_class="sentinela",
                    stage="road_active",
                    ruleset_version="gdd-1.5.0-baseline-1.0",
                    level=1,
                    xp=1000,
                    hp=Decimal("702"),
                    max_hp=Decimal("702"),
                    vigor=100,
                    max_vigor=100,
                    crowns=0,
                )
            )
            session.add_all(
                [
                    Quest(
                        character_id=character_id,
                        quest_id="P1",
                        title="Vozes na Estrada",
                        status="completed",
                        step=7,
                        content_version="tdo-1.0.15",
                    ),
                    WorldState(
                        character_id=character_id,
                        region="Terras do Ocaso",
                        location="Estrada das Cinzas",
                    ),
                    Unlock(
                        character_id=character_id,
                        unlock_id="hunt_manual.estrada_das_cinzas",
                    ),
                ]
            )
    return characters, RoadService(sessions, "ocaso")


async def _join_roster(groups, roster: tuple[int, ...]):
    leader = roster[0]
    await groups.create_group(leader)
    for member in roster[1:]:
        current = await groups.group(leader)
        invite = await groups.invite(
            leader,
            NAMES[ACTORS.index(member)],
            expected_group_revision=current.revision,
            now=datetime.now(UTC),
        )
        await groups.respond_invite(
            member,
            invite.invite_id,
            expected_revision=invite.revision,
            accept=True,
            now=datetime.now(UTC) + timedelta(seconds=1),
        )
    return await groups.group(leader)


async def _start_group_hunt(groups, road, characters, leader, roster):
    proposal = await groups.propose_activity(
        leader,
        activity_type="hunt_group",
        participant_character_ids=tuple(characters[actor] for actor in roster),
        eligibility_resolver=road.group_hunts.eligibility,
        context_payload=await road.group_hunts.context_payload(leader),
        now=datetime.now(UTC),
    )
    by_character = {character_id: actor for actor, character_id in characters.items()}
    for participant in proposal.participants:
        if (
            participant.character_id != characters[leader]
            and participant.eligibility != "ineligible"
        ):
            proposal = await groups.respond_activity(
                by_character[participant.character_id],
                proposal.proposal_id,
                expected_revision=proposal.revision,
                accept=True,
                now=datetime.now(UTC) + timedelta(seconds=1),
            )
    return await groups.start_activity(
        leader,
        proposal.proposal_id,
        expected_revision=proposal.revision,
        eligibility_resolver=road.group_hunts.eligibility,
        create_activity=road.group_hunts.create_activity,
        now=datetime.now(UTC) + timedelta(seconds=2),
    )


async def _collision_for(database, character_id):
    async with database[1]() as session:
        member = await session.scalar(
            select(PvpveCollisionMember).where(
                PvpveCollisionMember.character_id == character_id
            )
        )
        return await session.get(PvpveCollision, member.collision_id)


@pytest.mark.asyncio
async def test_manual_pvpve_match_reconnect_and_stale_action_are_idempotent(database):
    characters, road = await _seed_hunters(database)
    first = await road.start_hunt(ACTORS[0])
    assert first is not None and first.kind == "hunt_queue"

    second = await road.start_hunt(ACTORS[1])
    assert second is not None and second.kind == "combat"
    assert second.combat_context == "pvpve"
    assert second.combat is not None
    assert second.combat.external_consumables_allowed is False

    resumed = [await road.resume(actor) for actor in ACTORS[:2]]
    assert all(view is not None and view.kind == "combat" for view in resumed)
    assert all(view.encounter_id == second.encounter_id for view in resumed)
    assert len({view.combat_actor_key for view in resumed}) == 2
    active_key = active_player_key(second.combat)
    active_view = next(view for view in resumed if view.combat_actor_key == active_key)
    screen = render_road(active_view)
    callbacks = [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]
    assert callbacks and all(len(callback.encode()) < 64 for callback in callbacks)

    collision = await _collision_for(database, characters[ACTORS[0]])
    assert collision is not None and collision.status == "active"
    async with database[1]() as session:
        combat = decode(
            collision.combat_snapshot,
            collision.combat_id,
            collision.ruleset_version,
            collision.state_version,
        )
        actor_key = active_player_key(combat)
        assert actor_key is not None
        actor_id = combat.fighters[actor_key].id
        actor = next(
            account
            for account, character_id in characters.items()
            if character_id.hex == actor_id
        )
        target = next(
            fighter
            for fighter in combat.fighters.values()
            if fighter.side != combat.fighters[actor_key].side
        )
        activity_id = await session.scalar(
            select(PvpveCollisionMember.game_activity_id).where(
                PvpveCollisionMember.collision_id == collision.id,
                PvpveCollisionMember.character_id == actor_id,
            )
        )

    stale_version = collision.state_version
    changed = await road.action(
        actor,
        activity_id,
        stale_version,
        "attack",
        target_id=target.id,
    )
    assert changed is not None and changed.kind == "combat"
    assert changed.state_version == stale_version + 1

    duplicate = await road.action(
        actor,
        activity_id,
        stale_version,
        "attack",
        target_id=target.id,
    )
    assert duplicate is not None and duplicate.state_version == changed.state_version
    async with database[1]() as session:
        persisted = await session.get(PvpveCollision, collision.id)
        assert persisted.state_version == changed.state_version
        characters_after_pvp = list(
            (
                await session.scalars(
                    select(Character).where(Character.id.in_(characters.values()))
                )
            ).all()
        )
        assert {row.vigor for row in characters_after_pvp} == {100}
        assert (
            await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id.in_(characters.values())
                )
            )
            is None
        )


@pytest.mark.asyncio
async def test_pvp_winner_materializes_one_prey_and_freezes_domain_eligibility(database):
    characters, road = await _seed_hunters(database)
    await road.start_hunt(ACTORS[0])
    second = await road.start_hunt(ACTORS[1])
    assert second is not None and second.kind == "combat"
    collision = await _collision_for(database, characters[ACTORS[0]])
    assert collision is not None

    async with database[1].begin() as session:
        persisted = await session.get(PvpveCollision, collision.id)
        assert persisted is not None
        combat = decode(
            persisted.combat_snapshot,
            persisted.combat_id,
            persisted.ruleset_version,
            persisted.state_version,
        )
        actor_key = active_player_key(combat)
        assert actor_key is not None
        actor_fighter = combat.fighters[actor_key]
        opponents = {
            key: replace(fighter, hp=Decimal("1"))
            if fighter.side != actor_fighter.side
            else fighter
            for key, fighter in combat.fighters.items()
        }
        persisted.combat_snapshot = encode(replace(combat, fighters=opponents))
        acting_character = next(
            account
            for account, character_id in characters.items()
            if character_id.hex == actor_fighter.id
        )
        acting_activity = await session.scalar(
            select(PvpveCollisionMember.game_activity_id).where(
                PvpveCollisionMember.collision_id == collision.id,
                PvpveCollisionMember.character_id == UUID(hex=actor_fighter.id),
            )
        )
        activity_version = persisted.state_version
        target = next(
            fighter
            for fighter in opponents.values()
            if fighter.side != actor_fighter.side
        )

    result = await road.action(
        acting_character,
        acting_activity,
        activity_version,
        "attack",
        target_id=target.id,
    )
    assert result is not None

    async with database[1]() as session:
        persisted = await session.get(PvpveCollision, collision.id)
        members = list(
            (
                await session.scalars(
                    select(PvpveCollisionMember).where(
                        PvpveCollisionMember.collision_id == collision.id
                    )
                )
            ).all()
        )
        prey_contexts = list(
            (
                await session.scalars(
                    select(HuntContext).where(
                        HuntContext.pvpve_collision_id == collision.id
                    )
                )
            ).all()
        )
        activities = list(
            (
                await session.scalars(
                    select(GameActivity).where(
                        GameActivity.id.in_([row.game_activity_id for row in members])
                    )
                )
            ).all()
        )
        assert persisted.status == "prey"
        assert sum(row.status == "prey" for row in members) == 1
        assert sum(row.status == "defeated" for row in members) == 1
        winner = next(row for row in members if row.status == "prey")
        winner_id = winner.character_id
        winner_activity_id = winner.game_activity_id
        winner_actor = winner.account_id
        assert winner.contributed is True
        assert winner.domain_eligible is True
        assert len(prey_contexts) == 1
        assert prey_contexts[0].pvpve_domain_eligible is True
        winner_activity = next(
            row for row in activities if row.id == winner.game_activity_id
        )
        assert winner_activity.content_id == HUNT_CONTENT
        assert (
            await session.scalar(
                select(CombatRecord.id)
                .join(Encounter)
                .where(Encounter.game_activity_id == winner.game_activity_id)
            )
            is not None
        )

    pair = (min(ACTORS[:2]), max(ACTORS[:2]))
    async with database[1].begin() as session:
        account_pair = await session.get(PvpveAccountPair, pair, with_for_update=True)
        assert account_pair is not None
        account_pair.domain_until = datetime.now(UTC) + timedelta(minutes=30)
        character = await session.get(Character, winner_id)
        assert character is not None
        xp_before = character.xp
        crowns_before = character.crowns
        vigor_before = character.vigor
        activity = await session.get(GameActivity, winner_activity_id)
        record = await session.scalar(
            select(CombatRecord)
            .join(Encounter, Encounter.id == CombatRecord.encounter_id)
            .where(Encounter.game_activity_id == winner_activity_id)
        )
        assert activity is not None and record is not None
        prey = decode(
            record.snapshot,
            record.id,
            activity.ruleset_version,
            activity.state_version,
        )
        prey_fighters = dict(prey.fighters)
        prey_fighters["enemy"] = replace(prey_fighters["enemy"], hp=Decimal("1"))
        record.snapshot = encode(replace(prey, fighters=prey_fighters))
        prey_version = activity.state_version

    prey_result = await road.action(
        winner_actor,
        winner_activity_id,
        prey_version,
        "attack",
        target_id="enemy",
    )
    assert prey_result is not None and prey_result.kind == "hunt_victory"
    duplicate_prey_callback = await road.action(
        winner_actor,
        winner_activity_id,
        prey_version,
        "attack",
        target_id="enemy",
    )
    assert duplicate_prey_callback is not None
    assert duplicate_prey_callback.kind == "hunt_victory"

    async with database[1]() as session:
        character = await session.get(Character, winner_id)
        domain_grant = await session.get(PvpveDomainGrant, (collision.id, winner_id))
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == winner_id,
                RewardEvent.source_id == f"activity:{winner_activity_id}",
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
        )
        assert character is not None
        assert character.xp > xp_before
        assert character.crowns > crowns_before
        assert character.vigor == vigor_before - 2
        assert domain_grant is not None
        assert domain_grant.status == "locked"
        assert domain_grant.crowns == 0 and domain_grant.material_id is None
        assert any(component.kind == "xp" for component in components)
        assert any(component.kind == "crowns" for component in components)
        assert all(
            component.payload.get("source") != "dominio_do_rastro"
            for component in components
        )


@pytest.mark.asyncio
async def test_unmatched_manual_queue_falls_back_to_normal_pve_without_spending_vigor(
    database, monkeypatch
):
    characters, road = await _seed_hunters(database)
    queue_view = await road.start_hunt(ACTORS[0])
    assert queue_view is not None and queue_view.kind == "hunt_queue"
    async with database[1]() as session:
        activity_id = await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == characters[ACTORS[0]],
                GameActivity.status == "active",
            )
        )
        queue = await session.scalar(
            select(PvpveQueue)
            .join(PvpveQueueMember)
            .where(PvpveQueueMember.game_activity_id == activity_id)
        )
        assert queue is not None
        expires_at = queue.expires_at

    monkeypatch.setattr(
        "asterion.application.pvpve._utcnow",
        lambda: expires_at.replace(tzinfo=UTC) + timedelta(seconds=1),
    )
    assert await road.pvpve.refresh_queue(ACTORS[0], activity_id)
    resumed = await road.resume(ACTORS[0])
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.combat_context == "road"
    async with database[1]() as session:
        character = await session.get(Character, characters[ACTORS[0]])
        activity = await session.get(GameActivity, activity_id)
        assert character.vigor == 100
        assert activity.content_id == HUNT_CONTENT


@pytest.mark.asyncio
async def test_waiting_queue_can_be_cancelled_without_cost_or_collision(database):
    characters, road = await _seed_hunters(database)
    queue_view = await road.start_hunt(ACTORS[0])
    assert queue_view is not None and queue_view.kind == "hunt_queue"
    screen = render_road(queue_view)
    callbacks = [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]
    assert callbacks
    assert all(len(callback.encode()) < 64 for callback in callbacks)
    assert any(callback.startswith("road:pvpve:cancel:") for callback in callbacks)

    cancelled = await road.pvpve.cancel_queue(ACTORS[0], queue_view.activity_id)
    assert cancelled is not None and cancelled.kind == "road"
    duplicate = await road.pvpve.cancel_queue(ACTORS[0], queue_view.activity_id)
    assert duplicate is not None and duplicate.kind == "road"
    async with database[1]() as session:
        character = await session.get(Character, characters[ACTORS[0]])
        activity = await session.get(GameActivity, queue_view.activity_id)
        queue = await session.scalar(
            select(PvpveQueue)
            .join(PvpveQueueMember)
            .where(PvpveQueueMember.game_activity_id == queue_view.activity_id)
        )
        collision = await session.scalar(select(PvpveCollision))
        assert character.vigor == 100
        assert activity.status == "completed"
        assert queue.status == "cancelled"
        assert collision is None


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.parametrize("roster_size", (2, 3, 4))
async def test_group_pvpve_matches_equal_rosters_and_reconnects_all_members(
    database, roster_size
):
    participant_count = roster_size * 2
    characters, road = await _seed_hunters(database, count=participant_count)
    groups = GroupService(database[1], "ocaso")
    left_roster = ACTORS[:roster_size]
    right_roster = ACTORS[roster_size:participant_count]
    left_group = await _join_roster(groups, left_roster)
    right_group = await _join_roster(groups, right_roster)
    assert len(left_group.members) == len(right_group.members) == roster_size

    left = await _start_group_hunt(
        groups, road, characters, left_roster[0], left_roster
    )
    assert left.started
    async with database[1]() as session:
        waiting = await session.scalar(
            select(PvpveQueue).where(
                PvpveQueue.proposal_id == left.proposal.proposal_id
            )
        )
        assert waiting is not None and waiting.status == "waiting"

    right = await _start_group_hunt(
        groups, road, characters, right_roster[0], right_roster
    )
    assert right.started

    async with database[1]() as session:
        collision = await session.scalar(select(PvpveCollision))
        assert collision is not None and collision.roster_size == roster_size
        members = list(
            (
                await session.scalars(
                    select(PvpveCollisionMember).where(
                        PvpveCollisionMember.collision_id == collision.id
                    )
                )
            ).all()
        )
        assert len(members) == participant_count
        assert {member.side for member in members} == {"a", "b"}
        assert all(
            sum(member.side == side for member in members) == roster_size
            for side in ("a", "b")
        )
        combat = decode(
            collision.combat_snapshot,
            collision.combat_id,
            collision.ruleset_version,
            collision.state_version,
        )
        assert combat.party_mode is True
        assert combat.manual_sides == ("player", "enemy")
        assert len(combat.fighters) == participant_count
        assert len(combat.player_configuration_snapshots) == participant_count

    for actor in ACTORS[:participant_count]:
        view = await road.resume(actor)
        assert view is not None and view.kind == "combat"
        assert view.combat_context == "pvpve"
        assert view.encounter_id == collision.id
        assert view.combat_actor_key in view.combat.fighters


@pytest.mark.asyncio
async def test_pair_cooldowns_are_account_based_and_have_exact_boundaries(database):
    _, road = await _seed_hunters(database)
    now = datetime.now(UTC)
    account_a, account_b = ACTORS[:2]
    async with database[1].begin() as session:
        session.add_all(
            [
                PvpveAccountCooldown(account_id=account_a, pvp_until=now + timedelta(minutes=3)),
                PvpveAccountCooldown(account_id=account_b, pvp_until=now + timedelta(minutes=3)),
                PvpveAccountPair(
                    account_a=min(account_a, account_b),
                    account_b=max(account_a, account_b),
                    last_match_at=now,
                    domain_until=now + timedelta(minutes=30),
                ),
            ]
        )
    async with database[1].begin() as session:
        assert not await road.pvpve._pairing_available(
            session, {account_a}, {account_b}, now + timedelta(minutes=2, seconds=59)
        )
        assert not await road.pvpve._pairing_available(
            session, {account_a}, {account_b}, now + timedelta(minutes=9, seconds=59)
        )
        assert await road.pvpve._pairing_available(
            session, {account_a}, {account_b}, now + timedelta(minutes=10)
        )
        pair = await session.get(
            PvpveAccountPair,
            (min(account_a, account_b), max(account_a, account_b)),
        )
        assert pair is not None and pair.domain_until == now + timedelta(minutes=30)
