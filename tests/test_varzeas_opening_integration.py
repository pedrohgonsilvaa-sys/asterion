from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from asterion.application.groups import GroupService
from asterion.application.road import (
    NARETH_CAMARA_LABEL,
    NARETH_REGION,
    VARZEAS_DIQUES,
    VARZEAS_PORTO,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.application.varzeas_missions import (
    P19_ID,
    P19_REWARD_SOURCE,
    REGION,
    ROTAS_CODEX,
    S19_ID,
    S19_REWARD_SOURCE,
    VarzeasMissionService,
)
from asterion.bot.road_ui import render_current_local
from asterion.bot.varzeas_missions_ui import render_varzeas_mission
from asterion.domain.combat import allowed_actions
from asterion.domain.road import (
    VARZEAS_DIQUES_BRAZIER,
    VARZEAS_DIQUES_EXPLORE_UNLOCK,
    VARZEAS_DIQUES_HUNT_UNLOCK,
    VARZEAS_DIQUES_LOCATION,
    VARZEAS_DIQUES_PORTO_ROUTE,
    VARZEAS_DIQUES_PROFILE,
    VARZEAS_PORTO_BRAZIER,
    VARZEAS_REGION_ENTRY_UNLOCK,
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
    ExplorationAttempt,
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

    before = await road.resume(actor)
    assert before is not None and before.location == NARETH_CAMARA_LABEL
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
    assert await RoundService(sessions, "ocaso").prepare_round(actor, 5) is None
    local_ui = render_current_local(local, explore_state="available")
    assert "Desbravar" in local_ui.text and "Caçar" in local_ui.text

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
    assert await RoundService(sessions, "ocaso").prepare_round(actor, 5) is None
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
    async with sessions() as session:
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
