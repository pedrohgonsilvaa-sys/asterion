import asyncio
from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P25_COMBAT,
    P31_CONTENT_VERSION,
    P31_ID,
    S31_ID,
    AltosMissionService,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.road import CONFINS_MARCHA_LABEL, CONFINS_REGION_LABEL
from asterion.application.s31 import (
    S31_CODEX_ENTRY,
    S31_COMPLETION_UNLOCK,
    S31_CONTENT_VERSION,
    S31_CROWNS_REWARD,
    S31_IMPRESSIONS,
    S31_MISSION_ID,
    S31_TRAIL_POINTS,
    S31_XP_REWARD,
    S31Service,
)
from asterion.infrastructure.db.models import (
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_confins_p31 import _seed_confins_actor


async def _seed_s31(
    database,
    actor: int,
    *,
    level: int = 52,
    p31_status: str = "completed",
    at_marcha: bool = True,
):
    actor, _road, sessions = await _seed_confins_actor(
        database, actor, level=max(51, level)
    )
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        if level >= 60:
            character.xp = 0
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_MARCHA_LABEL if at_marcha else "Último Refúgio"
        if p31_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P31_ID,
                    title="Onde o Véu Afina",
                    status=p31_status,
                    step=8 if p31_status == "completed" else 4,
                    content_version=P31_CONTENT_VERSION,
                    state_version=8 if p31_status == "completed" else 4,
                    progress={"completed": p31_status == "completed"},
                )
            )
    mission = AltosMissionService(sessions, "ocaso")
    return actor, sessions, mission, S31Service(sessions, "ocaso", mission)


async def _observe_all_shared_evidence(service: S31Service, actor: int):
    view = await service.accept(actor, 0)
    assert view is not None and view.status == "active" and view.step == 2
    for index, _point in enumerate(S31_TRAIL_POINTS):
        action = f"observe_trail_point_{'abc'[index]}"
        view = await service.advance(actor, view.state_version, action)
        assert view is not None
        assert len(view.trail_points) == index + 1
    assert view.step == 3
    for index, _impression in enumerate(S31_IMPRESSIONS):
        action = f"record_impression_reading_{'ab'[index]}"
        view = await service.advance(actor, view.state_version, action)
        assert view is not None
        assert len(view.impressions) == index + 1
    assert view.step == 4
    return view


@pytest.mark.asyncio
async def test_s31_gate_is_p31_level_and_marcha_only_without_accepting(database):
    actor, _sessions, _mission, service = await _seed_s31(
        database, 831001, level=51
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, _sessions, _mission, service = await _seed_s31(
        database, 831002, level=52, p31_status="active"
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, _sessions, _mission, service = await _seed_s31(
        database, 831003, level=52, at_marcha=False
    )
    assert await service.offer(actor) is None

    actor, sessions, _mission, service = await _seed_s31(database, 831004)
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == S31_ID
            )
        ) is None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id.in_(("P32", "P36")),
            )
        ) is None
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 2


@pytest.mark.asyncio
async def test_s31_solo_scripted_combat_retry_codex_and_reward_are_idempotent(
    database, monkeypatch
):
    from tests.test_s4_s5_integration import _terminal

    actor, sessions, mission, service = await _seed_s31(database, 831010, level=60)
    async with sessions() as session:
        seeded = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert seeded is not None
        character_id = seeded.id
        initial_crowns = seeded.crowns

    view = await _observe_all_shared_evidence(service, actor)
    battle = await service.start_solo_combat(actor, view.state_version)
    assert battle is not None and battle.combat is not None
    enemies = [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert P25_COMBAT[S31_ID][3] == "creature.confins.gralha_duas_sombras"
    assert enemies[0].name == "Gralha de Duas Sombras"
    assert enemies[0].level == 52
    assert battle.combat.variant is None

    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert defeated is not None and defeated.step == 4
    recovered = await service.resume(actor)
    assert recovered is not None and recovered.step == 4
    assert recovered.progress["awaiting_retry"] is True
    retry = await service.retry_combat(actor, defeated.state_version)
    assert retry is not None and retry.kind == "combat" and retry.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor, retry.activity_id, retry.combat.version, "attack"
    )
    assert victory is not None and victory.step == 5

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert character.level == 60 and character.xp == 0
        assert character.crowns == initial_crowns
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S31_MISSION_ID,
            )
        ) is None
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S31_ID,
                )
            )
        ).all()
        assert len(credits) == 7  # acceptance + 3 points + 2 readings + victory

    view = await service.resume(actor)
    assert view is not None and view.step == 5 and view.victory_recorded
    codex = await service.advance(actor, view.state_version, "compare_with_talen")
    assert codex is not None and codex.step == 6 and codex.codex_owned
    version = codex.state_version
    results = await asyncio.gather(
        service.advance(actor, version, "conclude_with_talen"),
        service.advance(actor, version, "conclude_with_talen"),
    )
    assert all(result is not None and result.status == "completed" for result in results)

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert character.level == 60 and character.xp == 0
        assert character.crowns == initial_crowns + S31_CROWNS_REWARD
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S31_MISSION_ID,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert Counter((row.kind, row.item_id, row.quantity) for row in components) == Counter(
            {("xp", None, S31_XP_REWARD): 1, ("crowns", None, S31_CROWNS_REWARD): 1}
        )
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == S31_COMPLETION_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == S31_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == S31_CODEX_ENTRY,
                CodexFragment.fragment_id == S31_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == S31_ID,
                Quest.status == "completed",
                Quest.content_version == S31_CONTENT_VERSION,
            )
        ) is not None


@pytest.mark.asyncio
async def test_s31_abandon_and_reaccept_preserve_only_committed_evidence(database):
    actor, _sessions, _mission, service = await _seed_s31(database, 831020)
    view = await service.accept(actor, 0)
    assert view is not None and view.step == 2
    view = await service.advance(actor, view.state_version, "observe_trail_point_a")
    assert view is not None and view.trail_points == (S31_TRAIL_POINTS[0],)
    abandoned = await service.abandon(actor, view.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    reaccepted = await service.accept(
        actor, abandoned.state_version, reaccept=True
    )
    assert reaccepted is not None and reaccepted.status == "active" and reaccepted.step == 2
    assert reaccepted.trail_points == (S31_TRAIL_POINTS[0],)
    stale = await service.accept(actor, abandoned.state_version, reaccept=True)
    assert stale is not None and stale.status == "active"
    assert stale.trail_points == (S31_TRAIL_POINTS[0],)


@pytest.mark.asyncio
async def test_s31_each_character_accepts_and_observes_evidence_alone(database):
    actors = (831030, 831031)
    _leader, sessions, _mission, _service = await _seed_s31(database, actors[0])
    await _seed_s31(database, actors[1])
    async with sessions() as session:
        second = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert second is not None
        second_name = second.name
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], second_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    service = S31Service(sessions, "ocaso", mission)

    first_offer = await service.offer(actors[0])
    assert first_offer is not None and first_offer.available
    leader = await service.accept(actors[0], first_offer.state_version)
    assert leader is not None
    leader = await service.advance(actors[0], leader.state_version, "observe_trail_point_a")
    assert leader is not None and leader.trail_points == (S31_TRAIL_POINTS[0],)
    async with sessions() as session:
        second = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert second is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == second.id, Quest.quest_id == S31_ID
            )
        ) is None

    second_offer = await service.offer(actors[1])
    assert second_offer is not None and second_offer.available
    helper = await service.accept(actors[1], second_offer.state_version)
    assert helper is not None and helper.step == 2 and helper.trail_points == ()

    leader = await service.advance(actors[0], leader.state_version, "observe_trail_point_b")
    assert leader is not None and set(leader.trail_points) == set(S31_TRAIL_POINTS[:2])
    # Evidence is Solo (Ação × Consequência §5): nothing reaches the other member.
    helper = await service.resume(actors[1])
    assert helper is not None and helper.step == 2
    assert helper.trail_points == ()


@pytest.mark.asyncio
async def test_s31_group_refuses_scripted_encounter_and_solo_victory_gives_no_reward(
    database, monkeypatch
):
    from asterion.application import scripted_combat
    from tests.test_s4_s5_integration import _terminal

    actors = (831040, 831041)
    _leader, sessions, _mission, _service = await _seed_s31(database, actors[0])
    await _seed_s31(database, actors[1])
    async with sessions() as session:
        characters = (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all()
        name_by_actor = {character.telegram_id: character.name for character in characters}
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], name_by_actor[actors[1]], expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    service = S31Service(sessions, "ocaso", mission)
    for actor in actors:
        view = await service.accept(actor, 0)
        assert view is not None and view.step == 2
    view = await _observe_all_shared_evidence(service, actors[0])
    helper = await service.resume(actors[1])
    assert helper is not None and helper.step == 2
    assert helper.trail_points == ()

    # S31 is not a Boss: the Group proposal is refused, the fight is Solo.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await service.propose_group_combat(actors[0], view.state_version)
    assert not await groups.activity_proposals(actors[0])
    started = await service.start_solo_combat(actors[0], view.state_version)
    assert started is not None and started.combat is not None and started.group_size == 1
    assert not started.combat.party_mode and started.combat.variant is None
    enemies = [fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1 and enemies[0].level == 52
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    result = await mission.action(
        actors[0], started.activity_id, started.combat.version, "attack"
    )
    assert result is not None and result.step == 5
    resumed = await service.resume(actors[0])
    assert resumed is not None and resumed.step == 5 and resumed.victory_recorded
    helper = await service.resume(actors[1])
    assert helper is not None and helper.step == 2 and not helper.victory_recorded

    async with sessions() as session:
        characters = (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all()
        for character in characters:
            assert await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == S31_MISSION_ID,
                )
            ) is None
