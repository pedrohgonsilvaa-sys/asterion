from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select

from asterion.application.groups import GroupError, GroupService
from asterion.application.p1 import P1Service
from asterion.application.p5 import P5_ID, P5_VERSION, P5Service
from asterion.application.p6 import (
    P6_CHAMBER,
    P6_ID,
    P6_NUCLEUS_SOURCE,
    P6_VERSION,
    P6Service,
)
from asterion.application.road import RUINS
from asterion.application.s6 import S6_ID, S6_VERSION, S6Service
from asterion.domain.campaign_combat import scale_campaign_boss_stats
from asterion.domain.combat import active_player_key
from asterion.domain.road import (
    LAST_TRACE_GUARDIAN,
    SUNSET_CUSTODIAN,
    VIGIA_PARTIDO,
    road_enemy_stats,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    CampaignObjectiveCredit,
    CampaignSharedEncounter,
    Character,
    GroupActivityParticipant,
    Quest,
    RewardEvent,
    WorldState,
)


async def _seed_party(database, actors):
    sessions = database[1]
    names = {actor: f"Hero{chr(ord('a') + index)}" for index, actor in enumerate(actors)}
    async with sessions.begin() as session:
        for actor in actors:
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=names[actor],
                    race="remanescente",
                    character_class="sentinela",
                    stage="road_active",
                    ruleset_version="gdd-1.4.3-baseline-1.0",
                    level=1,
                    xp=320,
                    hp=Decimal("702"),
                    max_hp=Decimal("702"),
                    vigor=77,
                    max_vigor=100,
                    crowns=0,
                )
            )
        await session.flush()
        characters = list(
            (
                await session.scalars(
                    select(Character).where(Character.telegram_id.in_(actors))
                )
            ).all()
        )
        for character in characters:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id="P1",
                    title="Vozes na Estrada",
                    status="active",
                    step=1,
                    content_version="tdo-1.0.2",
                )
            )
            session.add(
                WorldState(
                    character_id=character.id,
                    region="Terras do Ocaso",
                    location="Estrada das Cinzas",
                )
            )
    return names


async def _create_group(groups, leader, other_actors, names):
    group = await groups.create_group(leader)
    for actor in other_actors:
        invite = await groups.invite(
            leader,
            names[actor],
            expected_group_revision=group.revision,
        )
        group = await groups.respond_invite(
            actor,
            invite.invite_id,
            expected_revision=invite.revision,
            accept=True,
        )
    return group


async def _confirm_and_start(groups, service, proposer, proposal_id, actors):
    proposal = await groups.activity_proposal(proposer, proposal_id)
    for actor in actors:
        if actor == proposer:
            continue
        proposal = await groups.respond_activity(
            actor,
            proposal_id,
            expected_revision=proposal.revision,
            accept=True,
        )
    return await service.start_group_combat(
        proposer,
        proposal_id,
        expected_revision=proposal.revision,
    )


async def _finish_p1_group_fight(service, actors, database, encounter_id):
    result = None
    for _ in range(100):
        views = [await service.resume(actor) for actor in actors]
        combat = next(
            (view.combat for view in views if view and view.combat is not None), None
        )
        if combat is None:
            break
        if combat.result:
            result = combat.result
            break
        turn_owner = active_player_key(combat)
        assert turn_owner is not None
        view = next(
            view
            for view in views
            if view is not None and view.combat_actor_key == turn_owner
        )
        updated = await service.action(
            actors[views.index(view)],
            view.activity_id,
            combat.version,
            "attack",
            target_id="enemy",
        )
        if updated.combat is None:
            async with database[1]() as session:
                encounter = await session.get(CampaignSharedEncounter, encounter_id)
                result = "victory" if encounter.status == "completed" else "defeat"
            break
    assert result == "victory"


async def _finish_p1_solo_fight(service, actor, database):
    """Fight the Solo P1 combat to the end; the hero must win it."""
    for _ in range(100):
        view = await service.resume(actor)
        if view.combat is None or view.combat.result:
            break
        await service.action(
            actor, view.activity_id, view.combat.version, "attack", target_id="enemy"
        )
    final = await service.resume(actor)
    assert final.step == 4


async def _seed_enemy_at_one_hp(database, encounter_id):
    """Make settlement assertions deterministic without simulating balance."""
    async with database[1].begin() as session:
        encounter = await session.get(CampaignSharedEncounter, encounter_id)
        combat = decode(
            encounter.combat_snapshot,
            encounter.id,
            encounter.ruleset_version,
            encounter.state_version,
        )
        enemy = combat.fighters["enemy"]
        enemy.hp = Decimal("1")
        enemy.stats = replace(enemy.stats, hp=Decimal("1"))
        enemy.takes_turn = False
        combat.order = tuple(key for key in combat.order if key != "enemy")
        combat.turn_index = 0
        encounter.combat_snapshot = encode(combat)
        await session.flush()
        stored = decode(
            encounter.combat_snapshot,
            encounter.id,
            encounter.ruleset_version,
            encounter.state_version,
        )
        assert stored.fighters["enemy"].hp == Decimal("1")


async def _complete_shared_boss_fight(service, actors, database, encounter_id):
    for _ in range(12):
        views = [await service.resume(actor) for actor in actors]
        combat_view = next(
            (view for view in views if view and view.combat is not None), None
        )
        if combat_view is None:
            break
        actor_key = active_player_key(combat_view.combat)
        assert actor_key is not None
        current = next(
            view
            for view in views
            if view and view.combat_actor_key == actor_key
        )
        actor = actors[views.index(current)]
        await service.action_combat(
            actor,
            current.activity_id,
            current.combat.version,
            "attack",
            target_id="enemy",
        )
        async with database[1]() as session:
            encounter = await session.get(CampaignSharedEncounter, encounter_id)
            if encounter.status == "completed":
                return
    raise AssertionError("The deterministic shared boss fight did not complete.")


async def _start_group_boss(groups, service, actor, helper, activity_type, version):
    await service.propose_group_combat(actor, version)
    proposals = await groups.activity_proposals(actor)
    proposal = next(row for row in proposals if row.activity_type == activity_type)
    accepted = await groups.respond_activity(
        helper,
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
    )
    started = await service.start_group_combat(
        actor, proposal.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None
    return started


@pytest.mark.asyncio
async def test_p1_group_keeps_objectives_solo_and_refuses_group_combat(database, monkeypatch):
    import asterion.application.p1 as p1_module

    monkeypatch.setattr(p1_module, "uuid4", lambda: UUID(int=7001))
    actors = (992101, 992102, 992103, 992104)
    names = await _seed_party(database, actors)
    groups = GroupService(database[1], "ocaso")
    await _create_group(groups, actors[0], actors[1:], names)
    services = {actor: P1Service(database[1], "ocaso", groups) for actor in actors}

    async def steps():
        async with database[1]() as session:
            rows = (
                await session.execute(
                    select(Character.telegram_id, Quest.step)
                    .join(Quest, Quest.character_id == Character.id)
                    .where(Character.telegram_id.in_(actors), Quest.quest_id == "P1")
                )
            ).all()
        return dict(rows)

    # Principais are Solo (Ação × Consequência §5): only the actor advances.
    followed = await services[actors[0]].follow_road(actors[0], 0)
    assert followed.step == 2
    assert await steps() == {actors[0]: 2, actors[1]: 1, actors[2]: 1, actors[3]: 1}

    tracks = await services[actors[0]].examine(actors[0], "pegadas", 1)
    assert tracks.progress["pegadas"] is True
    dog = await services[actors[0]].examine(actors[0], "sulcos", tracks.state_version)
    # The fight opens as a Solo combat even though the actor belongs to a Group.
    assert dog.step == 3 and dog.combat is not None and dog.group_size == 1
    assert not dog.combat.party_mode
    assert await steps() == {actors[0]: 3, actors[1]: 1, actors[2]: 1, actors[3]: 1}
    async with database[1]() as session:
        credits = list(
            (
                await session.scalars(
                    select(CampaignObjectiveCredit).where(
                        CampaignObjectiveCredit.quest_id == "P1"
                    )
                )
            ).all()
        )
        actor_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == actors[0])
        )
        assert len(credits) == 3
        assert {credit.character_id for credit in credits} == {actor_id}
    # The other members are still at the first step, with no progress at all.
    for actor in actors[1:]:
        view = await services[actor].resume(actor)
        assert view.step == 1 and not view.progress.get("pegadas")

    # P1 is not a Boss: the Group proposal is refused and nothing is reserved.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await services[actors[0]].propose_group_combat(actors[0], dog.state_version)
    assert not await groups.activity_proposals(actors[0])

    # The Solo fight reconnects to the same combat.
    ready = dog
    reconnected = await services[actors[0]].resume(actors[0])
    assert reconnected.activity_id == ready.activity_id
    assert reconnected.combat.version == ready.combat.version
    stale_view = await services[actors[0]].action(
        actors[0], ready.activity_id, ready.combat.version, "attack", target_id="enemy"
    )
    assert stale_view is not None
    await _finish_p1_solo_fight(services[actors[0]], actors[0], database)

    assert await steps() == {actors[0]: 4, actors[1]: 1, actors[2]: 1, actors[3]: 1}
    async with database[1]() as session:
        assert not await session.scalar(
            select(CampaignSharedEncounter.id).limit(1)
        )
        assert not await session.scalar(
            select(RewardEvent).where(RewardEvent.source_id == "p1.vozes_na_estrada")
        )


@pytest.mark.asyncio
async def test_p1_completed_members_keep_quest_and_reward_when_group_combat_is_refused(
    database, monkeypatch
):
    import asterion.application.p1 as p1_module

    monkeypatch.setattr(p1_module, "uuid4", lambda: UUID(int=7001))
    actors = (992111, 992112, 992113, 992114)
    names = await _seed_party(database, actors)
    async with database[1].begin() as session:
        characters = list(
            (
                await session.scalars(
                    select(Character).where(Character.telegram_id.in_(actors))
                )
            ).all()
        )
        character_by_actor = {character.telegram_id: character for character in characters}
        for actor in actors:
            character = character_by_actor[actor]
            quest = await session.scalar(
                select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P1")
            )
            if actor == actors[0]:
                quest.step = 3
                quest.state_version = 3
                quest.progress = {"pegadas": True, "sulcos": True}
            else:
                quest.status = "completed"
                quest.step = 7
                quest.progress = {"completed": True}
                session.add(
                    RewardEvent(
                        character_id=character.id,
                        source_id="p1.vozes_na_estrada",
                    )
                )
    groups = GroupService(database[1], "ocaso")
    await _create_group(groups, actors[0], actors[1:], names)
    service = P1Service(database[1], "ocaso", groups)
    # P1 is not a Boss: a Group of already-finished members cannot be proposed.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await service.propose_group_combat(actors[0], 3)
    assert not await groups.activity_proposals(actors[0])
    # Only the actor fights, Solo, and the finished members are left untouched.
    started = await service.start_solo_combat(actors[0], 3)
    assert started.combat is not None and not started.combat.party_mode
    await _finish_p1_solo_fight(service, actors[0], database)
    async with database[1]() as session:
        quests = {
            character.telegram_id: quest
            for quest, character in (
                await session.execute(
                    select(Quest, Character)
                    .join(Character, Character.id == Quest.character_id)
                    .where(Character.telegram_id.in_(actors), Quest.quest_id == "P1")
                )
            ).all()
        }
        assert quests[actors[0]].step == 4
        assert all(quests[actor].status == "completed" for actor in actors[1:])
        assert all(quests[actor].step == 7 for actor in actors[1:])
        helper_character_ids = list(
            (
                await session.scalars(
                    select(Character.id).where(Character.telegram_id.in_(actors[1:]))
                )
            ).all()
        )
        rewards = list(
            (
                await session.scalars(
                    select(RewardEvent).where(
                        RewardEvent.character_id.in_(helper_character_ids),
                        RewardEvent.source_id == "p1.vozes_na_estrada",
                    )
                )
            ).all()
        )
        assert len(rewards) == 3
        assert not await session.scalar(select(GroupActivityParticipant).limit(1))


@pytest.mark.asyncio
async def test_campaign_bosses_share_frozen_combat_and_settle_per_character(database):
    actors = (992121, 992122)
    names = await _seed_party(database, actors)
    sessions = database[1]
    async with sessions.begin() as session:
        characters = list(
            (
                await session.scalars(
                    select(Character).where(Character.telegram_id.in_(actors))
                )
            ).all()
        )
        for character in characters:
            character.level = 10
            world = await session.get(WorldState, character.id)
            world.region = "Terras do Ocaso"
            world.location = RUINS
            is_helper = character.telegram_id == actors[1]
            session.add_all(
                [
                    Quest(
                        character_id=character.id,
                        quest_id=P5_ID,
                        title="A Porta do Poente",
                        status="completed" if is_helper else "active",
                        step=6 if is_helper else 3,
                        content_version=P5_VERSION,
                        progress=(
                            {"completed": True, "door_known": True}
                            if is_helper
                            else {"door_known": True}
                        ),
                    ),
                    Quest(
                        character_id=character.id,
                        quest_id=P6_ID,
                        title="O Vigia Partido",
                        status="completed" if is_helper else "active",
                        step=9 if is_helper else 4,
                        content_version=P6_VERSION,
                        progress=(
                            {"completed": True}
                            if is_helper
                            else {
                                "door_known": True,
                                "central_structure_examined_before": True,
                            }
                        ),
                    ),
                    Quest(
                        character_id=character.id,
                        quest_id=S6_ID,
                        title="Onde os Nomes Terminaram",
                        status="completed" if is_helper else "active",
                        step=7 if is_helper else 4,
                        content_version=S6_VERSION,
                        progress=(
                            {"completed": True}
                            if is_helper
                            else {"abandoned_shelter_examined": True}
                        ),
                    ),
                ]
            )

    groups = GroupService(sessions, "ocaso")
    await _create_group(groups, actors[0], (actors[1],), names)

    p5 = P5Service(sessions, "ocaso", groups)
    p5_view = await _start_group_boss(
        groups, p5, actors[0], actors[1], "campaign_p5", version=0
    )
    assert p5_view.group_size == 2
    assert p5_view.combat.party_mode
    assert p5_view.combat.fighters["enemy"].stats == scale_campaign_boss_stats(
        road_enemy_stats(SUNSET_CUSTODIAN, 9), 2
    )
    p5_id = p5_view.encounter_id
    assert p5_id is not None
    await _seed_enemy_at_one_hp(database, p5_id)
    await _complete_shared_boss_fight(p5, actors, database, p5_id)
    async with sessions() as session:
        quests = {
            character.telegram_id: quest
            for quest, character in (
                await session.execute(
                    select(Quest, Character)
                    .join(Character, Character.id == Quest.character_id)
                    .where(Character.telegram_id.in_(actors), Quest.quest_id == P5_ID)
                )
            ).all()
        }
        assert quests[actors[0]].step == 4
        assert quests[actors[1]].status == "completed" and quests[actors[1]].step == 6

    async with sessions.begin() as session:
        for character in (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all():
            world = await session.get(WorldState, character.id)
            world.region = "Terras do Ocaso"
            world.location = P6_CHAMBER

    p6 = P6Service(sessions, "ocaso", groups)
    p6_view = await _start_group_boss(
        groups, p6, actors[0], actors[1], "campaign_p6", version=0
    )
    assert p6_view.group_size == 2
    assert p6_view.combat.fighters["enemy"].stats == scale_campaign_boss_stats(
        road_enemy_stats(VIGIA_PARTIDO, 10), 2
    )
    p6_id = p6_view.encounter_id
    assert p6_id is not None
    await _seed_enemy_at_one_hp(database, p6_id)
    await _complete_shared_boss_fight(p6, actors, database, p6_id)
    async with sessions() as session:
        quests = {
            character.telegram_id: quest
            for quest, character in (
                await session.execute(
                    select(Quest, Character)
                    .join(Character, Character.id == Quest.character_id)
                    .where(Character.telegram_id.in_(actors), Quest.quest_id == P6_ID)
                )
            ).all()
        }
        assert quests[actors[0]].step == 6
        assert quests[actors[1]].status == "completed" and quests[actors[1]].step == 9
        nucleus_events = list(
            (
                await session.scalars(
                    select(RewardEvent).where(
                        RewardEvent.source_id == P6_NUCLEUS_SOURCE
                    )
                )
            ).all()
        )
        assert len(nucleus_events) == 1
        assert nucleus_events[0].character_id == quests[actors[0]].character_id

    async with sessions.begin() as session:
        for character in (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all():
            world = await session.get(WorldState, character.id)
            world.region = "Terras do Ocaso"
            world.location = RUINS

    s6 = S6Service(sessions, "ocaso", groups)
    s6_view = await _start_group_boss(
        groups, s6, actors[0], actors[1], "campaign_s6", version=0
    )
    assert s6_view.group_size == 2
    assert s6_view.combat.fighters["enemy"].name == LAST_TRACE_GUARDIAN.name
    assert s6_view.combat.fighters["enemy"].stats == scale_campaign_boss_stats(
        road_enemy_stats(LAST_TRACE_GUARDIAN, 10), 2
    )
    s6_id = s6_view.encounter_id
    assert s6_id is not None
    await _seed_enemy_at_one_hp(database, s6_id)
    await _complete_shared_boss_fight(s6, actors, database, s6_id)
    async with sessions() as session:
        quests = {
            character.telegram_id: quest
            for quest, character in (
                await session.execute(
                    select(Quest, Character)
                    .join(Character, Character.id == Quest.character_id)
                    .where(Character.telegram_id.in_(actors), Quest.quest_id == S6_ID)
                )
            ).all()
        }
        assert quests[actors[0]].step == 5
        assert quests[actors[1]].status == "completed" and quests[actors[1]].step == 7


@pytest.mark.asyncio
async def test_single_member_social_group_uses_compatible_solo_combat_actor(database):
    actor = 992131
    names = await _seed_party(database, (actor,))
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.level = 9
        quest = Quest(
            character_id=character.id,
            quest_id=P5_ID,
            title="A Porta do Poente",
            status="active",
            step=3,
            content_version=P5_VERSION,
            progress={"door_known": True},
        )
        session.add(quest)
        world = await session.get(WorldState, character.id)
        world.region = "Terras do Ocaso"
        world.location = RUINS

    groups = GroupService(sessions, "ocaso")
    await _create_group(groups, actor, (), names)
    p5 = P5Service(sessions, "ocaso", groups)
    await p5.propose_group_combat(actor, 0)
    proposal = (await groups.activity_proposals(actor))[0]
    combat_view = await p5.start_group_combat(
        actor, proposal.proposal_id, expected_revision=proposal.revision
    )
    assert combat_view is not None and combat_view.combat is not None
    assert combat_view.group_size == 1
    assert combat_view.combat_actor_key == "player"
    assert not combat_view.combat.party_mode
    assert combat_view.combat.fighters["enemy"].stats == road_enemy_stats(
        SUNSET_CUSTODIAN, 9
    )
    await _seed_enemy_at_one_hp(database, combat_view.encounter_id)
    await _complete_shared_boss_fight(
        p5, (actor,), database, combat_view.encounter_id
    )
