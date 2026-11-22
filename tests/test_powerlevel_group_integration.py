"""Integração: PowerlevelFactor individual (GDD 3795) em Grupo, Caçada e Masmorra."""

from decimal import Decimal as D

import pytest
from sqlalchemy import select, update

from asterion.application.dungeons import DungeonService
from asterion.application.groups import GroupService
from asterion.application.road import RoadService
from asterion.domain.combat import active_player_key
from asterion.domain.road import creature_for, enemy_xp, powerlevel_factor
from asterion.infrastructure.db.models import (
    Character,
    DungeonRun,
    DungeonRunMember,
    GroupHuntMember,
    HuntContext,
    RewardComponent,
    RewardEvent,
)
from tests.test_dungeon_multiplayer import _form_matchmade_party, _seed_party
from tests.test_group_hunt_integration import (
    NAMES,
    _join_group,
    _ready_group_hunt,
    _seed_hunters,
)

HUNT_CREATURE = "cervo_ferrugem"  # Nv.37, comum, com tabela de materiais


async def _xp_component(session, character_id, source_prefix):
    event = await session.scalar(
        select(RewardEvent).where(
            RewardEvent.character_id == character_id,
            RewardEvent.source_id.like(f"{source_prefix}%"),
        )
    )
    assert event is not None
    return await session.scalar(
        select(RewardComponent).where(
            RewardComponent.reward_event_id == event.id, RewardComponent.kind == "xp"
        )
    )


@pytest.mark.asyncio
async def test_group_hunt_xp_applies_individual_powerlevel_factor(database, monkeypatch):
    actors, ids = await _seed_hunters(database, count=2)
    # Alpha Nv.45 (maior do Grupo); Bravo Nv.33 -> diferença 12 -> PowerlevelFactor 70%.
    async with database[1].begin() as session:
        for name, level in (("Alpha", 45), ("Bravo", 33)):
            await session.execute(
                update(Character).where(Character.id == ids[name]).values(level=level)
            )
    groups = GroupService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    group = await _join_group(groups, actors, count=2)
    monkeypatch.setattr(
        "asterion.application.group_hunts.select_creature",
        lambda _seed, _level, profile=None, **_kw: creature_for(HUNT_CREATURE),
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
    telegram_by_id = {ids[name]: actors[name] for name in ("Alpha", "Bravo")}
    actor_by_fighter = {m.actor_key: telegram_by_id[m.character_id] for m in members}
    for _ in range(600):
        if view.kind != "combat" or view.combat.result:
            break
        key = active_player_key(view.combat)
        actor = actor_by_fighter[key]
        member = next(row for row in members if row.actor_key == key)
        current = await road.resume(actor)
        view = await road.action(
            actor, member.game_activity_id, current.state_version, "attack"
        )
        assert view is not None
    assert view.kind == "hunt_victory"

    async with database[1]() as session:
        results = {}
        for name, level in (("Alpha", 45), ("Bravo", 33)):
            member = next(row for row in members if row.character_id == ids[name])
            context = await session.scalar(
                select(HuntContext).where(
                    HuntContext.game_activity_id == member.game_activity_id
                )
            )
            component = await _xp_component(session, ids[name], "activity:")
            results[name] = (level, context, component.quantity)
    for name, (level, context, granted) in results.items():
        gap = 45 - level
        expected = enemy_xp(
            context.enemy_level,
            context.category,
            D(1),
            player_level=level,
            powerlevel_factor=powerlevel_factor(gap),
        )
        without_factor = enemy_xp(
            context.enemy_level, context.category, D(1), player_level=level
        )
        assert granted == expected, name
        if gap:
            assert granted < without_factor
    assert results["Alpha"][2] == enemy_xp(
        results["Alpha"][1].enemy_level, results["Alpha"][1].category, D(1), player_level=45
    )


@pytest.mark.asyncio
async def test_dungeon_group_internal_enemy_xp_applies_individual_powerlevel_factor(database):
    actors = (781090, 781091)
    sessions, character_ids = await _seed_party(database, actors)
    service = DungeonService(sessions, "ocaso")
    ready = await _form_matchmade_party(service, actors, "dungeon.tdo.cripta_ocaso")
    levels = {character_ids[0]: 25, character_ids[1]: 8}  # diferença 17 -> 45%
    rewards = [[30, "elite"], [30, "common"]]
    async with sessions.begin() as session:
        run = await session.get(DungeonRun, ready.run_id)
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(DungeonRunMember.run_id == ready.run_id)
                .order_by(DungeonRunMember.position)
            )
        ).all()
        characters = (
            await session.scalars(select(Character).where(Character.id.in_(character_ids)))
        ).all()
        for character in characters:
            character.level = levels[character.id]
        for member in members:
            member.contribution = {"points": "100", "actions": 4}
        run.progress = {**run.progress, "internal_rewards": rewards}
        by_id = {character.id: character for character in characters}
        await service._settle_run(session, characters[0], run, members, by_id)

    async with sessions() as session:
        for character_id, level in levels.items():
            component = await _xp_component(session, character_id, "dungeon:")
            expected = sum(
                enemy_xp(
                    lvl,
                    category,
                    player_level=level,
                    powerlevel_factor=D("0.25") * powerlevel_factor(25 - level),
                    participation_factor=D(1),
                )
                for lvl, category in rewards
            )
            without_factor = sum(
                enemy_xp(
                    lvl, category, player_level=level, powerlevel_factor=D("0.25")
                )
                for lvl, category in rewards
            )
            assert component.payload["internal"] == expected
            if level < 25:
                assert expected < without_factor
            else:
                assert expected == without_factor
