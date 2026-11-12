from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.groups import GroupError, GroupService
from asterion.application.p7 import REGION as VDE_REGION
from asterion.application.p7 import VIGILIA as VDE_VIGILIA
from asterion.application.road import (
    VDE_CLAUSTRO,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.application.vde_missions import (
    BAIXIOS,
    BAIXIOS_EXPLORE_UNLOCK,
    BAIXIOS_ROUTE_UNLOCK,
    CLAUSTRO_LOCATION_ID,
    MATA,
    P9_ID,
    P10_CONTENT,
    P10_ID,
    P10_REWARD_SOURCE,
    S10_ID,
    S10_REWARD_SOURCE,
    VDEMissionService,
)
from asterion.domain.combat_math import Stats
from asterion.domain.road import (
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    LOCATION_LEVEL_BANDS,
    MATERIAL_POOLS,
    VDE_BAIXIOS_CLAUSTRO_ROUTE,
    VDE_CLAUSTRO_BRAZIER,
    VDE_CLAUSTRO_EXPLORATION_PROFILE,
    VDE_CLAUSTRO_EXPLORE_UNLOCK,
    VDE_CLAUSTRO_HUNT_UNLOCK,
    VDE_CLAUSTRO_LOCATION,
    VDE_CLAUSTRO_PROFILE,
    VDE_ROOTED_WATCHER,
    VDE_SANCTUARY_UNLOCK,
    VDE_TURF_LEECH,
    creature_for,
)
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    Brazier,
    CampaignSharedEncounter,
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_p7_integration import _terminal
from tests.test_vde_s8_p9_s9_integration import _seed_mid_region


async def _seed_late_region(database, actor: int, *, level: int = 18, p10: bool = False):
    character_id, sessions = await _seed_mid_region(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = VDE_REGION
        world.location = BAIXIOS
        session.add_all(
            (
                Quest(
                    character_id=character_id,
                    quest_id=P9_ID,
                    title="Sob a Madeira Morta",
                    status="completed",
                    step=8,
                    content_version="vales-1.0.4",
                    progress={"completed": True},
                ),
                Unlock(character_id=character_id, unlock_id=BAIXIOS_ROUTE_UNLOCK),
                Unlock(character_id=character_id, unlock_id=BAIXIOS_EXPLORE_UNLOCK),
                LocationDiscovery(
                    character_id=character_id,
                    location_id="vde.location.baixios_enredados",
                ),
            )
        )
        if p10:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P10_ID,
                    title="Pedra sob as Raízes",
                    status="completed",
                    step=8,
                    content_version="vales-1.0.4",
                    progress={"completed": True},
                )
            )
    return character_id, sessions


@pytest.mark.asyncio
async def test_p10_gate_and_claustro_activity_level_band(database):
    actor = 998709
    character_id, sessions = await _seed_late_region(database, actor, level=16)
    missions = VDEMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")

    blocked = await missions.start(actor, P10_ID)
    assert blocked is not None and blocked.kind == "unavailable"

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 17
    opened = await missions.start(actor, P10_ID)
    assert opened is not None and opened.status == "active" and opened.step == 1
    opened = await missions.advance(actor, P10_ID, opened.state_version, "follow")
    opened = await missions.advance(actor, P10_ID, opened.state_version, "passage")
    assert opened is not None and opened.location == VDE_CLAUSTRO
    local = await road.resume(actor)
    assert local is not None and not local.explore_enabled and not local.hunt_enabled
    assert await road.prepare_explore(actor) is None


def test_claustro_hunt_round_and_exploration_profiles_match_v104():
    assert HUNT_PROFILES[VDE_CLAUSTRO_LOCATION] is VDE_CLAUSTRO_PROFILE
    assert VDE_CLAUSTRO_PROFILE.creature_weights == (
        ("casca_errante", 35),
        ("mariposa_breu_verde", 30),
        ("vigia_enraizado", 32),
        ("carrasco_casca", 3),
    )
    assert VDE_CLAUSTRO_PROFILE.variant_chance == 18
    assert all(
        creature_id in MATERIAL_POOLS
        for creature_id, _ in VDE_CLAUSTRO_PROFILE.creature_weights
    )
    assert VDE_ROOTED_WATCHER.category == "uncommon"
    assert LOCATION_LEVEL_BANDS[VDE_CLAUSTRO] == (18, 20)

    profile = EXPLORATION_PROFILES[VDE_CLAUSTRO_LOCATION]
    assert profile is VDE_CLAUSTRO_EXPLORATION_PROFILE

    def weights(category):
        return {item.key: item.weight for item in profile.results if item.category == category}

    assert weights("great_discovery") == {"brazier_pedras_enlacadas": 50, "santuario_no_antigo": 50}
    assert weights("knowledge") == {"tracado_no": 60, "passos_vigia": 40}
    assert weights("narrative") == {"pedra_sob_madeira": 55, "corredores_persistem": 45}
    assert weights("combat") == {
        "casca_errante": 35,
        "mariposa_breu_verde": 30,
        "vigia_enraizado": 35,
    }
    assert weights("resource") == {"ferro": 35, "resina": 35, "erva": 20, "couro": 10}
    assert weights("atmospheric") == {
        "colunas_estranguladas": 34,
        "portas_sem_passagem": 33,
        "raizes_dentro_pedra": 33,
    }
    assert not any(
        creature_for(item.creature_id).category == "elite"
        for item in profile.results
        if item.category == "combat" and item.creature_id is not None
    )


@pytest.mark.asyncio
async def test_p10_opens_claustro_discovers_shared_sanctuary_and_rewards_once(
    database, monkeypatch
):
    import asterion.application.road as road_application
    import asterion.application.scripted_combat as scripted_combat

    actor = 998710
    character_id, sessions = await _seed_late_region(database, actor, level=18)
    async with sessions.begin() as session:
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id="dungeon.vde.fosso_raizes",
            )
        )
    missions = VDEMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))

    p10 = await missions.start(actor, P10_ID)
    assert p10 is not None and p10.status == "active" and p10.kind == "follow"
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "follow")
    assert p10 is not None and p10.kind == "open_claustro" and p10.step == 2
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "passage")
    assert p10 is not None and p10.kind == "inscriptions" and p10.step == 3
    assert p10.location == VDE_CLAUSTRO
    assert await road.resume(actor) is not None
    local = await road.resume(actor)
    assert local is not None and local.explore_enabled and not local.hunt_enabled
    assert await road.prepare_explore(actor) is not None

    p10 = await missions.examine(actor, P10_ID, p10.state_version, "a")
    p10 = await missions.examine(actor, P10_ID, p10.state_version, "b")
    assert p10 is not None and p10.kind == "combat_start" and p10.step == 4
    fight = await missions.start_solo_combat(actor, P10_ID, p10.state_version)
    assert fight is not None and fight.activity_id is not None and fight.combat is not None
    async with sessions() as session:
        activity = await session.get(GameActivity, fight.activity_id)
        assert activity is not None and activity.content_id == P10_CONTENT
        assert VDE_ROOTED_WATCHER.creature_id == "vigia_enraizado"
    p10 = await missions.action_combat(
        actor, fight.activity_id, fight.combat.version, "attack"
    )
    assert p10 is not None and p10.kind == "structure" and p10.step == 5
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "structure")
    assert p10 is not None and p10.kind == "sanctuary" and p10.step == 6
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "sanctuary")
    assert p10 is not None and p10.kind == "report" and p10.step == 7
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VDE_SANCTUARY_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.mystery.o_no_antigo",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id
                == "codex.fragment.no_antigo.entrada_santuario_descoberta",
            )
        ) is not None
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == VDE_ROOTED_WATCHER.creature_id,
            )
        ) is not None

    await road.travel_route(actor, BAIXIOS)
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "report")
    assert p10 is not None and p10.status == "completed"
    await missions.advance(actor, P10_ID, p10.state_version - 1, "report")
    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P10_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )).all()
        )
        assert {(item.kind, item.quantity, item.item_id) for item in components} == {
            ("xp", 14600, None),
            ("crowns", 450, None),
            ("material", 2, "material.vde.ferro_enredado"),
            ("material", 2, "material.vde.resina_enredada"),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P10_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.vde.sob_as_raizes",
            )
        ) is not None

    # P10's canonical entrance unlock suppresses only the equivalent unique
    # Desbravar reward; it cannot pay entrance discovery XP again.
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VDE_CLAUSTRO_EXPLORE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VDE_CLAUSTRO_HUNT_UNLOCK,
            )
        ) is not None

    await road.travel_route(actor, VDE_CLAUSTRO)
    observed = {}

    def no_duplicate_sanctuary(seed, level, recent, excluded, profile):
        observed["excluded"] = excluded
        return (
            "atmospheric",
            "explore.vde.claustro.portas_sem_passagem",
            "Portas antigas não oferecem passagem.",
        )

    monkeypatch.setattr(road_application, "_explore_result", no_duplicate_sanctuary)
    assert await road.prepare_explore(actor) is not None
    result = await road.explore(actor)
    assert result is not None and result.result_id == "explore.vde.claustro.portas_sem_passagem"
    assert "explore.vde.claustro.entrada_santuario_no_antigo" in observed["excluded"]
    await road.acknowledge_result(actor, result.attempt_id)
    assert await road.travel_route(actor, BAIXIOS) is not None

    # The Claustro uses the shared Ronda gate after one local Manual victory.
    await road.travel_route(actor, VDE_CLAUSTRO)
    round_service = RoundService(sessions, "ocaso")
    round_locked = await round_service.prepare_round(actor, 5)
    assert round_locked is not None and round_locked.kind == "vde_claustro"
    assert round_locked.familiar is False
    monkeypatch.setattr(
        road_application,
        "select_creature",
        lambda _seed, _level, profile=None: creature_for("mariposa_breu_verde"),
    )
    original_create_road_combat = road_application.create_road_combat

    def easy_hunt_combat(*args, **kwargs):
        combat = original_create_road_combat(*args, **kwargs)
        enemy = combat.fighters["enemy"]
        enemy.stats = Stats(Decimal(1), Decimal(1), Decimal(0), Decimal(0))
        return combat

    monkeypatch.setattr(road_application, "create_road_combat", easy_hunt_combat)
    queued = await road.start_hunt(actor)
    assert queued is not None and queued.kind == "hunt_queue"
    assert queued.pvpve_queue_id is not None
    combat = await road.pvpve.continue_queue(actor, queued.pvpve_queue_id)
    assert combat is not None and combat.kind == "combat"
    for _ in range(120):
        if combat.kind != "combat":
            break
        combat = await road.action(
            actor,
            combat.activity_id,
            combat.combat.version,
            "attack",
        )
        assert combat is not None
    assert combat.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    round_ready = await round_service.prepare_round(actor, 5)
    assert round_ready is not None and round_ready.kind == "round_prepare"


@pytest.mark.asyncio
async def test_claustro_desbravar_brazier_and_sanctuary_are_idempotent(database, monkeypatch):
    import asterion.application.road as road_application

    actor_brazier, actor_sanctuary = 998716, 998717
    brazier_character, sessions = await _seed_late_region(
        database, actor_brazier, level=18, p10=True
    )
    sanctuary_character, _ = await _seed_late_region(
        database, actor_sanctuary, level=18, p10=False
    )
    async with sessions.begin() as session:
        for character_id in (brazier_character, sanctuary_character):
            world = await session.get(WorldState, character_id)
            assert world is not None
            world.location = VDE_CLAUSTRO
            session.add_all(
                (
                    Unlock(
                        character_id=character_id,
                        unlock_id=VDE_BAIXIOS_CLAUSTRO_ROUTE,
                    ),
                    Unlock(character_id=character_id, unlock_id=VDE_CLAUSTRO_EXPLORE_UNLOCK),
                    LocationDiscovery(
                        character_id=character_id, location_id=CLAUSTRO_LOCATION_ID
                    ),
                )
            )
        session.add(
            Quest(
                character_id=sanctuary_character,
                quest_id=P10_ID,
                title="Pedra sob as Raízes",
                status="active",
                step=6,
                content_version="vales-1.0.4",
                progress={"inscriptions": ["a", "b"]},
            )
        )

    road = RoadService(sessions, "ocaso")
    result_id = "explore.vde.claustro.braseiro_pedras_enlacadas"
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *args, **kwargs: (
            "great_discovery",
            result_id,
            "Braseiro das Pedras Enlaçadas encontrado.",
        ),
    )
    assert await road.prepare_explore(actor_brazier) is not None
    brazier_result = await road.explore(actor_brazier)
    assert brazier_result is not None and brazier_result.result_id == result_id
    await road.acknowledge_result(actor_brazier, brazier_result.attempt_id)
    await road.acknowledge_result(actor_brazier, brazier_result.attempt_id)
    async with sessions() as session:
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == brazier_character,
                Brazier.brazier_id == VDE_CLAUSTRO_BRAZIER,
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == brazier_character,
                LocationDiscovery.location_id == CLAUSTRO_LOCATION_ID,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == brazier_character,
                Unlock.unlock_id == VDE_CLAUSTRO_EXPLORE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == brazier_character,
                RewardEvent.source_id == f"explore:{brazier_result.attempt_id}",
            )
        ) == 1
        assert await session.scalar(
            select(RewardComponent.quantity).join(RewardEvent).where(
                RewardEvent.character_id == brazier_character,
                RewardEvent.source_id == f"explore:{brazier_result.attempt_id}",
                RewardComponent.kind == "xp",
            )
        ) == 2704
        assert await session.scalar(
            select(RewardComponent.kind).join(RewardEvent).where(
                RewardEvent.character_id == brazier_character,
                RewardEvent.source_id == f"explore:{brazier_result.attempt_id}",
                RewardComponent.kind == "brazier",
            )
        ) == "brazier"

    # A Desbravar-first entrance discovery and P10 use one canonical unlock.
    result_id = "explore.vde.claustro.entrada_santuario_no_antigo"
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *args, **kwargs: (
            "great_discovery",
            result_id,
            "A entrada do Santuário do Nó Antigo foi descoberta.",
        ),
    )
    assert await road.prepare_explore(actor_sanctuary) is not None
    sanctuary_result = await road.explore(actor_sanctuary)
    assert sanctuary_result is not None and sanctuary_result.result_id == result_id
    await road.acknowledge_result(actor_sanctuary, sanctuary_result.attempt_id)
    missions = VDEMissionService(sessions, "ocaso")
    p10 = await missions.resume(actor_sanctuary, P10_ID)
    assert p10 is not None and p10.step == 6
    p10 = await missions.advance(actor_sanctuary, P10_ID, p10.state_version, "sanctuary")
    assert p10 is not None and p10.step == 7
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(Unlock.id)).where(
                Unlock.character_id == sanctuary_character,
                Unlock.unlock_id == VDE_SANCTUARY_UNLOCK,
            )
        ) == 1
        assert await session.scalar(
            select(func.count(RewardComponent.id)).join(RewardEvent).where(
                RewardEvent.character_id == sanctuary_character,
                RewardEvent.source_id == f"explore:{sanctuary_result.attempt_id}",
                RewardComponent.kind == "xp",
                RewardComponent.quantity == 2704,
            )
        ) == 1


@pytest.mark.asyncio
async def test_p10_group_member_enters_alone_and_scripted_encounter_is_solo(database):
    leader, helper = 998711, 998712
    leader_id, sessions = await _seed_late_region(database, leader, level=18)
    helper_id, _ = await _seed_late_region(database, helper, level=18)
    async with sessions() as session:
        helper_row = await session.get(Character, helper_id)
        assert helper_row is not None
        helper_name = helper_row.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invite = await groups.invite(leader, helper_name, expected_group_revision=group.revision)
    await groups.respond_invite(
        helper, invite.invite_id, expected_revision=invite.revision, accept=True
    )
    missions = VDEMissionService(sessions, "ocaso", groups)
    for actor in (leader, helper):
        view = await missions.start(actor, P10_ID)
        assert view is not None and view.status == "active" and view.step == 1

    lead = await missions.resume(leader, P10_ID)
    lead = await missions.advance(leader, P10_ID, lead.state_version, "follow")
    assert lead is not None and lead.step == 2
    lead = await missions.advance(leader, P10_ID, lead.state_version, "passage")
    assert lead is not None and lead.step == 3 and lead.location == VDE_CLAUSTRO
    # Objectives are Solo (Ação × Consequência §5): the helper stays on step 1.
    async with sessions() as session:
        helper_quest = await session.scalar(
            select(Quest).where(Quest.character_id == helper_id, Quest.quest_id == P10_ID)
        )
        helper_world = await session.get(WorldState, helper_id)
        assert helper_quest is not None and helper_quest.step == 1
        assert helper_world is not None and helper_world.location != VDE_CLAUSTRO
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == helper_id,
                LocationDiscovery.location_id == CLAUSTRO_LOCATION_ID,
            )
        ) is None
        assert leader_id != helper_id

    lead = await missions.examine(leader, P10_ID, lead.state_version, "a")
    lead = await missions.examine(leader, P10_ID, lead.state_version, "b")
    # P10 is not a Boss: the Group proposal is refused and nothing is reserved.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await missions.propose_group_combat(leader, P10_ID, lead.state_version)
    assert not await groups.activity_proposals(leader)
    assert not await groups.activity_proposals(helper)

    started = await missions.start_solo_combat(leader, P10_ID, lead.state_version)
    assert started is not None and started.kind == "combat"
    assert started.activity_id is not None and started.group_size == 1
    resumed = await missions.resume_active(leader)
    assert resumed is not None and resumed.activity_id == started.activity_id
    helper_active = await missions.resume_active(helper)
    assert helper_active is not None and helper_active.step == 1
    assert helper_active.activity_id is None
    async with sessions() as session:
        assert not await session.scalar(select(CampaignSharedEncounter).limit(1))


@pytest.mark.asyncio
async def test_s10_keeps_neutral_encounter_and_unknown_explorer_status(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998713
    character_id, sessions = await _seed_late_region(database, actor, level=18, p10=True)
    missions = VDEMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))

    s10 = await missions.start(actor, S10_ID)
    assert s10 is not None and s10.status == "active" and s10.kind == "markers"
    for point in ("a", "b", "c"):
        s10 = await missions.examine(actor, S10_ID, s10.state_version, point)
    assert s10 is not None and s10.kind == "zone" and s10.step == 2
    s10 = await missions.advance(actor, S10_ID, s10.state_version, "zone")
    assert s10 is not None and s10.kind == "bag" and s10.step == 3
    async with sessions() as session:
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == VDE_TURF_LEECH.creature_id,
            )
        ) is not None
        known_count = await session.scalar(
            select(func.count(BestiaryEntry.id)).where(
                BestiaryEntry.character_id == character_id
            )
        )

    s10 = await missions.advance(actor, S10_ID, s10.state_version, "bag")
    s10 = await missions.advance(actor, S10_ID, s10.state_version, "tracks")
    assert s10 is not None and s10.kind == "combat_start" and s10.step == 5
    fight = await missions.start_solo_combat(actor, S10_ID, s10.state_version)
    assert fight is not None and fight.activity_id is not None and fight.combat is not None
    s10 = await missions.action_combat(
        actor, fight.activity_id, fight.combat.version, "attack"
    )
    assert s10 is not None and s10.kind == "survivor" and s10.step == 6
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(BestiaryEntry.id)).where(
                BestiaryEntry.character_id == character_id
            )
        ) == known_count
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "scripted_fauna",
            )
        ) is None

    s10 = await missions.advance(actor, S10_ID, s10.state_version, "survivor")
    assert s10 is not None and s10.step == 7 and s10.progress["second_explorer_status"] == "missing"
    # Reach the Vigília through the existing Mata connection, not a new
    # regional shortcut.
    assert await road.travel_route(actor, MATA) is not None
    assert await road.travel_route(actor, VDE_VIGILIA) is not None
    assert await road.resume(actor) is not None
    s10 = await missions.resume(actor, S10_ID)
    assert s10 is not None and s10.location == VDE_VIGILIA
    s10 = await missions.advance(actor, S10_ID, s10.state_version, "report")
    assert s10 is not None and s10.status == "completed"
    await missions.advance(actor, S10_ID, s10.state_version - 1, "report")

    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S10_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )).all()
        )
        assert {(item.kind, item.quantity, item.item_id) for item in components} == {
            ("xp", 10220, None),
            ("crowns", 270, None),
            ("material", 2, "material.vde.ferro_enredado"),
            ("material", 1, "material.vde.couro_musgoso"),
            ("material", 1, "material.vde.resina_enredada"),
        }
        assert all(
            item.payload.get("bound") is True
            for item in components
            if item.kind == "material"
        )
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S10_REWARD_SOURCE,
            )
        ) == 1


@pytest.mark.asyncio
async def test_s10_group_member_plays_alone_and_scripted_combat_is_solo(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    leader, helper = 998714, 998715
    leader_id, sessions = await _seed_late_region(database, leader, level=18, p10=True)
    helper_id, _ = await _seed_late_region(database, helper, level=18, p10=True)
    async with sessions() as session:
        helper_row = await session.get(Character, helper_id)
        assert helper_row is not None
        helper_name = helper_row.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invite = await groups.invite(leader, helper_name, expected_group_revision=group.revision)
    await groups.respond_invite(
        helper, invite.invite_id, expected_revision=invite.revision, accept=True
    )
    missions = VDEMissionService(sessions, "ocaso", groups)
    for actor in (leader, helper):
        view = await missions.start(actor, S10_ID)
        assert view is not None and view.status == "active" and view.step == 1

    lead = await missions.resume(leader, S10_ID)
    for point in ("a", "b", "c"):
        lead = await missions.examine(leader, S10_ID, lead.state_version, point)
    assert lead is not None and lead.kind == "zone" and lead.step == 2
    lead = await missions.advance(leader, S10_ID, lead.state_version, "zone")
    assert lead is not None and lead.kind == "bag" and lead.step == 3
    # Objectives are Solo (Ação × Consequência §5): the helper stays on step 1.
    async with sessions() as session:
        helper_quest = await session.scalar(
            select(Quest).where(Quest.character_id == helper_id, Quest.quest_id == S10_ID)
        )
        assert helper_quest is not None and helper_quest.step == 1
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == leader_id,
                BestiaryEntry.creature_id == VDE_TURF_LEECH.creature_id,
            )
        ) is not None

    lead = await missions.advance(leader, S10_ID, lead.state_version, "bag")
    lead = await missions.advance(leader, S10_ID, lead.state_version, "tracks")
    # S10 is not a Boss: the Group proposal is refused, the fight is Solo.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await missions.propose_group_combat(leader, S10_ID, lead.state_version)
    assert not await groups.activity_proposals(leader)
    assert not await groups.activity_proposals(helper)
    started = await missions.start_solo_combat(leader, S10_ID, lead.state_version)
    assert started is not None and started.kind == "combat" and started.group_size == 1
    resumed = await missions.resume_active(leader)
    assert resumed is not None and resumed.activity_id == started.activity_id

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    result = await missions.action_combat(
        leader, started.activity_id, started.combat.version, "attack"
    )
    assert result is not None and result.kind == "survivor"
    async with sessions() as session:
        for character_id, expected_step in ((leader_id, 6), (helper_id, 1)):
            quest = await session.scalar(
                select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S10_ID)
            )
            assert quest is not None and quest.step == expected_step

    result = await missions.advance(leader, S10_ID, result.state_version, "survivor")
    assert result is not None and result.step == 7
    async with sessions() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == leader_id, Quest.quest_id == S10_ID)
        )
        assert quest is not None and quest.step == 7
        assert quest.progress["second_explorer_status"] == "missing"
        helper_quest = await session.scalar(
            select(Quest).where(Quest.character_id == helper_id, Quest.quest_id == S10_ID)
        )
        assert helper_quest is not None and helper_quest.step == 1
        assert "second_explorer_status" not in (helper_quest.progress or {})
