from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import (
    P27_CONTENT_VERSION,
    P28_ACHIEVEMENT,
    P28_CONTENT_VERSION,
    P28_ID,
    P28_MISSION_ID,
    P28_TITLE,
    AltosMissionService,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_BY_ID,
    ALTOS_REGION_ID,
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
    CREATURE_PRESENTATION,
    LOCATION_LABELS,
)
from asterion.application.road import (
    ALTOS_BASTILHA_LABEL,
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_REGION_LABEL,
    _grade_catalyst_for_level,
    _grade_fragment_for_level,
)
from asterion.application.round import RoundService
from asterion.domain.road import (
    ALTOS_BASTILHA,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
    ALTOS_BASTILHA_BRAZIER,
    ALTOS_BASTILHA_DUNGEON_UNLOCK,
    ALTOS_BASTILHA_EXPLORATION_PROFILE,
    ALTOS_BASTILHA_EXPLORE_UNLOCK,
    ALTOS_BASTILHA_HUNT_UNLOCK,
    ALTOS_BASTILHA_LOCATION,
    ALTOS_BASTILHA_PROFILE,
    ALTOS_BASTILHA_ROUND_UNLOCK,
    ALTOS_CARCACA_MINERAL,
    ALTOS_DEVORADOR_ESCORIA,
    ALTOS_MORCEGO_CHAMINE,
    ALTOS_QUEBRA_CABOS,
    ALTOS_SUPERVISOR_CARGA,
    ALTOS_VIGIA_CARGA,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    LOCATION_LEVEL_BANDS,
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
    ExplorationAttempt,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import disable_round_pvpve_for_test, start_manual_hunt_after_no_match
from tests.test_altos_p27 import _seed_p27_character
from tests.test_s4_s5_integration import _terminal


async def _seed_p28_character(
    database,
    actor: int,
    *,
    level: int = 47,
    p27_status: str | None = "completed",
    p28_status: str | None = None,
):
    actor, road, sessions = await _seed_p27_character(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION_LABEL
        world.location = (
            ALTOS_BASTILHA_LABEL if p28_status == "completed" else ALTOS_PEDREIRAS_LABEL
        )
        if p27_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id="P27",
                    title="A Continuidade a Qualquer Custo",
                    status=p27_status,
                    step=7 if p27_status == "completed" else 3,
                    content_version=P27_CONTENT_VERSION,
                    progress={"completed": p27_status == "completed"},
                )
            )
        if p27_status == "completed":
            session.add(
                LocationDiscovery(
                    character_id=character.id,
                    location_id="location.altos.pedreiras_suspensas",
                )
            )
            session.add(
                Unlock(
                    character_id=character.id,
                    unlock_id="unlock.location.altos.pedreiras_suspensas",
                )
            )
        if p28_status is not None:
            completed = p28_status == "completed"
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P28_ID,
                    title=P28_TITLE,
                    status=p28_status,
                    step=8 if completed else 2,
                    content_version=P28_CONTENT_VERSION,
                    progress={"completed": completed},
                )
            )
            if completed:
                session.add(
                    LocationDiscovery(
                        character_id=character.id,
                        location_id=ALTOS_BASTILHA_LOCATION,
                    )
                )
                session.add_all(
                    Unlock(character_id=character.id, unlock_id=unlock_id)
                    for unlock_id in (
                        ALTOS_BASTILHA_ACCESS_UNLOCK,
                        ALTOS_BASTILHA_HUNT_UNLOCK,
                        ALTOS_BASTILHA_EXPLORE_UNLOCK,
                    )
                )
    return actor, road, sessions


def test_p28_bastilha_profiles_catalog_and_screen_match_final_source():
    assert ALTOS_BASTILHA_PROFILE.creature_weights == (
        (ALTOS_MORCEGO_CHAMINE, 14),
        (ALTOS_CARCACA_MINERAL, 22),
        (ALTOS_QUEBRA_CABOS, 24),
        (ALTOS_VIGIA_CARGA, 34),
        (ALTOS_DEVORADOR_ESCORIA, 2),
        (ALTOS_SUPERVISOR_CARGA, 4),
    )
    assert sum(weight for _, weight in ALTOS_BASTILHA_PROFILE.creature_weights) == 100
    assert ALTOS_BASTILHA_PROFILE.variant_chance == 18
    assert ALTOS_BASTILHA_PROFILE.hunt_unlock == ALTOS_BASTILHA_HUNT_UNLOCK
    assert ALTOS_BASTILHA_PROFILE.explore_unlock == ALTOS_BASTILHA_EXPLORE_UNLOCK
    assert ALTOS_BASTILHA_PROFILE.round_familiarity == ALTOS_BASTILHA_ROUND_UNLOCK
    assert LOCATION_LEVEL_BANDS[ALTOS_BASTILHA] == (47, 50)
    vigia = creature_for(ALTOS_VIGIA_CARGA)
    supervisor = creature_for(ALTOS_SUPERVISOR_CARGA)
    assert (vigia.unlock_level, vigia.max_level) == (47, 50)
    assert (supervisor.unlock_level, supervisor.max_level) == (48, 50)
    assert VARIANT_POOL[ALTOS_SUPERVISOR_CARGA] == ()
    assert LOCATION_LABELS[ALTOS_BASTILHA_LOCATION] == ALTOS_BASTILHA_LABEL
    assert CREATURE_PRESENTATION[ALTOS_VIGIA_CARGA].habitats == (ALTOS_BASTILHA_LOCATION,)
    assert CREATURE_PRESENTATION[ALTOS_SUPERVISOR_CARGA].region_id == ALTOS_REGION_ID


def test_grade_v_hunt_settlement_uses_existing_global_material_ids():
    assert _grade_fragment_for_level(47) == "material.tdo.fragmento_aprimoramento_v"
    assert _grade_catalyst_for_level(47) == "material.tdo.catalisador_elite_v"
    assert CODEX_BY_ID["codex.altos.desvelados_origem"].location_id == ALTOS_BASTILHA_LOCATION
    assert "radicalização posterior" in CODEX_FRAGMENTS["codex.altos.desvelados_origem"].text
    assert "sabotagem da Âncora Central" in CODEX_FRAGMENTS["codex.altos.desvelados_origem"].text
    assert ACHIEVEMENT_BY_ID[P28_ACHIEVEMENT].name == "Os Desvelados"
    assert ACHIEVEMENT_BY_ID["achievement.altos.cartografo_peso"].name == "Cartógrafo do Peso"

    profile = EXPLORATION_PROFILES[ALTOS_BASTILHA_LOCATION]
    assert profile is ALTOS_BASTILHA_EXPLORATION_PROFILE
    result_map = {
        result.result_id: (result.category, result.weight, result.unique)
        for result in profile.results
    }
    assert result_map["explore.altos.bastilha.braseiro_externo"] == ("great_discovery", 50, True)
    assert result_map["explore.altos.bastilha.entrada_profunda"] == ("great_discovery", 50, True)
    assert result_map["explore.altos.bastilha.tabela_validade"] == ("knowledge", 60, True)
    assert result_map["explore.altos.bastilha.selos_reemitidos"] == ("knowledge", 40, False)
    assert [
        (result.result_id.rsplit(".", 1)[-1], result.weight)
        for result in profile.results
        if result.category == "combat"
    ] == [
        ("morcego_chamine", 15),
        ("carcaca_mineral", 20),
        ("quebra_cabos", 25),
        ("vigia_carga", 40),
    ]
    assert HUNT_PROFILES[ALTOS_BASTILHA_LOCATION] is ALTOS_BASTILHA_PROFILE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "p27_status", "expected"),
    ((47, None, "blocked"), (46, "completed", "suspended"), (47, "active", "blocked")),
)
async def test_p28_requires_p27_and_level_47_without_granting_access(
    database, level, p27_status, expected
):
    actor, _road, sessions = await _seed_p28_character(
        database,
        781300 + level + (0 if p27_status is None else len(p27_status)),
        level=level,
        p27_status=p27_status,
    )
    mission = AltosMissionService(sessions, "ocaso")
    view = await mission.start_p28(actor)
    if expected == "suspended":
        assert view is not None and view.quest_id == P28_ID and view.status == "suspended"
        offer = await mission.resume_active(actor)
        assert offer is not None and offer.status == "suspended"
    else:
        assert view is None
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_BASTILHA_ACCESS_UNLOCK,
            )
        ) is None


@pytest.mark.asyncio
async def test_p28_solo_steps_rewards_activity_gates_and_local_round_unlock(database, monkeypatch):
    import asterion.application.road as road_module
    import asterion.application.scripted_combat as scripted_combat

    actor, road, sessions = await _seed_p28_character(database, 781310)
    mission = AltosMissionService(sessions, "ocaso")
    offer = await mission.resume_active(actor)
    assert offer is not None and offer.quest_id == P28_ID and offer.status == "available"
    initial = await mission.start_p28(actor)
    assert initial is not None and initial.status == "active" and initial.step == 1
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character is not None
        xp_before = character.xp
        crowns_before = character.crowns
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_BASTILHA_ACCESS_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_BASTILHA_HUNT_UNLOCK,
            )
        ) is None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_BASTILHA_EXPLORE_UNLOCK,
            )
        ) is None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == ALTOS_BASTILHA_LOCATION,
            )
        ) is None

    assert await road.travel_route(actor, ALTOS_BASTILHA_LABEL) is not None
    view = await mission.resume_active(actor)
    assert view is not None and view.step == 2 and view.location == ALTOS_BASTILHA_LABEL
    local = await road.resume(actor)
    assert local is not None and not local.hunt_enabled and not local.explore_enabled
    assert await road.start_hunt(actor) is None
    assert await road.explore(actor) is None
    rounds = disable_round_pvpve_for_test(RoundService(sessions, "ocaso"))
    blocked_round = await rounds.prepare_round(actor, 5)
    assert blocked_round is None or blocked_round.kind != "round_prepare"

    view = await mission.advance(actor, view.state_version, "locate_containment_archive")
    assert view is not None and view.step == 3
    view = await mission.advance(actor, view.state_version, "locate_critical_memorial")
    assert view is not None and view.step == 4
    scripted = await mission.start_solo_combat(actor, view.state_version, P28_ID)
    assert scripted is not None and scripted.kind == "combat" and scripted.combat is not None
    assert scripted.combat.fighters["enemy"].name == "Vigia de Carga"
    assert scripted.combat.fighters["enemy"].level == 47
    assert scripted.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(actor, scripted.activity_id, scripted.combat.version, "attack")
    assert victory is not None and victory.step == 5
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character is not None
        assert character.xp == xp_before
        assert character.crowns == crowns_before
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P28_MISSION_ID,
            )
        ) is None

    view = await mission.advance(actor, victory.state_version, "compare_sources_with_sel_and_maro")
    assert view is not None and view.step == 6
    view = await mission.advance(actor, view.state_version, "record_desvelados_codex")
    assert view is not None and view.step == 7
    assert view.progress["codex_recorded"] is True
    completion_version = view.state_version
    completed = await mission.advance(actor, completion_version, "record_non_attribution")
    assert completed is not None and completed.status == "completed"
    assert completed.progress["collective_attribution_withheld"] is True
    assert completed.progress["anchor_sabotage_unconfirmed"] is True
    retried = await mission.advance(actor, completion_version, "record_non_attribution")
    assert retried is not None and retried.status == "completed"

    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character is not None
        assert character.xp - xp_before == 67_100
        assert character.crowns - crowns_before == 1_010
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P28_MISSION_ID,
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )
        ).all()
        assert Counter((row.kind, row.item_id, row.quantity) for row in components) == Counter(
            {
                ("xp", None, 67_100): 1,
                ("crowns", None, 1_010): 1,
                ("material", "material.altos.ferro_contrapeso", 2): 1,
                ("material", "material.altos.couro_escarpa", 1): 1,
                ("material", "material.altos.cinza_basalto", 1): 1,
            }
        )
        for unlock_id in (
            ALTOS_BASTILHA_ACCESS_UNLOCK,
            ALTOS_BASTILHA_HUNT_UNLOCK,
            ALTOS_BASTILHA_EXPLORE_UNLOCK,
            "narrative.altos.desvelados_contextualizados",
        ):
            assert await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == unlock_id,
                )
            ) is not None
        for forbidden_unlock in (
            ALTOS_BASTILHA_ROUND_UNLOCK,
            ALTOS_BASTILHA_DUNGEON_UNLOCK,
            "unlock.location.altos.coracao_colosso",
            "unlock.hunt.altos.coracao",
        ):
            assert await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == forbidden_unlock,
                )
            ) is None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == ALTOS_BASTILHA_BRAZIER,
            )
        ) is None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == "codex.altos.desvelados_origem",
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.fragment_id == "codex.altos.desvelados_origem",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == P28_ACHIEVEMENT,
            )
        ) is not None
        mission_events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P28_MISSION_ID,
                )
            )
        ).all()
        assert len(mission_events) == 1

    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    hunt = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert hunt is not None and hunt.combat is not None
    hunt_victory = await road.action(actor, hunt.activity_id, hunt.combat.version, "attack")
    assert hunt_victory is not None and hunt_victory.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_BASTILHA_ROUND_UNLOCK,
            )
        ) is not None
    prepared_round = await rounds.prepare_round(actor, 5)
    assert prepared_round is not None and prepared_round.kind == "round_prepare"


@pytest.mark.asyncio
async def test_p28_unique_bastilha_discoveries_are_independent_and_idempotent(
    database, monkeypatch
):
    import asterion.application.road as road_module

    actors = (781320, 781321, 781322)
    seeded = [
        await _seed_p28_character(database, actor, p28_status="completed")
        for actor in actors
    ]
    outcomes = (
        (
            "great_discovery",
            "explore.altos.bastilha.braseiro_externo",
            "brazier",
            ALTOS_BASTILHA_BRAZIER,
            11_520,
        ),
        (
            "great_discovery",
            "explore.altos.bastilha.entrada_profunda",
            "unlock",
            ALTOS_BASTILHA_DUNGEON_UNLOCK,
            11_520,
        ),
        ("knowledge", "explore.altos.bastilha.tabela_validade", None, None, 3_600),
    )
    for (actor, road, sessions), (category, result_id, kind, value_id, xp) in zip(
        seeded, outcomes, strict=True
    ):
        monkeypatch.setattr(
            road_module,
            "_explore_result",
            lambda *_args, _category=category, _result_id=result_id, **_kwargs: (
                _category,
                _result_id,
                "Descoberta registrada.",
            ),
        )
        attempt_view = await road.explore(actor)
        assert attempt_view is not None and attempt_view.attempt_id is not None
        assert await road.acknowledge_result(actor, attempt_view.attempt_id) is not None
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            attempt = await session.get(ExplorationAttempt, attempt_view.attempt_id)
            assert attempt is not None and attempt.status == "completed"
            event = await session.scalar(
                select(RewardEvent).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == f"explore:{attempt.id}",
                )
            )
            assert event is not None
            components = (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
            assert any(row.kind == "xp" and row.quantity == xp for row in components)
            if kind == "brazier":
                assert await session.scalar(
                    select(Brazier.id).where(
                        Brazier.character_id == character.id,
                        Brazier.brazier_id == value_id,
                    )
                ) is not None
                assert not any(row.kind == "unlock" for row in components)
            elif kind == "unlock":
                assert await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == value_id,
                    )
                ) is not None
                assert not any(row.kind == "brazier" for row in components)
            else:
                assert not any(row.kind in {"brazier", "unlock"} for row in components)
            duplicate_events = (
                await session.scalars(
                    select(RewardEvent).where(
                        RewardEvent.character_id == character.id,
                        RewardEvent.source_id == f"explore:{attempt.id}",
                    )
                )
            ).all()
            assert len(duplicate_events) == 1


@pytest.mark.asyncio
async def test_p28_group_member_advances_alone_and_scripted_combat_is_solo(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actors = (781330, 781331)
    seeded = [await _seed_p28_character(database, actor) for actor in actors]
    sessions = seeded[0][2]
    async with sessions() as session:
        helper = await session.scalar(select(Character).where(Character.telegram_id == actors[1]))
        assert helper is not None
        helper_name = helper.name
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    roads = {actor: road for actor, road, _sessions in seeded}
    for actor in actors:
        started = await mission.start_p28(actor)
        assert started is not None and started.step == 1
        assert await roads[actor].travel_route(actor, ALTOS_BASTILHA_LABEL) is not None
        arrived = await mission.resume_active(actor)
        assert arrived is not None and arrived.step == 2

    view = await mission.resume_active(actors[0])
    assert view is not None
    view = await mission.advance(actors[0], view.state_version, "locate_containment_archive")
    # Objectives are Solo (Ação × Consequência §5): the helper stays on step 2.
    helper_view = await mission.resume_active(actors[1])
    assert helper_view is not None and helper_view.step == 2
    assert not helper_view.progress.get("containment_archive_located")
    view = await mission.advance(actors[0], view.state_version, "locate_critical_memorial")
    assert view is not None and view.step == 4
    assert (await mission.resume_active(actors[1])).step == 2

    # P28 is not a Boss: the Group proposal is refused, the fight is Solo.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await mission.propose_group_combat(actors[0], view.state_version, P28_ID)
    assert not await groups.activity_proposals(actors[0])
    started = await mission.start_solo_combat(actors[0], view.state_version, P28_ID)
    assert started is not None and started.combat is not None
    assert started.group_size == 1 and not started.combat.party_mode
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actors[0], started.activity_id, started.combat.version, "attack"
    )
    assert victory is not None and victory.step == 5
    assert (await mission.resume_active(actors[1])).step == 2

    personal = await mission.advance(
        actors[0], victory.state_version, "compare_sources_with_sel_and_maro"
    )
    assert personal is not None and personal.step == 6
    helper_after = await mission.resume_active(actors[1])
    assert helper_after is not None and helper_after.step == 2
    async with sessions() as session:
        character_ids = set(
            (
                await session.scalars(
                    select(Character.id).where(Character.telegram_id.in_(actors))
                )
            ).all()
        )
        shared_credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id.in_(character_ids),
                    CampaignObjectiveCredit.quest_id == P28_ID,
                    CampaignObjectiveCredit.objective_id == "p28.containment_archive_located",
                )
            )
        ).all()
        assert len(shared_credits) == 1
        assert shared_credits[0].character_id == personal.character_id
        personal_credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id.in_(character_ids),
                    CampaignObjectiveCredit.quest_id == P28_ID,
                    CampaignObjectiveCredit.objective_id == "p28.sources_compared",
                )
            )
        ).all()
        assert len(personal_credits) == 1
        assert personal_credits[0].character_id == personal.character_id
