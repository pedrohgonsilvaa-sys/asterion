from copy import deepcopy

import pytest
from sqlalchemy import func, select

from asterion.application.nareth_missions import (
    CAMARA,
    CAMARA_LOCATION_ID,
    CAMPOS,
    CANAIS,
    CHAMBER_ROUTE_UNLOCK,
    CHAMBER_UNLOCK,
    OBSERVATORIO,
    OBSERVATORIO_LOCATION_ID,
    P13_ID,
    P14_ID,
    P15_ID,
    P16_ID,
    P17_ID,
    P17_REWARD_SOURCE,
    P18_ID,
    P18_REWARD_SOURCE,
    REGION_UNLOCK,
    S16_ID,
    S17_ID,
    S17_REWARD_SOURCE,
    S18_ID,
    S18_REWARD_SOURCE,
    NarethMissionService,
)
from asterion.application.road import (
    NARETH_CAMARA_LABEL,
    NARETH_CAMPOS_OBSERVATORIO_ROUTE,
    NARETH_CANAIS_CAMPOS_ROUTE,
    NARETH_POSTO_CANAIS_ROUTE,
    NARETH_POSTO_LABEL,
    NARETH_REGION,
    RoadService,
)
from asterion.infrastructure.db.models import (
    BestiaryEntry,
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
from tests.test_s6_p6_integration import _seed_final_campaign


def _terminal_victory(combat, _action, **_kwargs):
    updated = deepcopy(combat)
    updated.version += 1
    updated.result = "victory"
    return updated


async def _seed_nareth_final_stage(database, actor: int, *, include_s16: bool = False):
    """Start from a valid P16-complete return point to isolate final-stage services."""
    character_id, sessions = await _seed_final_campaign(database, actor, level=30)
    titles = {
        "P12": "A Matriarca das Raízes",
        P13_ID: "Linhas no Horizonte",
        P14_ID: "O Canal sem Norte",
        P15_ID: "A Distância Errada",
        P16_ID: "O Eixo sob a Terra",
    }
    if include_s16:
        titles[S16_ID] = "Cartografia do Erro"
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = 30
        world.region = NARETH_REGION
        world.location = NARETH_POSTO_LABEL
        session.add_all(
            Quest(
                character_id=character_id,
                quest_id=quest_id,
                title=title,
                status="completed",
                step=1,
                content_version="nareth-1.0.1",
                state_version=0,
                progress={"completed": True},
            )
            for quest_id, title in titles.items()
        )
        session.add_all(
            Unlock(character_id=character_id, unlock_id=unlock_id)
            for unlock_id in (
                REGION_UNLOCK,
                "route.nareth.campinas_posto",
                NARETH_POSTO_CANAIS_ROUTE,
                NARETH_CANAIS_CAMPOS_ROUTE,
                NARETH_CAMPOS_OBSERVATORIO_ROUTE,
            )
        )
        session.add(
            LocationDiscovery(
                character_id=character_id,
                location_id=OBSERVATORIO_LOCATION_ID,
            )
        )
    return character_id, sessions


async def _travel_to_observatory(road, missions, actor):
    for destination in (CANAIS, CAMPOS, OBSERVATORIO):
        arrived = await road.travel_route(actor, destination)
        assert arrived is not None and arrived.location == destination
        await missions.on_location(actor)


async def _travel_to_posto(road, missions, actor):
    for destination in (CAMPOS, CANAIS, NARETH_POSTO_LABEL):
        arrived = await road.travel_route(actor, destination)
        assert arrived is not None and arrived.location == destination
        await missions.on_location(actor)


@pytest.mark.asyncio
async def test_s17_and_p17_to_p18_auto_start_settle_once_and_open_only_the_regional_exit(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor = 994170
    character_id, sessions = await _seed_nareth_final_stage(database, actor)
    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso")

    async with sessions.begin() as session:
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id="dungeon.nareth.observatorio_afundado",
            )
        )
    s17 = await missions.resume(actor, S17_ID)
    assert s17 is not None and s17.available
    s17 = await missions.start(actor, S17_ID)
    assert s17 is not None and s17.status == "active" and s17.step == 1
    s17 = await missions.advance(actor, S17_ID, s17.state_version, "speak_talen")
    assert s17 is not None and s17.step == 2
    await _travel_to_observatory(road, missions, actor)
    s17 = await missions.resume(actor, S17_ID)
    assert s17 is not None and s17.step == 3
    for ordinal in range(3):
        s17 = await missions.advance(
            actor, S17_ID, s17.state_version, "examine_references"
        )
        assert s17 is not None
        assert s17.progress["geometric_references_examined"] == ordinal + 1
    assert s17.step == 4
    s17 = await missions.advance(actor, S17_ID, s17.state_version, "locate_submerged_entry")
    assert s17 is not None and s17.step == 5
    s17 = await missions.advance(actor, S17_ID, s17.state_version, "recover_calibration_piece")
    assert s17 is not None and s17.step == 6
    await _travel_to_posto(road, missions, actor)
    s17 = await missions.resume(actor, S17_ID)
    assert s17 is not None and s17.step == 7
    s17 = await missions.advance(actor, S17_ID, s17.state_version, "update_protocols")
    assert s17 is not None and s17.status == "completed"

    p17 = await missions.resume(actor, P17_ID)
    assert p17 is not None and p17.available
    p17 = await missions.start(actor, P17_ID)
    assert p17 is not None and p17.status == "active" and p17.step == 1
    for action in (
        "gather_researchers",
        "compare_records",
        "record_custody",
        "confirm_stability_monitoring",
    ):
        p17 = await missions.advance(actor, P17_ID, p17.state_version, action)
    assert p17 is not None and p17.step == 5
    await _travel_to_observatory(road, missions, actor)
    p17 = await missions.resume(actor, P17_ID)
    assert p17 is not None and p17.step == 6
    scripted = await missions.start_solo_combat(actor, P17_ID, p17.state_version)
    assert scripted is not None and scripted.combat is not None
    assert scripted.combat.variant is None
    assert scripted.combat.fighters["enemy"].name == "Custódio Invertido"
    monkeypatch.setattr(scripted_combat, "act", _terminal_victory)
    p17 = await missions.action_combat(
        actor, scripted.activity_id, scripted.combat.version, "attack"
    )
    assert p17 is not None and p17.step == 7 and p17.progress["combat_victory"]
    p17 = await missions.advance(actor, P17_ID, p17.state_version, "open_chamber")
    assert p17 is not None and p17.step == 8
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == CHAMBER_ROUTE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == CAMARA_LOCATION_ID,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == CHAMBER_UNLOCK,
            )
        ) is not None
    arrived = await road.travel_route(actor, NARETH_CAMARA_LABEL)
    assert arrived is not None and arrived.location == CAMARA
    await missions.on_location(actor)
    p17 = await missions.resume(actor, P17_ID)
    assert p17 is not None and p17.step == 8
    assert p17.kind == "examine_incomplete_record"
    p17 = await missions.advance(actor, P17_ID, p17.state_version, "examine_incomplete_record")
    assert p17 is not None and p17.step == 9
    await road.travel_route(actor, OBSERVATORIO)
    await missions.on_location(actor)
    p17 = await missions.resume(actor, P17_ID)
    assert p17 is not None and p17.step == 10
    p17 = await missions.advance(actor, P17_ID, p17.state_version, "prepare_arconte")
    assert p17 is not None and p17.status == "completed"
    stale_p17 = await missions.advance(
        actor, P17_ID, p17.state_version - 1, "prepare_arconte"
    )
    assert stale_p17 is not None and stale_p17.status == "completed"
    p18 = await missions.resume(actor, P18_ID)
    assert p18 is not None and p18.status == "active" and p18.step == 1
    assert p18.progress["automatic_start"] is True

    arrived = await road.travel_route(actor, NARETH_CAMARA_LABEL)
    assert arrived is not None
    await missions.on_location(actor)
    p18 = await missions.resume(actor, P18_ID)
    assert p18 is not None and p18.step == 2
    for action in ("examine_reference_lines", "identify_archon"):
        p18 = await missions.advance(actor, P18_ID, p18.state_version, action)
    assert p18 is not None and p18.step == 4
    boss = await missions.start_solo_combat(actor, P18_ID, p18.state_version)
    assert boss is not None and boss.combat is not None and boss.activity_id is not None
    assert boss.combat.variant is None
    assert boss.combat.fighters["enemy"].name == "Arconte Invertido"
    p18 = await missions.action_combat(
        actor, boss.activity_id, boss.combat.version, "attack"
    )
    assert p18 is not None and p18.step == 6
    p18 = await missions.advance(
        actor, P18_ID, p18.state_version, "examine_chamber_after_victory"
    )
    assert p18 is not None and p18.step == 7
    for action in (
        "record_anchor_function",
        "record_measurement_function",
        "record_logistics_direction",
    ):
        p18 = await missions.advance(actor, P18_ID, p18.state_version, action)
    assert p18 is not None and p18.kind == "choice" and p18.step == 10
    p18 = await missions.choose_midgame_reward(actor, p18.state_version, "2", P18_ID)
    assert p18 is not None and p18.status == "completed"
    duplicate_choice = await missions.choose_midgame_reward(
        actor, p18.state_version - 1, "1", P18_ID
    )
    assert duplicate_choice is not None and duplicate_choice.status == "completed"

    async with sessions() as session:
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S17_REWARD_SOURCE,
            )
        ) == 1
        p17_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P17_REWARD_SOURCE,
            )
        )
        p18_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P18_REWARD_SOURCE,
            )
        )
        core_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == "p18.arconte.first_victory.core",
            )
        )
        assert p17_event is not None and p18_event is not None and core_event is not None
        p17_components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == p17_event.id
                )
            )
        ).all()
        assert {(row.kind, row.item_id, row.quantity) for row in p17_components} == {
            ("xp", None, 30950),
            ("crowns", None, 680),
            ("material", "material.nareth.bronze_de_marco", 3),
            ("material", "material.nareth.po_de_eixo", 1),
        }
        p18_components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == p18_event.id
                )
            )
        ).all()
        assert {(row.kind, row.item_id, row.quantity) for row in p18_components} == {
            ("xp", None, 58680),
            ("crowns", None, 1100),
            ("equipment", None, 1),
            ("material", "material.nareth.bronze_de_marco", 4),
            ("material", "material.nareth.po_de_eixo", 4),
        }
        core_components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == core_event.id
                )
            )
        ).all()
        assert [
            (row.kind, row.item_id, row.quantity) for row in core_components
        ] == [("material", "material.nareth.nucleo_arconte_invertido", 1)]
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{boss.activity_id}",
            )
        ) == 0
        choice = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key == f"{P18_REWARD_SOURCE}:equipment:2",
            )
        )
        assert choice is not None and choice.item_name == "Selo do Eixo Estável"
        assert choice.rarity == "Épico" and choice.item_level == 30 and choice.bound
        assert choice.payload["enhancement"] == 0
        assert await session.scalar(
            select(func.count(EquipmentItem.id)).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key.like(f"{P18_REWARD_SOURCE}:equipment:%"),
            )
        ) == 1
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "arconte_invertido",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id
                == "codex.fragment.nareth.chamber.continuity_crimson_direction",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "region.varzeas_carmesins.available",
            )
        ) is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == "P19",
            )
        ) is None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "varzeas.location.borda_dos_canais",
            )
        ) is None


@pytest.mark.asyncio
async def test_s18_is_optional_after_p17_and_settles_only_its_mission_reward(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor = 994180
    character_id, sessions = await _seed_nareth_final_stage(
        database, actor, include_s16=True
    )
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P17_ID,
                title="Medir o que Permanece",
                status="completed",
                step=11,
                content_version="nareth-1.0.1",
                progress={"completed": True},
            )
        )
    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso")
    s18 = await missions.resume(actor, S18_ID)
    assert s18 is not None and s18.available
    s18 = await missions.start(actor, S18_ID)
    assert s18 is not None and s18.status == "active" and s18.step == 1
    s18 = await missions.advance(actor, S18_ID, s18.state_version, "read_cartography")
    assert s18 is not None and s18.step == 2
    arrived = await road.travel_route(actor, "Campinas do Meridiano")
    assert arrived is not None
    await missions.on_location(actor)
    s18 = await missions.resume(actor, S18_ID)
    assert s18 is not None and s18.step == 3
    s18 = await missions.advance(actor, S18_ID, s18.state_version, "compare_old_markers")
    assert s18 is not None and s18.step == 4
    arrived = await road.travel_route(actor, NARETH_POSTO_LABEL)
    assert arrived is not None
    arrived = await road.travel_route(actor, CANAIS)
    assert arrived is not None
    await missions.on_location(actor)
    s18 = await missions.resume(actor, S18_ID)
    assert s18 is not None and s18.step == 5
    s18 = await missions.advance(actor, S18_ID, s18.state_version, "recover_route_plate")
    assert s18 is not None and s18.step == 6
    arrived = await road.travel_route(actor, CAMPOS)
    assert arrived is not None
    await missions.on_location(actor)
    s18 = await missions.resume(actor, S18_ID)
    assert s18 is not None and s18.step == 7
    s18 = await missions.advance(actor, S18_ID, s18.state_version, "compare_travel_distances")
    assert s18 is not None and s18.step == 8
    arrived = await road.travel_route(actor, OBSERVATORIO)
    assert arrived is not None
    await missions.on_location(actor)
    s18 = await missions.resume(actor, S18_ID)
    assert s18 is not None and s18.step == 9
    s18 = await missions.advance(actor, S18_ID, s18.state_version, "follow_service_route")
    assert s18 is not None and s18.step == 10
    combat = await missions.start_solo_combat(actor, S18_ID, s18.state_version)
    assert combat is not None and combat.combat is not None and combat.activity_id is not None
    assert combat.combat.variant is None
    assert combat.combat.fighters["enemy"].name == "Custódio sem Norte"
    monkeypatch.setattr(scripted_combat, "act", _terminal_victory)
    s18 = await missions.action_combat(
        actor, combat.activity_id, combat.combat.version, "attack"
    )
    assert s18 is not None and s18.step == 11
    s18 = await missions.advance(actor, S18_ID, s18.state_version, "inspect_broken_reference")
    assert s18 is not None and s18.step == 12
    await _travel_to_posto(road, missions, actor)
    s18 = await missions.resume(actor, S18_ID)
    assert s18 is not None and s18.step == 13
    s18 = await missions.advance(actor, S18_ID, s18.state_version, "trace_modern_route")
    assert s18 is not None and s18.step == 14
    s18 = await missions.advance(actor, S18_ID, s18.state_version, "update_codex")
    assert s18 is not None and s18.status == "completed"
    await missions.advance(actor, S18_ID, s18.state_version - 1, "update_codex")

    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S18_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )
        ).all()
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 32600),
            ("crowns", None, 690),
            ("material", "material.nareth.bronze_de_marco", 2),
            ("material", "material.nareth.couro_de_horizonte", 2),
            ("material", "material.nareth.erva_de_vento", 2),
            ("material", "material.nareth.po_de_eixo", 2),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S18_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        ) == 0
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.route.os_caminhos_que_nao_coincidem",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id
                == "codex.fragment.nareth.routes.s18_verified_points",
            )
        ) is not None
