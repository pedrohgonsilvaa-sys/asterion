"""Bloco B (Combate no Local) da TdO v1.0.18: criterios 14, 15, 5 (Ronda) e 21 (secao 33.16)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.group_hunts import GroupHuntUnlockBlocked
from asterion.application.groups import GroupService
from asterion.application.road import CAMARA, CHARNECA, RUINS, RoadService
from asterion.application.round import RoundService
from asterion.domain.combat import active_player_key
from asterion.domain.road import (
    BOSQUE_EXPLORATION_PROFILE,
    BOSQUE_PROFILE,
    CHARNECA_EXPLORATION_PROFILE,
    CHARNECA_PROFILE,
    RUINS_EXPLORATION_PROFILE,
    RUINS_PROFILE,
    VDE_GARGANTA_PROFILE,
    creature_for,
    eligible_creature_weights,
    hunt_enemy_level,
    select_creature,
    select_exploration_result,
    unlock_level_blockers,
)
from asterion.domain.road import ROAD_PROFILE as ESTRADA_PROFILE
from asterion.domain.tdo_combat import hunt_unlock_blocked_message
from asterion.domain.tdo_explore import CHARNECA_LOCATION_ID, RUINS_LOCATION_ID
from asterion.infrastructure.db.models import (
    Character,
    GroupHuntMember,
    HuntContext,
    LocationDiscovery,
    PvpveQueue,
    Unlock,
    WorldState,
)
from tests.test_group_hunt_integration import (
    ACTORS,
    NAMES,
    NOW,
    _join_group,
    _materialize_group_queue_without_opponent,
    _seed_hunters,
)

TDO_PROFILES = (ESTRADA_PROFILE, CHARNECA_PROFILE, BOSQUE_PROFILE, RUINS_PROFILE)


# ---- criterio 14: nivel do inimigo = nivel do Local ------------------------------------


@pytest.mark.parametrize("profile", TDO_PROFILES)
def test_tdo_enemy_level_is_creature_max_level_for_any_player_level(profile):
    for creature_id, _ in profile.creature_weights:
        creature = creature_for(creature_id)
        for player_level in (1, 5, 60):
            assert hunt_enemy_level(profile, creature, player_level) == creature.max_level


def test_tdo_nv1_in_ruins_faces_ruins_level_and_other_regions_keep_min():
    creature = creature_for("vigia_rachado")
    assert hunt_enemy_level(RUINS_PROFILE, creature, 1) == creature.max_level == 10
    other = creature_for(VDE_GARGANTA_PROFILE.creature_weights[0][0])
    assert hunt_enemy_level(VDE_GARGANTA_PROFILE, other, 1) == min(1, other.max_level)


@pytest.mark.parametrize("profile", TDO_PROFILES)
def test_tdo_solo_pool_ignores_unlock_level(profile):
    assert eligible_creature_weights(profile, 1) == tuple(profile.creature_weights)
    drawn = {select_creature(f"s{i}", 1, profile).creature_id for i in range(400)}
    assert drawn == {creature_id for creature_id, _ in profile.creature_weights}


# ---- criterio 15: Grupo e unlock_level --------------------------------------------------


def test_tdo_group_pool_requires_every_member_to_meet_unlock_level():
    pool = eligible_creature_weights(RUINS_PROFILE, 60, [60, 6])
    assert {cid for cid, _ in pool} == {"carnical_fuligem", "mariposa_brasa"}
    for i in range(100):
        assert select_creature(f"g{i}", 60, RUINS_PROFILE, group_levels=[60, 6]).creature_id in {
            "carnical_fuligem",
            "mariposa_brasa",
        }


def test_group_blockers_cite_every_member_below_the_lowest_unlock_level():
    members = [("Alpha", 60), ("Bravo", 1), ("Cedar", 4)]
    assert unlock_level_blockers(RUINS_PROFILE, members) == ("Bravo", "Cedar")
    assert unlock_level_blockers(RUINS_PROFILE, [("Alpha", 60), ("Bravo", 5)]) == ()
    # Estrada tem criatura de unlock_level 1: nunca bloqueia.
    assert unlock_level_blockers(ESTRADA_PROFILE, [("Alpha", 60), ("Bravo", 1)]) == ()
    # Outras regioes: sem mudanca.
    assert unlock_level_blockers(VDE_GARGANTA_PROFILE, [("Alpha", 60), ("Bravo", 1)]) == ()


def test_group_blocked_message_singular_plural_and_wording():
    one = hunt_unlock_blocked_message(["Bravo"])
    assert "Bravo ainda não cumpre o nível mínimo de nenhuma criatura deste Local." in one
    two = hunt_unlock_blocked_message(["Bravo", "Cedar"])
    assert "Bravo e Cedar ainda não cumprem" in two
    three = hunt_unlock_blocked_message(["Bravo", "Cedar", "Doran"])
    assert "Bravo, Cedar e Doran ainda não cumprem" in three
    for text in (one, two, three):
        assert "nada para caçar" not in text.lower()
        assert not any(ch.isdigit() for ch in text)


async def _move_all(database, ids, location, *, levels=None, discovered=()):
    async with database[1].begin() as session:
        for name, character_id in ids.items():
            if levels is not None:
                (await session.get(Character, character_id)).level = levels[name]
            world = await session.get(WorldState, character_id)
            world.location = location
            for location_id in discovered:
                session.add(LocationDiscovery(character_id=character_id, location_id=location_id))


@pytest.mark.asyncio
async def test_group_hunt_in_ruins_is_blocked_citing_all_members(database):
    actors, ids = await _seed_hunters(database, count=3)
    await _move_all(
        database,
        ids,
        RUINS,
        levels={"Alpha": 60, "Bravo": 1, "Cedar": 4},
        discovered=(RUINS_LOCATION_ID,),
    )
    road = RoadService(database[1], "ocaso")
    roster = tuple(ids[name] for name in NAMES[:3])
    with pytest.raises(GroupHuntUnlockBlocked) as raised:
        await road.group_hunts.context_payload(actors["Alpha"], roster)
    assert raised.value.names == ("Bravo", "Cedar")
    assert "Bravo e Cedar ainda não cumprem" in raised.value.user_message
    # Sem Bravo e Cedar o Local abre.
    payload = await road.group_hunts.context_payload(actors["Alpha"], (ids["Alpha"],))
    assert payload["local_id"] == RUINS_PROFILE.local_id


# ---- Solo: inimigo no nivel do Local ----------------------------------------------------


@pytest.mark.asyncio
async def test_solo_nv1_hunt_in_ruins_spawns_ruins_level_enemy(database):
    actors, ids = await _seed_hunters(database, count=1)
    await _move_all(
        database, ids, RUINS, levels={"Alpha": 1}, discovered=(RUINS_LOCATION_ID,)
    )
    road = RoadService(database[1], "ocaso")
    view = await road.start_hunt(actors["Alpha"])
    assert view is not None
    async with database[1]() as session:
        queue = await session.scalar(select(PvpveQueue))
    if queue is not None and queue.status == "waiting":
        view = await road.pvpve.continue_queue(actors["Alpha"], queue.id)
    assert view is not None and view.kind == "combat"
    async with database[1]() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.character_id == ids["Alpha"])
        )
    assert context is not None
    creature = creature_for(context.creature_id)
    assert context.enemy_level == creature.max_level
    assert context.enemy_level >= 8


# ---- criterio 5: Ronda so apos a primeira vitoria manual valida -------------------------


@pytest.mark.asyncio
async def test_round_needs_first_manual_victory_without_mission_or_level_gate(database):
    actors, ids = await _seed_hunters(database, count=1)
    await _move_all(
        database,
        ids,
        CHARNECA,
        levels={"Alpha": 1},
        discovered=(CHARNECA_LOCATION_ID,),
    )
    rounds = RoundService(database[1], "ocaso")
    before = await rounds.prepare_round(actors["Alpha"], 5)
    assert before is None or before.kind != "round_prepare"
    async with database[1].begin() as session:
        session.add(
            Unlock(
                character_id=ids["Alpha"],
                unlock_id=CHARNECA_PROFILE.round_familiarity,
            )
        )
    after = await rounds.prepare_round(actors["Alpha"], 5)
    assert after is not None and after.kind == "round_prepare"


@pytest.mark.asyncio
async def test_round_unavailable_in_undiscovered_local_and_in_camara(database):
    actors, ids = await _seed_hunters(database, count=1)
    async with database[1].begin() as session:
        session.add(
            Unlock(
                character_id=ids["Alpha"],
                unlock_id=RUINS_PROFILE.round_familiarity,
            )
        )
    await _move_all(database, ids, RUINS)  # Ruinas nao descoberta
    rounds = RoundService(database[1], "ocaso")
    blocked = await rounds.prepare_round(actors["Alpha"], 5)
    assert blocked is None or blocked.kind != "round_prepare"
    await _move_all(database, ids, CAMARA)
    assert await rounds.prepare_round(actors["Alpha"], 5) is None


# ---- criterio 21: Ronda em Grupo so para quem participou da vitoria ---------------------


@pytest.mark.asyncio
async def test_group_victory_unlocks_round_only_for_participants(database, monkeypatch):
    actors, ids = await _seed_hunters(database, count=3)
    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=3)
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_creature",
        lambda _seed, _level, profile=None, **_kw: creature_for("dog_cinereo"),
    )
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_variant",
        lambda _seed, _creature, profile=None: None,
    )
    roster_names = NAMES[:2]
    roster = tuple(m.character_id for m in group.members if m.name in roster_names)
    proposal = await groups.propose_activity(
        actors[NAMES[0]],
        activity_type="hunt_group",
        participant_character_ids=roster,
        eligibility_resolver=road.group_hunts.eligibility,
        context_payload=await road.group_hunts.context_payload(actors[NAMES[0]], roster),
        now=NOW,
    )
    for member in proposal.participants:
        if member.name != NAMES[0]:
            proposal = await groups.respond_activity(
                actors[member.name],
                proposal.proposal_id,
                expected_revision=proposal.revision,
                accept=True,
                now=NOW + timedelta(seconds=1),
            )
    await groups.start_activity(
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
    assert {m.character_id for m in members} == {ids[n] for n in roster_names}
    actor_by_character = {ids[n]: actors[n] for n in NAMES[:3]}
    for _ in range(120):
        if view.kind != "combat" or view.combat.result:
            break
        key = active_player_key(view.combat)
        member = next(row for row in members if row.actor_key == key)
        actor = actor_by_character[member.character_id]
        activity = await road.resume(actor)
        view = await road.action(
            actor, member.game_activity_id, activity.state_version, "attack"
        )
        assert view is not None
    assert view.kind == "hunt_victory"
    async with database[1]() as session:
        unlocked = {
            row.character_id
            for row in (
                await session.scalars(
                    select(Unlock).where(
                        Unlock.unlock_id == ESTRADA_PROFILE.round_familiarity
                    )
                )
            ).all()
        }
    assert unlocked == {ids[n] for n in roster_names}
    assert ids[NAMES[2]] not in unlocked
    assert uuid4() not in unlocked and ACTORS  # silencia import nao usado


# ---- F1: Desbravar Solo nao filtra combate por nivel nos Locais TdO ----------------------


@pytest.mark.parametrize(
    ("profile", "creature_ids"),
    (
        (CHARNECA_EXPLORATION_PROFILE, {"aranha_cinza", "cervo_escoriado"}),
        (BOSQUE_EXPLORATION_PROFILE, {"mariposa_brasa"}),
        (RUINS_EXPLORATION_PROFILE, {"mariposa_brasa"}),
    ),
)
def test_nv1_solo_desbravar_can_draw_tdo_combat_results(profile, creature_ids):
    drawn = set()
    for i in range(3000):
        result_id = select_exploration_result(f"f1-{i}", 1, profile=profile)
        result = profile.result(result_id)
        if result.category == "combat" and result.creature_id:
            drawn.add(result.creature_id)
    assert creature_ids <= drawn
