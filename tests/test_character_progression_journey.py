from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import ActiveArtService
from asterion.application.path_selection import PathSelectionService
from asterion.application.road import REFUGE, ROAD, RoadService
from asterion.application.talents import TalentService
from asterion.domain.arts import SENTINEL_ART_IDS
from asterion.domain.combat import act, allowed_actions
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.talents import TALENTS_BY_CLASS
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    Character,
    Quest,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import start_manual_hunt_after_no_match
from tests.helpers.weapon_metadata import add_compatible_weapon_for_arts


@pytest.mark.asyncio
async def test_level_ten_progression_freezes_path_talents_and_active_arts_in_hunt(
    database, monkeypatch
):
    actor = 772399
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats("sentinela", 10, "remanescente")
    talents = TALENTS_BY_CLASS["sentinela"]
    selected_talents = tuple(
        talent.talent_id
        for talent in talents
        if talent.name in {"Aço Desperto", "Carne de Pedra"}
    )
    active_art_ids = (
        SENTINEL_ART_IDS["golpe_de_guarda"],
        SENTINEL_ART_IDS["quebra_postura"],
        SENTINEL_ART_IDS["muralha_breve"],
    )

    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Progression",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=10,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=100,
                max_vigor=100,
                crowns=500,
            )
        )
        await add_compatible_weapon_for_arts(session, character_id, active_art_ids)
        await session.flush()
        session.add_all(
            [
                Quest(
                    character_id=character_id,
                    quest_id="P1",
                    title="Vozes na Estrada",
                    status="completed",
                    step=7,
                    content_version="tdo-1.0.2",
                ),
                WorldState(
                    character_id=character_id,
                    region="Terras do Ocaso",
                    location=REFUGE,
                ),
                Brazier(character_id=character_id, brazier_id="tdo.brazier.estrada"),
                Brazier(
                    character_id=character_id,
                    brazier_id="tdo.brazier.refugio_do_ocaso",
                ),
                Unlock(character_id=character_id, unlock_id="class_trial_completed"),
                Unlock(
                    character_id=character_id,
                    unlock_id="hunt_manual.estrada_das_cinzas",
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id="explore.estrada_das_cinzas",
                ),
                BestiaryEntry(
                    character_id=character_id,
                    creature_id="dog_cinereo",
                    bkp=7,
                    stage="observed",
                ),
                BestiaryEntry(
                    character_id=character_id,
                    creature_id="corvo_fuligem",
                    bkp=7,
                    stage="observed",
                ),
                BestiaryEvidence(
                    character_id=character_id,
                    creature_id="dog_cinereo",
                    evidence_id="first_observation",
                    category="observation",
                ),
                BestiaryEvidence(
                    character_id=character_id,
                    creature_id="dog_cinereo",
                    evidence_id="first_combat",
                    category="combat",
                ),
                BestiaryEvidence(
                    character_id=character_id,
                    creature_id="corvo_fuligem",
                    evidence_id="first_observation",
                    category="observation",
                ),
            ]
        )

    talent_service = TalentService(sessions, "ocaso")
    first = await talent_service.acquire(actor, selected_talents[0], 0)
    second = await talent_service.acquire(actor, selected_talents[1], 1)
    assert first is not None and first.point_slot == 1
    assert second is not None and second.point_slot == 2

    path_service = PathSelectionService(sessions, "ocaso")
    selected_path = await path_service.choose_initial(
        actor, "bastiao", second.combat_configuration_version
    )
    assert selected_path is not None and selected_path.changed

    art_service = ActiveArtService(sessions, "ocaso")
    version = selected_path.view.configuration_version
    for slot, art_id in enumerate(active_art_ids, start=1):
        result = await art_service.equip_art(
            actor, slot, art_id, expected_configuration_version=version
        )
        assert result is not None and result.changed
        version = result.combat_configuration_version

    road = RoadService(sessions, "ocaso")
    traveled = await road.travel(actor, ROAD)
    assert traveled is not None and traveled.location == ROAD
    combat_view = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert combat_view is not None and combat_view.kind == "combat"
    combat = combat_view.combat

    expected_arts = {"attack", *active_art_ids}
    assert set(combat.player_actions) == expected_arts
    assert "art" not in allowed_actions(combat)
    assert "class_art.sentinela.impacto_resoluto" not in allowed_actions(combat)
    rejected = act(combat, "class_art.sentinela.impacto_resoluto")
    assert rejected is combat

    snapshot = combat.configuration_snapshot
    assert snapshot["combat_configuration_version"] == version
    assert snapshot["selected_path"] == "bastiao"
    assert snapshot["talents"] == [
        {"point_slot": slot, "talent_id": talent_id}
        for slot, talent_id in enumerate(selected_talents, start=1)
    ]
    assert snapshot["active_arts"] == [
        {"slot": slot, "art_id": art_id}
        for slot, art_id in enumerate(active_art_ids, start=1)
    ]
    assert combat.fighters["player"].selected_path == "bastiao"
    assert combat.fighters["player"].talent_ids == selected_talents

    resumed = await road.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.combat.configuration_snapshot == snapshot
    assert set(resumed.combat.player_actions) == expected_arts
    assert resumed.combat.fighters["player"].selected_path == "bastiao"
    assert resumed.combat.fighters["player"].talent_ids == selected_talents

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None and character.combat_configuration_version == version
