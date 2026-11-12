from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from asterion.application import road as road_module
from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P32_CONTENT_VERSION,
    P32_ID,
    P33_ACHIEVEMENT,
    P33_CODEX_ENTRY,
    P33_CONTENT_VERSION,
    P33_ID,
    P33_REWARD_OPTIONS,
    P33_REWARD_SOURCE,
    P33_TITLE_COSMETIC,
    AltosMissionService,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.knowledge_catalog import ACHIEVEMENT_BY_ID, CODEX_BY_ID
from asterion.application.road import (
    CONFINS_ESTRADAS_AUSENTES_LABEL,
    CONFINS_EXPLORATION_UNIQUE_XP,
    CONFINS_FRATURAS_LIMIAR_LABEL,
    CONFINS_REGION_LABEL,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.domain.road import (
    CONFINS_ANDARILHO_REPETIDO,
    CONFINS_ARANHA_LIMIAR,
    CONFINS_CASCA_REFLEXO,
    CONFINS_CERVO_PASSO_DUPLO,
    CONFINS_CUSTODIO_DESFASADO,
    CONFINS_FRATURAS_LIMIAR_LOCATION,
    CONFINS_FRATURAS_PROFILE,
    CONFINS_MARIPOSA_SEM_HORIZONTE,
    CONFINS_SANGUESSUGA_PALIDA,
    CONFINS_VIUVA_INTERVALO,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    LOCATION_LEVEL_BANDS,
    MATERIAL_POOLS,
    creature_for,
    select_creature,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    CampaignObjectiveCredit,
    Character,
    CharacterCosmetic,
    CodexFragment,
    EquipmentItem,
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
from tests.test_confins_p32 import _seed_p32_actor
from tests.test_s4_s5_integration import _terminal


async def _seed_p33_actor(
    database, actor: int, *, level: int = 55, p32_status: str = "completed"
):
    actor, _road, sessions = await _seed_p32_actor(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_ESTRADAS_AUSENTES_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P32_ID,
                title="A Fratura",
                status=p32_status,
                step=6 if p32_status == "completed" else 1,
                content_version=P32_CONTENT_VERSION,
                state_version=6 if p32_status == "completed" else 1,
                progress={"completed": p32_status == "completed"},
            )
        )
        session.add(
            LocationDiscovery(
                character_id=character.id,
                location_id="location.confins.estradas_ausentes",
            )
        )
        session.add(
            Unlock(
                character_id=character.id,
                unlock_id="unlock.location.confins.estradas_ausentes",
            )
        )
    return actor, RoadService(sessions, "ocaso"), sessions


@pytest.mark.parametrize(
    ("level", "p32_status", "expected_status"),
    ((54, "completed", "suspended"), (55, "active", None)),
)
@pytest.mark.asyncio
async def test_p33_gate_suspension_and_no_premature_fraturas_access(
    database, level, p32_status, expected_status
):
    actor, _road, sessions = await _seed_p33_actor(
        database, 793300 + level + (p32_status == "active"),
        level=level,
        p32_status=p32_status,
    )
    mission = AltosMissionService(sessions, "ocaso")

    view = await mission.start_p33(actor)
    if expected_status is None:
        assert view is None
    else:
        assert view is not None and view.status == expected_status
        assert view.quest_id == P33_ID

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P33_ID
            )
        ) is None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "unlock.location.confins.fraturas_limiar",
            )
        ) is None


def test_confins_fraturas_catalog_matches_source_and_filters_level_eligibility():
    assert LOCATION_LEVEL_BANDS[CONFINS_FRATURAS_LIMIAR_LABEL] == (55, 59)
    assert HUNT_PROFILES[CONFINS_FRATURAS_LIMIAR_LOCATION] is CONFINS_FRATURAS_PROFILE
    assert CONFINS_FRATURAS_PROFILE.creature_weights == (
        (CONFINS_ANDARILHO_REPETIDO, 14),
        (CONFINS_ARANHA_LIMIAR, 12),
        (CONFINS_CERVO_PASSO_DUPLO, 14),
        (CONFINS_SANGUESSUGA_PALIDA, 17),
        (CONFINS_CASCA_REFLEXO, 15),
        (CONFINS_MARIPOSA_SEM_HORIZONTE, 10),
        (CONFINS_VIUVA_INTERVALO, 10),
        (CONFINS_CUSTODIO_DESFASADO, 8),
    )
    assert CONFINS_FRATURAS_PROFILE.variant_chance == 18
    assert creature_for(CONFINS_VIUVA_INTERVALO).unlock_level == 57
    assert creature_for(CONFINS_CUSTODIO_DESFASADO).unlock_level == 59
    assert MATERIAL_POOLS[CONFINS_SANGUESSUGA_PALIDA] == (
        ("material.confins.musgo_limiar", 65),
        ("material.confins.po_referencia", 35),
    )
    assert MATERIAL_POOLS[CONFINS_CASCA_REFLEXO] == (
        ("material.confins.ferro_baliza", 40),
        ("material.confins.po_referencia", 60),
    )
    assert MATERIAL_POOLS[CONFINS_MARIPOSA_SEM_HORIZONTE] == (
        ("material.confins.po_referencia", 75),
        ("material.confins.musgo_limiar", 25),
    )
    assert MATERIAL_POOLS[CONFINS_CUSTODIO_DESFASADO] == (
        ("material.confins.ferro_baliza", 80),
        ("material.confins.po_referencia", 20),
    )

    at_55 = {
        select_creature(f"p33-l55-{index}", 55, CONFINS_FRATURAS_PROFILE).creature_id
        for index in range(512)
    }
    assert CONFINS_MARIPOSA_SEM_HORIZONTE not in at_55
    assert CONFINS_VIUVA_INTERVALO not in at_55
    assert CONFINS_CUSTODIO_DESFASADO not in at_55
    at_57 = {
        select_creature(f"p33-l57-{index}", 57, CONFINS_FRATURAS_PROFILE).creature_id
        for index in range(512)
    }
    assert CONFINS_CUSTODIO_DESFASADO not in at_57
    assert at_55 <= set(dict(CONFINS_FRATURAS_PROFILE.creature_weights))
    assert {
        "explore.confins.fraturas.braseiro_limiar": 14_920,
        "explore.confins.fraturas.corte_referencia": 14_920,
        "explore.confins.fraturas.ficha_dupla": 4_663,
    }.items() <= CONFINS_EXPLORATION_UNIQUE_XP.items()
    fraturas_results = {
        row.result_id
        for row in EXPLORATION_PROFILES[CONFINS_FRATURAS_LIMIAR_LOCATION].results
    }
    assert fraturas_results == {
        "explore.confins.fraturas.braseiro_limiar",
        "explore.confins.fraturas.corte_referencia",
        "explore.confins.fraturas.ficha_dupla",
        "explore.confins.fraturas.linhas_gastas",
        "explore.confins.fraturas.angulo_sem_retorno",
        "explore.confins.fraturas.eco_pedra",
        "explore.confins.fraturas.combate",
        "explore.confins.fraturas.recurso",
        "explore.confins.fraturas.atmos.silencio_limiar",
        "explore.confins.fraturas.atmos.dobras_nevoa",
        "explore.confins.fraturas.atmos.pedra_sem_mancha",
    }
    assert P33_CODEX_ENTRY in CODEX_BY_ID
    assert ACHIEVEMENT_BY_ID[P33_ACHIEVEMENT].name == "Nomear sem Dominar"


@pytest.mark.asyncio
async def test_p33_progress_retry_choice_rewards_unique_discoveries_and_round(
    database, monkeypatch
):
    actor, road, sessions = await _seed_p33_actor(database, 793330)
    mission = AltosMissionService(sessions, "ocaso")
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character_id = character.id
        initial_xp, initial_crowns = character.xp, character.crowns

    p33 = await mission.start_p33(actor)
    assert p33 is not None and p33.quest_id == P33_ID and p33.step == 1
    assert p33.status == "active"
    assert await road.travel_route(actor, CONFINS_FRATURAS_LIMIAR_LABEL) is not None
    await mission.on_location(actor)
    p33 = await mission.resume(actor, P33_ID)
    assert p33 is not None and p33.step == 2
    assert set(p33.progress["completed_steps"]) >= {1}

    local = await road.resume(actor)
    assert local is not None and not local.hunt_enabled and not local.explore_enabled
    assert await road.prepare_hunt(actor) is None
    assert await road.prepare_explore(actor) is None
    assert await road.travel_route(actor, "Nó Central") is None
    async with sessions() as session:
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "location.confins.fraturas_limiar",
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == "bonfire.confins.limiar_firme",
            )
        ) is None

    for evidence in (
        "inspect_stone_position",
        "inspect_wear_state",
        "inspect_trail_observation_sequence",
    ):
        current = await mission.resume(actor, P33_ID)
        assert current is not None and current.step == 2
        p33 = await mission.advance(actor, current.state_version, evidence)
        assert p33 is not None
    assert p33.step == 3
    assert set(p33.progress["physical_evidence_ids"]) == {
        "inspect_stone_position",
        "inspect_wear_state",
        "inspect_trail_observation_sequence",
    }

    battle = await mission.start_solo_combat(actor, p33.state_version, P33_ID)
    assert battle is not None and battle.kind == "combat" and battle.combat is not None
    enemies = [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert (enemies[0].name, enemies[0].level, battle.combat.variant) == (
        "Casca de Reflexo",
        55,
        None,
    )
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    failed = await mission.action(actor, battle.activity_id, battle.combat.version, "attack")
    assert failed is not None and failed.step == 3
    assert failed.progress["awaiting_retry"] is True
    retry = await mission.retry_combat(actor, failed.state_version, P33_ID)
    assert retry is not None and retry.kind == "combat" and retry.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    p33 = await mission.action(actor, retry.activity_id, retry.combat.version, "attack")
    assert p33 is not None and p33.step == 4
    assert p33.progress["scripted_casca_victory"] is True
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P33_REWARD_SOURCE,
            )
        ) is None

    p33 = await mission.advance(actor, p33.state_version, "interpret_avesso_with_roven")
    assert p33 is not None and p33.step == 5
    p33 = await mission.advance(actor, p33.state_version, "record_avesso_codex")
    assert p33 is not None and p33.step == 6
    assert p33.progress["codex_recorded"] is True
    selected_id = P33_REWARD_OPTIONS["selo_marco_valido"][0]
    p33 = await mission.choose_p33_reward(actor, p33.state_version, "selo_marco_valido")
    assert p33 is not None and p33.status == "completed"
    duplicate = await mission.choose_p33_reward(
        actor, p33.state_version - 1, "capuz_dupla_leitura"
    )
    assert duplicate is not None and duplicate.status == "completed"

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.xp - initial_xp, character.crowns - initial_crowns) == (
            87_650,
            920,
        )
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P33_REWARD_SOURCE,
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
                ("xp", None, 87_650): 1,
                ("crowns", None, 920): 1,
                ("equipment", selected_id, 1): 1,
            }
        )
        equipment = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.character_id == character_id,
                EquipmentItem.source_key == f"{P33_REWARD_SOURCE}:equipment",
            )
        )
        assert equipment is not None
        assert (equipment.item_name, equipment.rarity, equipment.slot, equipment.item_level) == (
            "Selo do Marco Válido",
            "Raro",
            "Acessório",
            55,
        )
        assert equipment.bound is True
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == P33_CODEX_ENTRY,
                CodexFragment.fragment_id == P33_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == P33_ACHIEVEMENT,
            )
        ) is not None
        assert await session.scalar(
            select(CharacterCosmetic.cosmetic_id).where(
                CharacterCosmetic.character_id == character_id,
                CharacterCosmetic.cosmetic_id == P33_TITLE_COSMETIC,
            )
        ) is not None
        unlocks = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(Unlock.character_id == character_id)
                )
            ).all()
        )
        assert {
            "unlock.hunt.confins.fraturas",
            "unlock.explore.confins.fraturas",
            "narrative.confins.avesso_nomeado",
        } <= unlocks
        assert "unlock.location.confins.no_central" not in unlocks
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == P33_ID,
                Quest.content_version == P33_CONTENT_VERSION,
                Quest.status == "completed",
            )
        ) is not None

    local = await road.resume(actor)
    assert local is not None and local.hunt_enabled and local.explore_enabled
    rounds = disable_round_pvpve_for_test(RoundService(sessions, "ocaso"))
    before_hunt = await rounds.prepare_round(actor, 5)
    assert before_hunt is None or before_hunt.kind != "round_prepare"

    # The Fraturas discoveries are independent and permanent; P33 itself grants none.
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.vigor = character.max_vigor
        character.hp = character.max_hp
    unique_results = (
        ("explore.confins.fraturas.braseiro_limiar", "great_discovery"),
        ("explore.confins.fraturas.corte_referencia", "great_discovery"),
        ("explore.confins.fraturas.ficha_dupla", "knowledge"),
    )
    for result_id, category in unique_results:
        monkeypatch.setattr(
            road_module,
            "_explore_result",
            lambda *_args, _id=result_id, _category=category: (
                _category,
                _id,
                "Evidência observada nas Fraturas do Limiar.",
            ),
        )
        attempt_view = await road.explore(actor)
        assert attempt_view is not None and attempt_view.attempt_id is not None
        await road.acknowledge_result(actor, attempt_view.attempt_id)
        async with sessions.begin() as session:
            attempt = await session.get(ExplorationAttempt, attempt_view.attempt_id)
            assert attempt is not None
            attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)

    async with sessions() as session:
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == "bonfire.confins.limiar_firme",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == "codex.confins.fratura_definicao",
                CodexFragment.fragment_id == "explore.confins.fraturas.corte_referencia",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == P33_CODEX_ENTRY,
                CodexFragment.fragment_id == "explore.confins.fraturas.ficha_dupla",
            )
        ) is not None

    async def materialize_manual_hunt(session, character, world, profile):
        view = await road._materialize_manual_hunt(
            session, character, world, profile, seed="confins-p33-round-test"
        )
        assert view.activity_id is not None
        activity = await session.get(GameActivity, view.activity_id)
        assert activity is not None
        return await road._combat_view(session, character, activity)

    monkeypatch.setattr(road.pvpve, "queue_manual_hunt", materialize_manual_hunt)
    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    hunt = await road.start_hunt(actor)
    assert hunt is not None and hunt.kind == "combat" and hunt.combat is not None
    result = await road.action(actor, hunt.activity_id, hunt.combat.version, "attack")
    assert result is not None and result.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    after_hunt = await rounds.prepare_round(actor, 5)
    assert after_hunt is not None and after_hunt.kind == "round_prepare"
    async with sessions() as session:
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "unlock.round.confins.fraturas",
            )
        ) is not None


@pytest.mark.asyncio
async def test_p33_shared_physical_evidence_skips_individually_ineligible_member(database):
    actors = (793340, 793341)
    await _seed_p33_actor(database, actors[0])
    _actor, _road, sessions = await _seed_p33_actor(database, actors[1])
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
        view = await mission.start_p33(actor)
        assert view is not None and view.status == "active"
        arrived = await road.travel_route(actor, CONFINS_FRATURAS_LIMIAR_LABEL)
        assert arrived is not None and arrived.location == CONFINS_FRATURAS_LIMIAR_LABEL
        await mission.on_location(actor)
    async with sessions.begin() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper.level = 54

    for evidence in (
        "inspect_stone_position",
        "inspect_wear_state",
        "inspect_trail_observation_sequence",
    ):
        leader = await mission.resume(actors[0], P33_ID)
        assert leader is not None and leader.step == 2
        await mission.advance(actors[0], leader.state_version, evidence)

    leader = await mission.resume(actors[0], P33_ID)
    helper = await mission.resume(actors[1], P33_ID)
    assert leader is not None and leader.step == 3
    assert helper is not None and helper.step == 2
    assert helper.progress["physical_evidence_ids"] == []
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert character is not None
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id == character.id,
                    CampaignObjectiveCredit.quest_id == P33_ID,
                )
            )
        ).all()
        assert not any(row.objective_id.startswith("p33.inspect_") for row in credits)


@pytest.mark.asyncio
async def test_p33_group_member_collects_evidence_alone_and_scripted_victory_is_solo(
    database, monkeypatch
):
    actors = (793350, 793351)
    await _seed_p33_actor(database, actors[0])
    _actor, _road, sessions = await _seed_p33_actor(database, actors[1])
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
        view = await mission.start_p33(actor)
        assert view is not None and view.status == "active" and view.step == 1
        arrived = await road.travel_route(actor, CONFINS_FRATURAS_LIMIAR_LABEL)
        assert arrived is not None and arrived.location == CONFINS_FRATURAS_LIMIAR_LABEL
        await mission.on_location(actor)

    # Objectives are Solo (Ação × Consequência §5): the helper stays on step 2.
    for evidence in (
        "inspect_stone_position",
        "inspect_wear_state",
        "inspect_trail_observation_sequence",
    ):
        leader = await mission.resume(actors[0], P33_ID)
        assert leader is not None and leader.step == 2
        await mission.advance(actors[0], leader.state_version, evidence)
        view = await mission.resume(actors[0], P33_ID)
        assert view is not None and evidence in view.progress["physical_evidence_ids"]
        helper_view = await mission.resume(actors[1], P33_ID)
        assert helper_view is not None and helper_view.step == 2
        assert not helper_view.progress.get("physical_evidence_ids")

    leader = await mission.resume(actors[0], P33_ID)
    assert leader is not None and leader.step == 3
    # P33 is not a Boss: the Group proposal is refused, the fight is Solo.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await mission.propose_group_combat(actors[0], leader.state_version, P33_ID)
    assert not await groups.activity_proposals(actors[0])
    started = await mission.start_solo_combat(actors[0], leader.state_version, P33_ID)
    assert started is not None and started.combat is not None
    assert started.group_size == 1 and not started.combat.party_mode
    assert started.combat.variant is None
    enemies = [fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1 and enemies[0].level == 55
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actors[0], started.activity_id, started.combat.version, "attack"
    )
    assert victory is not None
    view = await mission.resume(actors[0], P33_ID)
    assert view is not None and view.step == 4
    assert view.progress["scripted_casca_victory"] is True
    helper_view = await mission.resume(actors[1], P33_ID)
    assert helper_view is not None and helper_view.step == 2
    assert not helper_view.progress.get("scripted_casca_victory")
