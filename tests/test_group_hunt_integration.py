from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application import group_hunts as group_hunts_module
from asterion.application.group_hunts import group_hunt_scaling
from asterion.application.groups import GroupError, GroupService
from asterion.application.p7 import GARGANTA, GARGANTA_HUNT_UNLOCK, P7_ID, REGION
from asterion.application.road import ROAD, RoadService
from asterion.bot.groups_ui import render_hunt_roster
from asterion.domain.combat import active_player_key
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    creature_for,
)
from asterion.infrastructure.db.combat_codec import decode
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
    RewardComponent,
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
        lambda _seed, _level, profile=None, **_kw: creature_for("dog_cinereo"),
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
        lambda _seed, _level, profile=None, **_kw: creature_for("dog_cinereo"),
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
async def test_vde_group_hunt_uses_the_same_material_table_for_each_participant(
    database, monkeypatch
):
    actors, ids = await _seed_hunters(database, count=2)
    async with database[1].begin() as session:
        for name in NAMES[:2]:
            character = await session.get(Character, ids[name])
            world = await session.get(WorldState, ids[name])
            assert character is not None and world is not None
            character.level = 13
            character.ruleset_version = "vales-1.0.3"
            world.region = REGION
            world.location = GARGANTA
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P7_ID,
                    title="A Estrada Estrangulada",
                    status="completed",
                    step=7,
                    content_version="vales-1.0.3",
                    progress={"completed": True},
                )
            )
            session.add(
                Unlock(
                    character_id=character.id,
                    unlock_id=GARGANTA_HUNT_UNLOCK,
                )
            )

    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=2)
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_creature",
        lambda _seed, _level, profile=None, **_kw: creature_for("peregrino_enredado"),
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
    actor_by_fighter = {
        member.actor_key: next(
            actor for name, actor in actors.items() if ids[name] == member.character_id
        )
        for member in members
    }
    for _ in range(120):
        if view.kind != "combat":
            break
        actor = actor_by_fighter[active_player_key(view.combat)]
        member = next(row for row in members if row.actor_key == active_player_key(view.combat))
        current = await road.resume(actor)
        assert current is not None and current.kind == "combat"
        view = await road.action(
            actor, member.game_activity_id, current.state_version, "attack"
        )
        assert view is not None
    assert view.kind == "hunt_victory"

    async with database[1]() as session:
        for member in members:
            rows = list(
                (
                    await session.scalars(
                        select(RewardComponent)
                        .join(RewardEvent)
                        .where(
                            RewardEvent.character_id == member.character_id,
                            RewardEvent.source_id == f"activity:{member.game_activity_id}",
                            RewardComponent.kind == "material",
                        )
                        .order_by(RewardComponent.id)
                    )
                ).all()
            )
            assert 1 <= len(rows) <= 2
            assert all(
                row.item_id
                in {
                    "material.vde.ferro_enredado",
                    "material.vde.resina_enredada",
                }
                for row in rows
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


def _party_specs(count: int = 2):
    return tuple(
        PlayerCombatantSpec(
            fighter_key=f"p{index}",
            character_id=f"character-{index}",
            name=f"Hunter{index}",
            character_class="sentinela",
            race="remanescente",
            level=10,
            hp=Decimal("1000"),
            equipment_configuration=EquipmentConfigurationSnapshot(0),
            active_art_ids=(),
        )
        for index in range(1, count + 1)
    )


def test_start_combat_with_faster_enemy_hands_first_manual_turn_to_a_player():
    party = _party_specs()
    combat = create_creature_party_combat(
        uuid4(),
        party[0].name,
        party[0].character_class,
        party[0].race,
        party[0].hp,
        (
            CreatureCombatantSpec(
                creature_for("dog_cinereo"),
                10,
                "enemy",
                None,
                stat_multipliers=StatMultipliers(
                    Decimal(1), Decimal(1), Decimal(1), Decimal(100)
                ),
            ),
        ),
        player_level=10,
        party=party,
    )

    assert combat.order[0] == "enemy"
    assert combat.result is None
    assert active_player_key(combat) in {"p1", "p2"}


@pytest.mark.asyncio
async def test_new_active_group_hunt_gets_180_second_deadline(database):
    actors, ids = await _seed_hunters(database, count=2)
    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=2)

    before = datetime.now(UTC)
    started = await _ready_group_hunt(groups, road, actors, ids, group)
    after = datetime.now(UTC)

    async with database[1]() as session:
        encounter = await session.scalar(
            select(GroupHuntEncounter).where(
                GroupHuntEncounter.proposal_id == started.proposal.proposal_id
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
    assert encounter.status == "active"
    assert before + timedelta(seconds=180) <= encounter.deadline_at
    assert encounter.deadline_at <= after + timedelta(seconds=180)
    assert all(
        (m.consecutive_timeouts, m.total_timeouts, m.inactive_for_contribution)
        == (0, 0, False)
        for m in members
    )


@pytest.mark.asyncio
async def test_new_group_hunt_with_terminal_combat_gets_no_deadline(database, monkeypatch):
    actors, ids = await _seed_hunters(database, count=2)
    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=2)

    original = group_hunts_module.create_creature_party_combat

    def terminal_combat(*args, **kwargs):
        combat = original(*args, **kwargs)
        combat.result = "victory"
        return combat

    monkeypatch.setattr(
        "asterion.application.group_hunts.create_creature_party_combat", terminal_combat
    )
    started = await _ready_group_hunt(groups, road, actors, ids, group)

    async with database[1]() as session:
        encounter = await session.scalar(
            select(GroupHuntEncounter).where(
                GroupHuntEncounter.proposal_id == started.proposal.proposal_id
            )
        )
    assert encounter is not None
    assert encounter.deadline_at is None


async def _start_weak_pve_hunt(database, monkeypatch, *, count: int = 2):
    actors, ids = await _seed_hunters(database, count=max(count, 2))
    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=2)
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_creature",
        lambda _seed, _level, profile=None, **_kw: creature_for("dog_cinereo"),
    )
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_variant",
        lambda _seed, _creature, profile=None: None,
    )
    started = await _ready_group_hunt(groups, road, actors, ids, group)
    assert started.started
    view = await road.resume(actors[NAMES[0]])
    assert view is not None and view.kind == "combat"
    return road, actors, ids, view.encounter_id


async def _load_hunt(database, encounter_id):
    async with database[1]() as session:
        encounter = await session.get(GroupHuntEncounter, encounter_id)
        members = list(
            (
                await session.scalars(
                    select(GroupHuntMember).where(
                        GroupHuntMember.group_hunt_encounter_id == encounter_id
                    )
                )
            ).all()
        )
        combat = decode(
            encounter.combat_snapshot,
            encounter.combat_id,
            encounter.ruleset_version,
            encounter.state_version,
        )
    active = next(
        (row for row in members if row.actor_key == active_player_key(combat)), None
    )
    return encounter, members, combat, active


def _telegram_of(actors, ids, character_id):
    return next(actors[name] for name in actors if ids[name] == character_id)


@pytest.mark.asyncio
async def test_group_hunt_timeout_passes_turn_counts_and_renews_deadline(
    database, monkeypatch
):
    road, _actors, _ids, encounter_id = await _start_weak_pve_hunt(database, monkeypatch)
    encounter, _members, combat, active = await _load_hunt(database, encounter_id)
    assert active is not None
    enemy_hp = combat.fighters["enemy"].hp
    old_deadline = encounter.deadline_at
    version = encounter.state_version

    # Before the 180s deadline nothing happens.
    early = old_deadline - timedelta(seconds=1)
    assert await road.group_hunts.run_maintenance(now=early) == 0
    assert (await _load_hunt(database, encounter_id))[0].state_version == version

    due = old_deadline + timedelta(seconds=1)
    assert await road.group_hunts.run_maintenance(now=due) == 1

    encounter, members, combat, next_active = await _load_hunt(database, encounter_id)
    timed_out = next(row for row in members if row.actor_key == active.actor_key)
    assert encounter.state_version == version + 1
    assert next_active is not None and next_active.actor_key != active.actor_key
    assert combat.fighters["enemy"].hp == enemy_hp  # a hold deals no damage
    assert (timed_out.total_timeouts, timed_out.consecutive_timeouts) == (1, 1)
    assert timed_out.inactive_for_contribution is False
    other = next(row for row in members if row.actor_key != active.actor_key)
    assert (other.total_timeouts, other.consecutive_timeouts) == (0, 0)
    # New deadline is a fresh 180s window for the next player.
    assert encounter.deadline_at > old_deadline
    assert encounter.deadline_at >= datetime.now(UTC) + timedelta(seconds=170)

    # A tick before the renewed deadline is a no-op.
    before_new = encounter.deadline_at - timedelta(seconds=1)
    assert await road.group_hunts.run_maintenance(now=before_new) == 0
    assert (await _load_hunt(database, encounter_id))[0].state_version == version + 1


@pytest.mark.asyncio
async def test_three_consecutive_timeouts_mark_inactive_without_other_effects(
    database, monkeypatch
):
    road, _actors, _ids, encounter_id = await _start_weak_pve_hunt(database, monkeypatch)
    encounter, _members, _combat, active = await _load_hunt(database, encounter_id)
    async with database[1].begin() as session:
        row = await session.get(GroupHuntMember, (encounter_id, active.character_id))
        row.consecutive_timeouts = 2
        row.total_timeouts = 2

    due = encounter.deadline_at + timedelta(seconds=1)
    assert await road.group_hunts.run_maintenance(now=due) == 1

    encounter, members, _combat, _next = await _load_hunt(database, encounter_id)
    row = next(item for item in members if item.actor_key == active.actor_key)
    assert (row.consecutive_timeouts, row.total_timeouts) == (3, 3)
    assert row.inactive_for_contribution is True
    # No expulsion, settlement or status change comes with the mark.
    assert encounter.status == "active"
    assert row.settlement_state == "pending" and row.result is None


@pytest.mark.asyncio
async def test_valid_action_resets_consecutive_timeouts_and_inactive_mark(
    database, monkeypatch
):
    road, actors, ids, encounter_id = await _start_weak_pve_hunt(database, monkeypatch)
    _encounter, _members, _combat, active = await _load_hunt(database, encounter_id)
    async with database[1].begin() as session:
        row = await session.get(GroupHuntMember, (encounter_id, active.character_id))
        row.consecutive_timeouts = 3
        row.total_timeouts = 3
        row.inactive_for_contribution = True
    actor = _telegram_of(actors, ids, active.character_id)
    activity = await road.resume(actor)
    assert activity is not None and activity.kind == "combat"
    view = await road.action(actor, active.game_activity_id, activity.state_version, "attack")
    assert view is not None

    encounter, members, _combat, _next = await _load_hunt(database, encounter_id)
    row = next(item for item in members if item.actor_key == active.actor_key)
    assert row.consecutive_timeouts == 0
    assert row.inactive_for_contribution is False
    assert row.total_timeouts == 3  # the lifetime total is kept
    assert encounter.deadline_at is not None
    assert encounter.deadline_at >= datetime.now(UTC) + timedelta(seconds=170)


@pytest.mark.asyncio
async def test_terminal_group_hunt_clears_deadline(database, monkeypatch):
    road, actors, ids, encounter_id = await _start_weak_pve_hunt(database, monkeypatch)
    for _ in range(120):
        encounter, _members, _combat, active = await _load_hunt(database, encounter_id)
        if encounter.status != "active":
            break
        actor = _telegram_of(actors, ids, active.character_id)
        activity = await road.resume(actor)
        await road.action(actor, active.game_activity_id, activity.state_version, "attack")
    encounter = (await _load_hunt(database, encounter_id))[0]
    assert encounter.status == "completed"
    assert encounter.deadline_at is None
    # A terminal encounter is never picked up by the timeout job again.
    far = datetime.now(UTC) + timedelta(days=1)
    assert await road.group_hunts.run_maintenance(now=far) == 0


@pytest.mark.asyncio
async def test_group_hunt_job_ignores_solo_activities(database, monkeypatch):
    road, _actors, ids, encounter_id = await _start_weak_pve_hunt(
        database, monkeypatch, count=3
    )
    old = datetime.now(UTC) - timedelta(days=1)
    solo_id = uuid4()
    async with database[1].begin() as session:
        session.add(
            GameActivity(
                id=solo_id,
                character_id=ids["Cedar"],
                content_id="road_hunt",
                status="active",
                state_version=0,
                ruleset_version="tdo-1.0.15",
                last_valid_action_at=old,
            )
        )
    due = (await _load_hunt(database, encounter_id))[0].deadline_at + timedelta(seconds=1)
    assert await road.group_hunts.run_maintenance(now=due) == 1
    async with database[1]() as session:
        solo = await session.get(GameActivity, solo_id)
    assert solo.status == "active"
    assert solo.state_version == 0
    assert solo.last_valid_action_at == old


@pytest.mark.asyncio
async def test_group_hunt_job_never_reads_pvp_guild_battle_or_dungeon_tables(
    database, monkeypatch
):
    from sqlalchemy import event

    road, _actors, _ids, encounter_id = await _start_weak_pve_hunt(database, monkeypatch)
    due = (await _load_hunt(database, encounter_id))[0].deadline_at + timedelta(seconds=1)
    statements: list[str] = []

    def capture(_conn, _cursor, statement, *_rest):
        statements.append(statement.lower())

    sync_engine = database[0].sync_engine
    event.listen(sync_engine, "before_cursor_execute", capture)
    try:
        assert await road.group_hunts.run_maintenance(now=due) == 1
    finally:
        event.remove(sync_engine, "before_cursor_execute", capture)

    assert statements
    other_modes = ("pvp_", "arena_", "guild_battle", "dungeon_")
    assert not [
        sql for sql in statements if any(f"from {name}" in sql or f"join {name}" in sql
                                         or f"update {name}" in sql or f"into {name}" in sql
                                         for name in other_modes)
    ]
