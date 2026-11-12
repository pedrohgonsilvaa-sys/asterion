from copy import deepcopy
from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.groups import GroupError, GroupService
from asterion.application.p3 import P3_ID
from asterion.application.p4 import P4_ID, P4_REWARD_SOURCE, P4Service
from asterion.application.progression import level_xp
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, RoadService
from asterion.application.s3 import S3_ID, S3_REWARD_SOURCE, S3Service
from asterion.infrastructure.db.models import (
    Brazier,
    CampaignSharedEncounter,
    Character,
    CodexEntry,
    CodexFragment,
    Encounter,
    ExplorationAttempt,
    GameActivity,
    HuntContext,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_p3_integration import _seed_p3


def _terminal(result: str):
    def finish(combat, action, **_kwargs):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = result
        if result == "defeat":
            updated.fighters["player"].hp = Decimal(0)
        return updated

    return finish


async def _seed_campaign(database, actor: int, *, level: int):
    character_id, _ = await _seed_p3(database, actor, level=level)
    _, sessions = database
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P3_ID,
                title="Sob Galhos Calcinados",
                status="completed",
                step=6,
                content_version="tdo-1.0.10",
                progress={"completed": True},
            )
        )
        session.add_all(
            [
                LocationDiscovery(
                    character_id=character_id,
                    location_id="tdo.location.bosque_calcinado",
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id="route.tdo.charneca_bosque",
                ),
            ]
        )
    return character_id, sessions


async def _reach_bosque(sessions, actor: int):
    road = RoadService(sessions, "ocaso")
    charneca = await road.travel_route(actor, CHARNECA)
    assert charneca is not None and charneca.location == CHARNECA
    bosque = await road.travel_route(actor, BOSQUE)
    assert bosque is not None and bosque.location == BOSQUE
    return road


@pytest.mark.asyncio
async def test_s3_offer_tracks_and_fixed_combat_are_persistent(database):
    actor = 998401
    character_id, sessions = await _seed_campaign(database, actor, level=5)
    service = S3Service(sessions, "ocaso")
    offer = await service.offer(actor)
    assert offer is not None and offer.available and offer.status == "unaccepted"
    async with sessions() as session:
        assert await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S3_ID)
        ) is None

    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    road = await _reach_bosque(sessions, actor)
    route = await service.interact(actor, accepted.state_version, "route")
    assert route is not None and route.step == 2
    first = await service.interact(actor, route.state_version, "track", "s3.track.3")
    duplicate = await service.interact(actor, first.state_version, "track", "s3.track.3")
    second = await service.interact(actor, duplicate.state_version, "track", "s3.track.1")
    combat = await service.interact(actor, second.state_version, "track", "s3.track.2")
    assert combat is not None and combat.kind == "combat" and combat.combat is not None
    assert combat.combat.fighters["enemy"].name == "Cervo Escoriado"
    assert combat.combat.fighters["enemy"].level == 5
    assert combat.combat.variant is None
    assert combat.combat.ai_cycle[0] == "ocaso_charge"
    assert combat.activity_id and combat.encounter_id and combat.combat_id
    resumed = await service.resume(actor)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )
    async with sessions() as session:
        activity = await session.get(GameActivity, combat.activity_id)
        character = await session.get(Character, character_id)
        assert activity is not None and activity.content_id == "s3_scripted_cervo_escoriado"
        assert await session.scalar(
            select(HuntContext.game_activity_id).where(
                HuntContext.game_activity_id == combat.activity_id
            )
        ) is None
        assert await session.scalar(
            select(ExplorationAttempt.id).where(
                ExplorationAttempt.character_id == character_id
            )
        ) is None
        assert character is not None and character.vigor == 61
    assert road is not None


@pytest.mark.asyncio
async def test_s3_group_member_tracks_alone_and_group_encounter_is_refused(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actors = (998410, 998411)
    seeded = [await _seed_campaign(database, actor, level=5) for actor in actors]
    character_ids = [row[0] for row in seeded]
    sessions = database[1]
    groups = GroupService(sessions, "ocaso")
    service = S3Service(sessions, "ocaso", groups=groups)
    accepted = [await service.accept(actor) for actor in actors]
    assert all(view is not None and view.status == "active" for view in accepted)

    group = await groups.create_group(actors[0])
    async with sessions() as session:
        invitee = await session.scalar(
            select(Character).where(Character.id == character_ids[1])
        )
        assert invitee is not None
        invitee_name = invitee.name
    invite = await groups.invite(
        actors[0], invitee_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    await _reach_bosque(sessions, actors[0])
    await _reach_bosque(sessions, actors[1])

    # Objectives are Solo (Ação × Consequência §5): only the actor advances.
    view = await service.resume(actors[0])
    view = await service.interact(actors[0], view.state_version, "route")
    companion = await service.resume(actors[1])
    assert view.step == 2 and companion.step == 1
    for track_id in ("s3.track.2", "s3.track.1", "s3.track.3"):
        view = await service.interact(actors[0], view.state_version, "track", track_id)
    companion = await service.resume(actors[1])
    # The fight opens as a Solo combat even though the actor belongs to a Group.
    assert view.kind == "combat" and view.group_size == 1
    assert companion.step == 1 and not companion.progress.get("tracks")

    # S3 is not a Boss: the Group proposal is refused and nothing is reserved.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await service.propose_group_combat(actors[0], view.state_version)
    assert not await groups.activity_proposals(actors[1])
    resumed = await service.resume(actors[0])
    assert resumed.activity_id == view.activity_id

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    resolved = await service.action(
        actors[0], view.activity_id, view.activity_state_version, "attack"
    )
    assert resolved.step == 4
    companion = await service.resume(actors[1])
    assert companion.step == 1

    async with sessions() as session:
        activities = (
            await session.scalars(
                select(GameActivity).where(
                    GameActivity.character_id.in_(character_ids),
                    GameActivity.content_id == "s3_scripted_cervo_escoriado",
                )
            )
        ).all()
        assert [activity.character_id for activity in activities] == [character_ids[0]]
        assert {activity.status for activity in activities} == {"completed"}
        assert not await session.scalar(select(CampaignSharedEncounter).limit(1))


@pytest.mark.asyncio
async def test_s3_victory_report_reward_and_retry_are_idempotent(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998402
    character_id, sessions = await _seed_campaign(database, actor, level=5)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.xp = level_xp(5) - 1
    service = S3Service(sessions, "ocaso")
    accepted = await service.accept(actor)
    await _reach_bosque(sessions, actor)
    view = await service.interact(actor, accepted.state_version, "route")
    for track_id in ("s3.track.1", "s3.track.2", "s3.track.3"):
        view = await service.interact(actor, view.state_version, "track", track_id)
    assert view.kind == "combat"
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await service.action(
        actor, view.activity_id, view.activity_state_version, "attack"
    )
    assert victory is not None and victory.kind == "cargo" and victory.step == 4
    async with sessions() as session:
        assert (await session.get(Character, character_id)).level == 6
    cargo = await service.interact(actor, victory.state_version, "cargo")
    assert cargo is not None and cargo.kind == "report" and cargo.step == 5
    road = RoadService(sessions, "ocaso")
    await road.travel_route(actor, CHARNECA)
    await road.travel_route(actor, REFUGE)
    completed = await service.interact(actor, cargo.state_version, "report")
    assert completed is not None and completed.status == "completed"
    assert (await service.detail(actor)).kind == "completed"
    repeated = await service.interact(actor, cargo.state_version, "report")
    assert repeated is not None and repeated.status == "completed"
    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S3_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )
        ).all()
        assert {(row.kind, row.quantity) for row in components} == {
            ("xp", 1760),
            ("crowns", 90),
            ("material", 2),
        }
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"{S3_REWARD_SOURCE}:enemy-xp:{view.activity_id}",
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(CodexEntry.character_id == character_id)
        ) is None


@pytest.mark.asyncio
async def test_s3_defeat_keeps_tracks_and_retry_materializes_new_cervo(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998404
    character_id, sessions = await _seed_campaign(database, actor, level=5)
    service = S3Service(sessions, "ocaso")
    accepted = await service.accept(actor)
    await _reach_bosque(sessions, actor)
    view = await service.interact(actor, accepted.state_version, "route")
    for track_id in ("s3.track.3", "s3.track.1", "s3.track.2"):
        view = await service.interact(actor, view.state_version, "track", track_id)
    initial_id = view.activity_id
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await service.action(
        actor, view.activity_id, view.activity_state_version, "attack"
    )
    assert defeated is not None and defeated.kind == "recovery"
    assert defeated.status == "active" and defeated.location == REFUGE
    assert defeated.progress["tracks"] == ["s3.track.1", "s3.track.2", "s3.track.3"]
    assert defeated.progress["awaiting_retry"] is True
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.hp == character.max_hp
        assert character.vigor == 61
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S3_REWARD_SOURCE,
            )
        ) is None
    road = RoadService(sessions, "ocaso")
    await road.travel_route(actor, CHARNECA)
    await road.travel_route(actor, BOSQUE)
    monkeypatch.setattr(scripted_combat, "act", lambda combat, action: combat)
    retry = await service.retry(actor, defeated.state_version)
    assert retry is not None and retry.kind == "combat"
    assert retry.activity_id != initial_id
    assert retry.combat.fighters["enemy"].name == "Cervo Escoriado"
    assert retry.combat.fighters["enemy"].level == 5
    assert retry.combat.variant is None


@pytest.mark.asyncio
async def test_p4_defeat_recovery_retry_uses_new_fixed_vigia(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998405
    character_id, sessions = await _seed_campaign(database, actor, level=7)
    service = P4Service(sessions, "ocaso")
    accepted = await service.accept(actor)
    await _reach_bosque(sessions, actor)
    path = await service.action(actor, accepted.state_version, "path")
    combat = await service.action(actor, path.state_version, "enter")
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await service.action_combat(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert defeated is not None and defeated.kind == "recovery"
    assert defeated.location == REFUGE and defeated.progress["awaiting_retry"]
    assert defeated.progress["ruins_discovered"] is True
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.hp == character.max_hp
        assert character.vigor == 61
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P4_REWARD_SOURCE,
            )
        ) is None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "tdo.location.ruinas_do_vigia",
            )
        ) is not None
    road = RoadService(sessions, "ocaso")
    await road.travel_route(actor, CHARNECA)
    await road.travel_route(actor, BOSQUE)
    returned = await service.action(actor, defeated.state_version, "enter")
    assert returned is not None and returned.location == "Ruínas do Vigia"
    monkeypatch.setattr(scripted_combat, "act", lambda combat, action: combat)
    retry = await service.action(actor, returned.state_version, "retry")
    assert retry is not None and retry.kind == "combat"
    assert retry.activity_id != combat.activity_id
    assert retry.encounter_id != combat.encounter_id
    assert retry.combat.fighters["enemy"].name == "Vigia Rachado"
    assert retry.combat.fighters["enemy"].level == 7
    assert retry.combat.variant is None


@pytest.mark.asyncio
async def test_active_p4_rejects_stale_brazier_travel_callback(database):
    actor = 998406
    character_id, sessions = await _seed_campaign(database, actor, level=7)
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P4",
                title="Pedras que Ainda Vigiam",
                status="active",
                step=3,
                content_version="tdo-1.0.11",
                progress={"ruins_discovered": True},
            )
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        world.location = "Ruínas do Vigia"
        session.add_all(
            [
                Brazier(character_id=character_id, brazier_id="tdo.brazier.poente"),
                Brazier(character_id=character_id, brazier_id="tdo.brazier.refugio_do_ocaso"),
            ]
        )
    road = RoadService(sessions, "ocaso")
    assert await road.travel_brazier(actor, "tdo.brazier.refugio_do_ocaso") is None
    async with sessions() as session:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        assert world.location == "Ruínas do Vigia"


@pytest.mark.asyncio
async def test_p4_fixed_vigia_barrier_and_reward_unlocks(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998403
    character_id, sessions = await _seed_campaign(database, actor, level=7)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.xp = level_xp(7) - 1
    service = P4Service(sessions, "ocaso")
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    await _reach_bosque(sessions, actor)
    path = await service.action(actor, accepted.state_version, "path")
    combat = await service.action(actor, path.state_version, "enter")
    assert combat is not None and combat.kind == "combat" and combat.combat is not None
    assert combat.combat.fighters["enemy"].name == "Vigia Rachado"
    assert combat.combat.fighters["enemy"].level == 7
    assert combat.combat.variant is None
    assert combat.activity_id and combat.encounter_id and combat.combat_id
    guard = combat.combat.enemy_actions["guarda_rachada"]
    assert guard.self_barrier_coefficient == Decimal("0.70")
    assert guard.self_barrier_duration == 2
    resumed = await service.resume(actor)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await service.action_combat(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert victory is not None and victory.kind == "structures" and victory.step == 4
    async with sessions() as session:
        assert (await session.get(Character, character_id)).level == 8
    one = await service.action(actor, victory.state_version, "structure", "p4.guard_structure.2")
    two = await service.action(actor, one.state_version, "structure", "p4.guard_structure.1")
    safe = await service.action(actor, two.state_version, "safe_route")
    returned = await service.action(actor, safe.state_version, "return")
    road = RoadService(sessions, "ocaso")
    await road.travel_route(actor, CHARNECA)
    await road.travel_route(actor, REFUGE)
    oren = await service.action(actor, returned.state_version, "report_oren")
    assert oren is not None and oren.status == "active"
    completed = await service.action(actor, oren.state_version, "report_alda")
    assert completed is not None and completed.status == "completed"
    assert set(completed.progress["reports"]) == {"alda", "oren"}
    duplicate = await service.action(actor, oren.state_version, "report_alda")
    assert duplicate is not None and duplicate.status == "completed"
    async with sessions() as session:
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P4_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert {(row.kind, row.quantity) for row in components} == {
            ("xp", 5700),
            ("crowns", 250),
            ("material", 2),
        }
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.history.antigos_asterianos",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "p4.ruinas.funcao_de_guarda",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "explore.ruinas_do_vigia",
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(Brazier.character_id == character_id)
        ) is None
        assert await session.scalar(
            select(Encounter.game_activity_id).where(
                Encounter.game_activity_id == combat.activity_id
            )
        ) is not None


@pytest.mark.asyncio
async def test_p4_group_member_enters_ruins_alone_and_group_encounter_is_refused(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actors = (998421, 998422)
    seeded = [await _seed_campaign(database, actor, level=7) for actor in actors]
    character_ids = [row[0] for row in seeded]
    sessions = database[1]
    groups = GroupService(sessions, "ocaso")
    service = P4Service(sessions, "ocaso", groups=groups)
    for actor in actors:
        accepted = await service.accept(actor)
        assert accepted is not None and accepted.status == "active"
        await _reach_bosque(sessions, actor)

    async with sessions() as session:
        invitee = await session.scalar(
            select(Character).where(Character.id == character_ids[1])
        )
        assert invitee is not None
        invitee_name = invitee.name
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], invitee_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1],
        invitation.invite_id,
        expected_revision=invitation.revision,
        accept=True,
    )

    # Objectives are Solo (Ação × Consequência §5): only the actor advances.
    view = await service.resume(actors[0])
    assert view is not None and view.step == 1
    path = await service.action(actors[0], view.state_version, "path")
    assert path is not None and path.step == 2
    ruins = await service.action(actors[0], path.state_version, "enter")
    # The fight opens as a Solo combat even though the actor belongs to a Group.
    assert ruins is not None and ruins.step == 3
    assert ruins.kind == "combat" and ruins.group_size == 1
    second = await service.resume(actors[1])
    assert second is not None and second.step == 1

    # P4 is not a Boss: the Group proposal is refused and nothing is reserved.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await service.propose_group_combat(actors[0], ruins.state_version)
    assert not await groups.activity_proposals(actors[1])

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await service.action_combat(
        actors[0], ruins.activity_id, ruins.activity_state_version, "attack"
    )
    assert victory is not None and victory.step == 4

    async with sessions() as session:
        quests = {
            row.character_id: row.step
            for row in (
                await session.scalars(
                    select(Quest).where(
                        Quest.character_id.in_(character_ids), Quest.quest_id == P4_ID
                    )
                )
            ).all()
        }
        assert quests == {character_ids[0]: 4, character_ids[1]: 1}
        assert not await session.scalar(select(CampaignSharedEncounter).limit(1))
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id.in_(character_ids),
                RewardEvent.source_id == P4_REWARD_SOURCE,
            )
        ) is None
