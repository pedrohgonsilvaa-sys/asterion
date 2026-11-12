from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from asterion.application import road as road_module
from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P31_CONTENT_VERSION,
    P31_ID,
    P32_ACHIEVEMENT,
    P32_CODEX_ENTRY,
    P32_ID,
    P32_MISSION_ID,
    P32_REWARD_SOURCE,
    AltosMissionService,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.knowledge_catalog import ACHIEVEMENT_BY_ID, CODEX_BY_ID
from asterion.application.road import (
    CONFINS_ESTRADAS_AUSENTES_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.domain.road import (
    CONFINS_ANDARILHO_REPETIDO,
    CONFINS_ARANHA_LIMIAR,
    CONFINS_CAO_NEVOA,
    CONFINS_ESTRADAS_AUSENTES_LOCATION,
    CONFINS_ESTRADAS_PROFILE,
    CONFINS_GRALHA_DUAS_SOMBRAS,
    CONFINS_VIGIA_DESFASADO,
    CONFINS_VIUVA_INTERVALO,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    creature_for,
    select_creature,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    Character,
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
from tests.helpers.pvpve import disable_round_pvpve_for_test
from tests.test_confins_p31 import _seed_confins_actor
from tests.test_s4_s5_integration import _terminal


async def _seed_p32_actor(database, actor: int, *, level: int = 53, p31_status="completed"):
    actor, _road, sessions = await _seed_confins_actor(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_ULTIMO_REFUGIO_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id=P31_ID,
                title="Onde o Véu Afina",
                status=p31_status,
                step=8 if p31_status == "completed" else 1,
                content_version=P31_CONTENT_VERSION,
                state_version=8 if p31_status == "completed" else 1,
                progress={"completed": p31_status == "completed"},
            )
        )
        session.add_all(
            [
                LocationDiscovery(
                    character_id=character.id,
                    location_id="location.confins.marcha_nebulosa",
                ),
                LocationDiscovery(
                    character_id=character.id,
                    location_id="location.confins.ultimo_refugio",
                ),
            ]
        )
        session.add_all(
            [
                Unlock(
                    character_id=character.id,
                    unlock_id="unlock.location.confins.marcha_nebulosa",
                ),
                Unlock(
                    character_id=character.id,
                    unlock_id="unlock.location.confins.ultimo_refugio",
                ),
            ]
        )
    return actor, RoadService(sessions, "ocaso"), sessions


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "p31_status", "expected_status"),
    ((53, "active", None), (52, "completed", "suspended")),
)
async def test_p32_gate_suspension_and_activation(database, level, p31_status, expected_status):
    actor, _road, sessions = await _seed_p32_actor(
        database, 793200 + level, level=level, p31_status=p31_status
    )
    mission = AltosMissionService(sessions, "ocaso")

    view = await mission.start_p32(actor)
    if expected_status is None:
        assert view is None
    else:
        assert view is not None and view.status == expected_status

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P32_ID
            )
        ) is None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "unlock.location.confins.estradas_ausentes",
            )
        ) is None

    if expected_status == "suspended":
        async with sessions.begin() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            character.level = 53
        activated = await mission.start_p32(actor)
        assert activated is not None and activated.status == "active"
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            assert await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == "unlock.location.confins.estradas_ausentes",
                )
            ) is not None


@pytest.mark.asyncio
async def test_p32_solo_completion_activities_discoveries_and_round(database, monkeypatch):
    actor, road, sessions = await _seed_p32_actor(database, 793230)
    mission = AltosMissionService(sessions, "ocaso")
    p32 = await mission.start_p32(actor)
    assert p32 is not None and p32.status == "active" and p32.step == 1

    p32 = await mission.advance(actor, p32.state_version, "receive_p32_route_traces")
    assert p32 is not None and p32.step == 2
    p32 = await road.travel_route(actor, CONFINS_ESTRADAS_AUSENTES_LABEL)
    assert p32 is not None and p32.location == CONFINS_ESTRADAS_AUSENTES_LABEL
    await mission.on_location(actor)
    p32 = await mission.resume_active(actor)
    assert p32 is not None and p32.quest_id == P32_ID and p32.step == 3
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == CONFINS_ESTRADAS_AUSENTES_LOCATION,
            )
        ) is not None

    local = await road.resume(actor)
    assert local is not None and not local.hunt_enabled and not local.explore_enabled
    assert await road.prepare_hunt(actor) is None
    assert await road.prepare_explore(actor) is None
    assert await road.travel_route(actor, "Fraturas do Limiar") is None

    for evidence in (
        "inspect_finished_foundation",
        "inspect_absent_map_marker",
        "inspect_discordant_return_record",
    ):
        p32 = await mission.advance(actor, p32.state_version, evidence)
        assert p32 is not None
    assert p32.step == 4

    initial_xp = None
    initial_crowns = None
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        initial_xp, initial_crowns = character.xp, character.crowns

    battle = await mission.start_solo_combat(actor, p32.state_version, P32_ID)
    assert battle is not None and battle.kind == "combat" and battle.combat is not None
    enemies = [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert enemies[0].name == "Andarilho Repetido" and enemies[0].level == 53
    assert battle.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    p32 = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert p32 is not None and p32.step == 4
    assert p32.progress["awaiting_retry"] is True
    retry = await mission.retry_combat(actor, p32.state_version, P32_ID)
    assert retry is not None and retry.kind == "combat" and retry.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    p32 = await mission.action(
        actor, retry.activity_id, retry.combat.version, "attack"
    )
    assert p32 is not None and p32.step == 5
    assert p32.progress["scripted_andarilho_victory"] is True
    assert p32.progress["andarilho_not_clone_nor_soul_observed"] is True
    p32 = await mission.advance(actor, p32.state_version, "compare_fracture_evidence")
    assert p32 is not None and p32.step == 6
    completed = await mission.advance(
        actor, p32.state_version, "record_fracture_codex_and_conclude"
    )
    assert completed is not None and completed.status == "completed"
    duplicate = await mission.advance(
        actor, p32.state_version, "record_fracture_codex_and_conclude"
    )
    assert duplicate is not None and duplicate.status == "completed"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert (character.xp - initial_xp, character.crowns - initial_crowns) == (
            82_250,
            900,
        )
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P32_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert Counter((item.kind, item.item_id, item.quantity) for item in components) == Counter(
            {
                ("xp", None, 82_250): 1,
                ("crowns", None, 900): 1,
                ("material", "material.confins.ferro_baliza", 2): 1,
                ("material", "material.confins.musgo_limiar", 1): 1,
                ("material", "material.confins.po_referencia", 1): 1,
            }
        )
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == P32_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.entry_id == P32_CODEX_ENTRY,
                CodexFragment.fragment_id == P32_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == P32_ACHIEVEMENT,
            )
        ) is not None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P32_MISSION_ID,
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
            "unlock.hunt.confins.estradas",
            "unlock.explore.confins.estradas",
            "narrative.confins.fratura_reconhecida",
        } <= unlocks
        assert "unlock.dungeon.confins.arquivo_retorno" not in unlocks
        assert "unlock.location.confins.fraturas_limiar" not in unlocks

    local = await road.resume(actor)
    assert local is not None and local.hunt_enabled and local.explore_enabled
    assert await road.prepare_hunt(actor) is not None
    assert await road.prepare_explore(actor) is not None
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.vigor = character.max_vigor
    discoveries = (
        (
            "explore.confins.estradas.braseiro_conferida",
            "great_discovery",
            "bonfire.confins.estrada_conferida",
        ),
        (
            "explore.confins.estradas.arquivo_retorno",
            "great_discovery",
            "unlock.dungeon.confins.arquivo_retorno",
        ),
        (
            "explore.confins.estradas.memoria_fundacao",
            "knowledge",
            "codex.confins.casa_presente_ausente",
        ),
    )
    for index, (result_id, category, expected_id) in enumerate(discoveries):
        monkeypatch.setattr(
            road_module,
            "_explore_result",
            lambda *_args, _id=result_id, _category=category: (
                _category,
                _id,
                "Evidência descoberta nas Estradas Ausentes.",
            ),
        )
        discovery = await road.explore(actor)
        assert discovery is not None and discovery.attempt_id is not None
        await road.acknowledge_result(actor, discovery.attempt_id)
        async with sessions() as session:
            attempt = await session.get(ExplorationAttempt, discovery.attempt_id)
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert attempt is not None and attempt.result_id == result_id
            assert character is not None
            if index < 2:
                model = Brazier if index == 0 else Unlock
                key = "brazier_id" if index == 0 else "unlock_id"
                assert await session.scalar(
                    select(model.id).where(
                        model.character_id == character.id,
                        getattr(model, key) == expected_id,
                    )
                ) is not None
            else:
                assert await session.scalar(
                    select(CodexFragment.id).where(
                        CodexFragment.character_id == character.id,
                        CodexFragment.entry_id == expected_id,
                        CodexFragment.fragment_id == result_id,
                    )
                ) is not None
                assert await session.scalar(
                    select(Quest.id).where(
                        Quest.character_id == character.id,
                        Quest.quest_id == "S32",
                        Quest.status == "completed",
                    )
                ) is None
        async with sessions.begin() as session:
            attempt = await session.get(ExplorationAttempt, discovery.attempt_id)
            assert attempt is not None
            attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)

    rounds = disable_round_pvpve_for_test(RoundService(sessions, "ocaso"))
    blocked_round = await rounds.prepare_round(actor, 5)
    assert blocked_round is None or blocked_round.kind != "round_prepare"

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.hp = character.max_hp

    async def materialize_manual_hunt(session, character, world, profile):
        defeat_view = await road._materialize_manual_hunt(
            session, character, world, profile, seed="confins-p32-round-test"
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
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "unlock.round.confins.estradas",
            )
        ) is not None
    assert await rounds.prepare_round(actor, 5) is not None


def test_confins_estradas_catalog_filters_levels_and_matches_source():
    assert HUNT_PROFILES[CONFINS_ESTRADAS_AUSENTES_LOCATION] is CONFINS_ESTRADAS_PROFILE
    assert CONFINS_ESTRADAS_PROFILE.creature_weights == (
        (CONFINS_CAO_NEVOA, 14),
        (CONFINS_GRALHA_DUAS_SOMBRAS, 14),
        (CONFINS_ANDARILHO_REPETIDO, 22),
        (CONFINS_ARANHA_LIMIAR, 36),
        (CONFINS_VIGIA_DESFASADO, 6),
        (CONFINS_VIUVA_INTERVALO, 8),
    )
    assert CONFINS_ESTRADAS_PROFILE.variant_chance == 16
    assert creature_for(CONFINS_VIGIA_DESFASADO).unlock_level == 58
    assert creature_for(CONFINS_VIUVA_INTERVALO).unlock_level == 57
    allowed_at_53 = {
        select_creature(f"p32-level-filter-{index}", 53, CONFINS_ESTRADAS_PROFILE).creature_id
        for index in range(512)
    }
    assert allowed_at_53 <= {
        CONFINS_CAO_NEVOA,
        CONFINS_GRALHA_DUAS_SOMBRAS,
        CONFINS_ANDARILHO_REPETIDO,
        CONFINS_ARANHA_LIMIAR,
    }
    assert CONFINS_VIGIA_DESFASADO not in allowed_at_53
    assert CONFINS_VIUVA_INTERVALO not in allowed_at_53
    assert MATERIAL_POOLS[CONFINS_ANDARILHO_REPETIDO] == (
        ("material.confins.ferro_baliza", 55),
        ("material.confins.po_referencia", 45),
    )
    assert MATERIAL_POOLS[CONFINS_ARANHA_LIMIAR] == (
        ("material.confins.musgo_limiar", 80),
        ("material.confins.po_referencia", 20),
    )
    results = EXPLORATION_PROFILES[CONFINS_ESTRADAS_AUSENTES_LOCATION].results
    assert {result.result_id for result in results} == {
        "explore.confins.estradas.braseiro_conferida",
        "explore.confins.estradas.arquivo_retorno",
        "explore.confins.estradas.memoria_fundacao",
        "explore.confins.estradas.estacas_alternadas",
        "explore.confins.estradas.estrada_sem_ponte",
        "explore.confins.estradas.retorno_sem_ida",
        "explore.confins.estradas.combate",
        "explore.confins.estradas.recurso",
        "explore.confins.estradas.atmos.lama_incompleta",
        "explore.confins.estradas.atmos.placa_curva",
        "explore.confins.estradas.atmos.marco_nao_visto",
    }
    assert P32_CODEX_ENTRY in CODEX_BY_ID
    assert ACHIEVEMENT_BY_ID[P32_ACHIEVEMENT].name == "O Nome da Fratura"


@pytest.mark.asyncio
async def test_p32_group_member_collects_evidence_alone_and_scripted_combat_is_solo(
    database, monkeypatch
):
    actors = (793240, 793241)
    _leader, _road, sessions = await _seed_p32_actor(database, actors[0])
    await _seed_p32_actor(database, actors[1])
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
    road = RoadService(sessions, "ocaso")
    mission = AltosMissionService(sessions, "ocaso", groups=groups)

    views = {}
    for actor in actors:
        views[actor] = await mission.start_p32(actor)
        assert views[actor] is not None and views[actor].step == 1
        views[actor] = await mission.advance(
            actor, views[actor].state_version, "receive_p32_route_traces"
        )
        assert views[actor] is not None and views[actor].step == 2
    for actor in actors:
        arrived = await road.travel_route(actor, CONFINS_ESTRADAS_AUSENTES_LABEL)
        assert arrived is not None and arrived.location == CONFINS_ESTRADAS_AUSENTES_LABEL
        await mission.on_location(actor)
    for actor in actors:
        view = await mission.resume_active(actor)
        assert view is not None and view.step == 3

    # Objectives are Solo (Ação × Consequência §5): the helper stays on step 3.
    for evidence in (
        "inspect_finished_foundation",
        "inspect_absent_map_marker",
        "inspect_discordant_return_record",
    ):
        leader = await mission.resume_active(actors[0])
        assert leader is not None and leader.step == 3
        await mission.advance(actors[0], leader.state_version, evidence)
        view = await mission.resume_active(actors[0])
        assert view is not None
        assert evidence in view.progress["physical_fracture_evidence"]
        helper_view = await mission.resume_active(actors[1])
        assert helper_view is not None and helper_view.step == 3
        assert not helper_view.progress.get("physical_fracture_evidence")

    leader = await mission.resume_active(actors[0])
    assert leader is not None and leader.step == 4
    # P32 is not a Boss: the Group proposal is refused, the fight is Solo.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await mission.propose_group_combat(actors[0], leader.state_version, P32_ID)
    assert not await groups.activity_proposals(actors[0])
    started = await mission.start_solo_combat(actors[0], leader.state_version, P32_ID)
    assert started is not None and started.combat is not None
    assert started.group_size == 1 and not started.combat.party_mode
    assert started.combat.variant is None
    enemy_fighters = [
        fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"
    ]
    assert len(enemy_fighters) == 1
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actors[0], started.activity_id, started.combat.version, "attack"
    )
    assert victory is not None
    view = await mission.resume_active(actors[0])
    assert view is not None and view.step == 5
    assert view.progress["scripted_andarilho_victory"] is True
    assert view.progress["andarilho_not_clone_nor_soul_observed"] is True
    helper_view = await mission.resume_active(actors[1])
    assert helper_view is not None and helper_view.step == 3
    assert not helper_view.progress.get("scripted_andarilho_victory")
