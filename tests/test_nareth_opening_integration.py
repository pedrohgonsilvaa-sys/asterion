from dataclasses import replace
from datetime import UTC, datetime, timedelta

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
from asterion.domain.combat import allowed_actions
from asterion.domain.road import (
    EXPLORATION_CATEGORY_WEIGHTS,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    NARETH_BASIC_MATERIAL_CREATURE_IDS,
    NARETH_CAMPINAS_LOCATION,
    NARETH_CREATURES,
    creature_for,
    material_for,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    HuntContext,
    HuntRound,
    HuntRoundEncounter,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import start_manual_hunt_after_no_match
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


def test_nareth_material_table_matches_authority_and_uses_independent_ordinals():
    expected = {
        "galgo_meridiano": (("material.nareth.couro_de_horizonte", 100),),
        "abutre_marco": (("material.nareth.erva_de_vento", 65), ("material.nareth.po_de_eixo", 35)),
        "errante_valas": (
            ("material.nareth.bronze_de_marco", 65),
            ("material.nareth.po_de_eixo", 35),
        ),
        "escaravelho_canal": (
            ("material.nareth.erva_de_vento", 55),
            ("material.nareth.po_de_eixo", 45),
        ),
        "cervo_horizonte": (("material.nareth.couro_de_horizonte", 100),),
        "serpe_campinas": (
            ("material.nareth.erva_de_vento", 75),
            ("material.nareth.couro_de_horizonte", 25),
        ),
        "casco_invertido": (
            ("material.nareth.couro_de_horizonte", 80),
            ("material.nareth.po_de_eixo", 20),
        ),
        "mariposa_eixo": (
            ("material.nareth.po_de_eixo", 70),
            ("material.nareth.erva_de_vento", 30),
        ),
        "vigia_meridiano": (
            ("material.nareth.bronze_de_marco", 90),
            ("material.nareth.po_de_eixo", 10),
        ),
        "alfa_horizonte": (
            ("material.nareth.couro_de_horizonte", 85),
            ("material.nareth.po_de_eixo", 15),
        ),
        "serpe_eixo": (("material.nareth.erva_de_vento", 60), ("material.nareth.po_de_eixo", 40)),
        "custodio_invertido": (
            ("material.nareth.bronze_de_marco", 75),
            ("material.nareth.po_de_eixo", 25),
        ),
    }
    assert NARETH_BASIC_MATERIAL_CREATURE_IDS == frozenset(expected)
    assert {creature_id: MATERIAL_POOLS[creature_id] for creature_id in expected} == expected

    seed = "persisted-economic-seed"
    creature_id = "abutre_marco"
    results = tuple(
        material_for(creature_id, f"{seed}:material.basic.{ordinal}") for ordinal in range(4)
    )
    assert results == tuple(
        material_for(creature_id, f"{seed}:material.basic.{ordinal}") for ordinal in range(4)
    )
    assert all(
        item_id in {material for material, _ in expected[creature_id]} for item_id in results
    )


@pytest.mark.asyncio
async def test_nareth_hunt_and_round_unlock_after_p13_and_desbravar_is_unchanged(
    database, monkeypatch
):
    import asterion.application.road as road_module
    import asterion.application.round as round_module

    actor = 991321
    character_id, sessions = await _seed_nareth_entry(database, actor)
    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso")
    p13 = await _enter_campinas(road, missions, actor)
    assert p13 is not None and p13.status == "active"

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
        "escaravelho_canal",
        "cervo_horizonte",
        "serpe_campinas",
        "casco_invertido",
        "mariposa_eixo",
        "vigia_meridiano",
        "alfa_horizonte",
        "serpe_eixo",
        "custodio_invertido",
    }

    before_p13 = await road.resume(actor)
    assert before_p13 is not None and before_p13.kind == "nareth_campinas"
    assert before_p13.explore_enabled is True and before_p13.hunt_enabled is False
    assert await road.prepare_hunt(actor) is None
    assert await road.start_hunt(actor) is None
    assert await RoundService(sessions, "ocaso").prepare_round(actor, 5) is None

    local_screen = render_current_local(before_p13, explore_state="available")
    assert "Desbravar" in local_screen.text
    before_callbacks = {
        button.callback_data for row in local_screen.keyboard.inline_keyboard for button in row
    }
    assert "road:explore:start" in before_callbacks
    assert "road:hunt" not in before_callbacks
    assert "world:round" not in before_callbacks

    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.nareth.campinas.marco_primeiro_meridiano",
            "Marco do Primeiro Meridiano encontrado.",
        ),
    )
    exploration = await road.explore(actor)
    assert exploration is not None
    assert exploration.result_id == "explore.nareth.campinas.marco_primeiro_meridiano"
    assert exploration.kind == "exploration"
    async with sessions() as session:
        assert (
            await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"explore:{exploration.attempt_id}",
                )
            )
            == 1
        )
        assert (
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.fragment_id == "codex.fragment.nareth.campinas.meridian_marker",
                )
            )
            is not None
        )
    await road.acknowledge_result(actor, exploration.attempt_id)

    await _complete_p13(road, missions, actor)
    posto = await road.resume(actor)
    assert posto is not None and posto.kind == "nareth_posto"
    assert posto.hunt_enabled is False and posto.explore_enabled is False
    assert await road.prepare_hunt(actor) is None
    assert await RoundService(sessions, "ocaso").prepare_round(actor, 5) is None

    entered = await road.travel_route(actor, NARETH_CAMPINAS_LABEL)
    assert entered is not None and entered.location == NARETH_CAMPINAS_LABEL
    local = await road.resume(actor)
    assert local is not None and local.kind == "nareth_campinas"
    assert local.hunt_enabled is True and local.explore_enabled is True
    assert local.familiar is False
    prepared = await road.prepare_hunt(actor)
    assert prepared is not None and prepared.kind == "hunt_prepare"
    round_service = RoundService(sessions, "ocaso")
    round_before_manual_win = await round_service.prepare_round(actor, 5)
    assert round_before_manual_win is not None
    assert round_before_manual_win.kind == "nareth_campinas"
    callbacks = {
        button.callback_data
        for row in render_road(local).keyboard.inline_keyboard
        for button in row
    }
    assert "road:hunt" in callbacks
    assert "world:round" not in callbacks

    # Keep the integration focused on settlement, while forcing an eligible
    # canonical Campinas creature and a survivable combat in the test harness.
    original_create = road_module.create_road_combat

    def safe_combat(*args, **kwargs):
        combat = original_create(*args, **kwargs)
        enemy = combat.fighters["enemy"]
        enemy.stats = replace(enemy.stats, attack=1)
        return combat

    monkeypatch.setattr(road_module, "create_road_combat", safe_combat)
    monkeypatch.setattr(round_module, "create_road_combat", safe_combat)
    monkeypatch.setattr(
        road_module, "select_creature", lambda *_args, **_kwargs: creature_for("errante_valas")
    )
    monkeypatch.setattr(
        round_module, "select_creature", lambda *_args, **_kwargs: creature_for("errante_valas")
    )
    manual = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert manual is not None and manual.kind == "combat"
    activity_id = manual.activity_id
    submitted_version = manual.combat.version
    for _ in range(100):
        if manual.kind != "combat":
            break
        actions = allowed_actions(manual.combat)
        action = "art" if "art" in actions else "attack"
        submitted_version = manual.combat.version
        manual = await road.action(actor, activity_id, submitted_version, action)
    assert manual is not None and manual.kind == "hunt_victory"

    async with sessions() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity_id)
        )
        assert context is not None and context.creature_id == "errante_valas"
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{activity_id}",
            )
        )
        assert reward is not None
        manual_materials = list(
            (
                await session.scalars(
                    select(RewardComponent)
                    .where(
                        RewardComponent.reward_event_id == reward.id,
                        RewardComponent.kind == "material",
                    )
                    .order_by(RewardComponent.id)
                )
            ).all()
        )
        assert len(manual_materials) in {1, 2}
        expected_manual = [
            material_for(context.creature_id, f"{context.seed}:material.basic.{ordinal}")
            for ordinal in range(len(manual_materials))
        ]
        actual_manual = [row.item_id for row in manual_materials]
        # RewardComponent has random UUID ids, so ordering by that key does
        # not preserve the stable material.basic.<ordinal> draw order.
        assert sorted(actual_manual) == sorted(expected_manual), {
            "seed": context.seed,
            "actual": actual_manual,
            "expected": expected_manual,
            "legacy_first": material_for(context.creature_id, context.seed),
            "legacy_ordinal": material_for(context.creature_id, f"{context.seed}:material:0"),
            "basic_ordinal": material_for(
                context.creature_id, f"{context.seed}:material.basic.0"
            ),
        }
        assert (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == HUNT_PROFILES[NARETH_CAMPINAS_LOCATION].round_familiarity,
                )
            )
            is not None
        )

    repeated = await road.action(actor, activity_id, submitted_version, "attack")
    assert repeated is not None and repeated.kind == "hunt_victory"
    async with sessions() as session:
        assert (
            await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"activity:{activity_id}",
                )
            )
            == 1
        )
    await road.acknowledge_result(actor)

    # Ronda opens only after the first valid manual victory and settles through
    # the same RoadService table/subdraw implementation.
    async def no_round_match(*_args, **_kwargs):
        return False

    round_service.pvpve.queue_round_hunt = no_round_match
    round_prepare = await round_service.prepare_round(actor, 5)
    assert round_prepare is not None and round_prepare.kind == "round_prepare"
    round_started = await round_service.start_round(
        actor, round_prepare.round_id, round_prepare.state_version
    )
    assert round_started is not None and round_started.kind == "round_active"
    async with sessions.begin() as session:
        state = await session.get(HuntRound, round_started.round_id)
        assert state is not None and state.next_resolution_at is not None
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
    await round_service.advance_due_rounds()
    async with sessions() as session:
        state = await session.get(HuntRound, round_started.round_id)
        assert state is not None and state.completed_encounters == 1
        round_encounter = await session.scalar(
            select(HuntRoundEncounter).where(HuntRoundEncounter.round_id == state.id)
        )
        assert round_encounter is not None and round_encounter.status == "completed"
        assert round_encounter.creature_id == "errante_valas"
        round_context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == round_encounter.activity_id)
        )
        assert round_context is not None and round_context.loot_profile == "round"
        round_reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{round_encounter.activity_id}",
            )
        )
        assert round_reward is not None
        round_materials = list(
            (
                await session.scalars(
                    select(RewardComponent)
                    .where(
                        RewardComponent.reward_event_id == round_reward.id,
                        RewardComponent.kind == "material",
                    )
                    .order_by(RewardComponent.id)
                )
            ).all()
        )
        assert len(round_materials) in {1, 2}
        expected_round = [
            material_for(
                round_context.creature_id, f"{round_context.seed}:material.basic.{ordinal}"
            )
            for ordinal in range(len(round_materials))
        ]
        # RewardComponent uses random UUID ids, so row order does not preserve
        # the stable material.basic.<ordinal> draw order.
        assert sorted(row.item_id for row in round_materials) == sorted(expected_round)
