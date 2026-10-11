from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.character_surfaces import (
    BestiaryRecordView,
    CodexEntryView,
    KnowledgeView,
)
from asterion.application.groups import GroupService
from asterion.application.p7 import REGION as VDE_REGION
from asterion.application.p7 import VIGILIA as VDE_VIGILIA
from asterion.application.road import RoadService
from asterion.application.round import RoundService
from asterion.application.vde_missions import (
    BAIXIOS,
    BAIXIOS_EXPLORE_UNLOCK,
    BAIXIOS_ROUTE_UNLOCK,
    MATA,
    MATA_ROUTE_UNLOCK,
    P8_ID,
    P9_ID,
    P9_REWARD_SOURCE,
    S8_ID,
    S8_REWARD_SOURCE,
    S9_ID,
    S9_REWARD_SOURCE,
    VDEMissionService,
)
from asterion.bot.character_surfaces_ui import render_bestiary_root, render_codex_category
from asterion.domain.road import (
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    VDE_BAIXIOS_LOCATION,
    VDE_BAIXIOS_PROFILE,
    VDE_BAIXIOS_ROUND_FAMILIARITY,
    VDE_CREATURES,
    VDE_TURF_LEECH,
    creature_for,
)
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Brazier,
    Character,
    CodexEntry,
    CodexFragment,
    EquipmentItem,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_p7_integration import _terminal
from tests.test_vde_s7_p8_integration import _seed_vde_ready


async def _seed_mid_region(database, actor: int, *, level: int = 15):
    character_id, sessions = await _seed_vde_ready(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = VDE_REGION
        world.location = MATA
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P8_ID,
                title="Entre Galhos Suspensos",
                status="completed",
                step=7,
                content_version="vales-1.0.3",
                progress={"completed": True, "returned_vigilia": True},
            )
        )
        session.add_all(
            (
                Unlock(character_id=character_id, unlock_id=MATA_ROUTE_UNLOCK),
                Brazier(character_id=character_id, brazier_id="vde.brazier.mata_suspensa"),
                LocationDiscovery(
                    character_id=character_id,
                    location_id="vde.location.mata_suspensa",
                ),
            )
        )
    return character_id, sessions


def test_baixios_hunt_and_exploration_profiles_match_v104():
    hunt = HUNT_PROFILES[VDE_BAIXIOS_LOCATION]
    assert hunt is VDE_BAIXIOS_PROFILE
    assert hunt.creature_weights == (
        ("aranha_cipo", 22),
        ("cervo_no", 20),
        ("sanguessuga_turfa", 22),
        ("casca_errante", 18),
        ("mariposa_breu_verde", 15),
        ("viuva_cipos", 1),
        ("carrasco_casca", 2),
    )
    assert hunt.variant_chance == 15
    assert hunt.round_familiarity == VDE_BAIXIOS_ROUND_FAMILIARITY
    assert all(creature_id in MATERIAL_POOLS for creature_id, _ in hunt.creature_weights)

    exploration = EXPLORATION_PROFILES[VDE_BAIXIOS_LOCATION]

    def weights(category):
        return {
            item.key: item.weight for item in exploration.results if item.category == category
        }

    assert weights("great_discovery") == {"brazier_turfa": 50, "galeria_afogada": 50}
    assert weights("knowledge") == {"marcas_agua": 60, "rastros_turfa": 40}
    assert weights("narrative") == {"agua_sem_reflexo": 55, "raizes_lama": 45}
    assert weights("combat") == {
        "aranha_cipo": 22,
        "cervo_no": 20,
        "sanguessuga_turfa": 23,
        "casca_errante": 18,
        "mariposa_breu_verde": 17,
    }
    assert weights("resource") == {"erva": 35, "resina": 30, "couro": 25, "ferro": 10}
    assert weights("atmospheric") == {"agua_negra": 34, "troncos_submersos": 33, "luz_turfa": 33}
    assert not any(
        creature_for(item.creature_id).category == "elite"
        for item in exploration.results
        if item.category == "combat" and item.creature_id is not None
    )
    assert {
        item.result_id: item.unique
        for item in exploration.results
        if item.category == "great_discovery"
    } == {
        "explore.vde.baixios.braseiro_turfa_fria": True,
        "explore.vde.baixios.galeria_afogada": True,
    }

    by_id = {creature.creature_id: creature for creature in VDE_CREATURES}
    assert set(by_id) >= {
        "sanguessuga_turfa",
        "casca_errante",
        "mariposa_breu_verde",
        "viuva_cipos",
        "carrasco_casca",
    }
    assert VDE_TURF_LEECH.actions[1][28] == Decimal("0.30")
    assert VDE_TURF_LEECH.actions[2][29] == Decimal("0.55")
    assert by_id["casca_errante"].category == "uncommon"
    assert by_id["carrasco_casca"].category == "elite"


def test_codex_and_bestiary_navigation_includes_only_acquired_vales_data():
    locked = KnowledgeView("sentinela", (), (), (), frozenset())
    assert "Vales dos Enforcados" not in render_codex_category(locked, "regions").text
    assert "Vales dos Enforcados" not in render_bestiary_root(locked).text

    codex = KnowledgeView(
        "sentinela",
        (
            CodexEntryView(
                "codex.location.baixios_enredados",
                "Baixios Enredados",
                "regions",
                110,
                "vde.location.baixios_enredados",
                (),
            ),
        ),
        (
            BestiaryRecordView(
                "casca_errante",
                "Casca Errante",
                "observed",
                "Observado",
                (),
                (),
                (),
                (),
            ),
        ),
        (),
        frozenset({"vde.location.baixios_enredados"}),
    )
    screen = render_codex_category(codex, "regions")
    callbacks = [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]
    assert "kb:r:vde" in callbacks
    assert "Baixios Enredados" not in render_codex_category(locked, "regions").text
    bestiary = render_bestiary_root(codex)
    assert "1 Criaturas Conhecidas" in bestiary.text
    assert "kb:br:vde" in [
        button.callback_data
        for row in bestiary.keyboard.inline_keyboard
        for button in row
    ]


@pytest.mark.asyncio
async def test_s8_p9_and_s9_solo_missions_settle_exact_rewards_once(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 999781
    character_id, sessions = await _seed_mid_region(database, actor, level=15)
    missions = VDEMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))

    s8 = await missions.start(actor, S8_ID)
    assert s8 is not None and s8.status == "active" and s8.step == 1
    s8 = await missions.advance(actor, S8_ID, s8.state_version, "passage")
    for point in ("a", "b", "c"):
        s8 = await missions.examine(actor, S8_ID, s8.state_version, point)
    assert s8 is not None and s8.step == 3
    fight = await missions.start_solo_combat(actor, S8_ID, s8.state_version)
    assert fight is not None and fight.activity_id is not None and fight.combat is not None
    s8 = await missions.action_combat(
        actor, fight.activity_id, fight.combat.version, "attack"
    )
    assert s8 is not None and s8.kind == "hardware" and s8.step == 4
    s8 = await missions.advance(actor, S8_ID, s8.state_version, "hardware")
    s8 = await missions.advance(actor, S8_ID, s8.state_version, "hardware")
    assert s8 is not None and s8.kind == "alternate_route" and s8.step == 5
    s8 = await missions.advance(actor, S8_ID, s8.state_version, "route")
    assert s8 is not None and s8.kind == "report" and s8.step == 6
    await road.travel_route(actor, VDE_VIGILIA)
    s8 = await missions.advance(actor, S8_ID, s8.state_version, "report")
    assert s8 is not None and s8.status == "completed"
    await missions.advance(actor, S8_ID, s8.state_version, "report")

    # P9 is available only after P8 and starts in the Mata; travel and entry
    # are still performed through the public road and mission services.
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = MATA
    p9 = await missions.start(actor, P9_ID)
    assert p9 is not None and p9.kind == "follow" and p9.step == 1
    p9 = await missions.advance(actor, P9_ID, p9.state_version, "follow")
    assert p9 is not None and p9.kind == "enter_baixios" and p9.step == 2
    assert await road.travel_route(actor, BAIXIOS) is not None
    p9 = await missions.enter_baixios(actor, p9.state_version)
    assert p9 is not None and p9.step == 3 and p9.location == BAIXIOS
    for point in ("a", "b", "c"):
        p9 = await missions.examine(actor, P9_ID, p9.state_version, point)
    assert p9 is not None and p9.step == 4
    fight = await missions.start_solo_combat(actor, P9_ID, p9.state_version)
    assert fight is not None and fight.activity_id is not None and fight.combat is not None
    p9 = await missions.action_combat(
        actor, fight.activity_id, fight.combat.version, "attack"
    )
    assert p9 is not None and p9.kind == "inscription" and p9.step == 5
    p9 = await missions.advance(actor, P9_ID, p9.state_version, "inscription")
    p9 = await missions.advance(actor, P9_ID, p9.state_version, "fragment")
    assert p9 is not None and p9.kind == "report" and p9.step == 7
    p9 = await missions.advance(actor, P9_ID, p9.state_version, "report")
    assert p9 is not None and p9.kind == "choice" and p9.status == "active"
    async with sessions() as session:
        for entry_id in (
            "codex.location.baixios_enredados",
            "codex.figure.iven_raal",
            "codex.mystery.o_no_antigo",
        ):
            assert await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character_id,
                    CodexEntry.entry_id == entry_id,
                )
            ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "vde.location.baixios_enredados",
            )
        ) is not None
    p9 = await missions.choose_p9_reward(actor, p9.state_version, "2")
    assert p9 is not None and p9.status == "completed"
    await missions.choose_p9_reward(actor, p9.state_version - 1, "1")
    baixios_view = await road.resume(actor)
    assert baixios_view is not None and baixios_view.hunt_enabled
    assert await road.prepare_hunt(actor) is not None

    s9 = await missions.start(actor, S9_ID)
    assert s9 is not None and s9.status == "active" and s9.kind == "locate"
    s9 = await missions.advance(actor, S9_ID, s9.state_version, "locate")
    fight = await missions.start_solo_combat(actor, S9_ID, s9.state_version)
    assert fight is not None and fight.activity_id is not None and fight.combat is not None
    s9 = await missions.action_combat(
        actor, fight.activity_id, fight.combat.version, "attack"
    )
    assert s9 is not None and s9.kind == "fragments"
    s9 = await missions.advance(actor, S9_ID, s9.state_version, "fragments")
    s9 = await missions.advance(actor, S9_ID, s9.state_version, "sample")
    assert s9 is not None and s9.kind == "report"
    s9 = await missions.advance(actor, S9_ID, s9.state_version, "report")
    assert s9 is not None and s9.status == "completed"
    await missions.advance(actor, S9_ID, s9.state_version - 1, "report")

    async with sessions() as session:
        for source, expected in (
            (S8_REWARD_SOURCE, {("xp", 8015), ("crowns", 230), ("material", 1)}),
            (P9_REWARD_SOURCE, {("xp", 12450), ("crowns", 330), ("equipment", 1)}),
            (S9_REWARD_SOURCE, {("xp", 4980), ("crowns", 170), ("material", 2)}),
        ):
            event = await session.scalar(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == source,
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
            assert {(item.kind, item.quantity) for item in components} == expected
            assert await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == source,
                )
            ) == 1
        p9_equipment = await session.scalar(
            select(RewardComponent).join(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P9_REWARD_SOURCE,
                RewardComponent.kind == "equipment",
            )
        )
        assert p9_equipment is not None
        assert p9_equipment.payload["choice"] == "2"
        assert p9_equipment.payload["rarity"] == "Raro"
        assert p9_equipment.payload["item_level"] == 15
        item = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key.endswith(":equipment:2"),
            )
        )
        assert item is not None and item.bound and item.item_name == "Selo do Caminho Enredado"
        assert (
            await session.scalar(
                select(BestiaryEntry.id).where(
                    BestiaryEntry.character_id == character_id,
                    BestiaryEntry.creature_id == "casca_errante",
                )
            )
            is not None
        )
        assert (
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.fragment_id == "codex.fragment.mata.casca_camadas_externas",
                )
            )
            is not None
        )


@pytest.mark.asyncio
async def test_p9_cooperative_objectives_match_v104_quest_version(database):
    leader, helper = 999782, 999783
    leader_id, sessions = await _seed_mid_region(database, leader, level=15)
    helper_id, _ = await _seed_mid_region(database, helper, level=15)
    async with sessions() as session:
        helper_character = await session.get(Character, helper_id)
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invite = await groups.invite(leader, helper_name, expected_group_revision=group.revision)
    await groups.respond_invite(
        helper, invite.invite_id, expected_revision=invite.revision, accept=True
    )
    missions = VDEMissionService(sessions, "ocaso", groups)
    road = RoadService(sessions, "ocaso")
    for actor in (leader, helper):
        view = await missions.start(actor, P9_ID)
        assert view is not None and view.status == "active" and view.step == 1

    lead = await missions.resume(leader, P9_ID)
    lead = await missions.advance(leader, P9_ID, lead.state_version, "follow")
    assert lead is not None and lead.step == 2
    for actor in (leader, helper):
        await road.travel_route(actor, BAIXIOS)
    lead = await missions.enter_baixios(leader, lead.state_version)
    assert lead is not None and lead.step == 3
    async with sessions() as session:
        helper_quest = await session.scalar(
            select(Quest).where(Quest.character_id == helper_id, Quest.quest_id == P9_ID)
        )
        assert helper_quest is not None
        assert helper_quest.step == 3
        assert helper_quest.content_version == "vales-1.0.4"
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == helper_id,
                LocationDiscovery.location_id == "vde.location.baixios_enredados",
            )
        ) is not None
        assert leader_id != helper_id


@pytest.mark.asyncio
async def test_baixios_desbravar_registers_turfa_brazier_and_preserves_round_gate(
    database, monkeypatch
):
    import asterion.application.road as road_application

    actor = 999784
    character_id, sessions = await _seed_mid_region(database, actor, level=15)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = MATA
        session.add_all(
            (
                Quest(
                    character_id=character_id,
                    quest_id=P9_ID,
                    title="Sob a Madeira Morta",
                    status="completed",
                    step=8,
                    content_version="vales-1.0.4",
                    progress={"follow": True, "completed": True},
                ),
                Unlock(character_id=character_id, unlock_id=BAIXIOS_ROUTE_UNLOCK),
                Unlock(character_id=character_id, unlock_id=BAIXIOS_EXPLORE_UNLOCK),
                Unlock(
                    character_id=character_id,
                    unlock_id=VDE_BAIXIOS_PROFILE.hunt_unlock,
                ),
            )
        )

    road = RoadService(sessions, "ocaso")
    assert await road.travel_route(actor, BAIXIOS) is not None
    before = await road.resume(actor)
    assert before is not None and before.location == BAIXIOS
    assert before.explore_enabled is True
    assert before.hunt_enabled is True
    assert await road.prepare_explore(actor) is not None
    assert await road.prepare_hunt(actor) is not None
    round_view = await RoundService(sessions, "ocaso").prepare_round(actor, 5)
    assert round_view is not None and round_view.familiar is False

    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *args, **kwargs: (
            "great_discovery",
            "explore.vde.baixios.braseiro_turfa_fria",
            "Braseiro da Turfa Fria encontrado.",
        ),
    )
    result = await road.explore(actor)
    assert result is not None and result.result_id == "explore.vde.baixios.braseiro_turfa_fria"
    async with sessions() as session:
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == "vde.brazier.turfa_fria",
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "vde.location.baixios_enredados",
            )
        ) is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent)
                    .join(RewardEvent)
                    .where(
                        RewardEvent.character_id == character_id,
                        RewardEvent.source_id == f"explore:{result.attempt_id}",
                    )
                )
            ).all()
        )
        assert {(item.kind, item.quantity) for item in components} == {
            ("xp", 2336),
            ("brazier", 1),
        }
        assert not any(item.kind == "material" for item in components)

    await road.acknowledge_result(actor, result.attempt_id)
    await road.travel_route(actor, MATA)
    assert await road.travel_brazier(actor, "vde.brazier.turfa_fria") is not None
