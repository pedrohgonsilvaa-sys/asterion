from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from asterion.application.groups import GroupService
from asterion.application.nareth_missions import (
    CANAIS,
    P14_ID,
    P14_REWARD_SOURCE,
    S14_ID,
    S14_REWARD_SOURCE,
    NarethMissionService,
)
from asterion.application.road import (
    NARETH_CAMPINAS_LABEL,
    NARETH_EXPLORATION_UNIQUE_XP,
    NARETH_POSTO_LABEL,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.domain.combat import active_player_key, allowed_actions
from asterion.domain.road import (
    EXPLORATION_CATEGORY_WEIGHTS,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    NARETH_CANAIS_LOCATION,
    NARETH_CANAIS_PROFILE,
    VARIANT_POOL,
    creature_for,
    material_for,
)
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Brazier,
    CampaignObjectiveCredit,
    CampaignSharedEncounter,
    Character,
    CodexEntry,
    CodexFragment,
    ExplorationAttempt,
    HuntContext,
    HuntRound,
    HuntRoundEncounter,
    LocationDiscovery,
    RewardComponent,
    RewardEvent,
    Unlock,
)
from tests.test_nareth_opening_integration import (
    _complete_p13,
    _enter_campinas,
    _seed_nareth_entry,
)
from tests.test_p7_integration import _terminal


async def _complete_p14(road, missions, actor, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    p14 = await missions.start(actor, P14_ID)
    assert p14 is not None and p14.status == "active" and p14.step == 1
    p14 = await missions.advance(actor, P14_ID, p14.state_version, "receive_map")
    assert p14 is not None and p14.step == 2
    arrived = await road.travel_route(actor, CANAIS)
    assert arrived is not None and arrived.location == CANAIS
    await missions.on_location(actor)
    p14 = await missions.resume(actor, P14_ID)
    assert p14 is not None and p14.step == 3
    p14 = await missions.advance(actor, P14_ID, p14.state_version, "examine_gate")
    p14 = await missions.advance(actor, P14_ID, p14.state_version, "follow_bed")
    assert p14 is not None and p14.kind == "combat_start" and p14.step == 5
    combat = await missions.start_solo_combat(actor, P14_ID, p14.state_version)
    assert combat is not None and combat.kind == "combat" and combat.activity_id is not None
    assert combat.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    p14 = await missions.action_combat(
        actor, combat.activity_id, combat.combat.version, "attack"
    )
    assert p14 is not None and p14.step == 6 and p14.progress["combat_victory"]
    p14 = await missions.advance(actor, P14_ID, p14.state_version, "recover_plate")
    p14 = await missions.advance(actor, P14_ID, p14.state_version, "compare_plate")
    assert p14 is not None and p14.kind == "return_posto" and p14.step == 8
    returned = await road.travel_route(actor, NARETH_POSTO_LABEL)
    assert returned is not None and returned.location == NARETH_POSTO_LABEL
    await missions.on_location(actor)
    p14 = await missions.resume(actor, P14_ID)
    assert p14 is not None and p14.step == 9
    return await missions.advance(actor, P14_ID, p14.state_version, "deliver_plate"), combat


@pytest.mark.asyncio
async def test_nareth_p14_and_s14_public_flows_settle_once(database, monkeypatch):
    actor = 991401
    character_id, sessions = await _seed_nareth_entry(database, actor, level=24)
    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso")

    opening = await _enter_campinas(road, missions, actor)
    assert opening is not None
    assert not (await missions.resume(actor, P14_ID)).available
    await _complete_p13(road, missions, actor)

    completed, combat = await _complete_p14(road, missions, actor, monkeypatch)
    assert completed is not None and completed.status == "completed"
    stale = await missions.advance(actor, P14_ID, completed.state_version - 1, "deliver_plate")
    assert stale is not None and stale.status == "completed"

    async with sessions() as session:
        p14_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P14_REWARD_SOURCE,
            )
        )
        assert p14_event is not None
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P14_REWARD_SOURCE,
            )
        ) == 1
        p14_components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == p14_event.id
                    )
                )
            ).all()
        )
        assert {(item.kind, item.item_id, item.quantity) for item in p14_components} == {
            ("xp", None, 22000),
            ("crowns", None, 450),
            ("material", "material.nareth.bronze_de_marco", 1),
            ("material", "material.nareth.erva_de_vento", 2),
            ("material", "material.nareth.po_de_eixo", 1),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        ) == 0
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "escaravelho_canal",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "hunt.manual.nareth.canais_secos",
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "nareth.location.canais_secos",
            )
        ) is not None

    s14 = await missions.resume(actor, S14_ID)
    assert s14 is not None and s14.available
    s14 = await missions.start(actor, S14_ID)
    assert s14 is not None and s14.status == "active" and s14.step == 1
    s14 = await missions.advance(actor, S14_ID, s14.state_version, "receive_routes")
    arrived = await road.travel_route(actor, CANAIS)
    assert arrived is not None and arrived.location == CANAIS
    await missions.on_location(actor)
    s14 = await missions.resume(actor, S14_ID)
    for action in (
        "examine_bridge",
        "follow_low_route",
        "mark_stable_route",
        "find_access_signs",
    ):
        s14 = await missions.advance(actor, S14_ID, s14.state_version, action)
    assert s14 is not None and s14.kind == "return_posto" and s14.step == 7
    returned = await road.travel_route(actor, NARETH_POSTO_LABEL)
    assert returned is not None and returned.location == NARETH_POSTO_LABEL
    await missions.on_location(actor)
    s14 = await missions.resume(actor, S14_ID)
    assert s14 is not None and s14.step == 8
    s14 = await missions.advance(actor, S14_ID, s14.state_version, "report")
    assert s14 is not None and s14.status == "completed"
    await missions.advance(actor, S14_ID, s14.state_version - 1, "report")

    async with sessions() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S14_REWARD_SOURCE,
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
        assert {(item.kind, item.item_id, item.quantity) for item in components} == {
            ("xp", None, 16380),
            ("crowns", None, 350),
            ("material", "material.nareth.erva_de_vento", 1),
            ("material", "material.nareth.po_de_eixo", 1),
        }
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S14_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "dungeon.nareth.galerias_meridiano",
            )
        ) is None


@pytest.mark.asyncio
async def test_nareth_p14_group_credit_and_scripted_encounter_are_shared(database, monkeypatch):
    leader, helper = 991403, 991404
    leader_id, sessions = await _seed_nareth_entry(database, leader, level=24)
    helper_id, _ = await _seed_nareth_entry(database, helper, level=24)
    async with sessions() as session:
        helper_row = await session.get(Character, helper_id)
        assert helper_row is not None
        helper_name = helper_row.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invite = await groups.invite(
        leader, helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        helper, invite.invite_id, expected_revision=invite.revision, accept=True
    )
    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso", groups=groups)

    for actor in (leader, helper):
        await road.travel_route(actor, NARETH_CAMPINAS_LABEL)
        await missions.on_location(actor)
    p13 = await missions.resume(leader, "P13")
    for action in ("line", "compare", "horizon_brazier", "follow_route"):
        p13 = await missions.advance(leader, "P13", p13.state_version, action)
    assert p13 is not None and p13.step == 7

    await road.travel_route(leader, NARETH_POSTO_LABEL)
    await road.travel_route(helper, NARETH_POSTO_LABEL)
    await missions.on_location(leader)
    p13 = await missions.resume(leader, "P13")
    for action in ("posto_brazier", "speak_nera", "record_codex"):
        p13 = await missions.advance(leader, "P13", p13.state_version, action)
    assert p13 is not None and p13.status == "completed"

    p14 = await missions.start(leader, P14_ID)
    assert p14 is not None and p14.status == "active" and p14.step == 1
    p14 = await missions.advance(leader, P14_ID, p14.state_version, "receive_map")
    assert p14 is not None and p14.step == 2
    await road.travel_route(leader, CANAIS)
    await road.travel_route(helper, CANAIS)
    await missions.on_location(leader)

    async with sessions() as session:
        for character_id in (leader_id, helper_id):
            quest_reward = await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == P14_REWARD_SOURCE,
                )
            )
            assert quest_reward is None
            credit = await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == P14_ID,
                    CampaignObjectiveCredit.objective_id
                    == "p14.arrived.nareth.location.canais_secos",
                )
            )
            assert credit is not None
            progress = await session.scalar(
                select(CampaignObjectiveCredit.character_id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == P14_ID,
                    CampaignObjectiveCredit.objective_id
                    == "p14.location_discovered",
                )
            )
            assert progress == character_id

    p14 = await missions.resume(leader, P14_ID)
    assert p14 is not None and p14.step == 3
    p14 = await missions.advance(leader, P14_ID, p14.state_version, "examine_gate")
    p14 = await missions.advance(leader, P14_ID, p14.state_version, "follow_bed")
    proposal_view = await missions.propose_group_combat(
        leader, P14_ID, p14.state_version
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
    assert started is not None and started.kind == "combat" and started.group_size == 2
    helper_view = await missions.resume_active(helper)
    assert helper_view is not None and helper_view.encounter_id == started.encounter_id
    async with sessions() as session:
        encounter = await session.get(CampaignSharedEncounter, started.encounter_id)
        assert encounter is not None and encounter.roster_size == 2

    import asterion.application.campaign_coop as campaign_coop

    monkeypatch.setattr(campaign_coop, "act", _terminal("victory"))
    active_key = active_player_key(started.combat)
    assert active_key is not None
    views = {leader: started, helper: helper_view}
    turn_owner = next(
        actor
        for actor, participant_view in views.items()
        if participant_view.combat_actor_key == active_key
    )
    turn = views[turn_owner]
    result = await missions.action_combat(
        turn_owner,
        turn.activity_id,
        turn.combat.version,
        "attack",
    )
    if result is not None and result.kind == "combat_result":
        result = await missions.resume(leader, P14_ID)
    assert result is not None and result.step == 6
    async with sessions() as session:
        for character_id in (leader_id, helper_id):
            quest = await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == P14_REWARD_SOURCE,
                )
            )
            assert quest is None


def test_nareth_canais_hunt_and_exploration_profiles_match_authority():
    profile = HUNT_PROFILES[NARETH_CANAIS_LOCATION]
    assert profile.creature_weights == (
        ("galgo_meridiano", 20),
        ("abutre_marco", 17),
        ("errante_valas", 15),
        ("escaravelho_canal", 21),
        ("cervo_horizonte", 23),
        ("alfa_horizonte", 2),
        ("serpe_eixo", 2),
    )
    assert profile.variant_chance == 12
    assert profile.hunt_unlock == "hunt.manual.nareth.canais_secos"
    assert profile.round_familiarity == "hunt_round.nareth.canais_secos"
    assert NARETH_CANAIS_PROFILE == profile
    assert all(creature_id in MATERIAL_POOLS for creature_id, _ in profile.creature_weights)
    assert VARIANT_POOL["escaravelho_canal"] == ("resistant", "agile")
    assert VARIANT_POOL["cervo_horizonte"] == ("furious", "resistant")
    assert VARIANT_POOL["alfa_horizonte"] == ()
    assert VARIANT_POOL["serpe_eixo"] == ()
    assert {
        creature_id: (creature_for(creature_id).unlock_level, creature_for(creature_id).max_level)
        for creature_id, _ in profile.creature_weights
    } == {
        "galgo_meridiano": (21, 24),
        "abutre_marco": (21, 24),
        "errante_valas": (21, 25),
        "escaravelho_canal": (23, 26),
        "cervo_horizonte": (23, 27),
        "alfa_horizonte": (23, 24),
        "serpe_eixo": (25, 27),
    }

    explore = EXPLORATION_PROFILES[NARETH_CANAIS_LOCATION]
    assert explore.category_weights == tuple(EXPLORATION_CATEGORY_WEIGHTS.items())
    weights = {
        category: {
            result.key: result.weight
            for result in explore.results
            if result.category == category
        }
        for category in (
            "great_discovery",
            "knowledge",
            "narrative",
            "combat",
            "resource",
            "atmospheric",
        )
    }
    assert weights["great_discovery"] == {
        "braseiro_canal_alto": 50,
        "entrada_galerias": 50,
    }
    assert weights["knowledge"] == {
        "comporta_sem_agua": 55,
        "marcas_vazao": 45,
    }
    assert weights["narrative"] == {
        "pedra_raspada": 55,
        "ponte_seco": 45,
    }
    assert weights["combat"] == {
        "galgo": 20,
        "abutre": 15,
        "errante": 15,
        "escaravelho": 25,
        "cervo": 25,
    }
    assert weights["resource"] == {
        "bronze": 35,
        "erva": 30,
        "po": 25,
        "couro": 10,
    }
    assert weights["atmospheric"] == {
        "canal_some": 34,
        "eco_ponte": 33,
        "vento_comporta": 33,
    }
    canais_unique = (
        "explore.nareth.canais.braseiro_canal_alto",
        "explore.nareth.canais.entrada_galerias_meridiano",
        "explore.nareth.canais.comporta_sem_agua",
        "explore.nareth.canais.pedra_raspada",
    )
    assert {key: NARETH_EXPLORATION_UNIQUE_XP[key] for key in canais_unique} == {
        "explore.nareth.canais.braseiro_canal_alto": 3744,
        "explore.nareth.canais.entrada_galerias_meridiano": 3744,
        "explore.nareth.canais.comporta_sem_agua": 1170,
        "explore.nareth.canais.pedra_raspada": 0,
    }


@pytest.mark.asyncio
async def test_nareth_canais_manual_hunt_unlocks_round_and_brazier_discovery(
    database, monkeypatch
):
    import asterion.application.road as road_module
    import asterion.application.round as round_module

    actor = 991402
    character_id, sessions = await _seed_nareth_entry(database, actor, level=23)
    road = RoadService(sessions, "ocaso")
    missions = NarethMissionService(sessions, "ocaso")
    await _enter_campinas(road, missions, actor)
    await _complete_p13(road, missions, actor)
    await _complete_p14(road, missions, actor, monkeypatch)

    to_canais = await road.travel_route(actor, CANAIS)
    assert to_canais is not None and to_canais.location == CANAIS
    await missions.on_location(actor)
    local = await road.resume(actor)
    assert local is not None and local.kind == "nareth_canais"
    assert local.hunt_enabled and local.explore_enabled
    round_service = RoundService(sessions, "ocaso")
    locked = await round_service.prepare_round(actor, 5)
    assert locked is not None and locked.kind == "nareth_canais" and locked.familiar is False

    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.nareth.canais.braseiro_canal_alto",
            "Braseiro do Canal Alto descoberto.",
        ),
    )
    exploration = await road.explore(actor)
    assert exploration is not None and exploration.kind == "exploration"
    await road.acknowledge_result(actor, exploration.attempt_id)
    await road.acknowledge_result(actor, exploration.attempt_id)
    async with sessions.begin() as session:
        attempt = await session.get(ExplorationAttempt, exploration.attempt_id)
        assert attempt is not None
        attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "great_discovery",
            "explore.nareth.canais.entrada_galerias_meridiano",
            "Entrada das Galerias descoberta.",
        ),
    )
    galleries = await road.explore(actor)
    assert galleries is not None and galleries.kind == "exploration"
    await road.acknowledge_result(actor, galleries.attempt_id)

    original_create = road_module.create_road_combat
    from dataclasses import replace

    from asterion.domain.road import creature_for
    from tests.helpers.pvpve import start_manual_hunt_after_no_match

    def safe_combat(*args, **kwargs):
        combat = original_create(*args, **kwargs)
        enemy = combat.fighters["enemy"]
        enemy.stats = replace(enemy.stats, attack=1)
        return combat

    monkeypatch.setattr(road_module, "create_road_combat", safe_combat)
    monkeypatch.setattr(round_module, "create_road_combat", safe_combat)
    monkeypatch.setattr(
        road_module, "select_creature", lambda *_args, **_kwargs: creature_for("escaravelho_canal")
    )
    monkeypatch.setattr(
        round_module, "select_creature", lambda *_args, **_kwargs: creature_for("escaravelho_canal")
    )
    hunt = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert hunt is not None and hunt.kind == "combat" and hunt.activity_id is not None
    for _ in range(100):
        if hunt.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(hunt.combat) else "attack"
        hunt = await road.action(actor, hunt.activity_id, hunt.combat.version, action)
    assert hunt is not None and hunt.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    open_round = await round_service.prepare_round(actor, 5)
    assert open_round is not None and open_round.kind == "round_prepare"
    async def no_round_match(*_args, **_kwargs):
        return False

    round_service.pvpve.queue_round_hunt = no_round_match
    started_round = await round_service.start_round(
        actor, open_round.round_id, open_round.state_version
    )
    assert started_round is not None and started_round.kind == "round_active"
    async with sessions.begin() as session:
        state = await session.get(HuntRound, started_round.round_id)
        assert state is not None
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
    await round_service.advance_due_rounds()
    async with sessions() as session:
        state = await session.get(HuntRound, started_round.round_id)
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == started_round.round_id
            )
        )
        assert state is not None and state.completed_encounters == 1
        assert encounter is not None and encounter.status == "completed"
        assert encounter.creature_id == "escaravelho_canal"
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
        material_rows = list(
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
        assert [row.item_id for row in material_rows] == [
            material_for(
                context.creature_id,
                f"{context.seed}:material.basic.{ordinal}",
            )
            for ordinal in range(len(material_rows))
        ]
    async with sessions() as session:
        assert await session.scalar(
            select(func.count(Brazier.id)).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == "nareth.brazier.canal_alto",
            )
        ) == 1
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.location.canais_secos",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.nareth.canais.brazier",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "dungeon.nareth.galerias_meridiano",
            )
        ) is not None
        assert await session.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == character_id,
                ExplorationAttempt.status == "completed",
            )
        ) == 2
