from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.group_hunts import group_hunt_scaling
from asterion.application.groups import GroupError, GroupService
from asterion.application.road import ROAD, RoadService
from asterion.bot.groups_ui import render_hunt_roster
from asterion.domain.combat import active_player_key
from asterion.domain.road import creature_for
from asterion.infrastructure.db.models import (
    Account,
    Character,
    GameActivity,
    GroupActivityParticipant,
    GroupHuntEncounter,
    GroupHuntMember,
    HuntContext,
    PvpveQueue,
    Quest,
    RewardEvent,
    Unlock,
    WorldState,
)

ACTORS = (882001, 882002, 882003, 882004)
NAMES = ("Alpha", "Bravo", "Cedar", "Doran")
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("roster_size", "hp_factor", "attack_factor"),
    (
        (2, Decimal("1.72"), Decimal("1.08")),
        (3, Decimal("2.44"), Decimal("1.16")),
        (4, Decimal("3.16"), Decimal("1.24")),
    ),
)
def test_group_hunt_scaling_is_exact_and_only_changes_hp_attack(
    roster_size, hp_factor, attack_factor
):
    factors = group_hunt_scaling(roster_size)
    assert factors.hp == hp_factor
    assert factors.attack == attack_factor
    assert factors.defense == Decimal(1)
    assert factors.agility == Decimal(1)
    with pytest.raises(ValueError):
        group_hunt_scaling(1)


async def _seed_hunters(database, count: int = 2):
    sessions = database[1]
    ids = {}
    async with sessions.begin() as session:
        for actor, name in zip(ACTORS[:count], NAMES[:count], strict=True):
            character_id = uuid4()
            ids[name] = character_id
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    id=character_id,
                    telegram_id=actor,
                    server_id="ocaso",
                    name=name,
                    race="remanescente",
                    character_class="sentinela",
                    stage="road_active",
                    ruleset_version="tdo-1.0.15",
                    level=60,
                    xp=0,
                    hp=Decimal("1000"),
                    max_hp=Decimal("1000"),
                    vigor=100,
                    max_vigor=100,
                    crowns=0,
                )
            )
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id="P1",
                    title="Vozes na Estrada",
                    status="completed",
                    step=7,
                    content_version="tdo-1.0.15",
                )
            )
            session.add(
                WorldState(
                    character_id=character_id,
                    region="Terras do Ocaso",
                    location=ROAD,
                )
            )
            session.add(
                Unlock(
                    character_id=character_id,
                    unlock_id="hunt_manual.estrada_das_cinzas",
                )
            )
    return dict(zip(NAMES[:count], ACTORS[:count], strict=True)), ids


async def _join_group(groups, actors, count: int):
    group = await groups.create_group(actors[NAMES[0]])
    for index in range(1, count):
        group = await groups.group(actors[NAMES[0]])
        invite = await groups.invite(
            actors[NAMES[0]],
            NAMES[index],
            expected_group_revision=group.revision,
            now=NOW,
        )
        await groups.respond_invite(
            actors[NAMES[index]],
            invite.invite_id,
            expected_revision=invite.revision,
            accept=True,
            now=NOW + timedelta(seconds=1),
        )
    return await groups.group(actors[NAMES[0]])


async def _ready_group_hunt(groups, road, actors, ids, group):
    proposal = await groups.propose_activity(
        actors[NAMES[0]],
        activity_type="hunt_group",
        participant_character_ids=tuple(member.character_id for member in group.members),
        eligibility_resolver=road.group_hunts.eligibility,
        context_payload=await road.group_hunts.context_payload(actors[NAMES[0]]),
        now=NOW,
    )
    for member in proposal.participants:
        if member.name != NAMES[0] and member.eligibility != "ineligible":
            proposal = await groups.respond_activity(
                actors[member.name],
                proposal.proposal_id,
                expected_revision=proposal.revision,
                accept=True,
                now=NOW + timedelta(seconds=1),
            )
    started = await groups.start_activity(
        actors[NAMES[0]],
        proposal.proposal_id,
        expected_revision=proposal.revision,
        eligibility_resolver=road.group_hunts.eligibility,
        create_activity=road.group_hunts.create_activity,
        now=NOW + timedelta(seconds=2),
    )
    await _materialize_group_queue_without_opponent(
        road, actors[NAMES[0]], proposal.proposal_id
    )
    return started


async def _materialize_group_queue_without_opponent(road, actor, proposal_id):
    """Use the public immediate no-rival continuation for a group Hunt."""
    async with road.sessions() as session:
        queue = await session.scalar(
            select(PvpveQueue).where(PvpveQueue.proposal_id == proposal_id)
        )
    if queue is None or queue.status != "waiting":
        return
    view = await road.pvpve.continue_queue(actor, queue.id)
    assert view is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("roster_size", "hp_factor", "attack_factor"),
    (
        (2, "1.72", "1.08"),
        (3, "2.44", "1.16"),
        (4, "3.16", "1.24"),
    ),
)
async def test_group_hunt_ready_check_freezes_roster_and_reconnects(
    database, monkeypatch, roster_size, hp_factor, attack_factor
):
    actors, ids = await _seed_hunters(database, count=4)
    levels = {name: 60 - index * 10 for index, name in enumerate(NAMES)}
    async with database[1].begin() as session:
        for name, character_id in ids.items():
            character = await session.get(Character, character_id)
            assert character is not None
            character.level = levels[name]
    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=4)
    selected_names = set(NAMES[:roster_size])
    selected = tuple(
        member.character_id for member in group.members if member.name in selected_names
    )
    screen = render_hunt_roster(group)
    callbacks = [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]
    assert callbacks and all(len(callback.encode()) < 64 for callback in callbacks)
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_creature",
        lambda _seed, _level, profile=None: creature_for("dog_cinereo"),
    )
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_variant",
        lambda _seed, _creature, profile=None: None,
    )
    proposal = await groups.propose_activity(
        actors[NAMES[0]],
        activity_type="hunt_group",
        participant_character_ids=selected,
        eligibility_resolver=road.group_hunts.eligibility,
        context_payload=await road.group_hunts.context_payload(actors[NAMES[0]]),
        now=NOW,
    )
    assert proposal.status == "pending"
    assert len(proposal.participants) == roster_size
    confirmed = proposal
    for participant in proposal.participants:
        if participant.name != NAMES[0] and participant.eligibility != "ineligible":
            confirmed = await groups.respond_activity(
                actors[participant.name],
                confirmed.proposal_id,
                expected_revision=confirmed.revision,
                accept=True,
                now=NOW + timedelta(seconds=1),
            )
    started = await groups.start_activity(
        actors[NAMES[0]],
        proposal.proposal_id,
        expected_revision=confirmed.revision,
        eligibility_resolver=road.group_hunts.eligibility,
        create_activity=road.group_hunts.create_activity,
        now=NOW + timedelta(seconds=2),
    )
    assert started.started
    await _materialize_group_queue_without_opponent(
        road, actors[NAMES[0]], proposal.proposal_id
    )

    async with database[1]() as session:
        encounter = await session.scalar(
            select(GroupHuntEncounter).where(
                GroupHuntEncounter.proposal_id == proposal.proposal_id
            )
        )
        members = list(
            (
                await session.scalars(
                    select(GroupHuntMember).where(
                        GroupHuntMember.group_hunt_encounter_id == encounter.id
                    )
                )
            ).all()
        )
        assert encounter.roster_size == roster_size
        assert encounter.reference_level == 60
        assert encounter.scaling_snapshot["hp_factor"] == hp_factor
        assert encounter.scaling_snapshot["attack_factor"] == attack_factor
        assert {member.character_id for member in members} == set(selected)
        assert len({member.game_activity_id for member in members}) == roster_size
        contexts = list(
            (
                await session.scalars(
                    select(HuntContext).where(
                        HuntContext.game_activity_id.in_(
                            [member.game_activity_id for member in members]
                        )
                    )
                )
            ).all()
        )
        assert len(contexts) == roster_size

    member_by_character = {member.character_id: member for member in members}
    for name in NAMES[:roster_size]:
        view = await road.resume(actors[name])
        assert view is not None and view.kind == "combat"
        assert view.combat_context == "group_hunt"
        assert view.combat.party_mode
        assert view.encounter_id == encounter.id
        assert view.state_version == encounter.state_version
        assert view.combat_actor_key == member_by_character[ids[name]].actor_key
        assert view.combat.fighters[view.combat_actor_key].level == levels[name]

    # Social members outside the frozen roster remain free to propose or travel.
    async with database[1]() as session:
        for name in NAMES[roster_size:]:
            unselected_activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == ids[name], GameActivity.status == "active"
                )
            )
            assert unselected_activity is None


@pytest.mark.asyncio
async def test_group_hunt_victory_uses_individual_settlement_and_duplicate_callback_is_safe(
    database, monkeypatch
):
    actors, ids = await _seed_hunters(database, count=2)
    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=2)
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_creature",
        lambda _seed, _level, profile=None: creature_for("dog_cinereo"),
    )
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_variant",
        lambda _seed, _creature, profile=None: None,
    )
    started = await _ready_group_hunt(groups, road, actors, ids, group)
    assert started.started
    view = await road.resume(actors[NAMES[0]])
    assert view is not None and view.kind == "combat"

    async with database[1]() as session:
        members = list(
            (
                await session.scalars(
                    select(GroupHuntMember).where(
                        GroupHuntMember.group_hunt_encounter_id == view.encounter_id
                    )
                )
            ).all()
        )
    # Rebuild the actor mapping from persisted IDs; SQL row order is not a social ordering.
    async with database[1]() as session:
        characters = list(
            (
                await session.scalars(
                    select(Character).where(Character.id.in_(ids.values()))
                )
            ).all()
        )
    telegram_by_id = {character.id: character.telegram_id for character in characters}
    actor_by_fighter = {
        member.actor_key: telegram_by_id[member.character_id] for member in members
    }

    for _ in range(120):
        if view.kind != "combat" or view.combat.result:
            break
        active_key = active_player_key(view.combat)
        assert active_key in actor_by_fighter
        actor = actor_by_fighter[active_key]
        member = next(row for row in members if row.actor_key == active_key)
        activity = await road.resume(actor)
        assert activity is not None and activity.kind == "combat"
        view = await road.action(
            actor,
            member.game_activity_id,
            activity.state_version,
            "attack",
        )
        assert view is not None
    assert view is not None and view.kind == "hunt_victory"
    assert view.combat_context == "group_hunt"

    async with database[1]() as session:
        activities = list(
            (
                await session.scalars(
                    select(GameActivity).where(
                        GameActivity.id.in_([member.game_activity_id for member in members])
                    )
                )
            ).all()
        )
        rewards = list(
            (
                await session.scalars(
                    select(RewardEvent).where(
                        RewardEvent.character_id.in_(ids.values())
                    )
                )
            ).all()
        )
        participants = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant).where(
                        GroupActivityParticipant.proposal_id == started.proposal.proposal_id
                    )
                )
            ).all()
        )
        assert all(activity.status == "completed" for activity in activities)
        assert len([event for event in rewards if event.source_id.startswith("activity:")]) == 2
        assert all(row.reservation_state == "released" for row in participants)
        characters = list(
            (
                await session.scalars(
                    select(Character).where(Character.id.in_(ids.values()))
                )
            ).all()
        )
        assert {character.vigor for character in characters} == {98}

    for name in NAMES[:2]:
        member = next(row for row in members if row.character_id == ids[name])
        current = await road.action(
            actors[name], member.game_activity_id, view.state_version, "attack"
        )
        assert current is not None
        await road.acknowledge_result(actors[name])

    async with database[1]() as session:
        rewards_after = list(
            (
                await session.scalars(
                    select(RewardEvent).where(RewardEvent.character_id.in_(ids.values()))
                )
            ).all()
        )
        assert (
            len([event for event in rewards_after if event.source_id.startswith("activity:")])
            == 2
        )


@pytest.mark.asyncio
async def test_pending_road_receipt_cannot_leave_a_one_person_group_hunt(database):
    actors, ids = await _seed_hunters(database, count=2)
    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=2)
    pending_activity_id = uuid4()
    async with database[1].begin() as session:
        session.add(
            GameActivity(
                id=pending_activity_id,
                character_id=ids[NAMES[1]],
                content_id="road_manual_hunt",
                status="completed",
                state_version=1,
                ruleset_version="tdo-1.0.15",
                last_valid_action_at=NOW,
            )
        )
        session.add(
            HuntContext(
                game_activity_id=pending_activity_id,
                character_id=ids[NAMES[1]],
                local_id="estrada_das_cinzas",
                creature_id="dog_cinereo",
                category="common",
                enemy_level=60,
                seed="pending-result",
                loot_profile="hunt",
                result_acknowledged=False,
            )
        )

    with pytest.raises(GroupError, match="group_roster_size_invalid"):
        await groups.propose_activity(
            actors[NAMES[0]],
            activity_type="hunt_group",
            participant_character_ids=tuple(ids[name] for name in NAMES[:2]),
            eligibility_resolver=road.group_hunts.eligibility,
            context_payload=await road.group_hunts.context_payload(actors[NAMES[0]]),
            now=NOW,
        )

    async with database[1]() as session:
        assert (
            await session.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == ids[NAMES[0]],
                    GameActivity.status == "active",
                )
            )
            is None
        )
        assert group.group_id is not None
