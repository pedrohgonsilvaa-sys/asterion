import pytest
from sqlalchemy import func, select

from asterion.application.groups import GroupService
from asterion.application.nareth_missions import (
    CAMPINAS_LOCATION_ID,
    HORIZON_BRAZIER,
    P13_ID,
    P13_REWARD_SOURCE,
    POSTO,
    POSTO_BRAZIER,
    POSTO_LOCATION_ID,
    REGION_UNLOCK,
    ROTAS_CODEX,
    S13_ID,
    S13_REWARD_SOURCE,
    NarethMissionService,
)
from asterion.application.p7 import REGION as VDE_REGION
from asterion.application.road import (
    NARETH_CAMPINAS_LABEL,
    NARETH_POSTO_LABEL,
    NARETH_REGION,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.bot.nareth_missions_ui import render_nareth_mission
from asterion.bot.road_ui import render_current_local, render_road
from asterion.domain.road import (
    EXPLORATION_CATEGORY_WEIGHTS,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    NARETH_CAMPINAS_LOCATION,
    NARETH_CREATURES,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_s6_p6_integration import _seed_final_campaign


async def _seed_nareth_entry(database, actor: int, *, level: int = 21):
    """Seed a valid P12-complete return point so these tests isolate Nareth."""
    character_id, sessions = await _seed_final_campaign(database, actor, level=level)
    completed = (
        ("P6", "A Âncora do Poente"),
        ("P7", "A Estrada Estrangulada"),
        ("P8", "Entre Galhos Suspensos"),
        ("P9", "Sob a Madeira Morta"),
        ("P10", "Pedra sob as Raízes"),
        ("P11", "Onde Tudo se Enreda"),
        ("P12", "A Matriarca das Raízes"),
    )
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = VDE_REGION
        world.location = "Berço da Matriarca"
        session.add_all(
            [
                Quest(
                    character_id=character_id,
                    quest_id=quest_id,
                    title=title,
                    status="completed",
                    step=1,
                    content_version="vales-1.0.6",
                    progress={"completed": True},
                )
                for quest_id, title in completed
            ]
        )
        session.add_all(
            [
                LocationDiscovery(
                    character_id=character_id,
                    location_id="vde.location.berco_da_matriarca",
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id="route.vde.claustro_berco",
                ),
            ]
        )
    return character_id, sessions


async def _enter_campinas(road, missions, actor: int):
    berco = await road.resume(actor)
    assert berco is not None
    assert NARETH_CAMPINAS_LABEL in berco.route_destinations
    entered = await road.travel_route(actor, NARETH_CAMPINAS_LABEL)
    assert entered is not None and entered.location == NARETH_CAMPINAS_LABEL
    await missions.on_location(actor)
    return await missions.resume(actor, P13_ID)


async def _complete_p13(road, missions, actor: int):
    view = await missions.resume(actor, P13_ID)
    assert view is not None and view.status == "active" and view.kind == "line"
    screen = render_nareth_mission(view)
    assert "Examine a antiga linha de pedra" in screen.text
    for action in ("line", "compare", "horizon_brazier", "follow_route"):
        view = await missions.advance(actor, P13_ID, view.state_version, action)
        assert view is not None
    assert view.kind == "arrive_posto" and view.step == 7
    arrived = await road.travel_route(actor, NARETH_POSTO_LABEL)
    assert arrived is not None and arrived.location == NARETH_POSTO_LABEL
    await missions.on_location(actor)
    view = await missions.resume(actor, P13_ID)
    assert view is not None and view.kind == "posto_brazier" and view.step == 8
    for action in ("posto_brazier", "speak_nera", "record_codex"):
        view = await missions.advance(actor, P13_ID, view.state_version, action)
        assert view is not None
    return view


@pytest.mark.asyncio
async def test_nareth_p13_s13_route_rewards_and_persistence_are_character_scoped(database):
    actor = 991301
    character_id, sessions = await _seed_nareth_entry(database, actor)
    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso")

    p13 = await _enter_campinas(road, missions, actor)
    assert p13 is not None and p13.status == "active" and p13.step == 3
    async with sessions() as session:
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == CAMPINAS_LOCATION_ID,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == REGION_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "explore.nareth.campinas_do_meridiano",
            )
        ) is not None

    completed_p13 = await _complete_p13(road, missions, actor)
    assert completed_p13.status == "completed"
    stale = await missions.advance(
        actor, P13_ID, completed_p13.state_version - 1, "record_codex"
    )
    assert stale is not None and stale.status == "completed"
    async with sessions() as session:
        world = await session.get(WorldState, character_id)
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P13_ID)
        )
        assert world is not None and (world.region, world.location) == (NARETH_REGION, POSTO)
        assert quest is not None and quest.status == "completed"
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P13_REWARD_SOURCE,
            )
        ) == 1
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P13_REWARD_SOURCE,
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
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 19350),
            ("crowns", None, 420),
            ("material", "material.nareth.bronze_de_marco", 1),
            ("material", "material.nareth.couro_de_horizonte", 1),
        }
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id, Brazier.brazier_id == HORIZON_BRAZIER
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id, Brazier.brazier_id == POSTO_BRAZIER
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == POSTO_LOCATION_ID,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "route.nareth.campinas_posto",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "hunt.manual.nareth.campinas_do_meridiano",
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == ROTAS_CODEX,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.nareth.p13.routes_initial",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.nareth.primeiro_meridiano",
            )
        ) is not None

    # Recreating the service models reconnect/resume; completed state and rewards persist.
    missions = NarethMissionService(sessions, "ocaso")
    assert (await missions.resume(actor, P13_ID)).status == "completed"

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 22
    offer = await missions.resume(actor, S13_ID)
    assert offer is not None and offer.kind == "offer" and offer.available
    assert "Pedras que Apontam" in render_nareth_mission(offer).text
    s13 = await missions.start(actor, S13_ID)
    assert s13 is not None and s13.status == "active" and s13.step == 2

    await road.travel_route(actor, NARETH_CAMPINAS_LABEL)
    await missions.on_location(actor)
    s13 = await missions.resume(actor, S13_ID)
    for point in ("a", "b", "c"):
        s13 = await missions.examine(actor, S13_ID, s13.state_version, point)
    assert s13 is not None and s13.kind == "compare" and s13.step == 5
    s13 = await missions.advance(actor, S13_ID, s13.state_version, "compare")
    assert s13 is not None and s13.step == 6 and s13.kind == "report"
    await road.travel_route(actor, NARETH_POSTO_LABEL)
    await missions.on_location(actor)
    s13 = await missions.resume(actor, S13_ID)
    old_version = s13.state_version
    completed_s13 = await missions.advance(actor, S13_ID, old_version, "report")
    assert completed_s13 is not None and completed_s13.status == "completed"
    await missions.advance(actor, S13_ID, old_version, "report")

    async with sessions() as session:
        p13_events = await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P13_REWARD_SOURCE,
            )
        )
        s13_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S13_REWARD_SOURCE,
            )
        )
        assert p13_events == 1 and s13_event is not None
        s13_components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == s13_event.id
                    )
                )
            ).all()
        )
        assert {(row.kind, row.quantity) for row in s13_components} == {
            ("xp", 8260),
            ("crowns", 220),
        }
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.nareth.s13.references",
            )
        ) is not None


@pytest.mark.asyncio
async def test_nareth_shared_p13_credit_is_persisted_individually(database):
    leader, member = 991311, 991312
    leader_id, sessions = await _seed_nareth_entry(database, leader)
    member_id, _ = await _seed_nareth_entry(database, member)
    async with sessions() as session:
        member_row = await session.get(Character, member_id)
        assert member_row is not None
        member_name = member_row.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invite = await groups.invite(
        leader, member_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        member, invite.invite_id, expected_revision=invite.revision, accept=True
    )

    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso")
    await road.travel_route(leader, NARETH_CAMPINAS_LABEL)
    await missions.on_location(leader)
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == leader_id, Quest.quest_id == P13_ID)
        ) is not None
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == member_id, Quest.quest_id == P13_ID)
        ) is None

    await road.travel_route(member, NARETH_CAMPINAS_LABEL)
    await missions.on_location(member)
    view = await missions.resume(leader, P13_ID)
    assert view is not None and view.step == 3
    view = await missions.advance(leader, P13_ID, view.state_version, "line")
    assert view is not None and view.step == 4
    async with sessions() as session:
        for character_id in (leader_id, member_id):
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character_id, Quest.quest_id == P13_ID
                )
            )
            assert quest is not None and quest.status == "active" and quest.step == 4
            assert await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == P13_ID,
                    CampaignObjectiveCredit.objective_id == "p13.old_stone_line",
                )
            ) is not None


@pytest.mark.asyncio
async def test_nareth_desbravar_available_while_hunt_round_settlement_is_blocked(
    database, monkeypatch
):
    import asterion.application.road as road_module

    actor = 991321
    character_id, sessions = await _seed_nareth_entry(database, actor)
    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso")
    p13 = await _enter_campinas(road, missions, actor)
    assert p13 is not None and p13.status == "active"

    local = await road.resume(actor)
    assert local is not None and local.kind == "nareth_campinas"
    assert local.explore_enabled is True
    assert local.hunt_enabled is False
    assert await road.prepare_hunt(actor) is None
    assert await road.start_hunt(actor) is None
    assert await RoundService(sessions, "ocaso").prepare_round(actor, 5) is None

    assert NARETH_CAMPINAS_LOCATION in EXPLORATION_PROFILES
    explore_profile = EXPLORATION_PROFILES[NARETH_CAMPINAS_LOCATION]
    assert explore_profile.category_weights == tuple(EXPLORATION_CATEGORY_WEIGHTS.items())
    assert HUNT_PROFILES[NARETH_CAMPINAS_LOCATION].creature_weights == (
        ("galgo_meridiano", 34),
        ("abutre_marco", 33),
        ("errante_valas", 30),
        ("alfa_horizonte", 3),
    )
    assert {creature.creature_id for creature in NARETH_CREATURES} == {
        "galgo_meridiano",
        "abutre_marco",
        "errante_valas",
        "alfa_horizonte",
    }
    assert all(creature.creature_id not in MATERIAL_POOLS for creature in NARETH_CREATURES)

    local_screen = render_current_local(local, explore_state="available")
    assert "Desbravar" in local_screen.text
    local_callbacks = {
        button.callback_data
        for row in local_screen.keyboard.inline_keyboard
        for button in row
    }
    assert "road:explore:start" in local_callbacks
    assert "road:hunt" not in local_callbacks
    assert "world:round" not in local_callbacks
    assert "road:explore:start" in {
        button.callback_data
        for row in render_road(local).keyboard.inline_keyboard
        for button in row
    }

    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.nareth.campinas.marco_primeiro_meridiano",
            "Marco do Primeiro Meridiano encontrado.",
        ),
    )
    result = await road.explore(actor)
    assert result is not None
    assert result.result_id == "explore.nareth.campinas.marco_primeiro_meridiano"
    assert result.kind == "exploration"
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"explore:{result.attempt_id}",
            )
        ) == 1
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"explore:{result.attempt_id}",
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
        assert [(row.kind, row.quantity) for row in components] == [("xp", 3304)]
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.nareth.campinas.meridian_marker",
            )
        ) is not None
