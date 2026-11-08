import asyncio
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText
from sqlalchemy import func, select

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.groups import GroupService
from asterion.application.road import (
    NARETH_CAMARA_LABEL,
    NARETH_REGION,
    VARZEAS_BREJOS,
    VARZEAS_DIQUES,
    VARZEAS_PORTO,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.application.varzeas_missions import (
    P19_ID,
    P19_REWARD_SOURCE,
    P20_ID,
    P20_REWARD_SOURCE,
    P21_ID,
    P21_REWARD_SOURCE,
    P22_CODEX,
    P22_FRAGMENT,
    P22_ID,
    P22_REWARD_SOURCE,
    P23_ID,
    P23_REWARD_SOURCE,
    P24_ID,
    P24_REWARD_SOURCE,
    REGION,
    ROTAS_CODEX,
    S19_ID,
    S19_REWARD_SOURCE,
    S20_ID,
    S20_REWARD_SOURCE,
    S21_ID,
    S21_REWARD_SOURCE,
    S22_CODEX,
    S22_FRAGMENT,
    S22_ID,
    S22_REWARD_SOURCE,
    S23_ID,
    S23_REWARD_SOURCE,
    S24_ID,
    S24_REWARD_SOURCE,
    VarzeasMissionService,
)
from asterion.bot.combat_ui import (
    CampaignCombatCallback,
    CombatConsumableFlowCallback,
    VarzeasSoloCombatCallback,
    class_trial_action_ids,
)
from asterion.bot.road_ui import render_current_local
from asterion.bot.varzeas_missions_handlers import varzeas_missions_router
from asterion.bot.varzeas_missions_ui import render_varzeas_mission
from asterion.domain.combat import (
    active_player_key,
    allowed_actions,
    use_combat_consumable,
)
from asterion.domain.road import (
    VARZEAS_BREJOS_BRAZIER,
    VARZEAS_BREJOS_EXPLORE_UNLOCK,
    VARZEAS_BREJOS_HORTOS_ROUTE,
    VARZEAS_BREJOS_HUNT_UNLOCK,
    VARZEAS_BREJOS_LOCATION,
    VARZEAS_BREJOS_PROFILE,
    VARZEAS_CAMARA,
    VARZEAS_CAMARA_ACCESS_UNLOCK,
    VARZEAS_DIQUES_BRAZIER,
    VARZEAS_DIQUES_EXPLORE_UNLOCK,
    VARZEAS_DIQUES_HUNT_UNLOCK,
    VARZEAS_DIQUES_LOCATION,
    VARZEAS_DIQUES_PORTO_ROUTE,
    VARZEAS_DIQUES_PROFILE,
    VARZEAS_GALERIAS,
    VARZEAS_GALERIAS_BRAZIER,
    VARZEAS_GALERIAS_CAMARA_ROUTE,
    VARZEAS_GALERIAS_HUNT_UNLOCK,
    VARZEAS_GALERIAS_LOCATION,
    VARZEAS_GALERIAS_PROFILE,
    VARZEAS_HORTOS,
    VARZEAS_HORTOS_BRAZIER,
    VARZEAS_HORTOS_EXPLORE_UNLOCK,
    VARZEAS_HORTOS_GALERIAS_ROUTE,
    VARZEAS_HORTOS_HUNT_UNLOCK,
    VARZEAS_HORTOS_LOCATION,
    VARZEAS_HORTOS_ROUND_FAMILIARITY,
    VARZEAS_PORTO_BRAZIER,
    VARZEAS_PORTO_BREJOS_ROUTE,
    VARZEAS_REGION_ENTRY_UNLOCK,
    creature_for,
    material_for,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    CampaignObjectiveCredit,
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    ConsumableStack,
    DungeonRun,
    DungeonRunMember,
    EquipmentItem,
    ExplorationAttempt,
    GameActivity,
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
from tests.helpers.pvpve import (
    disable_round_pvpve_for_test,
    start_manual_hunt_after_no_match,
)
from tests.test_s4_s5_integration import _terminal
from tests.test_s6_p6_integration import _seed_final_campaign


async def _seed_nareth_exit(database, actor: int, *, level: int, p18: bool = True):
    character_id, sessions = await _seed_final_campaign(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = NARETH_REGION
        world.location = NARETH_CAMARA_LABEL
        if p18:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id="P17",
                    title="Medir o que Permanece",
                    status="completed",
                    step=11,
                    content_version="nareth-1.0.1",
                    progress={"completed": True},
                )
            )
            session.add(
                Unlock(
                    character_id=character_id,
                    unlock_id="region.nareth.camara_arconte.available",
                )
            )
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id="P18",
                    title="O Arconte Invertido",
                    status="completed",
                    step=1,
                    content_version="nareth-1.0.2",
                    progress={"completed": True},
                )
            )
            session.add(
                Unlock(
                    character_id=character_id,
                    unlock_id=VARZEAS_REGION_ENTRY_UNLOCK,
                )
            )
    return character_id, sessions


async def _seed_varzeas_porto(
    database,
    actor: int,
    *,
    level: int,
    p19: bool = True,
    p20: bool = False,
):
    character_id, sessions = await _seed_nareth_exit(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = REGION
        world.location = VARZEAS_PORTO
        if p19:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P19_ID,
                    title="Águas de Ferro",
                    status="completed",
                    step=10,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                )
            )
            session.add_all(
                [
                    Unlock(character_id=character_id, unlock_id=VARZEAS_DIQUES_PORTO_ROUTE),
                    Brazier(character_id=character_id, brazier_id=VARZEAS_PORTO_BRAZIER),
                    LocationDiscovery(
                        character_id=character_id,
                        location_id="varzeas.location.diques_rubros",
                    ),
                    LocationDiscovery(
                        character_id=character_id,
                        location_id="varzeas.location.porto_da_salmoura",
                    ),
                ]
            )
        if p20:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P20_ID,
                    title="O Pulso sob a Lama",
                    status="completed",
                    step=8,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                )
            )
            session.add_all(
                [
                    Unlock(character_id=character_id, unlock_id=VARZEAS_PORTO_BREJOS_ROUTE),
                    Unlock(character_id=character_id, unlock_id=VARZEAS_BREJOS_HUNT_UNLOCK),
                    Unlock(character_id=character_id, unlock_id=VARZEAS_BREJOS_EXPLORE_UNLOCK),
                    LocationDiscovery(
                        character_id=character_id,
                        location_id=VARZEAS_BREJOS_LOCATION,
                    ),
                ]
            )
    return character_id, sessions


async def _seed_varzeas_hortos(
    database,
    actor: int,
    *,
    level: int = 35,
    p21_step: int = 2,
    p21_status: str = "active",
):
    character_id, sessions = await _seed_varzeas_porto(
        database, actor, level=level, p19=True, p20=True
    )
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.location = VARZEAS_HORTOS
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P21_ID,
                title="Os Hortos Vazios",
                status=p21_status,
                step=p21_step,
                content_version="varzeas-1.0.0",
                progress={"beds_examined": []},
            )
        )
        session.add_all(
            [
                Unlock(character_id=character_id, unlock_id=VARZEAS_BREJOS_HORTOS_ROUTE),
                Unlock(character_id=character_id, unlock_id=VARZEAS_HORTOS_HUNT_UNLOCK),
                Unlock(character_id=character_id, unlock_id=VARZEAS_HORTOS_EXPLORE_UNLOCK),
                LocationDiscovery(character_id=character_id, location_id=VARZEAS_HORTOS_LOCATION),
            ]
        )
    return character_id, sessions


async def _seed_varzeas_p23_endgame(
    database,
    actor: int,
    *,
    level: int = 40,
    location: str = VARZEAS_HORTOS,
    s22_completed: bool = False,
):
    character_id, sessions = await _seed_varzeas_hortos(
        database,
        actor,
        level=level,
        p21_step=8,
        p21_status="completed",
    )
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.location = location
        session.add_all(
            (
                Quest(
                    character_id=character_id,
                    quest_id=P22_ID,
                    title="Transferência",
                    status="completed",
                    step=8,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                ),
                Quest(
                    character_id=character_id,
                    quest_id=P23_ID,
                    title="O Custo da Persistência",
                    status="completed",
                    step=8,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id=VARZEAS_CAMARA_ACCESS_UNLOCK,
                ),
            )
        )
        if s22_completed:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=S22_ID,
                    title="Protocolos sem Paciente",
                    status="completed",
                    step=6,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                )
            )
    return character_id, sessions


def _callback_update(data: str, *, actor: int, update_id: int) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": str(update_id),
            "from": {"id": actor, "is_bot": False, "first_name": "Player"},
            "chat_instance": "varzeas-solo-callback-test",
            "data": data,
            "message": {
                "message_id": update_id,
                "date": 1,
                "from": {"id": 123456, "is_bot": True, "first_name": "Asterion"},
                "chat": {"id": actor, "type": "private"},
                "text": "Asterion",
            },
        },
    }


@pytest.mark.asyncio
async def test_varzeas_entry_p19_and_s19_rewards_are_gated_persisted_and_idempotent(database):
    actor = 993191
    character_id, sessions = await _seed_nareth_exit(database, actor, level=30)
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")

    # P18 and its existing regional unlock are present, but level 31 is still required.
    assert await road.travel_route(actor, VARZEAS_DIQUES) is None
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 31

    async with sessions() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        assert world.region == NARETH_REGION
        assert world.location == NARETH_CAMARA_LABEL
    crossed = await road.travel_route(actor, VARZEAS_DIQUES)
    assert crossed is not None and crossed.location == VARZEAS_DIQUES
    await missions.on_location(actor)
    p19 = await missions.resume(actor, P19_ID)
    assert p19 is not None and p19.status == "active" and p19.step == 3
    assert p19.kind == "inspect_water"
    locked_s19 = await missions.resume(actor, S19_ID)
    assert locked_s19 is not None and not locked_s19.available
    assert await road.prepare_hunt(actor) is None
    assert await road.prepare_explore(actor) is None

    # The first objectives are recorded on legitimate P18-gated entry; P19's
    # remaining beats persist independently and the safe route opens at step 5.
    p19 = await missions.advance(actor, P19_ID, p19.state_version, "inspect_water")
    assert p19 is not None and p19.step == 4
    p19 = await missions.advance(actor, P19_ID, p19.state_version, "register_dique_brazier")
    assert p19 is not None and p19.step == 5
    p19 = await missions.advance(actor, P19_ID, p19.state_version, "follow_safe_route")
    assert p19 is not None and p19.step == 6
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_DIQUES_PORTO_ROUTE,
            )
        ) is not None

    arrived = await road.travel_route(actor, VARZEAS_PORTO)
    assert arrived is not None and arrived.location == VARZEAS_PORTO
    await missions.on_location(actor)
    p19 = await missions.resume(actor, P19_ID)
    assert p19 is not None and p19.step == 7
    p19 = await missions.advance(actor, P19_ID, p19.state_version, "register_porto_brazier")
    assert p19 is not None and p19.step == 8
    p19 = await missions.advance(actor, P19_ID, p19.state_version, "speak_sera")
    assert p19 is not None and p19.step == 9
    p19_version = p19.state_version
    completed_p19 = await missions.advance(actor, P19_ID, p19_version, "record_codex")
    assert completed_p19 is not None and completed_p19.status == "completed"
    repeated_p19 = await missions.advance(actor, P19_ID, p19_version, "record_codex")
    assert repeated_p19 is not None and repeated_p19.status == "completed"

    async with sessions() as session:
        events = list(
            (
                await session.scalars(
                    select(RewardEvent).where(
                        RewardEvent.character_id == character_id,
                        RewardEvent.source_id == P19_REWARD_SOURCE,
                    )
                )
            ).all()
        )
        assert len(events) == 1
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == events[0].id)
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 34300),
            ("crowns", None, 570),
            ("material", "material.varzeas.ferro_de_salmoura", 1),
            ("material", "material.varzeas.couro_de_varzea", 1),
        }
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_DIQUES_BRAZIER,
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_PORTO_BRAZIER,
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "varzeas.location.diques_rubros",
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "varzeas.location.porto_da_salmoura",
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
                CodexFragment.fragment_id == "codex.fragment.varzeas.p19.rotas_initial",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.agua_de_ferro",
            )
        ) is not None
        assert await session.scalar(
            select(func.count(CampaignObjectiveCredit.id)).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == P19_ID,
            )
        ) == 9

    # P19 releases the first regional pool, but Ronda still waits for a valid
    # manual victory at this exact Local.
    await road.travel_route(actor, VARZEAS_DIQUES)
    local = await road.resume(actor)
    assert local is not None and local.kind == "varzeas_diques"
    assert local.hunt_enabled is True and local.explore_enabled is True
    assert local.familiar is False
    assert await road.prepare_hunt(actor) is not None
    blocked_round = await RoundService(sessions, "ocaso").prepare_round(actor, 5)
    assert blocked_round is not None and blocked_round.kind == "varzeas_diques"
    local_ui = render_current_local(local, explore_state="available")
    assert "Desbravar" in local_ui.text and "Caçada · Disponível" in local_ui.text

    # S19 is offered at Sera only after P19 and level 32; its repair/record
    # settlement contains no material or equipment component.
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 31
    locked_s19 = await missions.resume(actor, S19_ID)
    assert locked_s19 is not None and not locked_s19.available
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 32
    await road.travel_route(actor, VARZEAS_PORTO)
    offer = await missions.resume(actor, S19_ID)
    assert offer is not None and offer.kind == "offer" and offer.available
    assert "Sal nas Feridas" in render_varzeas_mission(offer).text
    s19 = await missions.start(actor, S19_ID)
    assert s19 is not None and s19.status == "active" and s19.step == 1
    await road.travel_route(actor, VARZEAS_DIQUES)
    s19 = await missions.advance(actor, S19_ID, s19.state_version, "inspect_a")
    assert s19 is not None and s19.step == 1
    duplicate_point = await missions.advance(
        actor, S19_ID, s19.state_version, "inspect_a"
    )
    assert duplicate_point is not None
    assert duplicate_point.state_version == s19.state_version
    s19 = duplicate_point
    for action in ("inspect_b", "inspect_c"):
        s19 = await missions.advance(actor, S19_ID, s19.state_version, action)
    assert s19 is not None and s19.step == 2
    s19 = await missions.advance(actor, S19_ID, s19.state_version, "differentiate_brine_damage")
    assert s19 is not None and s19.step == 3
    s19_version = s19.state_version
    completed_s19 = await missions.advance(actor, S19_ID, s19_version, "repair_and_record")
    assert completed_s19 is not None and completed_s19.status == "completed"
    await missions.advance(actor, S19_ID, s19_version, "repair_and_record")
    async with sessions() as session:
        s19_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S19_REWARD_SOURCE,
            )
        )
        assert s19_event is not None
        s19_components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == s19_event.id)
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in s19_components} == {
            ("xp", None, 14400),
            ("crowns", None, 290),
        }


@pytest.mark.asyncio
async def test_varzeas_manual_hunt_and_round_share_grau_iv_settlement(database, monkeypatch):
    import asterion.application.road as road_module
    import asterion.application.round as round_module

    actor = 993192
    character_id, sessions = await _seed_nareth_exit(database, actor, level=31)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        world.region = REGION
        world.location = VARZEAS_DIQUES
        session.add_all(
            [
                Quest(
                    character_id=character_id,
                    quest_id=P19_ID,
                    title="Águas de Ferro",
                    status="completed",
                    step=9,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                ),
                Unlock(character_id=character_id, unlock_id=VARZEAS_DIQUES_HUNT_UNLOCK),
                Unlock(character_id=character_id, unlock_id=VARZEAS_DIQUES_EXPLORE_UNLOCK),
                Brazier(character_id=character_id, brazier_id=VARZEAS_DIQUES_BRAZIER),
                LocationDiscovery(
                    character_id=character_id,
                    location_id=VARZEAS_DIQUES_LOCATION,
                ),
            ]
        )
    road = RoadService(sessions, "ocaso")
    local = await road.resume(actor)
    assert local is not None and local.hunt_enabled and local.explore_enabled
    blocked_round = await RoundService(sessions, "ocaso").prepare_round(actor, 5)
    assert blocked_round is not None and blocked_round.kind == "varzeas_diques"
    assert await road.prepare_hunt(actor) is not None

    original_create = road_module.create_road_combat

    def safe_combat(*args, **kwargs):
        combat = original_create(*args, **kwargs)
        combat.fighters["enemy"].stats = replace(combat.fighters["enemy"].stats, attack=1)
        return combat

    monkeypatch.setattr(road_module, "create_road_combat", safe_combat)
    monkeypatch.setattr(round_module, "create_road_combat", safe_combat)
    original_draw = road_module._draw_int

    def force_common_basic_material(seed, purpose, modulo):
        if purpose == "material-roll":
            return 0
        return original_draw(seed, purpose, modulo)

    monkeypatch.setattr(road_module, "_draw_int", force_common_basic_material)
    monkeypatch.setattr(
        road_module, "select_creature", lambda *_args, **_kwargs: creature_for("garca_ferruginosa")
    )
    monkeypatch.setattr(
        round_module, "select_creature", lambda *_args, **_kwargs: creature_for("garca_ferruginosa")
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
        assert context is not None and context.creature_id == "garca_ferruginosa"
        manual_reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{activity_id}",
            )
        )
        assert manual_reward is not None
        materials = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == manual_reward.id,
                        RewardComponent.kind == "material",
                    )
                )
            ).all()
        )
        assert materials
        expected = Counter(
            material_for(context.creature_id, f"{context.seed}:material.basic.{ordinal}")
            for ordinal in range(len(materials))
        )
        assert Counter(row.item_id for row in materials) == expected
        assert set(row.item_id for row in materials) <= {
            "material.varzeas.junco_ferruginoso",
            "material.varzeas.soro_antigo",
        }
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_DIQUES_PROFILE.round_familiarity,
            )
        ) is not None
    await road.acknowledge_result(actor)

    rounds = RoundService(sessions, "ocaso")

    async def no_round_match(*_args, **_kwargs):
        return False

    rounds.pvpve.queue_round_hunt = no_round_match
    preparing = await rounds.prepare_round(actor, 5)
    assert preparing is not None and preparing.kind == "round_prepare"
    active = await rounds.start_round(actor, preparing.round_id, preparing.state_version)
    assert active is not None and active.kind == "round_active"
    async with sessions.begin() as session:
        state = await session.get(HuntRound, active.round_id)
        assert state is not None
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
    await rounds.advance_due_rounds()
    async with sessions() as session:
        state = await session.get(HuntRound, active.round_id)
        assert state is not None and state.completed_encounters == 1
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(HuntRoundEncounter.round_id == state.id)
        )
        assert encounter is not None and encounter.status == "completed"
        assert encounter.creature_id == "garca_ferruginosa"
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == encounter.activity_id)
        )
        assert context is not None and context.loot_profile == "round"
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{encounter.activity_id}",
            )
        )
        assert reward is not None
        round_materials = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == reward.id,
                        RewardComponent.kind == "material",
                    )
                )
            ).all()
        )
        assert round_materials
        expected_round = Counter(
            material_for(context.creature_id, f"{context.seed}:material.basic.{ordinal}")
            for ordinal in range(len(round_materials))
        )
        assert Counter(row.item_id for row in round_materials) == expected_round
        assert set(row.item_id for row in round_materials) <= {
            "material.varzeas.junco_ferruginoso",
            "material.varzeas.soro_antigo",
        }


@pytest.mark.asyncio
async def test_varzeas_region_requires_p18_and_posto_is_a_safe_hub(database):
    actor = 993193
    character_id, sessions = await _seed_nareth_exit(database, actor, level=31, p18=False)
    async with sessions.begin() as session:
        session.add(
            Unlock(character_id=character_id, unlock_id=VARZEAS_REGION_ENTRY_UNLOCK)
        )
    road = RoadService(sessions, "ocaso")
    assert await road.travel_route(actor, VARZEAS_DIQUES) is None
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = REGION
        world.location = VARZEAS_PORTO
    local = await road.resume(actor)
    assert local is not None and local.kind == "varzeas_porto"
    assert local.hunt_enabled is False and local.explore_enabled is False
    assert local.familiar is False
    assert await road.prepare_hunt(actor) is None
    assert await RoundService(sessions, "ocaso").prepare_round(actor, 5) is None
    screen = render_current_local(local)
    callbacks = {
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    }
    assert "road:hunt" not in callbacks
    assert "road:explore:start" not in callbacks


@pytest.mark.asyncio
async def test_varzeas_p19_shared_objective_credit_is_recorded_per_present_member(database):
    leader, helper = 993194, 993195
    leader_id, sessions = await _seed_nareth_exit(database, leader, level=31)
    helper_id, _ = await _seed_nareth_exit(database, helper, level=31)
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
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")

    # Entry and P19 are persisted separately for whoever is present. The helper
    # joins the same legitimate checkpoint later and receives its own records.
    await road.travel_route(leader, VARZEAS_DIQUES)
    await missions.on_location(leader)
    assert (await missions.resume(leader, P19_ID)).step == 3
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == helper_id, Quest.quest_id == P19_ID)
        ) is None

    await road.travel_route(helper, VARZEAS_DIQUES)
    await missions.on_location(helper)
    leader_view = await missions.resume(leader, P19_ID)
    helper_view = await missions.resume(helper, P19_ID)
    assert leader_view is not None and leader_view.step == helper_view.step == 3
    shared = await missions.advance(
        leader, P19_ID, leader_view.state_version, "inspect_water"
    )
    assert shared is not None and shared.step == 4
    async with sessions() as session:
        for character_id in (leader_id, helper_id):
            quest = await session.scalar(
                select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P19_ID)
            )
            assert quest is not None and quest.status == "active" and quest.step == 4
            assert await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == P19_ID,
                    CampaignObjectiveCredit.objective_id == "p19.examined_water_and_gate",
                )
            ) is not None


@pytest.mark.asyncio
async def test_varzeas_desbravar_unique_xp_codex_feat_and_idempotency(database, monkeypatch):
    import asterion.application.road as road_module

    actor = 993196
    character_id, sessions = await _seed_nareth_exit(database, actor, level=32)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        world.region = REGION
        world.location = VARZEAS_DIQUES
        character.vigor = character.max_vigor
        session.add_all(
            [
                Quest(
                    character_id=character_id,
                    quest_id=P19_ID,
                    title="Águas de Ferro",
                    status="completed",
                    step=10,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                ),
                Unlock(character_id=character_id, unlock_id=VARZEAS_DIQUES_EXPLORE_UNLOCK),
                Unlock(character_id=character_id, unlock_id=VARZEAS_DIQUES_HUNT_UNLOCK),
                LocationDiscovery(character_id=character_id, location_id=VARZEAS_DIQUES_LOCATION),
            ]
        )

    road = RoadService(sessions, "ocaso")
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.varzeas.diques.comporta_primeiro_dique",
            "Comporta do Primeiro Dique encontrada.",
        ),
    )
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        starting_xp = character.xp
    first = await road.explore(actor)
    assert first is not None and first.result_id == "explore.varzeas.diques.comporta_primeiro_dique"
    assert first.attempt_id is not None
    async with sessions.begin() as session:
        attempt = await session.get(ExplorationAttempt, first.attempt_id)
        character = await session.get(Character, character_id)
        assert attempt is not None and attempt.status == "completed"
        assert character is not None and character.xp == starting_xp + 5760
        first_xp = character.xp
        attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)

    await road.acknowledge_result(actor, first.attempt_id)
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"explore:{first.attempt_id}",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id
                == "codex.fragment.varzeas.diques.comporta_primeiro_dique",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.entre_os_diques",
            )
        ) is None

    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "narrative",
            "explore.varzeas.diques.agua_sobe_sem_chuva",
            "Água que Sobe sem Chuva observada.",
        ),
    )
    second = await road.explore(actor)
    assert second is not None and second.result_id == "explore.varzeas.diques.agua_sobe_sem_chuva"
    assert second.attempt_id is not None
    await road.acknowledge_result(actor, second.attempt_id)
    await road.acknowledge_result(actor, second.attempt_id)
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.xp == first_xp + 1800
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"explore:{second.attempt_id}",
            )
        ) is not None
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"explore:{second.attempt_id}",
            )
        ) == 1
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.entre_os_diques",
            )
        ) is not None


@pytest.mark.asyncio
async def test_varzeas_p20_gates_scripted_spider_and_reward_are_persistent(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 993197
    character_id, sessions = await _seed_varzeas_porto(
        database, actor, level=32, p19=False
    )
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")

    assert (await missions.resume(actor, P20_ID)).available is False
    assert await road.travel_route(actor, VARZEAS_BREJOS) is None
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P19_ID,
                title="Águas de Ferro",
                status="completed",
                step=10,
                content_version="varzeas-1.0.0",
                progress={"completed": True},
            )
        )
    await missions.on_location(actor)
    assert await sessionless_quest(sessions, character_id, P20_ID) is None

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 33
    await missions.on_location(actor)
    p20 = await missions.resume(actor, P20_ID)
    assert p20 is not None and p20.status == "active" and p20.step == 1
    assert p20.kind == "travel_brejos"
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    await missions.on_location(actor)
    p20 = await missions.resume(actor, P20_ID)
    assert p20 is not None and p20.step == 2
    assert await road.prepare_hunt(actor) is None
    assert await road.prepare_explore(actor) is None
    async with sessions() as session:
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == VARZEAS_BREJOS_LOCATION,
            )
        ) is not None

    p20 = await missions.advance(actor, P20_ID, p20.state_version, "observe_pulse_a")
    assert p20 is not None and p20.progress["water_occurrences"] == ["a"]
    duplicate = await missions.advance(actor, P20_ID, p20.state_version, "observe_pulse_a")
    assert duplicate is not None and duplicate.state_version == p20.state_version
    p20 = await missions.advance(actor, P20_ID, duplicate.state_version, "observe_pulse_b")
    p20 = await missions.advance(actor, P20_ID, p20.state_version, "observe_pulse_c")
    assert p20 is not None and p20.step == 3
    p20 = await missions.advance(actor, P20_ID, p20.state_version, "compare_buried_valves")
    assert p20 is not None and p20.step == 4

    combat = await missions.start_solo_combat(actor, P20_ID, p20.state_version)
    assert combat is not None and combat.kind == "combat"
    assert combat.combat.fighters["enemy"].name == "Aranha de Junco"
    assert combat.combat.fighters["enemy"].level == 33
    assert combat.combat.variant is None
    assert combat.activity_id is not None
    async with sessions() as session:
        activity_reward = await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        )
        assert activity_reward is None
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "aranha_junco",
            )
        ) is not None
        assert await session.scalar(
            select(HuntContext.id).where(
                HuntContext.game_activity_id == combat.activity_id
            )
        ) is None

    resumed = await missions.resume(actor, P20_ID)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id) == (
        combat.activity_id,
        combat.encounter_id,
    )
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await missions.action_combat(
        actor, combat.activity_id, combat.combat.version, "attack"
    )
    assert victory is not None and victory.step == 5
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        ) is None
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == "aranha_junco",
                BestiaryEvidence.evidence_id == "first_victory",
            )
        ) is not None

    p20 = await missions.advance(actor, P20_ID, victory.state_version, "examine_conduit")
    assert p20 is not None and p20.step == 6
    assert await road.travel_route(actor, VARZEAS_PORTO) is not None
    await missions.on_location(actor)
    p20 = await missions.resume(actor, P20_ID)
    assert p20 is not None and p20.step == 7
    version = p20.state_version
    completed = await missions.advance(actor, P20_ID, version, "record_pulse")
    repeated = await missions.advance(actor, P20_ID, version, "record_pulse")
    assert completed is not None and completed.status == "completed"
    assert repeated is not None and repeated.status == "completed"

    async with sessions() as session:
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P20_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 37800),
            ("crowns", None, 600),
            ("material", "material.varzeas.ferro_de_salmoura", 1),
            ("material", "material.varzeas.junco_ferruginoso", 2),
            ("material", "material.varzeas.soro_antigo", 1),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P20_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.o_pulso_sob_a_lama",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.varzeas.p20.pulso_sob_a_lama",
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.mystery.pulso_sob_a_lama",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_BREJOS_HUNT_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_BREJOS_EXPLORE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_BREJOS_BRAZIER,
            )
        ) is None


async def sessionless_quest(sessions, character_id, quest_id):
    async with sessions() as session:
        return await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == quest_id,
            )
        )


@pytest.mark.asyncio
async def test_varzeas_s20_uses_default_scripted_encounter_and_exact_quest_reward(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor = 993198
    character_id, sessions = await _seed_varzeas_porto(
        database, actor, level=33, p20=False
    )
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")
    assert not (await missions.resume(actor, S20_ID)).available
    async with sessions.begin() as session:
        p20 = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == P20_ID,
            )
        )
        assert p20 is not None and p20.status == "active"
        p20.status = "completed"
        p20.step = 8
        p20.progress = {**(p20.progress or {}), "completed": True}
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_PORTO_BREJOS_ROUTE,
            )
        ) is not None
    assert not (await missions.resume(actor, S20_ID)).available
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 34

    offer = await missions.resume(actor, S20_ID)
    assert offer is not None and offer.available and offer.kind == "offer"
    s20 = await missions.start(actor, S20_ID)
    assert s20 is not None and s20.status == "active" and s20.step == 1
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    await missions.on_location(actor)
    s20 = await missions.advance(actor, S20_ID, s20.state_version, "observe_tracks")
    s20 = await missions.advance(actor, S20_ID, s20.state_version, "follow_continuity_signs")
    s20 = await missions.advance(actor, S20_ID, s20.state_version, "locate_portador")
    assert s20 is not None and s20.step == 4

    combat = await missions.start_solo_combat(actor, S20_ID, s20.state_version)
    assert combat is not None and combat.kind == "combat"
    assert combat.combat.fighters["enemy"].name == "Portador Rubro"
    assert combat.combat.fighters["enemy"].level == 34
    assert combat.combat.variant is None
    assert combat.activity_id is not None
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        ) is None
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "portador_rubro",
            )
        ) is not None
    resumed = await missions.resume(actor, S20_ID)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id) == (
        combat.activity_id,
        combat.encounter_id,
    )
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await missions.action_combat(
        actor, combat.activity_id, combat.combat.version, "attack"
    )
    assert victory is not None and victory.step == 5
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        ) is None
        assert await session.scalar(
            select(HuntContext.id).where(
                HuntContext.game_activity_id == combat.activity_id
            )
        ) is None
    s20 = await missions.advance(
        actor, S20_ID, victory.state_version, "record_anatomy_and_environment"
    )
    assert s20 is not None and s20.step == 6
    assert await road.travel_route(actor, VARZEAS_PORTO) is not None
    await missions.on_location(actor)
    s20 = await missions.resume(actor, S20_ID)
    assert s20 is not None and s20.step == 7
    version = s20.state_version
    completed = await missions.advance(actor, S20_ID, version, "report_to_sera")
    duplicate = await missions.advance(actor, S20_ID, version, "report_to_sera")
    assert completed is not None and completed.status == "completed"
    assert duplicate is not None and duplicate.status == "completed"
    async with sessions() as session:
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S20_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 27720),
            ("crowns", None, 460),
            ("material", "material.varzeas.junco_ferruginoso", 1),
            ("material", "material.varzeas.soro_antigo", 1),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S20_REWARD_SOURCE,
            )
        ) == 1


@pytest.mark.asyncio
async def test_varzeas_viuva_mastery_requires_published_evidence(database):
    from types import SimpleNamespace

    actor = 993199
    character_id, sessions = await _seed_varzeas_porto(
        database, actor, level=35, p20=True
    )
    recorder = BestiaryRecorder()
    async with sessions.begin() as session:
        await recorder.record(
            session,
            character_id,
            "viuva_rubra",
            victory=True,
            elite=True,
            observation_category="elite",
        )
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "viuva_rubra",
            )
        )
        assert entry is not None and entry.stage != "dominated"
        new_evidence = await recorder.record_combat_events(
            session,
            character_id,
            "viuva_rubra",
            None,
            SimpleNamespace(
                events=(
                    SimpleNamespace(actor="enemy", action="picada_rubra", damage=1),
                    SimpleNamespace(actor="enemy", action="teia_junco", damage=1),
                    SimpleNamespace(actor="enemy", action="salto_agua", damage=1),
                )
            ),
        )
        assert new_evidence == {
            "mechanic:poison",
            "action:teia_junco",
            "action:picada_rubra",
            "action:salto_agua",
        }
        await recorder.record(
            session,
            character_id,
            "viuva_rubra",
            elite=True,
            observation_category="elite",
        )
        assert entry.stage == "dominated"


@pytest.mark.asyncio
async def test_varzeas_brejos_exploration_brazier_and_local_round_unlock(
    database, monkeypatch
):
    import asterion.application.road as road_module
    import asterion.application.round as round_module

    actor = 993200
    character_id, sessions = await _seed_varzeas_porto(
        database, actor, level=35, p20=True
    )
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.vigor = character.max_vigor
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id=VARZEAS_DIQUES_PROFILE.round_familiarity,
            )
        )
    road = RoadService(sessions, "ocaso")
    rounds = RoundService(sessions, "ocaso")
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    local = await road.resume(actor)
    assert local is not None and local.kind == "varzeas_brejos"
    assert local.hunt_enabled and local.explore_enabled
    blocked_round = await rounds.prepare_round(actor, 5)
    assert blocked_round is not None and blocked_round.kind == "varzeas_brejos"
    assert await road.prepare_hunt(actor) is not None

    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.varzeas.brejos.braseiro_juncos_baixos",
            "Braseiro dos Juncos Baixos descoberto.",
        ),
    )
    exploration = await road.explore(actor)
    assert exploration is not None and exploration.attempt_id is not None
    assert exploration.result_id == "explore.varzeas.brejos.braseiro_juncos_baixos"
    assert exploration.attempt_id is not None
    await road.acknowledge_result(actor, exploration.attempt_id)
    async with sessions.begin() as session:
        attempt = await session.get(ExplorationAttempt, exploration.attempt_id)
        assert attempt is not None
        attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_BREJOS_BRAZIER,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id
                == "codex.fragment.varzeas.brejos.braseiro_juncos_baixos",
            )
        ) is not None

    original_create = road_module.create_road_combat

    def safe_combat(*args, **kwargs):
        combat = original_create(*args, **kwargs)
        combat.fighters["enemy"].stats = replace(
            combat.fighters["enemy"].stats, attack=1
        )
        return combat

    monkeypatch.setattr(road_module, "create_road_combat", safe_combat)
    monkeypatch.setattr(round_module, "create_road_combat", safe_combat)
    original_draw = road_module._draw_int

    def ensure_common_material(seed, purpose, modulo):
        return 0 if purpose == "material-roll" else original_draw(seed, purpose, modulo)

    monkeypatch.setattr(road_module, "_draw_int", ensure_common_material)
    monkeypatch.setattr(
        road_module,
        "select_creature",
        lambda *_args, **_kwargs: creature_for("aranha_junco"),
    )
    monkeypatch.setattr(
        round_module,
        "select_creature",
        lambda *_args, **_kwargs: creature_for("aranha_junco"),
    )
    manual = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert manual is not None and manual.kind == "combat"
    activity_id = manual.activity_id
    for _ in range(100):
        if manual.kind != "combat":
            break
        actions = allowed_actions(manual.combat)
        action = "art" if "art" in actions else "attack"
        manual = await road.action(actor, activity_id, manual.combat.version, action)
    assert manual is not None and manual.kind == "hunt_victory"
    async with sessions() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity_id)
        )
        assert context is not None and context.creature_id == "aranha_junco"
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_BREJOS_PROFILE.round_familiarity,
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{activity_id}",
            )
        )
        assert reward is not None
        materials = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == reward.id,
                        RewardComponent.kind == "material",
                    )
                )
            ).all()
        )
        assert materials
        expected = Counter(
            material_for(context.creature_id, f"{context.seed}:material.basic.{ordinal}")
            for ordinal in range(len(materials))
        )
        assert Counter(row.item_id for row in materials) == expected
        assert set(expected) <= {
            "material.varzeas.junco_ferruginoso",
            "material.varzeas.soro_antigo",
        }
    await road.acknowledge_result(actor)

    disable_round_pvpve_for_test(rounds)
    preparing = await rounds.prepare_round(actor, 5)
    assert preparing is not None and preparing.kind == "round_prepare"
    active = await rounds.start_round(actor, preparing.round_id, preparing.state_version)
    assert active is not None and active.kind == "round_active"
    async with sessions.begin() as session:
        round_state = await session.get(HuntRound, active.round_id)
        assert round_state is not None
        round_state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
    await rounds.advance_due_rounds()
    async with sessions() as session:
        round_state = await session.get(HuntRound, active.round_id)
        assert round_state is not None and round_state.completed_encounters == 1
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == round_state.id
            )
        )
        assert encounter is not None and encounter.status == "completed"
        assert encounter.creature_id == "aranha_junco"
        context = await session.scalar(
            select(HuntContext).where(
                HuntContext.game_activity_id == encounter.activity_id
            )
        )
        assert context is not None and context.loot_profile == "round"
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{encounter.activity_id}",
            )
        )
        assert reward is not None
        round_materials = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == reward.id,
                        RewardComponent.kind == "material",
                    )
                )
            ).all()
        )
        assert round_materials
        expected_round = Counter(
            material_for(
                context.creature_id,
                f"{context.seed}:material.basic.{ordinal}",
            )
            for ordinal in range(len(round_materials))
        )
        assert Counter(row.item_id for row in round_materials) == expected_round
        assert set(expected_round) <= {
            "material.varzeas.junco_ferruginoso",
            "material.varzeas.soro_antigo",
        }


@pytest.mark.asyncio
async def test_varzeas_enfermaria_exploration_records_entry_without_starting_dungeon(
    database, monkeypatch
):
    import asterion.application.road as road_module

    actor = 993201
    character_id, sessions = await _seed_varzeas_porto(
        database, actor, level=34, p20=True
    )
    road = RoadService(sessions, "ocaso")
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.varzeas.brejos.entrada_enfermaria_afundada",
            "Entrada da Enfermaria Afundada descoberta.",
        ),
    )
    discovery = await road.explore(actor)
    assert discovery is not None
    assert discovery.result_id == "explore.varzeas.brejos.entrada_enfermaria_afundada"
    assert discovery.attempt_id is not None
    await road.acknowledge_result(actor, discovery.attempt_id)
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "dungeon.varzeas.enfermaria_afundada.discovered",
            )
        ) is not None
        assert await session.scalar(
            select(func.count(DungeonRun.id))
        ) == 0
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_BREJOS_BRAZIER,
            )
        ) is None


@pytest.mark.asyncio
async def test_varzeas_p20_objective_credit_is_shared_only_with_present_members(database):
    leader, helper = 993202, 993203
    leader_id, sessions = await _seed_varzeas_porto(
        database, leader, level=33, p19=True
    )
    helper_id, _ = await _seed_varzeas_porto(
        database, helper, level=33, p19=True
    )
    async with sessions() as session:
        helper_character = await session.get(Character, helper_id)
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invite = await groups.invite(
        leader, helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        helper, invite.invite_id, expected_revision=invite.revision, accept=True
    )
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso", groups=groups)
    await missions.on_location(leader)
    await missions.on_location(helper)
    leader_quest = await sessionless_quest(sessions, leader_id, P20_ID)
    helper_quest = await sessionless_quest(sessions, helper_id, P20_ID)
    assert leader_quest is not None and leader_quest.step == 1
    assert helper_quest is not None and helper_quest.step == 1

    assert await road.travel_route(leader, VARZEAS_BREJOS) is not None
    await missions.on_location(leader)
    leader_view = await missions.resume(leader, P20_ID)
    helper_view = await missions.resume(helper, P20_ID)
    assert leader_view is not None and leader_view.step == 2
    assert helper_view is not None and helper_view.step == 1
    leader_view = await missions.advance(
        leader, P20_ID, leader_view.state_version, "observe_pulse_a"
    )
    assert leader_view is not None and leader_view.progress["water_occurrences"] == ["a"]
    async with sessions() as session:
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == leader_id,
                CampaignObjectiveCredit.quest_id == P20_ID,
                CampaignObjectiveCredit.objective_id == "p20.water_occurrence_a",
            )
        ) is not None
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == helper_id,
                CampaignObjectiveCredit.quest_id == P20_ID,
                CampaignObjectiveCredit.objective_id == "p20.water_occurrence_a",
            )
        ) is None

    assert await road.travel_route(helper, VARZEAS_BREJOS) is not None
    await missions.on_location(helper)
    leader_view = await missions.resume(leader, P20_ID)
    assert leader_view is not None and leader_view.step == 2
    leader_view = await missions.advance(
        leader, P20_ID, leader_view.state_version, "observe_pulse_b"
    )
    assert leader_view is not None
    async with sessions() as session:
        for character_id in (leader_id, helper_id):
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P20_ID,
                )
            )
            assert quest is not None
            assert "b" in quest.progress["water_occurrences"]
            assert await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == P20_ID,
                    CampaignObjectiveCredit.objective_id == "p20.water_occurrence_b",
                )
            ) is not None


@pytest.mark.asyncio
async def test_varzeas_p20_scripted_spider_uses_shared_campaign_combat(database):
    leader, helper = 993204, 993205
    leader_id, sessions = await _seed_varzeas_porto(
        database, leader, level=33, p19=True
    )
    helper_id, _ = await _seed_varzeas_porto(
        database, helper, level=33, p19=True
    )
    async with sessions() as session:
        helper_character = await session.get(Character, helper_id)
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invitation = await groups.invite(
        leader, helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        helper,
        invitation.invite_id,
        expected_revision=invitation.revision,
        accept=True,
    )
    missions = VarzeasMissionService(sessions, "ocaso", groups=groups)
    road = RoadService(sessions, "ocaso")
    await missions.on_location(leader)
    leader_view = await missions.resume(leader, P20_ID)
    helper_view = await missions.resume(helper, P20_ID)
    assert leader_view is not None and leader_view.step == 1
    assert helper_view is not None and helper_view.step == 1

    assert await road.travel_route(leader, VARZEAS_BREJOS) is not None
    await missions.on_location(leader)
    assert await road.travel_route(helper, VARZEAS_BREJOS) is not None
    await missions.on_location(helper)
    leader_view = await missions.resume(leader, P20_ID)
    assert leader_view is not None and leader_view.step == 2
    for point in ("a", "b", "c"):
        leader_view = await missions.advance(
            leader,
            P20_ID,
            leader_view.state_version,
            f"observe_pulse_{point}",
        )
    assert leader_view is not None and leader_view.step == 3
    leader_view = await missions.advance(
        leader, P20_ID, leader_view.state_version, "compare_buried_valves"
    )
    assert leader_view is not None and leader_view.step == 4

    proposal_view = await missions.propose_group_combat(
        leader, P20_ID, leader_view.state_version
    )
    assert proposal_view is not None and proposal_view.proposal_id is not None
    proposal = await groups.activity_proposal(leader, proposal_view.proposal_id)
    accepted = await groups.respond_activity(
        helper,
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
    )
    started = await missions.start_group_combat(
        leader, proposal.proposal_id, expected_revision=accepted.revision
    )
    helper_view = await missions.resume(helper, P20_ID)
    assert started is not None and started.kind == "combat"
    assert started.group_size == 2 and started.combat is not None
    assert started.combat.fighters["enemy"].name == "Aranha de Junco"
    assert started.combat.fighters["enemy"].level == 33
    assert started.combat.variant is None
    assert helper_view is not None and helper_view.kind == "combat"
    assert helper_view.group_size == 2
    assert helper_view.encounter_id == started.encounter_id
    assert helper_view.activity_id != started.activity_id
    async with sessions() as session:
        for character_id in (leader_id, helper_id):
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P20_ID,
                )
            )
            assert quest is not None and quest.step == 4
            assert quest.progress["activity_id"]


@pytest.mark.asyncio
async def test_varzeas_p21_gate_journey_choice_and_rewards_are_idempotent(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    blocked_actor = 993220
    blocked_id, blocked_sessions = await _seed_varzeas_porto(
        database, blocked_actor, level=35, p19=True, p20=False
    )
    blocked_road = RoadService(blocked_sessions, "ocaso")
    blocked_missions = VarzeasMissionService(blocked_sessions, "ocaso")
    assert (await blocked_missions.resume(blocked_actor, P21_ID)).available is False
    arrived = await blocked_road.travel_route(blocked_actor, VARZEAS_BREJOS)
    assert arrived is not None and arrived.kind == "varzeas_brejos"
    assert arrived.location == VARZEAS_BREJOS
    await blocked_missions.on_location(blocked_actor)
    blocked_p20 = await sessionless_quest(blocked_sessions, blocked_id, P20_ID)
    assert blocked_p20 is not None and blocked_p20.status == "active" and blocked_p20.step == 2
    assert (await blocked_missions.resume(blocked_actor, P21_ID)).available is False
    assert await sessionless_quest(blocked_sessions, blocked_id, P21_ID) is None
    blocked_local = await blocked_road.resume(blocked_actor)
    assert blocked_local is not None and blocked_local.kind == "varzeas_brejos"
    assert blocked_local.hunt_enabled is False and blocked_local.explore_enabled is False
    assert await blocked_road.prepare_hunt(blocked_actor) is None
    assert await blocked_road.prepare_explore(blocked_actor) is None

    actor = 993221
    character_id, sessions = await _seed_varzeas_porto(
        database, actor, level=34, p19=True, p20=True
    )
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")

    # P20 alone is insufficient below Nv.35; the new route is not exposed.
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    await missions.on_location(actor)
    p21 = await missions.resume(actor, P21_ID)
    assert p21 is not None and p21.available is False
    assert await sessionless_quest(sessions, character_id, P21_ID) is None
    blocked_round = await RoundService(sessions, "ocaso").prepare_round(actor, 5)
    assert blocked_round is not None and blocked_round.kind == "varzeas_brejos"
    assert await road.travel_route(actor, VARZEAS_HORTOS) is None

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 35
    await missions.on_location(actor)
    p21 = await missions.resume(actor, P21_ID)
    assert p21 is not None and p21.status == "active" and p21.step == 1
    assert p21.kind == "travel_hortos"
    assert await road.travel_route(actor, VARZEAS_HORTOS) is not None
    await missions.on_location(actor)
    p21 = await missions.resume(actor, P21_ID)
    assert p21 is not None and p21.step == 2
    assert p21.kind == "examine_beds"
    local = await road.resume(actor)
    assert local is not None and local.kind == "varzeas_hortos"
    assert local.hunt_enabled and local.explore_enabled
    async with sessions() as session:
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == VARZEAS_HORTOS_LOCATION,
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_HORTOS_BRAZIER,
            )
        ) is None

    p21 = await missions.advance(actor, P21_ID, p21.state_version, "examine_bed_a")
    assert p21 is not None and p21.step == 2
    duplicate = await missions.advance(
        actor, P21_ID, p21.state_version, "examine_bed_a"
    )
    assert duplicate is not None and duplicate.state_version == p21.state_version
    p21 = await missions.advance(actor, P21_ID, duplicate.state_version, "examine_bed_b")
    p21 = await missions.advance(actor, P21_ID, p21.state_version, "examine_bed_c")
    assert p21 is not None and p21.step == 3
    assert creature_for("cervo_ferrugem").actions[2][8] is True

    combat = await missions.start_solo_combat(actor, P21_ID, p21.state_version)
    assert combat is not None and combat.kind == "combat"
    assert combat.combat.fighters["enemy"].name == "Cervo Ferrugem"
    assert combat.combat.fighters["enemy"].level == 35
    assert combat.combat.variant is None
    assert combat.activity_id is not None
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        ) is None
    await missions.resume(actor, P21_ID)
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await missions.action_combat(
        actor, combat.activity_id, combat.combat.version, "attack"
    )
    assert victory is not None and victory.step == 4
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        ) is None
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == "cervo_ferrugem",
                BestiaryEvidence.evidence_id == "first_victory",
            )
        ) is not None

    p21 = await missions.advance(actor, P21_ID, victory.state_version, "find_technical_plate")
    p21 = await missions.advance(actor, P21_ID, p21.state_version, "report_to_ilyan")
    p21 = await missions.advance(actor, P21_ID, p21.state_version, "record_project_hemaris")
    assert p21 is not None and p21.step == 7 and p21.status == "active"
    async with sessions() as session:
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.history.projeto_hemaris_registro_inicial",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.nome_recuperado",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.hortos_vazios",
            )
        ) is None

    choice_version = p21.state_version
    completed = await missions.choose_p21_reward(actor, choice_version, "seal")
    repeated = await missions.choose_p21_reward(actor, choice_version, "mask")
    assert completed is not None and completed.status == "completed"
    assert completed.progress["reward_choice"] == "seal"
    assert repeated is not None and repeated.status == "completed"
    assert repeated.progress["reward_choice"] == "seal"
    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P21_REWARD_SOURCE,
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
        assert {(row.kind, row.quantity) for row in components} == {
            ("xp", 41450), ("crowns", 630), ("equipment", 1)
        }
        equipment = [row for row in components if row.kind == "equipment"]
        assert len(equipment) == 1 and equipment[0].payload["choice"] == "seal"
        item = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key == f"{P21_REWARD_SOURCE}:equipment:seal",
            )
        )
        assert item is not None
        assert (item.item_name, item.rarity, item.slot, item.item_level, item.bound) == (
            "Selo dos Diques", "Raro", "Acessório", 35, True
        )
        assert item.payload["enhancement"] == 0
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P21_REWARD_SOURCE,
            )
        ) == event.id
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.hortos_vazios",
            )
        ) is not None


@pytest.mark.asyncio
async def test_varzeas_p21_shared_objective_credit_is_individual_for_present_group_members(
    database,
):
    leader, helper = 993227, 993228
    leader_id, sessions = await _seed_varzeas_hortos(database, leader)
    helper_id, _ = await _seed_varzeas_hortos(database, helper)
    async with sessions() as session:
        helper_character = await session.get(Character, helper_id)
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invitation = await groups.invite(
        leader, helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        helper,
        invitation.invite_id,
        expected_revision=invitation.revision,
        accept=True,
    )
    missions = VarzeasMissionService(sessions, "ocaso", groups=groups)
    leader_view = await missions.resume(leader, P21_ID)
    helper_view = await missions.resume(helper, P21_ID)
    assert leader_view is not None and leader_view.step == 2
    assert helper_view is not None and helper_view.step == 2

    result = await missions.advance(
        leader, P21_ID, leader_view.state_version, "examine_bed_a"
    )
    assert result is not None and result.step == 2
    async with sessions() as session:
        for character_id in (leader_id, helper_id):
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P21_ID,
                )
            )
            assert quest is not None and quest.progress["beds_examined"] == ["a"]
            assert await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == P21_ID,
                    CampaignObjectiveCredit.objective_id == "p21.examined_bed_a",
                )
            ) is not None


@pytest.mark.asyncio
async def test_varzeas_s21_published_investigation_and_reward_are_idempotent(database):
    blocked_actor = 993226
    blocked_id, blocked_sessions = await _seed_varzeas_hortos(database, blocked_actor)
    async with blocked_sessions.begin() as session:
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == blocked_id,
                Quest.quest_id == P21_ID,
            )
        )
        assert quest is not None
        await session.delete(quest)
    blocked_missions = VarzeasMissionService(blocked_sessions, "ocaso")
    blocked_offer = await blocked_missions.resume(blocked_actor, S21_ID)
    assert blocked_offer is not None and not blocked_offer.available

    actor = 993222
    character_id, sessions = await _seed_varzeas_hortos(database, actor)
    missions = VarzeasMissionService(sessions, "ocaso")

    offer = await missions.resume(actor, S21_ID)
    assert offer is not None and offer.available
    s21 = await missions.start(actor, S21_ID)
    assert s21 is not None and s21.status == "active" and s21.step == 1
    for action, expected_step in (
        ("examine_cultivation_sector", 2),
        ("observe_autonomous_grafts", 3),
        ("analyze_support_function", 4),
    ):
        s21 = await missions.advance(actor, S21_ID, s21.state_version, action)
        assert s21 is not None and s21.step == expected_step
    async with sessions() as session:
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "enxerto_horto",
            )
        ) is not None
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == "enxerto_horto",
                BestiaryEvidence.evidence_id == "first_observation",
            )
        ) is not None

    version = s21.state_version
    completed = await missions.advance(actor, S21_ID, version, "report_to_ilyan")
    repeated = await missions.advance(actor, S21_ID, version, "report_to_ilyan")
    assert completed is not None and completed.status == "completed"
    assert repeated is not None and repeated.status == "completed"
    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S21_REWARD_SOURCE,
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
            ("xp", None, 16580),
            ("crowns", None, 320),
            ("material", "material.varzeas.couro_de_varzea", 2),
        }
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S21_REWARD_SOURCE,
            )
        ) == event.id


@pytest.mark.asyncio
async def test_varzeas_hortos_discovery_gates_and_estufa_codex_are_persistent(
    database, monkeypatch
):
    import asterion.application.road as road_module

    actor_before, actor_after = 993223, 993224
    before_id, before_sessions = await _seed_varzeas_hortos(database, actor_before)
    after_id, after_sessions = await _seed_varzeas_hortos(database, actor_after)
    async with after_sessions.begin() as session:
        session.add(
            CodexEntry(
                character_id=after_id,
                entry_id="codex.history.projeto_hemaris_registro_inicial",
            )
        )

    async def discover_estufa(actor, sessions, character_id, expected_fragment):
        road = RoadService(sessions, "ocaso")
        assert (await road.resume(actor)).explore_enabled
        monkeypatch.setattr(
            road_module,
            "_explore_result",
            lambda *_args, **_kwargs: (
                "great_discovery",
                "explore.varzeas.hortos.estufa_restituicao",
                "Estufa de Restituição descoberta.",
            ),
        )
        view = await road.explore(actor)
        assert view is not None and view.result_id == "explore.varzeas.hortos.estufa_restituicao"
        await road.acknowledge_result(actor, view.attempt_id)
        async with sessions() as session:
            assert await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.fragment_id == expected_fragment,
                )
            ) is not None

    await discover_estufa(
        actor_before,
        before_sessions,
        before_id,
        "codex.fragment.varzeas.hortos.estufa_technical",
    )
    await discover_estufa(
        actor_after,
        after_sessions,
        after_id,
        "codex.fragment.varzeas.hortos.estufa_therapeutic",
    )


@pytest.mark.asyncio
async def test_varzeas_hortos_brazier_and_round_gate_use_local_hunt_settlement(
    database, monkeypatch
):
    import asterion.application.road as road_module
    import asterion.application.round as round_module

    actor = 993225
    character_id, sessions = await _seed_varzeas_hortos(database, actor)
    road = RoadService(sessions, "ocaso")
    rounds = RoundService(sessions, "ocaso")
    local = await road.resume(actor)
    assert local is not None and local.kind == "varzeas_hortos"
    assert local.hunt_enabled and local.explore_enabled
    assert await road.prepare_hunt(actor) is not None
    blocked_round = await rounds.prepare_round(actor, 5)
    assert blocked_round is not None and blocked_round.kind == "varzeas_hortos"
    async with sessions() as session:
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_HORTOS_BRAZIER,
            )
        ) is None

    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.varzeas.hortos.braseiro_horto_seco",
            "Braseiro do Horto Seco descoberto.",
        ),
    )
    discovery = await road.explore(actor)
    assert discovery is not None and discovery.attempt_id is not None
    await road.acknowledge_result(actor, discovery.attempt_id)
    async with sessions() as session:
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_HORTOS_BRAZIER,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id
                == "codex.fragment.varzeas.hortos.braseiro_horto_seco",
            )
        ) is not None

    original_create = road_module.create_road_combat

    def weak_enemy(*args, **kwargs):
        combat = original_create(*args, **kwargs)
        combat.fighters["enemy"].stats = replace(
            combat.fighters["enemy"].stats, attack=1
        )
        return combat

    monkeypatch.setattr(road_module, "create_road_combat", weak_enemy)
    monkeypatch.setattr(round_module, "create_road_combat", weak_enemy)
    monkeypatch.setattr(
        road_module,
        "select_creature",
        lambda *_args, **_kwargs: creature_for("cervo_ferrugem"),
    )
    monkeypatch.setattr(
        round_module,
        "select_creature",
        lambda *_args, **_kwargs: creature_for("cervo_ferrugem"),
    )
    manual = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert manual is not None and manual.kind == "combat"
    activity_id = manual.activity_id
    assert activity_id is not None
    for _ in range(100):
        if manual.kind != "combat":
            break
        actions = allowed_actions(manual.combat)
        action = "art" if "art" in actions else "attack"
        manual = await road.action(actor, activity_id, manual.combat.version, action)
    assert manual is not None and manual.kind == "hunt_victory"
    async with sessions() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity_id)
        )
        assert context is not None and context.creature_id == "cervo_ferrugem"
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_HORTOS_ROUND_FAMILIARITY,
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{activity_id}",
            )
        )
        assert reward is not None
        materials = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == reward.id,
                        RewardComponent.kind == "material",
                    )
                )
            ).all()
        )
        assert {row.item_id for row in materials} <= {
            "material.varzeas.couro_de_varzea"
        }
    await road.acknowledge_result(actor)

    disable_round_pvpve_for_test(rounds)
    preparing = await rounds.prepare_round(actor, 5)
    assert preparing is not None and preparing.kind == "round_prepare"
    active = await rounds.start_round(
        actor, preparing.round_id, preparing.state_version
    )
    assert active is not None and active.kind == "round_active"
    async with sessions.begin() as session:
        state = await session.get(HuntRound, active.round_id)
        assert state is not None
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
    await rounds.advance_due_rounds()
    async with sessions() as session:
        state = await session.get(HuntRound, active.round_id)
        assert state is not None and state.completed_encounters == 1
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == state.id
            )
        )
        assert encounter is not None and encounter.creature_id == "cervo_ferrugem"
        context = await session.scalar(
            select(HuntContext).where(
                HuntContext.game_activity_id == encounter.activity_id
            )
        )
        assert context is not None and context.loot_profile == "round"
        round_reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{encounter.activity_id}",
            )
        )
        assert round_reward is not None
        round_materials = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == round_reward.id,
                        RewardComponent.kind == "material",
                    )
                )
            ).all()
        )
        assert {row.item_id for row in round_materials} <= {
            "material.varzeas.couro_de_varzea"
        }


@pytest.mark.asyncio
async def test_varzeas_p22_and_s22_galleries_progress_rewards_and_codex_are_idempotent(
    database, monkeypatch
):
    import asterion.application.road as road_module
    import asterion.application.scripted_combat as scripted_combat

    actor = 993240
    character_id, sessions = await _seed_varzeas_hortos(
        database,
        actor,
        level=37,
        p21_step=8,
        p21_status="completed",
    )
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")

    # P22 auto-starts from the legitimate P21 completion and level gate.
    p22 = await missions.resume(actor, P22_ID)
    assert p22 is not None and p22.status == "active" and p22.step == 1
    assert await road.travel_route(actor, VARZEAS_GALERIAS) is not None
    await missions.on_location(actor)
    p22 = await missions.resume(actor, P22_ID)
    assert p22 is not None and p22.step == 2
    local = await road.resume(actor)
    assert local is not None and local.location == VARZEAS_GALERIAS
    assert local.hunt_enabled is False and local.explore_enabled is True
    assert await road.prepare_hunt(actor) is None

    p22 = await missions.advance(
        actor, P22_ID, p22.state_version, "register_valves_brazier"
    )
    assert p22 is not None and p22.step == 3
    async with sessions() as session:
        discovery_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id
                == "explore.unique:explore.varzeas.galerias.braseiro_valvulas",
            )
        )
        assert discovery_event is not None
        discovery_xp = await session.scalar(
            select(RewardComponent).where(
                RewardComponent.reward_event_id == discovery_event.id,
                RewardComponent.kind == "xp",
            )
        )
        assert discovery_xp is not None and discovery_xp.quantity == 7896

    excluded_results = {}

    def select_nonrepeat_explore(_seed, _level, _recent, excluded, *, profile):
        excluded_results["ids"] = excluded
        return "linha_retorno"

    monkeypatch.setattr(
        road_module, "select_exploration_result", select_nonrepeat_explore
    )
    exploration = await road.explore(actor)
    assert exploration is not None
    assert "explore.varzeas.galerias.braseiro_valvulas" in excluded_results["ids"]
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id
                == "explore.unique:explore.varzeas.galerias.braseiro_valvulas",
            )
        ) == 1
    acknowledged = await road.acknowledge_result(actor, exploration.attempt_id)
    assert acknowledged is not None and acknowledged.location == VARZEAS_GALERIAS

    p22 = await missions.advance(actor, P22_ID, p22.state_version, "examine_reservoir_a")
    p22 = await missions.advance(actor, P22_ID, p22.state_version, "examine_reservoir_b")
    p22 = await missions.advance(
        actor, P22_ID, p22.state_version, "examine_transport_line"
    )
    assert p22 is not None and p22.step == 4

    encounter = await missions.start_solo_combat(actor, P22_ID, p22.state_version)
    assert encounter is not None and encounter.kind == "combat"
    assert encounter.combat.fighters["enemy"].name == "Vigia Hemaris"
    assert encounter.combat.fighters["enemy"].level == 37
    assert encounter.combat.variant is None
    assert encounter.activity_id is not None
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{encounter.activity_id}",
            )
        ) is None
        assert await session.scalar(
            select(HuntContext.id).where(
                HuntContext.game_activity_id == encounter.activity_id
            )
        ) is None
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "vigia_hemaris",
            )
        ) is not None
    resumed = await missions.resume(actor, P22_ID)
    assert resumed is not None and resumed.activity_id == encounter.activity_id

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await missions.action_combat(
        actor, encounter.activity_id, encounter.combat.version, "attack"
    )
    assert victory is not None and victory.step == 5
    async with sessions() as session:
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == "vigia_hemaris",
                BestiaryEvidence.evidence_id == "first_victory",
            )
        ) is not None

    p22 = await missions.advance(actor, P22_ID, victory.state_version, "recover_transfer_record")
    p22 = await missions.advance(actor, P22_ID, p22.state_version, "compare_hortos_record")
    assert p22 is not None and p22.step == 7
    returned = await road.travel_route(actor, VARZEAS_HORTOS)
    assert returned is not None and returned.location == VARZEAS_HORTOS
    await missions.on_location(actor)
    p22 = await missions.resume(actor, P22_ID)
    version = p22.state_version
    completed = await missions.advance(actor, P22_ID, version, "report_to_ilyan")
    repeated = await missions.advance(actor, P22_ID, version, "report_to_ilyan")
    assert completed is not None and completed.status == "completed"
    assert repeated is not None and repeated.status == "completed"
    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P22_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == event.id
                    )
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 45300),
            ("crowns", None, 830),
            ("material", "material.varzeas.ferro_de_salmoura", 2),
            ("material", "material.varzeas.soro_antigo", 2),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P22_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == VARZEAS_GALERIAS_BRAZIER,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == "codex.location.galerias_transferencia",
                CodexFragment.fragment_id == "codex.fragment.varzeas.galerias.braseiro_valvulas",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == P22_CODEX,
                CodexFragment.fragment_id == P22_FRAGMENT,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_GALERIAS_HUNT_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.transferencia",
            )
        ) is not None

    # The Gallery round remains closed until a valid manual Hunt victory there.
    assert await road.travel_route(actor, VARZEAS_GALERIAS) is not None
    local = await road.resume(actor)
    assert local is not None and local.hunt_enabled is True
    rounds = RoundService(sessions, "ocaso")
    blocked_round = await rounds.prepare_round(actor, 5)
    assert blocked_round is not None and blocked_round.kind == "varzeas_galerias"
    from asterion.domain.road import creature_for

    original_create = road_module.create_road_combat

    def survivable_combat(*args, **kwargs):
        combat = original_create(*args, **kwargs)
        combat.fighters["enemy"].stats = replace(
            combat.fighters["enemy"].stats, attack=1
        )
        return combat

    monkeypatch.setattr(road_module, "create_road_combat", survivable_combat)
    monkeypatch.setattr(
        road_module,
        "select_creature",
        lambda *_args, **_kwargs: creature_for("enxerto_horto"),
    )
    prepared_hunt = await road.prepare_hunt(actor)
    assert prepared_hunt is not None and prepared_hunt.kind == "hunt_prepare"
    manual = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert manual is not None and manual.kind == "combat"
    hunt_activity_id = manual.activity_id
    for _ in range(100):
        if manual.kind != "combat":
            break
        available_actions = allowed_actions(manual.combat)
        action = "art" if "art" in available_actions else "attack"
        manual = await road.action(
            actor, hunt_activity_id, manual.combat.version, action
        )
    assert manual is not None and manual.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_GALERIAS_PROFILE.round_familiarity,
            )
        ) is not None
    round_prepare = await rounds.prepare_round(actor, 5)
    assert round_prepare is not None and round_prepare.kind == "round_prepare"

    # S22 remains an investigation flow and never materializes dungeon loot.
    s22_actor = 993241
    s22_character_id, s22_sessions = await _seed_varzeas_hortos(
        database,
        s22_actor,
        level=37,
        p21_step=8,
        p21_status="completed",
    )
    async with s22_sessions.begin() as session:
        session.add(
            Quest(
                character_id=s22_character_id,
                quest_id=P22_ID,
                title="Transferência",
                status="active",
                step=1,
                content_version="varzeas-1.0.0",
                progress={},
            )
        )
    s22_missions = VarzeasMissionService(s22_sessions, "ocaso")
    async with s22_sessions.begin() as session:
        s22_character = await session.get(Character, s22_character_id)
        assert s22_character is not None
        s22_character.level = 36
    below_level = await s22_missions.start(s22_actor, S22_ID)
    assert below_level is not None and below_level.available is False
    async with s22_sessions.begin() as session:
        s22_character = await session.get(Character, s22_character_id)
        assert s22_character is not None
        s22_character.level = 37
    undiscovered = await s22_missions.start(s22_actor, S22_ID)
    assert undiscovered is not None and undiscovered.available is False
    assert await sessionless_quest(s22_sessions, s22_character_id, S22_ID) is None
    async with s22_sessions.begin() as session:
        session.add(
            Unlock(
                character_id=s22_character_id,
                unlock_id="dungeon.varzeas.enfermaria_afundada.discovered",
            )
        )
    offered = await s22_missions.start(s22_actor, S22_ID)
    assert offered is not None and offered.status == "active" and offered.step == 1
    s22 = await s22_missions.advance(
        s22_actor, S22_ID, offered.state_version, "inspect_automated_routines"
    )
    s22 = await s22_missions.advance(
        s22_actor, S22_ID, s22.state_version, "record_treatment_preparation"
    )
    s22 = await s22_missions.advance(
        s22_actor, S22_ID, s22.state_version, "record_no_valid_patient"
    )
    completed_s22 = await s22_missions.advance(
        s22_actor, S22_ID, s22.state_version, "report_to_ilyan"
    )
    assert completed_s22 is not None and completed_s22.status == "completed"
    async with s22_sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == s22_character_id,
                RewardEvent.source_id == S22_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == event.id
                    )
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 31710),
            ("crowns", None, 500),
            ("material", "material.varzeas.ferro_de_salmoura", 2),
            ("material", "material.varzeas.junco_ferruginoso", 1),
            ("material", "material.varzeas.soro_antigo", 1),
        }
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == s22_character_id,
                CodexFragment.entry_id == S22_CODEX,
                CodexFragment.fragment_id == S22_FRAGMENT,
            )
        ) is not None
        assert await session.scalar(
            select(func.count(DungeonRun.id))
            .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
            .where(
                DungeonRunMember.character_id == s22_character_id
            )
        ) == 0


@pytest.mark.asyncio
async def test_varzeas_p22_reuses_prior_brazier_and_shares_objectives_with_present_group(
    database, monkeypatch
):
    import asterion.application.road as road_module

    prior_actor = 993242
    prior_id, prior_sessions = await _seed_varzeas_hortos(
        database,
        prior_actor,
        level=37,
        p21_step=8,
        p21_status="completed",
    )
    prior_road = RoadService(prior_sessions, "ocaso")
    prior_missions = VarzeasMissionService(prior_sessions, "ocaso")
    p22 = await prior_missions.resume(prior_actor, P22_ID)
    assert p22 is not None and p22.step == 1
    assert await prior_road.travel_route(prior_actor, VARZEAS_GALERIAS) is not None
    await prior_missions.on_location(prior_actor)
    p22 = await prior_missions.resume(prior_actor, P22_ID)
    assert p22 is not None and p22.step == 2
    monkeypatch.setattr(
        road_module,
        "select_exploration_result",
        lambda *_args, **_kwargs: "braseiro_valvulas",
    )
    prior_discovery = await prior_road.explore(prior_actor)
    assert prior_discovery is not None
    p22 = await prior_missions.resume(prior_actor, P22_ID)
    assert p22 is not None and p22.step == 3
    assert p22.progress["brazier_registered"] is True
    async with prior_sessions() as session:
        prior_attempt = await session.scalar(
            select(ExplorationAttempt).where(
                ExplorationAttempt.character_id == prior_id,
                ExplorationAttempt.local_id == VARZEAS_GALERIAS_LOCATION,
            )
        )
        assert prior_attempt is not None
        prior_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == prior_id,
                RewardEvent.source_id == f"explore:{prior_attempt.id}",
            )
        )
        assert prior_event is not None
        prior_xp = await session.scalar(
            select(RewardComponent).where(
                RewardComponent.reward_event_id == prior_event.id,
                RewardComponent.kind == "xp",
            )
        )
        assert prior_xp is not None and prior_xp.quantity == 7896
        assert await session.scalar(
            select(func.count(Brazier.id)).where(
                Brazier.character_id == prior_id,
                Brazier.brazier_id == VARZEAS_GALERIAS_BRAZIER,
            )
        ) == 1
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == prior_id,
                RewardEvent.source_id == P22_REWARD_SOURCE,
            )
        ) is None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == prior_id,
                RewardEvent.source_id
                == "explore.unique:explore.varzeas.galerias.braseiro_valvulas",
            )
        ) is None

    leader, helper = 993243, 993244
    leader_id, sessions = await _seed_varzeas_hortos(
        database,
        leader,
        level=37,
        p21_step=8,
        p21_status="completed",
    )
    helper_id, _ = await _seed_varzeas_hortos(
        database,
        helper,
        level=37,
        p21_step=8,
        p21_status="completed",
    )
    async with sessions() as session:
        helper_character = await session.get(Character, helper_id)
        assert helper_character is not None
        helper_name = helper_character.name
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invitation = await groups.invite(
        leader, helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        helper,
        invitation.invite_id,
        expected_revision=invitation.revision,
        accept=True,
    )
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso", groups=groups)
    p22 = await missions.resume(leader, P22_ID)
    helper_p22 = await missions.resume(helper, P22_ID)
    assert p22 is not None and p22.step == 1
    assert helper_p22 is not None and helper_p22.step == 1
    assert await road.travel_route(leader, VARZEAS_GALERIAS) is not None
    await missions.on_location(leader)
    leader_p22 = await missions.resume(leader, P22_ID)
    helper_p22 = await missions.resume(helper, P22_ID)
    assert leader_p22 is not None and leader_p22.step == 2
    assert helper_p22 is not None and helper_p22.step == 1
    assert await road.travel_route(helper, VARZEAS_GALERIAS) is not None
    await missions.on_location(helper)
    leader_p22 = await missions.resume(leader, P22_ID)
    helper_p22 = await missions.resume(helper, P22_ID)
    assert leader_p22 is not None and leader_p22.step == 2
    assert helper_p22 is not None and helper_p22.step == 2
    result = await missions.advance(
        leader, P22_ID, leader_p22.state_version, "register_valves_brazier"
    )
    assert result is not None and result.step == 3
    async with sessions() as session:
        for member_id in (leader_id, helper_id):
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == member_id,
                    Quest.quest_id == P22_ID,
                )
            )
            assert quest is not None and quest.step == 3
            assert await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == member_id,
                    CampaignObjectiveCredit.quest_id == P22_ID,
                    CampaignObjectiveCredit.objective_id == "p22.registered_brazier",
                )
            ) is not None


@pytest.mark.asyncio
async def test_varzeas_p22_requires_p21_completion_and_level_37(database):
    underlevel_actor = 993245
    underlevel_id, underlevel_sessions = await _seed_varzeas_hortos(
        database,
        underlevel_actor,
        level=36,
        p21_step=8,
        p21_status="completed",
    )
    underlevel = await VarzeasMissionService(
        underlevel_sessions, "ocaso"
    ).resume(underlevel_actor, P22_ID)
    assert underlevel is not None and underlevel.available is False
    assert await sessionless_quest(underlevel_sessions, underlevel_id, P22_ID) is None

    incomplete_actor = 993246
    incomplete_id, incomplete_sessions = await _seed_varzeas_hortos(
        database,
        incomplete_actor,
        level=37,
        p21_step=8,
        p21_status="active",
    )
    incomplete = await VarzeasMissionService(
        incomplete_sessions, "ocaso"
    ).resume(incomplete_actor, P22_ID)
    assert incomplete is not None and incomplete.available is False
    assert await sessionless_quest(incomplete_sessions, incomplete_id, P22_ID) is None


@pytest.mark.asyncio
async def test_varzeas_s22_accepts_completed_p22_when_enfermaria_is_discovered(database):
    actor = 993247
    character_id, sessions = await _seed_varzeas_hortos(
        database,
        actor,
        level=37,
        p21_step=8,
        p21_status="completed",
    )
    async with sessions.begin() as session:
        session.add_all(
            (
                Quest(
                    character_id=character_id,
                    quest_id=P22_ID,
                    title="Transferência",
                    status="completed",
                    step=8,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id="dungeon.varzeas.enfermaria_afundada.discovered",
                ),
            )
        )
    missions = VarzeasMissionService(sessions, "ocaso")
    offer = await missions.resume(actor, S22_ID)
    assert offer is not None and offer.available is True
    started = await missions.start(actor, S22_ID)
    assert started is not None and started.status == "active" and started.step == 1


@pytest.mark.asyncio
async def test_varzeas_p23_completes_without_side_quests_or_dungeon_clears(database):
    actor = 993248
    character_id, sessions = await _seed_varzeas_hortos(
        database,
        actor,
        level=39,
        p21_step=8,
        p21_status="completed",
    )
    async with sessions.begin() as session:
        session.add_all(
            (
                Quest(
                    character_id=character_id,
                    quest_id=P22_ID,
                    title="Transferência",
                    status="completed",
                    step=8,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id=VARZEAS_HORTOS_GALERIAS_ROUTE,
                ),
            )
        )

    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")
    p23 = await missions.resume(actor, P23_ID)
    assert p23 is not None and p23.status == "active" and p23.step == 1
    assert await sessionless_quest(sessions, character_id, S22_ID) is None
    assert await sessionless_quest(sessions, character_id, S23_ID) is None

    p23 = await missions.advance(
        actor, P23_ID, p23.state_version, "gather_hortos_records"
    )
    assert p23 is not None and p23.step == 1
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    p23 = await missions.advance(
        actor, P23_ID, p23.state_version, "investigate_enfermaria_record"
    )
    assert p23 is not None and p23.step == 1
    assert await road.travel_route(actor, VARZEAS_HORTOS) is not None
    assert await road.travel_route(actor, VARZEAS_GALERIAS) is not None
    p23 = await missions.advance(
        actor, P23_ID, p23.state_version, "gather_galerias_records"
    )
    assert p23 is not None and p23.step == 2
    assert await road.travel_route(actor, VARZEAS_CAMARA) is None

    for action, next_step in (
        ("identify_protocol_sequence", 3),
        ("confirm_emergency_coercion", 4),
        ("record_hereditary_changes", 5),
        ("record_modern_hemary_distinction", 6),
        ("open_matrix_access", 7),
    ):
        p23 = await missions.advance(actor, P23_ID, p23.state_version, action)
        assert p23 is not None and p23.step == next_step
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_CAMARA_ACCESS_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VARZEAS_GALERIAS_CAMARA_ROUTE,
            )
        ) is not None
    assert await road.travel_route(actor, VARZEAS_CAMARA) is not None
    camera_view = await road.resume(actor)
    assert camera_view is not None and camera_view.kind == "varzeas_camara"
    assert camera_view.hunt_enabled is False
    assert camera_view.explore_enabled is False
    camera_screen = render_current_local(camera_view)
    assert "Local de clímax" in camera_screen.text
    assert "Terras do Ocaso" not in camera_screen.text
    assert "Nv. 1–10" not in camera_screen.text
    assert "Braseiro" not in camera_screen.text
    camera_callbacks = {
        button.callback_data
        for row in camera_screen.keyboard.inline_keyboard
        for button in row
    }
    assert "road:route:varzeas_galerias" in camera_callbacks
    assert not camera_callbacks.intersection(
        {"road:hunt", "road:explore:start", "world:round"}
    )
    assert await road.travel_route(actor, VARZEAS_GALERIAS) is not None

    version = p23.state_version
    completed = await missions.advance(
        actor, P23_ID, version, "prepare_entry_with_sera_and_ilyan"
    )
    repeated = await missions.advance(
        actor, P23_ID, version, "prepare_entry_with_sera_and_ilyan"
    )
    assert completed is not None and completed.status == "completed"
    assert repeated is not None and repeated.status == "completed"
    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P23_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == event.id
                    )
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 49350),
            ("crowns", None, 860),
            ("material", "material.varzeas.ferro_de_salmoura", 2),
            ("material", "material.varzeas.junco_ferruginoso", 1),
            ("material", "material.varzeas.soro_antigo", 1),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P23_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(func.count(DungeonRun.id))
            .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
            .where(
                DungeonRunMember.character_id == character_id
            )
        ) == 0
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id.in_((S22_ID, S23_ID)),
            )
        ) is None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.persistencia_tem_preco",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.varzeas.p23.custos_emergencia",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.varzeas.p23.origem_ancestral",
            )
        ) is not None


@pytest.mark.asyncio
async def test_varzeas_s23_needs_no_optional_dungeon_and_rewards_once(database):
    actor = 993249
    character_id, sessions = await _seed_varzeas_hortos(
        database,
        actor,
        level=38,
        p21_step=8,
        p21_status="completed",
    )
    async with sessions.begin() as session:
        session.add_all(
            (
                Quest(
                    character_id=character_id,
                    quest_id=P22_ID,
                    title="Transferência",
                    status="completed",
                    step=8,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id=VARZEAS_HORTOS_GALERIAS_ROUTE,
                ),
            )
        )
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    assert await road.travel_route(actor, VARZEAS_PORTO) is not None
    offered = await missions.resume(actor, S23_ID)
    assert offered is not None and offered.available is True
    started = await missions.start(actor, S23_ID)
    assert started is not None and started.status == "active" and started.step == 1
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    assert await road.travel_route(actor, VARZEAS_HORTOS) is not None
    assert await road.travel_route(actor, VARZEAS_GALERIAS) is not None
    for action in (
        "investigate_transfer_lines",
        "identify_emergency_markings",
        "record_progressive_ethical_limits",
    ):
        started = await missions.advance(actor, S23_ID, started.state_version, action)
    assert started is not None and started.step == 4
    assert await road.travel_route(actor, VARZEAS_HORTOS) is not None
    assert await road.travel_route(actor, VARZEAS_BREJOS) is not None
    assert await road.travel_route(actor, VARZEAS_PORTO) is not None
    version = started.state_version
    completed = await missions.advance(actor, S23_ID, version, "report_to_sera")
    repeated = await missions.advance(actor, S23_ID, version, "report_to_sera")
    assert completed is not None and completed.status == "completed"
    assert repeated is not None and repeated.status == "completed"
    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S23_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == event.id
                    )
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 33110),
            ("crowns", None, 500),
            ("material", "material.varzeas.ferro_de_salmoura", 1),
            ("material", "material.varzeas.junco_ferruginoso", 1),
            ("material", "material.varzeas.soro_antigo", 2),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S23_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(func.count(DungeonRun.id))
            .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
            .where(
                DungeonRunMember.character_id == character_id
            )
        ) == 0
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == "codex.history.protocolos_de_emergencia",
                CodexFragment.fragment_id == "codex.fragment.varzeas.s23.protocolos_emergencia",
            )
        ) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "p22_completed"),
    ((37, True), (38, False)),
)
async def test_varzeas_s23_requires_p22_and_level_38(database, level, p22_completed):
    actor = 993300 + level + int(p22_completed)
    character_id, sessions = await _seed_varzeas_hortos(
        database,
        actor,
        level=level,
        p21_step=8,
        p21_status="completed",
    )
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = REGION
        world.location = VARZEAS_PORTO
        if p22_completed:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P22_ID,
                    title="Transferência",
                    status="completed",
                    step=8,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                )
            )
    missions = VarzeasMissionService(sessions, "ocaso")
    offer = await missions.resume(actor, S23_ID)
    assert offer is not None and offer.available is False
    started = await missions.start(actor, S23_ID)
    assert started is not None and started.status is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "p22_completed"),
    ((38, True), (39, False)),
)
async def test_varzeas_p23_requires_p22_and_level_39(database, level, p22_completed):
    actor = 993400 + level + int(p22_completed)
    character_id, sessions = await _seed_varzeas_hortos(
        database,
        actor,
        level=level,
        p21_step=8,
        p21_status="completed",
    )
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = REGION
        world.location = VARZEAS_HORTOS
        if p22_completed:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P22_ID,
                    title="Transferência",
                    status="completed",
                    step=8,
                    content_version="varzeas-1.0.0",
                    progress={"completed": True},
                )
            )
    missions = VarzeasMissionService(sessions, "ocaso")
    view = await missions.resume(actor, P23_ID)
    assert view is not None and view.status is None
    assert await sessionless_quest(sessions, character_id, P23_ID) is None


@pytest.mark.asyncio
async def test_p24_solo_defender_visible_callback_dispatches_and_persists(database):
    from copy import deepcopy

    from asterion.domain.combat import act

    actor = 993608
    outsider = 993609
    character_id, sessions = await _seed_varzeas_p23_endgame(
        database, actor, level=40, location=VARZEAS_CAMARA
    )
    await _seed_varzeas_p23_endgame(
        database, outsider, level=40, location=VARZEAS_CAMARA
    )
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P24_ID,
                title="A Matriz Rubra",
                status="active",
                step=4,
                state_version=3,
                content_version="varzeas-1.0.0",
                progress={},
            )
        )

    missions = VarzeasMissionService(sessions, "ocaso")
    started = await missions.start_solo_combat(actor, P24_ID, 3)
    assert started is not None and started.kind == "combat"
    assert started.combat is not None and started.combat.party_mode
    assert started.campaign_shared is False
    initial_version = started.combat.version
    initial_cursor = started.combat.rng_cursor

    screen = render_varzeas_mission(started)
    defender = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Defender"
    )
    assert len(defender.callback_data.encode("utf-8")) <= 64
    callback = VarzeasSoloCombatCallback.unpack(defender.callback_data)
    assert callback.activity_id == started.activity_id
    assert callback.combat_version == initial_version
    assert class_trial_action_ids(
        started.combat, actor_key="player"
    )[callback.action_index] == "defend"
    assert callback.target == "x"
    expected = act(deepcopy(started.combat), "defend")
    assert expected.version == initial_version + 1

    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(varzeas_missions_router(missions, {}))
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(
            defender.callback_data, actor=actor, update_id=1
        ),
    )

    restarted_missions = VarzeasMissionService(sessions, "ocaso")
    persisted = await restarted_missions.combat_view_for_actor(
        actor, started.activity_id
    )
    assert persisted is not None and persisted.combat is not None
    assert persisted.combat.version == initial_version + 1
    assert persisted.combat.result is None
    assert persisted.combat.rng_cursor == expected.rng_cursor
    assert persisted.combat.rng_cursor >= initial_cursor
    async with sessions() as session:
        activity = await session.get(GameActivity, started.activity_id)
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == P24_ID
            )
        )
        assert activity is not None and activity.state_version == initial_version + 1
        assert quest is not None and quest.step == 4

    # Replaying the original versioned intent only refreshes the public view.
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(
            defender.callback_data, actor=actor, update_id=2
        ),
    )
    repeated = await missions.combat_view_for_actor(actor, started.activity_id)
    assert repeated is not None and repeated.combat is not None
    assert repeated.combat.version == persisted.combat.version
    assert repeated.combat.rng_cursor == persisted.combat.rng_cursor

    # A different character cannot use the owner's callback.
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(
            defender.callback_data, actor=outsider, update_id=3
        ),
    )
    unauthorized = await missions.combat_view_for_actor(actor, started.activity_id)
    assert unauthorized is not None and unauthorized.combat is not None
    assert unauthorized.combat.version == persisted.combat.version

    # The shared-only cc: route remains strict for a Solo activity.
    cc_callback = CampaignCombatCallback.for_intent(
        started.activity_id,
        unauthorized.combat.version,
        0,
        "x",
    ).pack()
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(cc_callback, actor=actor, update_id=4),
    )
    after_cc = await missions.combat_view_for_actor(actor, started.activity_id)
    assert after_cc is not None and after_cc.combat is not None
    assert after_cc.combat.version == persisted.combat.version
    assert after_cc.combat.rng_cursor == persisted.combat.rng_cursor

    # A prepared transfer window still renders and dispatches through its
    # dedicated public reservoir callback, without changing combat version.
    from asterion.infrastructure.db.combat_codec import decode, encode

    async with sessions.begin() as session:
        record = await session.get(CombatRecord, started.combat.id)
        activity = await session.get(GameActivity, started.activity_id)
        assert record is not None and activity is not None
        transfer_window = decode(
            record.snapshot,
            record.id,
            activity.ruleset_version,
            activity.state_version,
        )
        transfer_window.prepared_action = "transferencia_externa"
        window_id = (
            f"{started.combat.id.hex}:1:2:enemy:transferencia_externa:prepared"
        )
        transfer_window.prepared_action_instance_id = window_id
        record.snapshot = encode(transfer_window)
    window_view = await missions.combat_view_for_actor(actor, started.activity_id)
    assert window_view is not None and window_view.combat is not None
    window_screen = render_varzeas_mission(window_view)
    reservoir_button = next(
        button
        for row in window_screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Resolver Reservatório A"
    )
    assert reservoir_button.callback_data == (
        f"varzeas:reservoir:{started.activity_id.hex}:"
        f"{window_view.combat.version}:a"
    )
    await asyncio.gather(
        dispatcher.feed_raw_update(
            bot,
            _callback_update(
                reservoir_button.callback_data, actor=actor, update_id=6
            ),
        ),
        dispatcher.feed_raw_update(
            bot,
            _callback_update(
                reservoir_button.callback_data, actor=actor, update_id=7
            ),
        ),
    )
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(reservoir_button.callback_data, actor=actor, update_id=8),
    )
    after_reservoir = await missions.combat_view_for_actor(actor, started.activity_id)
    assert after_reservoir is not None and after_reservoir.combat is not None
    assert after_reservoir.combat.version == window_view.combat.version
    assert after_reservoir.progress["reservoirs_used"] == ["a"]
    assert after_reservoir.progress["reservoir_window_results"] == {
        window_id: {
            "reservoir_id": "a",
            "state": "resolved",
            "consumed": True,
        }
    }
    async with sessions() as session:
        credits = list(
            (
                await session.scalars(
                    select(CampaignObjectiveCredit).where(
                        CampaignObjectiveCredit.character_id == character_id,
                        CampaignObjectiveCredit.quest_id == P24_ID,
                        CampaignObjectiveCredit.objective_id
                        == "p24.reservoir_window_recorded",
                    )
                )
            ).all()
        )
    assert len(f"p24.reservoir_window:{character_id}:{window_id}") > 128
    assert len(credits) == 1
    assert len(credits[0].source_key) <= 128
    assert credits[0].source_key == missions._matrix_reservoir_credit_source_key(
        character_id, window_id
    )
    assert len(credits[0].source_key) == 74

    # A different actor cannot consume the owner's contextual callback.
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(
            reservoir_button.callback_data, actor=outsider, update_id=9
        ),
    )
    still_once = await missions.combat_view_for_actor(actor, started.activity_id)
    assert still_once is not None and still_once.combat is not None
    assert still_once.progress["reservoirs_used"] == ["a"]
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(CampaignObjectiveCredit.id)).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == P24_ID,
                CampaignObjectiveCredit.objective_id
                == "p24.reservoir_window_recorded",
            )
        ) == 1


@pytest.mark.parametrize("heal_case", ["full_amount", "capped_by_missing_hp"])
@pytest.mark.asyncio
async def test_p24_varzeas_heal_uses_public_menu_dispatcher_and_postgres(
    database, heal_case
):
    actor = 993618 if heal_case == "full_amount" else 993619
    outsider = actor + 100
    item_id = "consumable.heal.varzeas.iv"
    character_id, sessions = await _seed_varzeas_p23_endgame(
        database, actor, level=40, location=VARZEAS_CAMARA
    )
    await _seed_varzeas_p23_endgame(
        database, outsider, level=40, location=VARZEAS_CAMARA
    )
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P24_ID,
                title="A Matriz Rubra",
                status="active",
                step=4,
                state_version=3,
                content_version="varzeas-1.0.0",
                progress={},
            )
        )
        session.add(
            ConsumableStack(
                character_id=character_id,
                consumable_id=item_id,
                quantity=1,
            )
        )

    missions = VarzeasMissionService(sessions, "ocaso")
    started = await missions.start_solo_combat(actor, P24_ID, 3)
    assert started is not None and started.kind == "combat"
    assert started.combat is not None
    assert started.consumable_budget_limit == 3

    # Prepare the isolated integration fixture with the character and combat
    # records consistently damaged. All menu, action, and persistence behavior
    # below uses the public bot dispatcher and transaction services.
    combat_max = started.combat.fighters["player"].stats.hp
    nominal_heal = (combat_max * Decimal("0.22")).to_integral_value(
        rounding=ROUND_FLOOR
    )
    missing_hp = (
        nominal_heal + Decimal("17")
        if heal_case == "full_amount"
        else nominal_heal - Decimal("7")
    )
    expected_heal = min(nominal_heal, missing_hp)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        activity = await session.get(GameActivity, started.activity_id)
        record = await session.get(CombatRecord, started.combat.id)
        assert character is not None and activity is not None and record is not None
        combat = decode(
            record.snapshot,
            record.id,
            activity.ruleset_version,
            activity.state_version,
        )
        combat.fighters["player"].hp = combat_max - missing_hp
        character.hp = combat.fighters["player"].hp
        record.snapshot = encode(combat)

    damaged = await missions.combat_view_for_actor(actor, started.activity_id)
    assert damaged is not None and damaged.combat is not None
    assert any(option.item_id == item_id for option in damaged.consumable_options)
    hud = render_varzeas_mission(damaged)
    assert hud.keyboard is not None
    open_button = next(
        button
        for row in hud.keyboard.inline_keyboard
        for button in row
        if button.text == "Consumível"
    )

    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(varzeas_missions_router(missions, {}))
    await dispatcher.feed_raw_update(
        bot, _callback_update(open_button.callback_data, actor=actor, update_id=101)
    )
    menu_edits = [
        call.args[1]
        for call in bot.session.make_request.call_args_list
        if len(call.args) > 1 and isinstance(call.args[1], EditMessageText)
    ]
    assert menu_edits
    menu = menu_edits[-1]
    assert "Poção de Cura da Salmoura" in menu.text
    item_button = next(
        button
        for row in menu.reply_markup.inline_keyboard
        for button in row
        if button.text == "1"
    )
    item_callback = CombatConsumableFlowCallback.unpack(item_button.callback_data)
    assert item_callback.item_id == item_id
    assert len(item_button.callback_data.encode("utf-8")) <= 64

    before = await missions.combat_view_for_actor(actor, started.activity_id)
    assert before is not None and before.combat is not None
    before_version = before.combat.version
    before_cursor = before.combat.rng_cursor
    expected = use_combat_consumable(
        deepcopy(before.combat),
        item_id,
        target_id="player",
        budget_limit=before.consumable_budget_limit,
    )

    # Unknown item tokens and a valid callback from another character cannot
    # consume stock or advance the persisted combat.
    invalid_callback = CombatConsumableFlowCallback(
        activity=item_callback.activity,
        version=item_callback.version,
        step="i",
        item="?",
        target="-",
        effect="-",
        parent="i",
    ).pack()
    await dispatcher.feed_raw_update(
        bot, _callback_update(invalid_callback, actor=actor, update_id=102)
    )
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(item_button.callback_data, actor=outsider, update_id=103),
    )
    unchanged = await missions.combat_view_for_actor(actor, started.activity_id)
    assert unchanged is not None and unchanged.combat is not None
    assert unchanged.combat.version == before_version
    async with sessions() as session:
        stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == item_id,
            )
        )
        assert stack is not None and stack.quantity == 1

    await dispatcher.feed_raw_update(
        bot,
        _callback_update(item_button.callback_data, actor=actor, update_id=104),
    )
    restarted = VarzeasMissionService(sessions, "ocaso")
    persisted = await restarted.combat_view_for_actor(actor, started.activity_id)
    assert persisted is not None and persisted.combat is not None
    assert persisted.combat.version == before_version + 1
    assert persisted.combat.round == expected.round
    assert persisted.combat.rng_cursor == expected.rng_cursor
    assert persisted.combat.rng_cursor >= before_cursor
    assert persisted.combat.consumable_uses == 1
    assert persisted.combat.fighters["player"].cooldowns["consumable"] == (
        before.combat.fighters["player"].opportunity + 2
    )
    heal_events = [
        event
        for event in persisted.combat.events
        if event.action == f"consumable:{item_id}"
    ]
    assert len(heal_events) == 1
    assert heal_events[0].healed == expected_heal
    assert persisted.combat.fighters["player"].hp == expected.fighters["player"].hp
    async with sessions() as session:
        stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == item_id,
            )
        )
        activity = await session.get(GameActivity, started.activity_id)
        character = await session.get(Character, character_id)
        assert stack is not None and stack.quantity == 0
        assert activity is not None and activity.state_version == persisted.combat.version
        assert character is not None
        assert character.hp == persisted.combat.fighters["player"].hp

    # Reusing the original versioned selection is stale and must not heal or
    # consume again after application-service reconstruction.
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(item_button.callback_data, actor=actor, update_id=105),
    )
    final = await VarzeasMissionService(sessions, "ocaso").combat_view_for_actor(
        actor, started.activity_id
    )
    assert final is not None and final.combat is not None
    assert final.combat.version == persisted.combat.version
    assert final.combat.rng_cursor == persisted.combat.rng_cursor
    assert sum(
        event.action == f"consumable:{item_id}" for event in final.combat.events
    ) == 1
    async with sessions() as session:
        quantity = await session.scalar(
            select(ConsumableStack.quantity).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == item_id,
            )
        )
        assert quantity == 0


@pytest.mark.asyncio
async def test_varzeas_shared_boss_callback_remains_cc_and_dispatches(database):
    leader, helper = 993606, 993607
    leader_id, sessions = await _seed_varzeas_p23_endgame(
        database, leader, level=40, location=VARZEAS_CAMARA
    )
    helper_id, _ = await _seed_varzeas_p23_endgame(
        database, helper, level=40, location=VARZEAS_CAMARA
    )
    async with sessions.begin() as session:
        for character_id in (leader_id, helper_id):
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P24_ID,
                    title="A Matriz Rubra",
                    status="active",
                    step=4,
                    state_version=1,
                    content_version="varzeas-1.0.0",
                    progress={},
                )
            )
        helper_character = await session.get(Character, helper_id)
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invite = await groups.invite(
        leader, helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        helper, invite.invite_id, expected_revision=invite.revision, accept=True
    )
    missions = VarzeasMissionService(sessions, "ocaso", groups=groups)
    proposal_view = await missions.propose_group_combat(leader, P24_ID, 1)
    assert proposal_view is not None and proposal_view.proposal_id is not None
    proposal = await groups.activity_proposal(leader, proposal_view.proposal_id)
    accepted = await groups.respond_activity(
        helper,
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
    )
    started = await missions.start_group_combat(
        leader, proposal.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None
    assert started.group_size == 2 and started.campaign_shared is True
    assert started.encounter_id is not None

    active_key = active_player_key(started.combat)
    assert active_key is not None
    async with sessions() as session:
        active_actor = await session.scalar(
            select(Character.telegram_id)
            .join(
                CampaignSharedEncounterMember,
                CampaignSharedEncounterMember.character_id == Character.id,
            )
            .where(
                CampaignSharedEncounterMember.shared_encounter_id
                == started.encounter_id,
                CampaignSharedEncounterMember.actor_key == active_key,
            )
        )
    assert active_actor is not None
    active_view = await missions.combat_view_for_actor(
        active_actor, started.activity_id
    )
    assert active_view is not None and active_view.combat is not None
    assert active_view.combat_actor_key == active_key

    screen = render_varzeas_mission(active_view)
    defender = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Defender"
    )
    assert defender.callback_data.startswith("cc:")
    callback = CampaignCombatCallback.unpack(defender.callback_data)
    assert callback.activity_id == active_view.activity_id
    assert callback.combat_version == active_view.combat.version

    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(varzeas_missions_router(missions, {}))
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(defender.callback_data, actor=active_actor, update_id=5),
    )
    updated = await missions.combat_view_for_actor(
        active_actor, active_view.activity_id
    )
    assert updated is not None and updated.combat is not None
    assert updated.combat.version == active_view.combat.version + 1
    assert updated.campaign_shared is True


@pytest.mark.asyncio
async def test_varzeas_p24_autostarts_at_level_40_without_optional_quests_or_dungeons(database):
    actor = 993610
    character_id, sessions = await _seed_varzeas_p23_endgame(
        database,
        actor,
        level=39,
        location=VARZEAS_CAMARA,
    )
    missions = VarzeasMissionService(sessions, "ocaso")
    below_gate = await missions.resume(actor, P24_ID)
    assert below_gate is not None and below_gate.kind == "unavailable"
    assert await sessionless_quest(sessions, character_id, P24_ID) is None

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 40
    started = await missions.resume(actor, P24_ID)
    assert started is not None and started.status == "active" and started.step == 2

    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id.in_((S22_ID, S23_ID, S24_ID)),
            )
        ) is None
        assert await session.scalar(
            select(func.count(DungeonRun.id))
            .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
            .where(
                DungeonRunMember.character_id == character_id
            )
        ) == 0
        assert await session.scalar(
            select(Quest.status).where(
                Quest.character_id == character_id,
                Quest.quest_id == P23_ID,
            )
        ) == "completed"


@pytest.mark.asyncio
async def test_matrix_reservoir_success_and_omission_are_persisted_once_without_rewards(database):
    actor = 993613
    character_id, sessions = await _seed_varzeas_p23_endgame(
        database,
        actor,
        level=40,
        location=VARZEAS_CAMARA,
    )
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P24_ID,
                title="A Matriz Rubra",
                status="active",
                step=4,
                state_version=1,
                content_version="varzeas-1.0.0",
                progress={},
            )
        )
    missions = VarzeasMissionService(sessions, "ocaso")
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        initial_economy = (character.xp, character.crowns)
    success_window_id = (
        "a" * 32 + ":0:2:enemy:transferencia_externa:prepared"
    )
    failed_window_id = (
        "b" * 32 + ":1:5:enemy:transferencia_externa:prepared"
    )
    third_window_id = (
        "c" * 32 + ":2:8:enemy:transferencia_externa:prepared"
    )
    fourth_window_id = (
        "d" * 32 + ":3:11:enemy:transferencia_externa:prepared"
    )
    success_window = SimpleNamespace(
        action="transferencia_externa",
        prepared_resolution=True,
        prepared_action_instance_id=success_window_id,
    )
    failed_window = SimpleNamespace(
        action="transferencia_externa",
        prepared_resolution=True,
        prepared_action_instance_id=failed_window_id,
    )
    third_window = SimpleNamespace(
        action="transferencia_externa",
        prepared_resolution=True,
        prepared_action_instance_id=third_window_id,
    )
    fourth_window = SimpleNamespace(
        action="transferencia_externa",
        prepared_resolution=True,
        prepared_action_instance_id=fourth_window_id,
    )
    success_key = missions._matrix_reservoir_credit_source_key(
        character_id, success_window_id
    )
    assert success_key == missions._matrix_reservoir_credit_source_key(
        character_id, success_window_id
    )
    assert success_key != missions._matrix_reservoir_credit_source_key(
        character_id, failed_window_id
    )
    assert success_key != missions._matrix_reservoir_credit_source_key(
        uuid4(), success_window_id
    )
    assert len(success_key) == 74
    assert all(
        len(f"p24.reservoir_window:{character_id}:{window_id}") > 128
        for window_id in (
            success_window_id,
            failed_window_id,
            third_window_id,
            fourth_window_id,
        )
    )

    async with sessions.begin() as session:
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == P24_ID,
            ).with_for_update()
        )
        assert quest is not None
        await missions._save_reservoir_resolution(
            session,
            character_id,
            quest,
            success_window_id,
            "a",
            outcome="resolved",
        )
        # A stale duplicate callback cannot create a second result.
        await missions._save_reservoir_resolution(
            session,
            character_id,
            quest,
            "transfer-window-success",
            "a",
            outcome="resolved",
        )
        # The attack occurrence preserves a previously successful result.
        await missions._record_matrix_reservoir_failures(
            session,
            character_id,
            quest,
            SimpleNamespace(events=[]),
            SimpleNamespace(events=[success_window]),
        )
        await missions._record_matrix_reservoir_failures(
            session,
            character_id,
            quest,
            SimpleNamespace(events=[success_window]),
            SimpleNamespace(events=[success_window, failed_window]),
        )
        # Reprocessing the same event is idempotent.
        await missions._record_matrix_reservoir_failures(
            session,
            character_id,
            quest,
            SimpleNamespace(events=[success_window]),
            SimpleNamespace(events=[success_window, failed_window]),
        )
        await missions._record_matrix_reservoir_failures(
            session,
            character_id,
            quest,
            SimpleNamespace(events=[success_window, failed_window]),
            SimpleNamespace(events=[success_window, failed_window, third_window]),
        )
        await missions._record_matrix_reservoir_failures(
            session,
            character_id,
            quest,
            SimpleNamespace(events=[success_window, failed_window, third_window]),
            SimpleNamespace(events=[success_window, failed_window, third_window, fourth_window]),
        )

        assert quest.progress["reservoirs_used"] == ["a", "b", "c"]
        assert quest.progress["resolved_transfer_windows"] == [
            success_window_id,
        ]
        assert quest.progress["recorded_transfer_windows"] == [
            success_window_id,
            failed_window_id,
            third_window_id,
        ]
        assert quest.progress["failed_transfer_windows"] == [
            failed_window_id,
            third_window_id,
        ]
        assert quest.progress["reservoir_window_results"] == {
            success_window_id: {
                "reservoir_id": "a",
                "state": "resolved",
                "consumed": True,
            },
            failed_window_id: {
                "reservoir_id": "b",
                "state": "failed",
                "consumed": True,
            },
            third_window_id: {
                "reservoir_id": "c",
                "state": "failed",
                "consumed": True,
            },
        }

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.xp, character.crowns) == initial_economy
        credits = list(
            (
                await session.scalars(
                    select(CampaignObjectiveCredit).where(
                        CampaignObjectiveCredit.character_id == character_id,
                        CampaignObjectiveCredit.quest_id == P24_ID,
                        CampaignObjectiveCredit.objective_id
                        == "p24.reservoir_window_recorded",
                    )
                )
            ).all()
        )
        assert {
            (
                row.evidence["window_id"],
                row.evidence["reservoir"],
                row.evidence["outcome"],
                row.evidence["reservoir_state"],
            )
            for row in credits
        } == {
            (success_window_id, "a", "resolved", "consumed"),
            (failed_window_id, "b", "failed", "consumed"),
            (third_window_id, "c", "failed", "consumed"),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id.in_(
                    (P24_REWARD_SOURCE, "p24.matriz_rubra.first_victory.core")
                ),
            )
        ) == 0
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == "matriz_rubra",
            )
        ) is None


@pytest.mark.asyncio
async def test_matrix_failed_reservoir_window_is_persisted_by_public_combat_callback(
    database,
):
    actor = 993614
    character_id, sessions = await _seed_varzeas_p23_endgame(
        database, actor, level=40, location=VARZEAS_CAMARA
    )
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P24_ID,
                title="A Matriz Rubra",
                status="active",
                step=4,
                state_version=1,
                content_version="varzeas-1.0.0",
                progress={},
            )
        )
    missions = VarzeasMissionService(sessions, "ocaso")
    view = await missions.start_solo_combat(actor, P24_ID, 1)
    assert view is not None and view.combat is not None
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(varzeas_missions_router(missions, {}))

    reservoir_button = None
    screen = render_varzeas_mission(view)
    for update_id in range(30, 38):
        buttons = [
            button
            for row in screen.keyboard.inline_keyboard
            for button in row
        ]
        reservoir_button = next(
            (
                button
                for button in buttons
                if button.text == "Resolver Reservatório A"
                and (button.callback_data or "").startswith("varzeas:reservoir:")
            ),
            None,
        )
        if reservoir_button is not None:
            break
        action_button = next(
            (
                button
                for button in buttons
                if button.text == "Atacar"
                and (button.callback_data or "").startswith("vsc:")
            ),
            None,
        )
        if action_button is None:
            action_button = next(
                (
                    button
                    for button in buttons
                    if button.text == "Defender"
                    and (button.callback_data or "").startswith("vsc:")
                ),
                None,
            )
        assert action_button is not None
        await dispatcher.feed_raw_update(
            bot,
            _callback_update(
                action_button.callback_data,
                actor=actor,
                update_id=update_id,
            ),
        )
        view = await missions.combat_view_for_actor(actor, view.activity_id)
        assert view is not None and view.combat is not None
        assert view.combat.result is None
        screen = render_varzeas_mission(view)
    assert reservoir_button is not None
    assert view.combat.prepared_action == "transferencia_externa"
    window_id = view.combat.prepared_action_instance_id
    assert window_id
    before_version = view.combat.version
    assert view.progress.get("reservoirs_used", []) == []

    # Leave the contextual button untouched; the public combat action advances
    # the announced telegraph and records the normal failed-window outcome.
    defender = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Defender"
        and (button.callback_data or "").startswith("vsc:")
    )
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(defender.callback_data, actor=actor, update_id=38),
    )
    after = await missions.combat_view_for_actor(actor, view.activity_id)
    assert after is not None and after.combat is not None
    assert after.combat.version == before_version + 1
    assert after.combat.result is None
    assert (
        after.combat.fighters["player"].hp
        < view.combat.fighters["player"].hp
    )
    assert after.progress["reservoirs_used"] == ["a"]
    assert after.progress["failed_transfer_windows"] == [window_id]
    assert after.progress["reservoir_window_results"][window_id] == {
        "reservoir_id": "a",
        "state": "failed",
        "consumed": True,
    }
    resolution = next(
        event
        for event in after.combat.events
        if event.prepared_resolution and event.action == "transferencia_externa"
    )
    assert resolution.prepared_action_instance_id == window_id
    assert resolution.damage > 0

    async with sessions() as session:
        credits = list(
            (
                await session.scalars(
                    select(CampaignObjectiveCredit).where(
                        CampaignObjectiveCredit.character_id == character_id,
                        CampaignObjectiveCredit.quest_id == P24_ID,
                        CampaignObjectiveCredit.objective_id
                        == "p24.reservoir_window_recorded",
                    )
                )
            ).all()
        )
        assert len(credits) == 1
        assert credits[0].evidence["window_id"] == window_id
        assert credits[0].evidence["outcome"] == "failed"
        assert credits[0].source_key == missions._matrix_reservoir_credit_source_key(
            character_id, window_id
        )
        assert len(credits[0].source_key) <= 128
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id.in_(
                    (P24_REWARD_SOURCE, "p24.matriz_rubra.first_victory.core")
                ),
            )
        ) == 0

    # Replayed stale action and service reconstruction preserve exactly one result.
    await dispatcher.feed_raw_update(
        bot,
        _callback_update(defender.callback_data, actor=actor, update_id=39),
    )
    restarted = VarzeasMissionService(sessions, "ocaso")
    persisted = await restarted.combat_view_for_actor(actor, view.activity_id)
    assert persisted is not None and persisted.combat is not None
    assert persisted.combat.version == after.combat.version
    assert persisted.progress["failed_transfer_windows"] == [window_id]
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(CampaignObjectiveCredit.id)).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == P24_ID,
                CampaignObjectiveCredit.objective_id
                == "p24.reservoir_window_recorded",
            )
        ) == 1


@pytest.mark.asyncio
async def test_matrix_reservoir_credit_and_progress_roll_back_together(database):
    actor = 993615
    character_id, sessions = await _seed_varzeas_p23_endgame(
        database, actor, level=40, location=VARZEAS_CAMARA
    )
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P24_ID,
                title="A Matriz Rubra",
                status="active",
                step=4,
                state_version=1,
                content_version="varzeas-1.0.0",
                progress={},
            )
        )
    missions = VarzeasMissionService(sessions, "ocaso")
    window_id = (
        "e" * 32 + ":1:7:enemy:transferencia_externa:prepared"
    )

    with pytest.raises(RuntimeError, match="rollback reservoir credit"):
        async with sessions.begin() as session:
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P24_ID,
                ).with_for_update()
            )
            assert quest is not None
            await missions._save_reservoir_resolution(
                session,
                character_id,
                quest,
                window_id,
                "a",
                outcome="resolved",
            )
            raise RuntimeError("rollback reservoir credit")

    async with sessions() as session:
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == P24_ID,
            )
        )
        assert quest is not None
        assert quest.progress == {}
        assert quest.state_version == 1
        assert await session.scalar(
            select(func.count(CampaignObjectiveCredit.id)).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == P24_ID,
                CampaignObjectiveCredit.objective_id
                == "p24.reservoir_window_recorded",
            )
        ) == 0


@pytest.mark.asyncio
async def test_varzeas_p24_choice_reward_and_matrix_core_are_individual_and_idempotent(database):
    actor = 993611
    character_id, sessions = await _seed_varzeas_p23_endgame(
        database,
        actor,
        level=40,
        location=VARZEAS_CAMARA,
    )
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P24_ID,
                title="A Matriz Rubra",
                status="active",
                step=7,
                state_version=4,
                content_version="varzeas-1.0.0",
                progress={"reservoirs_used": ["a"], "resolved_transfer_windows": []},
            )
        )
    missions = VarzeasMissionService(sessions, "ocaso")

    chosen = await missions.choose_p24_reward(actor, 4, "guard")
    stale_choice = await missions.choose_p24_reward(actor, 4, "seal")
    assert chosen is not None and chosen.step == 8 and chosen.progress["reward_choice"] == "guard"
    assert stale_choice is not None and stale_choice.step == 8
    assert stale_choice.progress["reward_choice"] == "guard"

    completed = await missions.advance(actor, P24_ID, 5, "complete_climax")
    stale_complete = await missions.advance(actor, P24_ID, 5, "complete_climax")
    assert completed is not None and completed.status == "completed"
    assert stale_complete is not None and stale_complete.status == "completed"

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        await missions._grant_matrix_core(session, character)
        await missions._grant_matrix_core(session, character)

    async with sessions() as session:
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P24_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == reward.id
                    )
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 92520),
            ("crowns", None, 1400),
            ("equipment", None, 1),
            ("material", "material.varzeas.ferro_de_salmoura", 4),
            ("material", "material.varzeas.soro_antigo", 4),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P24_REWARD_SOURCE,
            )
        ) == 1
        core_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == "p24.matriz_rubra.first_victory.core",
            )
        )
        assert core_event is not None
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == "p24.matriz_rubra.first_victory.core",
            )
        ) == 1
        equipment = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key == f"{P24_REWARD_SOURCE}:equipment:guard",
            )
        )
        assert equipment is not None
        assert (equipment.item_name, equipment.rarity, equipment.slot, equipment.item_level) == (
            "Guarda de Transferência", "Épico", "Secundária", 40
        )
        assert equipment.bound is True
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "recipe.varzeas.matriz.regulacao",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.matriz_silenciada",
            )
        ) is not None


@pytest.mark.asyncio
async def test_varzeas_s24_can_complete_before_p24_and_rewards_once(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 993612
    character_id, sessions = await _seed_varzeas_p23_endgame(
        database,
        actor,
        level=40,
        location=VARZEAS_HORTOS,
        s22_completed=True,
    )
    road = RoadService(sessions, "ocaso")
    missions = VarzeasMissionService(sessions, "ocaso")
    offer = await missions.resume(actor, S24_ID)
    assert offer is not None and offer.available is True
    started = await missions.start(actor, S24_ID)
    assert started is not None and started.status == "active"

    async with sessions.begin() as session:
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == S24_ID,
            )
        )
        assert quest is not None
        quest.step = 6
        quest.state_version = 8
        quest.progress = {
            "dique_record": True,
            "hortos_record": True,
            "galerias_record": True,
            "containment_context_confirmed": True,
            "safe_route_reconstructed": True,
        }
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id=VARZEAS_HORTOS_GALERIAS_ROUTE,
            )
        )

    arrived = await road.travel_route(actor, VARZEAS_GALERIAS)
    assert arrived is not None and arrived.location == VARZEAS_GALERIAS
    opened = await missions.advance(actor, S24_ID, 8, "open_quarantine_door")
    assert opened is not None and opened.step == 7

    encounter = await missions.start_solo_combat(actor, S24_ID, opened.state_version)
    assert encounter is not None and encounter.kind == "combat"
    assert encounter.combat.fighters["enemy"].name == "Custódio de Quarentena"
    assert encounter.combat.fighters["enemy"].level == 40
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await missions.action_combat(
        actor, encounter.activity_id, encounter.combat.version, "attack"
    )
    assert victory is not None and victory.step == 8

    observed = await missions.advance(
        actor, S24_ID, victory.state_version, "record_observed_facts"
    )
    assert observed is not None and observed.step == 9
    returned = await road.travel_route(actor, VARZEAS_HORTOS)
    assert returned is not None and returned.location == VARZEAS_HORTOS

    completed = await missions.advance(
        actor, S24_ID, observed.state_version, "conclude_with_ilyan"
    )
    repeated = await missions.advance(
        actor, S24_ID, observed.state_version, "conclude_with_ilyan"
    )
    assert completed is not None and completed.status == "completed"
    assert repeated is not None and repeated.status == "completed"

    async with sessions() as session:
        assert await session.scalar(
            select(Quest.status).where(
                Quest.character_id == character_id,
                Quest.quest_id == P24_ID,
            )
        ) == "active"
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S24_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == event.id
                    )
                )
            ).all()
        )
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 51400),
            ("crowns", None, 880),
            ("material", "material.varzeas.ferro_de_salmoura", 2),
            ("material", "material.varzeas.couro_de_varzea", 2),
            ("material", "material.varzeas.junco_ferruginoso", 2),
            ("material", "material.varzeas.soro_antigo", 2),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S24_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.varzeas.quarentena_encerrada",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == "codex.mystery.quarentena_sem_supervisao",
                CodexFragment.fragment_id == "codex.fragment.varzeas.s24.quarentena_sem_supervisao",
            )
        ) is not None
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == "custodio_quarentena",
                BestiaryEvidence.evidence_id == "s24_observed_facts",
            )
        ) is not None
        assert await session.scalar(
            select(func.count(DungeonRun.id))
            .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
            .where(
                DungeonRunMember.character_id == character_id
            )
        ) == 0
