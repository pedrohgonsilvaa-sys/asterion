from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from asterion.application import road as road_module
from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P33_CONTENT_VERSION,
    P33_ID,
    P34_ACHIEVEMENT,
    P34_CODEX_ENTRY,
    P34_CONTENT_VERSION,
    P34_ID,
    P34_REWARD_SOURCE,
    AltosMissionService,
)
from asterion.application.groups import GroupService
from asterion.application.knowledge_catalog import ACHIEVEMENT_BY_ID, CODEX_BY_ID
from asterion.application.road import (
    CONFINS_CARTOGRAPHER_UNIQUE_IDS,
    CONFINS_EXPLORATION_UNIQUE_XP,
    CONFINS_FRATURAS_LIMIAR_LABEL,
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_REGION_LABEL,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.domain.road import (
    CONFINS_CASCA_REFLEXO,
    CONFINS_CUSTODIO_DESFASADO,
    CONFINS_ESTRADAS_AUSENTES_LOCATION,
    CONFINS_FRATURAS_LIMIAR_LOCATION,
    CONFINS_MARCHA_LOCATION,
    CONFINS_NO_CENTRAL_LOCATION,
    CONFINS_NO_CENTRAL_PROFILE,
    CONFINS_SANGUESSUGA_PALIDA,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    LOCATION_LEVEL_BANDS,
    creature_for,
    select_creature,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    CampaignObjectiveCredit,
    Character,
    CodexFragment,
    ExplorationAttempt,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import disable_round_pvpve_for_test
from tests.test_confins_p33 import _seed_p33_actor
from tests.test_s4_s5_integration import _terminal


async def _seed_p34_actor(
    database, actor: int, *, level: int = 57, p33_status: str = "completed"
):
    actor, _road, sessions = await _seed_p33_actor(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_FRATURAS_LIMIAR_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P33_ID,
                title="O Avesso",
                status=p33_status,
                step=6 if p33_status == "completed" else 1,
                content_version=P33_CONTENT_VERSION,
                state_version=6 if p33_status == "completed" else 1,
                progress={"completed": p33_status == "completed"},
            )
        )
        session.add(
            LocationDiscovery(
                character_id=character.id,
                location_id="location.confins.fraturas_limiar",
            )
        )
        session.add(
            Unlock(
                character_id=character.id,
                unlock_id="unlock.location.confins.fraturas_limiar",
            )
        )
    return actor, RoadService(sessions, "ocaso"), sessions


@pytest.mark.parametrize(
    ("level", "p33_status", "expected_status"),
    ((56, "completed", "suspended"), (57, "active", None)),
)
@pytest.mark.asyncio
async def test_p34_requires_completed_p33_and_level_57(
    database, level, p33_status, expected_status
):
    actor, _road, sessions = await _seed_p34_actor(
        database, 793400 + level + (p33_status == "active"),
        level=level,
        p33_status=p33_status,
    )
    mission = AltosMissionService(sessions, "ocaso")

    view = await mission.start_p34(actor)
    if expected_status == "suspended":
        assert view is not None and view.status == "suspended"
        assert view.quest_id == P34_ID
    else:
        assert view is None

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P34_ID
            )
        ) is None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "unlock.location.confins.no_central",
            )
        ) is None


def test_p34_node_hunt_exploration_catalog_and_level_filtering():
    assert HUNT_PROFILES[CONFINS_NO_CENTRAL_LOCATION] is CONFINS_NO_CENTRAL_PROFILE
    assert CONFINS_NO_CENTRAL_PROFILE.creature_weights == (
        (CONFINS_SANGUESSUGA_PALIDA, 10),
        (CONFINS_CASCA_REFLEXO, 19),
        ("creature.confins.mariposa_sem_horizonte", 17),
        ("creature.confins.vigia_desfasado", 39),
        (CONFINS_CUSTODIO_DESFASADO, 15),
    )
    assert CONFINS_NO_CENTRAL_PROFILE.variant_chance == 20
    assert LOCATION_LEVEL_BANDS[CONFINS_NO_CENTRAL_LABEL] == (57, 60)
    assert creature_for(CONFINS_CUSTODIO_DESFASADO).unlock_level == 59
    at_57 = {
        select_creature(f"p34-node-level-57-{index}", 57, CONFINS_NO_CENTRAL_PROFILE).creature_id
        for index in range(512)
    }
    assert CONFINS_CUSTODIO_DESFASADO not in at_57
    assert at_57 <= set(dict(CONFINS_NO_CENTRAL_PROFILE.creature_weights))
    assert {
        "explore.confins.no.braseiro_retorno": 16_304,
        "explore.confins.no.camara_contradicoes": 16_304,
        "explore.confins.no.rede_incompleta": 5_095,
    }.items() <= CONFINS_EXPLORATION_UNIQUE_XP.items()
    assert len(CONFINS_CARTOGRAPHER_UNIQUE_IDS) == 11
    node_results = {
        result.result_id
        for result in EXPLORATION_PROFILES[CONFINS_NO_CENTRAL_LOCATION].results
    }
    assert node_results == {
        "explore.confins.no.braseiro_retorno",
        "explore.confins.no.camara_contradicoes",
        "explore.confins.no.rede_incompleta",
        "explore.confins.no.junta_marco",
        "explore.confins.no.ordem_muro",
        "explore.confins.no.corda_medida",
        "explore.confins.no.combate",
        "explore.confins.no.recurso",
        "explore.confins.no.atmos.metal_paz",
        "explore.confins.no.atmos.registro_sem_voz",
        "explore.confins.no.atmos.parede_repetida",
    }
    assert P34_CODEX_ENTRY in CODEX_BY_ID
    assert ACHIEVEMENT_BY_ID[P34_ACHIEVEMENT].name == "Nó Não é Fonte"


@pytest.mark.asyncio
async def test_p34_scripted_combat_conclusion_rewards_and_local_round(
    database, monkeypatch
):
    actor, road, sessions = await _seed_p34_actor(database, 793410)
    mission = AltosMissionService(sessions, "ocaso")
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character_id = character.id
        initial_xp, initial_crowns = character.xp, character.crowns

    p34 = await mission.start_p34(actor)
    assert p34 is not None and p34.quest_id == P34_ID
    assert p34.status == "active" and p34.step == 2
    assert p34.progress["completed_steps"] == [1]
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "unlock.location.confins.no_central",
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == CONFINS_NO_CENTRAL_LOCATION,
            )
        ) is None

    before_arrival = await road.resume(actor)
    assert before_arrival is not None and not before_arrival.hunt_enabled
    assert not before_arrival.explore_enabled
    assert CONFINS_NO_CENTRAL_LABEL in before_arrival.route_destinations
    arrived = await road.travel_route(actor, CONFINS_NO_CENTRAL_LABEL)
    assert arrived is not None and arrived.location == CONFINS_NO_CENTRAL_LABEL
    await mission.on_location(actor)
    p34 = await mission.resume(actor, P34_ID)
    assert p34 is not None and p34.step == 2
    assert p34.progress["no_arrival_recorded"] is True
    local = await road.resume(actor)
    assert local is not None and not local.hunt_enabled and not local.explore_enabled
    assert await road.prepare_hunt(actor) is None
    assert await road.prepare_explore(actor) is None

    for evidence_id in (
        "inspect_reference_conduction",
        "inspect_route_alignment",
        "inspect_failure_communication",
    ):
        current = await mission.resume(actor, P34_ID)
        assert current is not None and current.step == 2
        p34 = await mission.advance(actor, current.state_version, evidence_id)
        assert p34 is not None
    assert p34.step == 3
    assert set(p34.progress["physical_point_evidence_ids"]) == {
        "inspect_reference_conduction",
        "inspect_route_alignment",
        "inspect_failure_communication",
    }

    battle = await mission.start_solo_combat(actor, p34.state_version, P34_ID)
    assert battle is not None and battle.kind == "combat" and battle.combat is not None
    enemies = [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert (enemies[0].name, enemies[0].level, battle.combat.variant) == (
        "Custódio Desfasado",
        57,
        None,
    )
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    p34 = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert p34 is not None and p34.step == 4
    assert p34.progress["scripted_custodio_victory"] is True
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.xp, character.crowns) == (initial_xp, initial_crowns)
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P34_REWARD_SOURCE,
            )
        ) is None

    p34 = await mission.advance(
        actor, p34.state_version, "observe_regional_anchor_evidence"
    )
    assert p34 is not None and p34.step == 5
    p34 = await mission.advance(actor, p34.state_version, "compare_eris_with_roven")
    assert p34 is not None and p34.step == 6
    p34 = await mission.advance(
        actor, p34.state_version, "record_anchor_codex_and_conclude"
    )
    assert p34 is not None and p34.status == "completed"
    duplicate = await mission.advance(
        actor, p34.state_version - 1, "record_anchor_codex_and_conclude"
    )
    assert duplicate is not None and duplicate.status == "completed"

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.xp - initial_xp, character.crowns - initial_crowns) == (
            93_250,
            1_200,
        )
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P34_REWARD_SOURCE,
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
                ("xp", None, 93_250): 1,
                ("crowns", None, 1_200): 1,
                ("material", "material.confins.ferro_baliza", 2): 1,
                ("material", "material.confins.couro_marcha", 1): 1,
                ("material", "material.confins.po_referencia", 1): 1,
            }
        )
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == P34_CODEX_ENTRY,
                CodexFragment.fragment_id == P34_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == P34_ACHIEVEMENT,
            )
        ) is not None
        unlocks = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(
                        Unlock.character_id == character_id
                    )
                )
            ).all()
        )
        assert {
            "unlock.location.confins.no_central",
            "unlock.hunt.confins.no",
            "unlock.explore.confins.no",
            "narrative.confins.ancora_central_compreendida",
        } <= unlocks
        assert "unlock.round.confins.no" not in unlocks
        assert "unlock.dungeon.confins.camara_contradicoes" not in unlocks
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == P34_ID,
                Quest.content_version == P34_CONTENT_VERSION,
                Quest.status == "completed",
            )
        ) is not None

    rounds = disable_round_pvpve_for_test(RoundService(sessions, "ocaso"))
    before_hunt = await rounds.prepare_round(actor, 5)
    assert before_hunt is None or before_hunt.kind != "round_prepare"

    async def materialize_manual_hunt(session, character, world, profile):
        view = await road._materialize_manual_hunt(
            session, character, world, profile, seed="confins-p34-round-test"
        )
        assert view.activity_id is not None
        activity = await session.get(GameActivity, view.activity_id)
        assert activity is not None
        return await road._combat_view(session, character, activity)

    monkeypatch.setattr(road.pvpve, "queue_manual_hunt", materialize_manual_hunt)
    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    hunt = await road.start_hunt(actor)
    assert hunt is not None and hunt.kind == "combat" and hunt.combat is not None
    victory = await road.action(
        actor, hunt.activity_id, hunt.combat.version, "attack"
    )
    assert victory is not None and victory.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    after_hunt = await rounds.prepare_round(actor, 5)
    assert after_hunt is not None and after_hunt.kind == "round_prepare"
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "unlock.round.confins.no",
            )
        ) is not None


@pytest.mark.asyncio
async def test_p34_shared_evidence_is_individually_eligible_and_starts_group_encounter(
    database,
):
    actors = (793430, 793431)
    await _seed_p34_actor(database, actors[0])
    _actor, _road, sessions = await _seed_p34_actor(database, actors[1])
    groups = GroupService(sessions, "ocaso")
    async with sessions() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper_name = helper.name
    group = await groups.create_group(actors[0])
    invite = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    road = RoadService(sessions, "ocaso")

    for actor in actors:
        view = await mission.start_p34(actor)
        assert view is not None and view.status == "active"
        assert await road.travel_route(actor, CONFINS_NO_CENTRAL_LABEL) is not None
        await mission.on_location(actor)

    async with sessions.begin() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper.level = 56

    leader = await mission.resume(actors[0], P34_ID)
    assert leader is not None and leader.step == 2
    await mission.advance(
        actors[0], leader.state_version, "inspect_reference_conduction"
    )
    helper = await mission.resume(actors[1], P34_ID)
    assert helper is not None and helper.step == 2
    assert helper.progress["physical_point_evidence_ids"] == []
    async with sessions() as session:
        helper_row = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper_row is not None
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == helper_row.id,
                CampaignObjectiveCredit.quest_id == P34_ID,
                CampaignObjectiveCredit.objective_id
                == "p34.inspect_reference_conduction",
            )
        ) is None

    async with sessions.begin() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper.level = 57
    helper = await mission.resume(actors[1], P34_ID)
    assert helper is not None and helper.step == 2
    await mission.advance(
        actors[1], helper.state_version, "inspect_reference_conduction"
    )
    for action in ("inspect_route_alignment", "inspect_failure_communication"):
        leader = await mission.resume(actors[0], P34_ID)
        assert leader is not None and leader.step == 2
        await mission.advance(actors[0], leader.state_version, action)

    for actor in actors:
        view = await mission.resume(actor, P34_ID)
        assert view is not None and view.step == 3
        assert set(view.progress["physical_point_evidence_ids"]) == {
            "inspect_reference_conduction",
            "inspect_route_alignment",
            "inspect_failure_communication",
        }

    leader = await mission.resume(actors[0], P34_ID)
    assert leader is not None
    pending = await mission.propose_group_combat(
        actors[0], leader.state_version, P34_ID
    )
    assert pending is not None and pending.proposal_id is not None
    proposal = await groups.activity_proposal(actors[0], pending.proposal_id)
    accepted = await groups.respond_activity(
        actors[1],
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
    )
    started = await mission.start_group_combat(
        actors[0], pending.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None
    enemies = [fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert enemies[0].name == "Custódio Desfasado"
    assert enemies[0].level == 57
    assert started.combat.variant is None


@pytest.mark.asyncio
async def test_p34_exploration_uniques_grant_only_after_all_eleven(database, monkeypatch):
    actor, road, sessions = await _seed_p34_actor(database, 793420)
    mission = AltosMissionService(sessions, "ocaso")
    p34 = await mission.start_p34(actor)
    assert p34 is not None
    assert await road.travel_route(actor, CONFINS_NO_CENTRAL_LABEL) is not None
    await mission.on_location(actor)
    await _complete_p34_for_exploration(mission, actor, monkeypatch)

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        world = await session.get(WorldState, character.id)
        assert world is not None and world.location == CONFINS_NO_CENTRAL_LABEL
        character.vigor = character.max_vigor
        prior_ids = CONFINS_CARTOGRAPHER_UNIQUE_IDS[:8]
        prior_locations = {
            **{result_id: CONFINS_MARCHA_LOCATION for result_id in prior_ids[:2]},
            **{
                result_id: CONFINS_ESTRADAS_AUSENTES_LOCATION
                for result_id in prior_ids[2:5]
            },
            **{
                result_id: CONFINS_FRATURAS_LIMIAR_LOCATION
                for result_id in prior_ids[5:]
            },
        }
        session.add_all(
            ExplorationAttempt(
                character_id=character.id,
                local_id=prior_locations[result_id],
                ruleset_version="test",
                seed=f"p34-cartographer-prior-{index}",
                category="great_discovery",
                result_id=result_id,
                status="completed",
                progress={"settled": True},
                result_acknowledged=True,
                completed_at=datetime.now(UTC),
            )
            for index, result_id in enumerate(prior_ids)
        )

    results = (
        ("explore.confins.no.braseiro_retorno", "great_discovery"),
        ("explore.confins.no.camara_contradicoes", "great_discovery"),
        ("explore.confins.no.rede_incompleta", "knowledge"),
    )
    for index, (result_id, category) in enumerate(results):
        monkeypatch.setattr(
            road_module,
            "_explore_result",
            lambda *_args, _id=result_id, _category=category: (
                _category,
                _id,
                "Uma evidência observável foi registrada no Nó Central.",
            ),
        )
        attempt_view = await road.explore(actor)
        assert attempt_view is not None and attempt_view.attempt_id is not None
        assert attempt_view.result_id == result_id
        await road.acknowledge_result(actor, attempt_view.attempt_id)
        async with sessions.begin() as session:
            attempt = await session.get(ExplorationAttempt, attempt_view.attempt_id)
            assert (
                attempt is not None
                and attempt.status == "completed"
                and attempt.result_id == result_id
            )
            attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            character.vigor = character.max_vigor
            completed_unique_ids = set(
                (
                    await session.scalars(
                        select(ExplorationAttempt.result_id).where(
                            ExplorationAttempt.character_id == character.id,
                            ExplorationAttempt.status == "completed",
                            ExplorationAttempt.result_id.in_(
                                CONFINS_CARTOGRAPHER_UNIQUE_IDS
                            ),
                        )
                    )
                ).all()
            )
            expected_unique_ids = set(prior_ids) | {
                result_id for result_id, _category in results[: index + 1]
            }
            assert expected_unique_ids <= completed_unique_ids, (
                expected_unique_ids - completed_unique_ids
            )
            achievement = await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character.id,
                    Achievement.achievement_id == "achievement.confins.cartografo_ausencias",
                )
            )
            if index < 2:
                assert achievement is None
            else:
                assert achievement is not None

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == "bonfire.confins.no_retorno",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "unlock.dungeon.confins.camara_contradicoes",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.entry_id == P34_CODEX_ENTRY,
                CodexFragment.fragment_id == "explore.confins.no.rede_incompleta",
            )
        ) is not None


async def _complete_p34_for_exploration(mission, actor, monkeypatch):
    current = await mission.resume(actor, P34_ID)
    assert current is not None
    for action in (
        "inspect_reference_conduction",
        "inspect_route_alignment",
        "inspect_failure_communication",
    ):
        current = await mission.advance(actor, current.state_version, action)
        assert current is not None
    battle = await mission.start_solo_combat(actor, current.state_version, P34_ID)
    assert battle is not None and battle.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    current = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert current is not None and current.step == 4
    current = await mission.advance(
        actor, current.state_version, "observe_regional_anchor_evidence"
    )
    assert current is not None
    current = await mission.advance(
        actor, current.state_version, "compare_eris_with_roven"
    )
    assert current is not None
    current = await mission.advance(
        actor, current.state_version, "record_anchor_codex_and_conclude"
    )
    assert current is not None and current.status == "completed"
