from collections import Counter
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import (
    P25_CONTENT_VERSION,
    P25_ID,
    P26_ID,
    P26_MISSION_ID,
    P26_TITLE,
    AltosMissionService,
    AltosMissionView,
)
from asterion.application.groups import GroupService
from asterion.application.knowledge_catalog import CODEX_BY_ID, CODEX_FRAGMENTS
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_ESCARPA_LABEL,
    ALTOS_PONTES_LABEL,
    ALTOS_REGION_LABEL,
)
from asterion.application.round import RoundService
from asterion.bot.altos_missions_ui import render_altos_mission
from asterion.domain.road import (
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_ABRIGO_BRAZIER,
    ALTOS_ABRIGO_LOCATION,
    ALTOS_DEVORADOR_ESCORIA,
    ALTOS_ESCARPA_ACCESS_UNLOCK,
    ALTOS_ESCARPA_BRAZIER,
    ALTOS_ESCARPA_EXPLORE_UNLOCK,
    ALTOS_ESCARPA_HUNT_UNLOCK,
    ALTOS_ESCARPA_LOCATION,
    ALTOS_ESCARPA_ROUND_UNLOCK,
    ALTOS_LAGARTO_ESCORIA,
    ALTOS_PONTES_ACCESS_UNLOCK,
    ALTOS_PONTES_BRAZIER,
    ALTOS_PONTES_EXPLORATION_PROFILE,
    ALTOS_PONTES_EXPLORE_UNLOCK,
    ALTOS_PONTES_HUNT_UNLOCK,
    ALTOS_PONTES_LOCATION,
    ALTOS_PONTES_PROFILE,
    ALTOS_PONTES_ROUND_UNLOCK,
    ALTOS_QUEBRA_CABOS,
    EXPLORATION_CATEGORY_WEIGHTS,
    EXPLORATION_PROFILES,
    MATERIAL_POOLS,
    VARIANT_POOL,
    creature_for,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import disable_round_pvpve_for_test, start_manual_hunt_after_no_match
from tests.test_altos_opening import _seed_altos_exit
from tests.test_s4_s5_integration import _terminal


def test_p26_ui_exposes_the_giver_and_only_the_current_step_actions():
    def render(status, step, *, progress=None, location=ALTOS_ABRIGO_LABEL):
        return render_altos_mission(
            AltosMissionView(
                character_id=uuid4(),
                quest_id=P26_ID,
                title=P26_TITLE,
                kind="mission",
                status=status,
                step=step,
                state_version=12,
                progress=progress or {},
                location=location,
                level=43,
            )
        )

    available = render("available", 1)
    assert "Sel Ardan" in available.text
    assert "altos:action:0:receive_order" in {
        button.callback_data
        for row in available.keyboard.inline_keyboard
        for button in row
    }

    expected_actions = {
        2: {"road:route:altos_pontes"},
        3: {
            "altos:action:12:inspect_order_station_1",
            "altos:action:12:inspect_order_station_2",
            "altos:action:12:inspect_order_station_3",
        },
        4: {"altos:action:12:verify_waiting_bridge"},
        5: {"altos:action:12:compare_records_with_sel"},
        6: {"altos:action:12:record_regencia_codex"},
        7: {"altos:action:12:conclude_emergency_authority"},
    }
    for step, actions in expected_actions.items():
        screen = render("active", step, location=ALTOS_PONTES_LABEL)
        callbacks = {
            button.callback_data
            for row in screen.keyboard.inline_keyboard
            for button in row
        }
        assert actions <= callbacks
        assert "world:missions" in callbacks

    remaining_stations = render(
        "active",
        3,
        progress={"order_stations": ["inspect_order_station_1"]},
        location=ALTOS_PONTES_LABEL,
    )
    remaining_callbacks = {
        button.callback_data
        for row in remaining_stations.keyboard.inline_keyboard
        for button in row
    }
    assert "altos:action:12:inspect_order_station_1" not in remaining_callbacks


async def _seed_p26_character(database, actor: int, *, level=43, p25_status="completed"):
    actor, road, sessions = await _seed_altos_exit(
        database, actor, level=level, p24_status="completed"
    )
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION_LABEL
        world.location = ALTOS_ABRIGO_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P25_ID,
                title="O Peso Antigo",
                status=p25_status,
                step=9,
                state_version=9,
                content_version=P25_CONTENT_VERSION,
                progress={"completed": p25_status == "completed"},
            )
        )
        session.add_all(
            (
                Unlock(character_id=character.id, unlock_id=ALTOS_ESCARPA_ACCESS_UNLOCK),
                Unlock(character_id=character.id, unlock_id=ALTOS_ABRIGO_ACCESS_UNLOCK),
                Unlock(character_id=character.id, unlock_id=ALTOS_ESCARPA_HUNT_UNLOCK),
                Unlock(character_id=character.id, unlock_id=ALTOS_ESCARPA_EXPLORE_UNLOCK),
                LocationDiscovery(
                    character_id=character.id, location_id=ALTOS_ESCARPA_LOCATION
                ),
                LocationDiscovery(
                    character_id=character.id, location_id=ALTOS_ABRIGO_LOCATION
                ),
                Brazier(character_id=character.id, brazier_id=ALTOS_ESCARPA_BRAZIER),
                Brazier(character_id=character.id, brazier_id=ALTOS_ABRIGO_BRAZIER),
            )
        )
    return actor, road, sessions


def test_altos_pontes_profiles_match_the_final_source():
    assert ALTOS_PONTES_PROFILE.creature_weights == (
        ("creature.altos.lobo_escarpa", 15),
        ("creature.altos.abutre_fuligem", 18),
        ("creature.altos.carneiro_peso", 20),
        (ALTOS_QUEBRA_CABOS, 25),
        (ALTOS_LAGARTO_ESCORIA, 17),
        ("elite.altos.quebra_escarpas", 2),
        (ALTOS_DEVORADOR_ESCORIA, 3),
    )
    assert sum(weight for _, weight in ALTOS_PONTES_PROFILE.creature_weights) == 100
    assert ALTOS_PONTES_PROFILE.variant_chance == 13
    assert ALTOS_PONTES_PROFILE.hunt_unlock == ALTOS_PONTES_HUNT_UNLOCK
    assert ALTOS_PONTES_PROFILE.explore_unlock == ALTOS_PONTES_EXPLORE_UNLOCK
    assert ALTOS_PONTES_PROFILE.round_familiarity == ALTOS_PONTES_ROUND_UNLOCK
    assert (
        creature_for(ALTOS_LAGARTO_ESCORIA).unlock_level,
        creature_for(ALTOS_LAGARTO_ESCORIA).max_level,
    ) == (43, 47)
    assert (
        creature_for(ALTOS_QUEBRA_CABOS).unlock_level,
        creature_for(ALTOS_QUEBRA_CABOS).max_level,
    ) == (43, 49)
    assert (
        creature_for(ALTOS_DEVORADOR_ESCORIA).unlock_level,
        creature_for(ALTOS_DEVORADOR_ESCORIA).max_level,
    ) == (46, 48)
    assert VARIANT_POOL[ALTOS_LAGARTO_ESCORIA] == ("furious", "resistant", "agile")
    assert VARIANT_POOL[ALTOS_QUEBRA_CABOS] == ("agile", "resistant")
    assert VARIANT_POOL[ALTOS_DEVORADOR_ESCORIA] == ()
    assert MATERIAL_POOLS[ALTOS_LAGARTO_ESCORIA] == (
        ("material.altos.couro_escarpa", 70),
        ("material.altos.cinza_basalto", 30),
    )
    assert MATERIAL_POOLS[ALTOS_QUEBRA_CABOS] == (
        ("material.altos.liquen_pedreira", 65),
        ("material.altos.couro_escarpa", 35),
    )
    assert MATERIAL_POOLS[ALTOS_DEVORADOR_ESCORIA] == (
        ("material.altos.couro_escarpa", 70),
        ("material.altos.cinza_basalto", 30),
    )

    profile = EXPLORATION_PROFILES[ALTOS_PONTES_LOCATION]
    assert dict(profile.category_weights) == EXPLORATION_CATEGORY_WEIGHTS
    assert profile is ALTOS_PONTES_EXPLORATION_PROFILE
    great_discoveries = {
        result.result_id: (result.weight, result.unique)
        for result in profile.results
        if result.category == "great_discovery"
    }
    assert great_discoveries == {
        "explore.altos.pontes.braseiro_ponte_alta": (50, True),
        "explore.altos.pontes.plataforma_contrapeso": (50, True),
    }
    assert CODEX_BY_ID["codex.altos.regencia_continuidade"].location_id == ALTOS_PONTES_LOCATION
    assert CODEX_FRAGMENTS["codex.altos.regencia_continuidade"].text.endswith(
        "Sua cadeia integral de decisões permanece desconhecida."
    )
    assert ALTOS_PONTES_BRAZIER == "bonfire.altos.ponte_alta"


@pytest.mark.asyncio
async def test_p26_is_suspended_or_blocked_until_p25_and_level_43(database):
    low_actor, low_road, low_sessions = await _seed_p26_character(
        database, 780260, level=42
    )
    low_mission = AltosMissionService(low_sessions, "ocaso")
    suspended = await low_mission.resume_active(low_actor)
    assert suspended is not None and suspended.quest_id == P26_ID
    assert suspended.status == "suspended"
    assert await low_mission.start_p26(low_actor) is not None
    assert await low_road.travel_route(low_actor, ALTOS_PONTES_LABEL) is None

    active_actor, active_road, active_sessions = await _seed_p26_character(
        database, 780261, level=43, p25_status="active"
    )
    active_mission = AltosMissionService(active_sessions, "ocaso")
    assert await active_mission.start_p26(active_actor) is None
    assert await active_road.travel_route(active_actor, ALTOS_PONTES_LABEL) is None
    async with active_sessions() as session:
        active_character = await session.scalar(
            select(Character).where(Character.telegram_id == active_actor)
        )
        assert active_character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == active_character.id,
                Unlock.unlock_id == ALTOS_PONTES_ACCESS_UNLOCK,
            )
        ) is None


@pytest.mark.asyncio
async def test_p26_persistence_rewards_local_gates_exploration_and_round(database, monkeypatch):
    import asterion.application.road as road_module

    actor, road, sessions = await _seed_p26_character(database, 780262)
    mission = AltosMissionService(sessions, "ocaso")

    offer = await mission.resume_active(actor)
    assert offer is not None and offer.status == "available"
    assert offer.title == P26_TITLE
    assert await road.travel_route(actor, ALTOS_PONTES_LABEL) is None
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        initial_xp = character.xp
        initial_crowns = character.crowns

    view = await mission.advance(actor, offer.state_version, "receive_order")
    assert view is not None and view.status == "active" and view.step == 2
    assert view.quest_id == P26_ID
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_PONTES_ACCESS_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == ALTOS_PONTES_LOCATION,
            )
        ) is None

    abrigo = await road.resume(actor)
    assert abrigo is not None and ALTOS_PONTES_LABEL in abrigo.route_destinations
    arrived = await road.travel_route(actor, ALTOS_PONTES_LABEL)
    assert arrived is not None and arrived.location == ALTOS_PONTES_LABEL
    view = await mission.resume_active(actor)
    assert view is not None and view.step == 3
    assert await mission.known_locations(actor) == {
        ALTOS_ESCARPA_LABEL,
        ALTOS_ABRIGO_LABEL,
        ALTOS_PONTES_LABEL,
    }
    locked = await road.resume(actor)
    assert locked is not None and not locked.hunt_enabled and not locked.explore_enabled
    assert await road.start_hunt(actor) is None
    assert await road.explore(actor) is None

    stale_version = view.state_version
    view = await mission.advance(actor, stale_version, "inspect_order_station_1")
    assert view is not None and view.step == 3
    duplicate = await mission.advance(actor, stale_version, "inspect_order_station_1")
    assert duplicate is not None and duplicate.state_version == view.state_version
    assert duplicate.progress["order_stations"] == ["inspect_order_station_1"]
    for action in ("inspect_order_station_2", "inspect_order_station_3"):
        view = await mission.advance(actor, view.state_version, action)
        assert view is not None
    assert view.step == 4
    view = await mission.advance(actor, view.state_version, "verify_waiting_bridge")
    assert view is not None and view.step == 5
    view = await mission.advance(actor, view.state_version, "compare_records_with_sel")
    assert view is not None and view.step == 6
    view = await mission.advance(actor, view.state_version, "record_regencia_codex")
    assert view is not None and view.step == 7
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == "codex.altos.regencia_continuidade",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.entry_id == "codex.altos.regencia_continuidade",
                CodexFragment.fragment_id == "codex.altos.regencia_continuidade",
            )
        ) is not None

    view = await mission.advance(actor, view.state_version, "conclude_emergency_authority")
    assert view is not None and view.status == "completed"
    completed_again = await mission.advance(
        actor, view.state_version, "conclude_emergency_authority"
    )
    assert completed_again is not None and completed_again.status == "completed"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.xp - initial_xp == 57_900
        assert character.crowns - initial_crowns == 750
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == P26_ID,
                Quest.status == "completed",
            )
        ) is not None
        unlocks = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(Unlock.character_id == character.id)
                )
            ).all()
        )
        assert {
            ALTOS_PONTES_ACCESS_UNLOCK,
            ALTOS_PONTES_HUNT_UNLOCK,
            ALTOS_PONTES_EXPLORE_UNLOCK,
            "narrative.altos.regencia_identificada",
        } <= unlocks
        assert ALTOS_PONTES_ROUND_UNLOCK not in unlocks
        assert not any("pedreiras" in unlock_id or "bastilha" in unlock_id for unlock_id in unlocks)
        discoveries = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character.id,
                        LocationDiscovery.location_id.like("location.altos.%"),
                    )
                )
            ).all()
        )
        assert discoveries == {
            ALTOS_ESCARPA_LOCATION,
            ALTOS_ABRIGO_LOCATION,
            ALTOS_PONTES_LOCATION,
        }
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == ALTOS_PONTES_BRAZIER,
            )
        ) is None
        achievement = await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == "achievement.altos.ordens_emergencia",
            )
        )
        assert achievement is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P26_MISSION_ID,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert Counter((row.kind, row.item_id, row.quantity) for row in components) == Counter(
            {
                ("xp", None, 57_900): 1,
                ("crowns", None, 750): 1,
                ("material", "material.altos.ferro_contrapeso", 3): 1,
                ("material", "material.altos.cinza_basalto", 1): 1,
            }
        )
        materials = {
            (row.material_id, row.quantity, row.bound)
            for row in (
                await session.scalars(
                    select(MaterialStack).where(MaterialStack.character_id == character.id)
                )
            ).all()
            if row.material_id in {
                "material.altos.ferro_contrapeso",
                "material.altos.cinza_basalto",
            }
        }
        assert materials == {
            ("material.altos.ferro_contrapeso", 3, True),
            ("material.altos.cinza_basalto", 1, True),
        }
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == character.id,
                CampaignObjectiveCredit.quest_id == P26_ID,
                CampaignObjectiveCredit.objective_id == "p26.completed",
            )
        ) is not None

    unlocked = await road.resume(actor)
    assert unlocked is not None and unlocked.hunt_enabled and unlocked.explore_enabled
    assert unlocked.route_destinations == (ALTOS_ABRIGO_LABEL,)
    assert await road.travel_route(actor, "Pedreiras Suspensas") is None

    # The Pontes brazier appears only when its published great discovery is settled.
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.altos.pontes.braseiro_ponte_alta",
            "O Braseiro da Ponte Alta foi descoberto.",
        ),
    )
    exploration = await road.explore(actor)
    assert exploration is not None and exploration.attempt_id is not None
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == ALTOS_PONTES_BRAZIER,
            )
        ) is not None
    await road.acknowledge_result(actor, exploration.attempt_id)

    rounds = disable_round_pvpve_for_test(RoundService(sessions, "ocaso"))
    blocked_round = await rounds.prepare_round(actor, 5)
    assert blocked_round is None or blocked_round.kind != "round_prepare"

    # A manual victory at another Local opens only that Local's Ronda.
    assert await road.travel_brazier(actor, ALTOS_ESCARPA_BRAZIER) is not None
    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    escarpa_hunt = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert escarpa_hunt is not None and escarpa_hunt.combat is not None
    escarpa_hunt = await road.action(
        actor, escarpa_hunt.activity_id, escarpa_hunt.combat.version, "attack"
    )
    assert escarpa_hunt is not None and escarpa_hunt.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_ESCARPA_ROUND_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_PONTES_ROUND_UNLOCK,
            )
        ) is None
    assert await road.travel_brazier(actor, ALTOS_PONTES_BRAZIER) is not None
    blocked_pontes_round = await rounds.prepare_round(actor, 5)
    assert blocked_pontes_round is None or blocked_pontes_round.kind != "round_prepare"

    pontes_hunt = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert pontes_hunt is not None and pontes_hunt.combat is not None
    pontes_hunt = await road.action(
        actor, pontes_hunt.activity_id, pontes_hunt.combat.version, "attack"
    )
    assert pontes_hunt is not None and pontes_hunt.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_PONTES_ROUND_UNLOCK,
            )
        ) is not None
    round_ready = await rounds.prepare_round(actor, 5)
    assert round_ready is not None and round_ready.kind == "round_prepare"


@pytest.mark.asyncio
async def test_p26_shareable_evidence_is_persisted_for_eligible_group_members(database):
    leader, road, sessions = await _seed_p26_character(database, 780263)
    helper, _helper_road, _ = await _seed_p26_character(database, 780264)
    async with sessions() as session:
        helper_character = await session.scalar(
            select(Character).where(Character.telegram_id == helper)
        )
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
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    for actor in (leader, helper):
        offer = await mission.resume_active(actor)
        assert offer is not None and offer.status == "available"
        started = await mission.advance(actor, offer.state_version, "receive_order")
        assert started is not None and started.step == 2
        arrived = await road.travel_route(actor, ALTOS_PONTES_LABEL)
        assert arrived is not None and arrived.location == ALTOS_PONTES_LABEL
        resumed = await mission.resume_active(actor)
        assert resumed is not None and resumed.step == 3

    view = await mission.resume_active(leader)
    assert view is not None and view.step == 3
    view = await mission.advance(leader, view.state_version, "inspect_order_station_1")
    assert view is not None and view.step == 3
    reconnected = await AltosMissionService(sessions, "ocaso", groups=groups).resume_active(helper)
    assert reconnected is not None and reconnected.step == 3
    assert reconnected.progress["order_stations"] == ["inspect_order_station_1"]

    async with sessions() as session:
        character_ids = set(
            (
                await session.scalars(
                    select(Character.id).where(
                        Character.telegram_id.in_((leader, helper))
                    )
                )
            ).all()
        )
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id.in_(character_ids),
                    CampaignObjectiveCredit.quest_id == P26_ID,
                    CampaignObjectiveCredit.objective_id
                    == "p26.inspect_order_station_1",
                )
            )
        ).all()
        assert len(credits) == 2
        assert len({credit.character_id for credit in credits}) == 2

    view = await mission.resume_active(leader)
    assert view is not None
    for action in ("inspect_order_station_2", "inspect_order_station_3"):
        view = await mission.advance(leader, view.state_version, action)
        assert view is not None
    assert view.step == 4
    helper_view = await mission.resume_active(helper)
    assert helper_view is not None and helper_view.step == 4
    view = await mission.advance(leader, view.state_version, "verify_waiting_bridge")
    assert view is not None and view.step == 5
    helper_view = await mission.resume_active(helper)
    assert helper_view is not None and helper_view.step == 5
    view = await mission.advance(leader, view.state_version, "compare_records_with_sel")
    assert view is not None and view.step == 6
    helper_view = await mission.resume_active(helper)
    assert helper_view is not None and helper_view.step == 5
