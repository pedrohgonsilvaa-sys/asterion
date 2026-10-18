from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from asterion.application import road as road_module
from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P30_CONTENT_VERSION,
    P30_ID,
    P31_ACHIEVEMENT,
    P31_CODEX_ENTRY,
    P31_CONTENT_VERSION,
    P31_ID,
    P31_MISSION_ID,
    P31_REWARD_SOURCE,
    P31_TITLE_COSMETIC,
    AltosMissionService,
)
from asterion.application.groups import GroupService
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_BY_ID,
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
)
from asterion.application.road import (
    ALTOS_CORACAO_LABEL,
    ALTOS_REGION_LABEL,
    CONFINS_CARTOGRAPHER_ACHIEVEMENT,
    CONFINS_CARTOGRAPHER_UNIQUE_IDS,
    CONFINS_EXPLORATION_UNIQUE_XP,
    CONFINS_LOCATION_CATALOG,
    CONFINS_LOCATIONS,
    CONFINS_MARCHA_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
    TRAVEL_LOCATIONS,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.domain.combat import active_player_key
from asterion.domain.road import (
    CONFINS_CAO_NEVOA,
    CONFINS_CERVO_PASSO_DUPLO,
    CONFINS_GRALHA_DUAS_SOMBRAS,
    CONFINS_MARCHA_LOCATION,
    CONFINS_MARCHA_PROFILE,
    CONFINS_PREDADOR_DUAS_PEGADAS,
    CONFINS_ULTIMO_REFUGIO_LOCATION,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    creature_for,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    CampaignObjectiveCredit,
    CampaignSharedEncounter,
    Character,
    CharacterCosmetic,
    CodexEntry,
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
from tests.helpers.pvpve import (
    disable_round_pvpve_for_test,
)
from tests.test_altos_p30 import _seed_p30_character
from tests.test_campaign_coop_integration import _seed_enemy_at_one_hp
from tests.test_s4_s5_integration import _terminal


async def _seed_confins_actor(
    database, actor: int, *, level: int = 51, p30_status: str = "completed"
):
    actor, _road, sessions = await _seed_p30_character(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION_LABEL
        world.location = ALTOS_CORACAO_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P30_ID,
                title="O Colosso Cinéreo",
                status=p30_status,
                step=10 if p30_status == "completed" else 1,
                content_version=P30_CONTENT_VERSION,
                state_version=10 if p30_status == "completed" else 1,
                progress={"completed": p30_status == "completed"},
            )
        )
    return actor, RoadService(sessions, "ocaso"), sessions


async def _enter_marcha(road: RoadService, mission: AltosMissionService, actor: int):
    arrived = await road.travel_route(actor, CONFINS_MARCHA_LABEL)
    assert arrived is not None and arrived.location == CONFINS_MARCHA_LABEL
    await mission.on_location(actor)
    view = await mission.resume_active(actor)
    assert view is not None and view.quest_id == P31_ID and view.step == 2
    return view


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "p30_status", "allowed"),
    ((50, "completed", False), (51, "active", False), (51, "completed", True)),
)
async def test_confins_entry_requires_p30_and_level_51(
    database, level, p30_status, allowed
):
    actor, road, sessions = await _seed_confins_actor(
        database, 790310 + level + (p30_status == "active"),
        level=level,
        p30_status=p30_status,
    )
    arrived = await road.travel_route(actor, CONFINS_MARCHA_LABEL)
    assert (arrived is not None) is allowed
    if allowed:
        mission = AltosMissionService(sessions, "ocaso")
        await mission.on_location(actor)
        view = await mission.resume_active(actor)
        assert view is not None and view.quest_id == P31_ID and view.step == 2
        assert view.progress["arrival_recorded"] is True
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert (
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id, Quest.quest_id == P31_ID
                )
            )
            is not None
        ) is allowed


@pytest.mark.asyncio
async def test_p31_solo_entry_story_rewards_hunt_round_and_exploration(
    database, monkeypatch
):
    actor, road, sessions = await _seed_confins_actor(database, 790330)
    mission = AltosMissionService(sessions, "ocaso")
    async with sessions() as session:
        seeded_character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert seeded_character is not None
        character_id = seeded_character.id
        initial_xp, initial_crowns = seeded_character.xp, seeded_character.crowns

    view = await _enter_marcha(road, mission, actor)
    local = await road.resume(actor)
    assert local is not None and not local.hunt_enabled and not local.explore_enabled
    assert await road.prepare_hunt(actor) is None
    assert await road.prepare_explore(actor) is None
    assert await road.travel_route(actor, "Estradas Ausentes") is None

    first_marker = await mission.advance(actor, view.state_version, "inspect_talen_marker")
    assert first_marker is not None and first_marker.step == 2
    duplicate = await mission.advance(actor, view.state_version, "inspect_talen_marker")
    assert duplicate is not None and duplicate.state_version == first_marker.state_version
    second_marker = await mission.advance(
        actor, first_marker.state_version, "inspect_ground_marker"
    )
    assert second_marker is not None and second_marker.step == 3
    assert set(second_marker.progress["route_marker_evidence"]) == {
        "inspect_talen_marker",
        "inspect_ground_marker",
    }
    view = await mission.advance(actor, second_marker.state_version, "discover_marco_duplo")
    assert view is not None and view.step == 4
    async with sessions() as session:
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == "bonfire.confins.marco_duplo",
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.confins.regiao",
            )
        ) is not None

    battle = await mission.start_solo_combat(actor, view.state_version, P31_ID)
    assert battle is not None and battle.kind == "combat" and battle.combat is not None
    enemies = [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert enemies[0].name == "Cão de Névoa"
    assert enemies[0].level == 51
    assert battle.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await mission.action(actor, battle.activity_id, battle.combat.version, "attack")
    assert defeated is not None and defeated.step == 4
    assert defeated.progress["awaiting_retry"] is True
    retry = await mission.retry_combat(actor, defeated.state_version, P31_ID)
    assert retry is not None and retry.kind == "combat" and retry.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(actor, retry.activity_id, retry.combat.version, "attack")
    assert victory is not None and victory.step == 5
    assert victory.progress["cao_nevoa_victory"] is True
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.xp, character.crowns) == (initial_xp, initial_crowns)
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P31_REWARD_SOURCE,
            )
        ) is None

    arrived = await road.travel_route(actor, CONFINS_ULTIMO_REFUGIO_LABEL)
    assert arrived is not None and arrived.location == CONFINS_ULTIMO_REFUGIO_LABEL
    await mission.on_location(actor)
    view = await mission.resume_active(actor)
    assert view is not None and view.step == 6
    view = await mission.advance(actor, view.state_version, "discover_testemunha")
    assert view is not None and view.step == 7
    view = await mission.advance(actor, view.state_version, "compare_dual_readings")
    assert view is not None and view.step == 8
    codex_action_version = view.state_version
    completed = await mission.advance(
        actor, codex_action_version, "record_p31_codex_and_conclude"
    )
    assert completed is not None and completed.status == "completed"
    repeated = await mission.advance(
        actor, codex_action_version, "record_p31_codex_and_conclude"
    )
    assert repeated is not None and repeated.status == "completed"

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.xp - initial_xp, character.crowns - initial_crowns) == (
            77_050,
            860,
        )
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P31_MISSION_ID,
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
                ("xp", None, 77_050): 1,
                ("crowns", None, 860): 1,
                ("material", "material.confins.ferro_baliza", 1): 1,
                ("material", "material.confins.musgo_limiar", 1): 1,
            }
        )
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == P31_ID,
                Quest.status == "completed",
                Quest.content_version == P31_CONTENT_VERSION,
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id, CodexEntry.entry_id == P31_CODEX_ENTRY
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == P31_CODEX_ENTRY,
                CodexFragment.fragment_id == P31_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == P31_ACHIEVEMENT,
            )
        ) is not None
        assert await session.scalar(
                select(CharacterCosmetic.cosmetic_id).where(
                CharacterCosmetic.character_id == character_id,
                CharacterCosmetic.cosmetic_id == P31_TITLE_COSMETIC,
                CharacterCosmetic.cosmetic_type == "title",
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == "bonfire.confins.testemunha",
            )
        ) is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == CONFINS_ULTIMO_REFUGIO_LOCATION,
            )
        ) is not None
        discoverable_confins = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character_id,
                        LocationDiscovery.location_id.like("location.confins.%"),
                    )
                )
            ).all()
        )
        assert discoverable_confins == {
            "location.confins.marcha_nebulosa",
            CONFINS_ULTIMO_REFUGIO_LOCATION,
        }

    refuge_view = await road.resume(actor)
    assert refuge_view is not None
    assert not refuge_view.hunt_enabled and not refuge_view.explore_enabled
    march = await road.travel_route(actor, CONFINS_MARCHA_LABEL)
    assert march is not None and march.location == CONFINS_MARCHA_LABEL
    march_view = await road.resume(actor)
    assert march_view is not None and march_view.hunt_enabled and march_view.explore_enabled
    assert await road.prepare_hunt(actor) is not None
    assert await road.prepare_explore(actor) is not None
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "unlock.round.confins.marcha",
            )
        ) is None

    rounds = disable_round_pvpve_for_test(RoundService(sessions, "ocaso"))
    blocked_round = await rounds.prepare_round(actor, 5)
    assert blocked_round is None or blocked_round.kind != "round_prepare"

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.hp = character.max_hp

    async def materialize_manual_hunt(session, character, world, profile):
        defeat_view = await road._materialize_manual_hunt(
            session, character, world, profile, seed="confins-p31-round-test"
        )
        assert defeat_view.activity_id is not None
        activity = await session.get(GameActivity, defeat_view.activity_id)
        assert activity is not None
        return await road._combat_view(session, character, activity)

    monkeypatch.setattr(road.pvpve, "queue_manual_hunt", materialize_manual_hunt)
    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    hunt = await road.start_hunt(actor)
    assert hunt is not None and hunt.kind == "combat" and hunt.combat is not None
    result = await road.action(actor, hunt.activity_id, hunt.combat.version, "attack")
    assert result is not None and result.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "unlock.round.confins.marcha",
            )
        ) is not None
    round_ready = await rounds.prepare_round(actor, 5)
    assert round_ready is not None and round_ready.kind == "round_prepare"

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.vigor = character.max_vigor

    def great_discovery(*_args, **_kwargs):
        return (
            "great_discovery",
            "explore.confins.marcha.duas_balizas",
            "Duas balizas físicas da mesma estrada ocupam posições incompatíveis.",
        )

    monkeypatch.setattr(road_module, "_explore_result", great_discovery)
    before_explore = None
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        before_explore = character.xp
    attempt = await road.explore(actor)
    assert attempt is not None and attempt.attempt_id is not None
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and before_explore is not None
        assert character.xp - before_explore == 12_744
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.confins.marcos_incompativeis",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "explore.confins.marcha.duas_balizas",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == CONFINS_CARTOGRAPHER_ACHIEVEMENT,
            )
        ) is None
    await road.acknowledge_result(actor, attempt.attempt_id)

    async with sessions.begin() as session:
        completed_attempt = await session.get(ExplorationAttempt, attempt.attempt_id)
        assert completed_attempt is not None
        completed_attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)

    def knowledge_discovery(*_args, **_kwargs):
        return (
            "knowledge",
            "explore.confins.marcha.caderno_marcha",
            "O Caderno de Ida e Volta registra duas leituras honestas da rota.",
        )

    monkeypatch.setattr(road_module, "_explore_result", knowledge_discovery)
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        before_knowledge = character.xp
    notebook = await road.explore(actor)
    assert notebook is not None and notebook.attempt_id is not None
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert character.xp - before_knowledge == 3_983
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == "codex.confins.duas_leituras_rota",
                CodexFragment.fragment_id == "explore.confins.marcha.caderno_marcha",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == CONFINS_CARTOGRAPHER_ACHIEVEMENT,
            )
        ) is None


@pytest.mark.asyncio
async def test_p31_shared_marker_evidence_is_individual_and_persistent(database):
    actors = (790340, 790341)
    _leader, road, sessions = await _seed_confins_actor(database, actors[0])
    await _seed_confins_actor(database, actors[1])
    async with sessions() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper_name = helper.name
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invite = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    views = {}
    for actor in actors:
        views[actor] = await _enter_marcha(road, mission, actor)

    first = await mission.advance(actors[0], views[actors[0]].state_version, "inspect_talen_marker")
    assert first is not None and first.step == 2
    helper = await mission.resume_active(actors[1])
    assert helper is not None and helper.step == 2
    assert helper.progress["route_marker_evidence"] == ["inspect_talen_marker"]
    second = await mission.advance(actors[0], first.state_version, "inspect_ground_marker")
    assert second is not None and second.step == 3
    helper = await mission.resume_active(actors[1])
    assert helper is not None and helper.step == 3
    assert set(helper.progress["route_marker_evidence"]) == {
        "inspect_talen_marker",
        "inspect_ground_marker",
    }
    async with sessions() as session:
        characters = (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all()
        character_by_actor = {row.telegram_id: row for row in characters}
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id.in_(
                        tuple(row.id for row in characters)
                    ),
                    CampaignObjectiveCredit.quest_id == P31_ID,
                    CampaignObjectiveCredit.objective_id.in_(
                        ("p31.inspect_talen_marker", "p31.inspect_ground_marker")
                    ),
                )
            )
        ).all()
        assert len(credits) == 4
        assert {row.character_id for row in credits} == {
            character_by_actor[actor].id for actor in actors
        }

    view = await mission.advance(
        actors[0], second.state_version, "discover_marco_duplo"
    )
    assert view is not None and view.step == 4
    helper = await mission.resume_active(actors[1])
    assert helper is not None and helper.step == 4
    pending = await mission.propose_group_combat(actors[0], view.state_version, P31_ID)
    assert pending is not None and pending.proposal_id is not None
    proposal = await groups.activity_proposal(actors[0], pending.proposal_id)
    accepted = await groups.respond_activity(
        actors[1], proposal.proposal_id, expected_revision=proposal.revision, accept=True
    )
    started = await mission.start_group_combat(
        actors[0], proposal.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None and started.group_size == 2
    assert started.combat.variant is None
    assert len(
        [fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"]
    ) == 1
    async with sessions() as session:
        encounter = await session.get(CampaignSharedEncounter, started.encounter_id)
        assert encounter is not None and encounter.roster_size == 2

    await _seed_enemy_at_one_hp(database, started.encounter_id)
    views = {actor: await mission.resume(actor, P31_ID) for actor in actors}
    combat = next(item.combat for item in views.values() if item is not None)
    active_actor = next(
        actor
        for actor, item in views.items()
        if item is not None and item.combat_actor_key == active_player_key(combat)
    )
    active_view = views[active_actor]
    victory = await mission.action(
        active_actor,
        active_view.activity_id,
        combat.version,
        "attack",
        target_id="enemy",
    )
    assert victory is not None and victory.step == 5
    for actor in actors:
        resumed = await mission.resume_active(actor)
        assert resumed is not None and resumed.step == 5
        assert resumed.progress["cao_nevoa_victory"] is True


def test_confins_catalog_and_activity_pools_match_the_opening_contract():
    assert CONFINS_REGION_LABEL == "Confins do Véu"
    assert CONFINS_LOCATION_CATALOG == (
        "Marcha Nebulosa",
        "Último Refúgio",
        "Estradas Ausentes",
        "Fraturas do Limiar",
        "Nó Central",
        "Câmara da Regência",
    )
    assert CONFINS_LOCATIONS == frozenset(CONFINS_LOCATION_CATALOG[:2])
    assert TRAVEL_LOCATIONS.isdisjoint(CONFINS_LOCATION_CATALOG[2:])
    assert HUNT_PROFILES[CONFINS_MARCHA_LOCATION] is CONFINS_MARCHA_PROFILE
    assert CONFINS_MARCHA_PROFILE.creature_weights == (
        (CONFINS_CAO_NEVOA, 50),
        (CONFINS_GRALHA_DUAS_SOMBRAS, 26),
        (CONFINS_CERVO_PASSO_DUPLO, 15),
        (CONFINS_PREDADOR_DUAS_PEGADAS, 9),
    )
    assert CONFINS_MARCHA_PROFILE.variant_chance == 14
    assert creature_for(CONFINS_CERVO_PASSO_DUPLO).unlock_level > 51
    assert creature_for(CONFINS_PREDADOR_DUAS_PEGADAS).unlock_level > 51
    assert MATERIAL_POOLS[CONFINS_CAO_NEVOA] == (("material.confins.couro_marcha", 100),)
    assert MATERIAL_POOLS[CONFINS_GRALHA_DUAS_SOMBRAS] == (
        ("material.confins.musgo_limiar", 60),
        ("material.confins.po_referencia", 40),
    )
    assert MATERIAL_POOLS[CONFINS_CERVO_PASSO_DUPLO] == (
        ("material.confins.couro_marcha", 90),
        ("material.confins.musgo_limiar", 10),
    )
    assert MATERIAL_POOLS[CONFINS_PREDADOR_DUAS_PEGADAS] == (
        ("material.confins.couro_marcha", 85),
        ("material.confins.po_referencia", 15),
    )
    exploration = EXPLORATION_PROFILES[CONFINS_MARCHA_LOCATION]
    assert {
        row.result_id for row in exploration.results
    } == {
        "explore.confins.marcha.duas_balizas",
        "explore.confins.marcha.caderno_marcha",
        "explore.confins.marcha.giz_apagado",
        "explore.confins.marcha.marca_repetida",
        "explore.confins.marcha.sino_distante",
        "explore.confins.marcha.combate",
        "explore.confins.marcha.recurso",
        "explore.confins.marcha.atmos.nevoa_sem_vento",
        "explore.confins.marcha.atmos.pedra_volta",
        "explore.confins.marcha.atmos.passo_umido",
    }
    assert CONFINS_EXPLORATION_UNIQUE_XP == {
        "explore.confins.marcha.duas_balizas": 12_744,
        "explore.confins.marcha.caderno_marcha": 3_983,
    }
    assert len(CONFINS_CARTOGRAPHER_UNIQUE_IDS) == 11
    assert CONFINS_CARTOGRAPHER_UNIQUE_IDS[:2] == tuple(
        row.result_id for row in exploration.results if row.unique
    )
    assert "codex.confins.duas_leituras_rota" in CODEX_BY_ID
    assert CODEX_FRAGMENTS["codex.confins.duas_leituras_rota"].title == "Dois marcos honestos"
    assert ACHIEVEMENT_BY_ID["achievement.confins.primeira_marcha"].name == "Primeira Marcha"
