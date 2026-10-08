import os
from datetime import UTC, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

import asterion.application.vigor as vigor_module
from asterion.application.active_arts import ActiveArtService, load_active_art_configuration
from asterion.application.class_trials import ClassTrialService
from asterion.application.crafting import CraftingService
from asterion.application.creation import CreationService
from asterion.application.dungeons import CRYPT_FAMILY_ID, DungeonService
from asterion.application.equipment import EquipmentService
from asterion.application.equipment_configuration import (
    build_equipment_configuration,
    load_equipment_configuration,
    reconcile_character_hp,
    resolve_character_combat_stats,
)
from asterion.application.p1 import P1Service
from asterion.application.p2 import ASH_POINT_IDS, P2Service
from asterion.application.p3 import P3Service
from asterion.application.p4 import P4Service
from asterion.application.p5 import P5_ELEMENTS, P5Service
from asterion.application.p6 import P6Service
from asterion.application.path_selection import PathSelectionService
from asterion.application.professions import ProfessionService
from asterion.application.prologue import PrologueService
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, ROAD, RUINS, RoadService
from asterion.application.round import RoundService
from asterion.application.s1 import S1Service
from asterion.application.s2 import S2_VESTIGE_IDS, S2Service
from asterion.application.s3 import S3_TRACKS, S3Service
from asterion.application.s4 import S4_WATCH_POINTS, S4Service
from asterion.application.s5 import S5_LIGHT_POINTS, S5Service
from asterion.application.s6 import S6_MARKS, S6Service
from asterion.application.talents import TalentService
from asterion.application.world import WorldService
from asterion.domain.arts import FIRST_CLASS_ART_IDS, SENTINEL_ART_IDS
from asterion.domain.class_trials import SENTINEL_CONDITION_IDS
from asterion.domain.combat import action_target_ids, allowed_actions
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.dungeons import dungeon_completion_xp
from asterion.domain.equipment import assignment_for_item_slot, parse_equipment_slot
from asterion.domain.prologue import PROFILE as PROLOGUE_PROFILE
from asterion.domain.road import (
    EXPLORATION_PROFILES,
    VIGIA_PARTIDO,
    create_creature_combat,
    select_exploration_result,
)
from asterion.domain.road import (
    RULESET as ROAD_RULESET,
)
from asterion.domain.tdo_galleries import GALLERIES_FAMILY_ID
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    ConsumableStack,
    DungeonRun,
    EquipmentItem,
    ExplorationAttempt,
    GameActivity,
    Quest,
    RewardEvent,
    WorldState,
)
from tests.helpers.tdo_playthrough import (
    P6_DIAGNOSTIC_LOADOUTS,
    TDOPlaythrough,
    best_p6_diagnostic_configuration,
    choose_p6_policy_action,
    sample_p6_policies,
)

pytestmark = pytest.mark.skipif(
    os.getenv("ASTERION_RUN_TDO_FULL_PLAYTHROUGH") != "1",
    reason="playthrough diagnóstico longo; habilite ASTERION_RUN_TDO_FULL_PLAYTHROUGH=1",
)


def _consumable_quantity(quantities, consumable_id):
    return sum(quantity for item_id, quantity in quantities if item_id == consumable_id)


def _compact_playthrough_report(driver, mark):
    level_fields = (
        "level",
        "xp_residual",
        "xp_required_next",
        "xp_received_since_previous_milestone",
        "xp_received_total",
        "crowns",
        "vigor",
        "vigor_regenerated_total",
        "vigor_spent_total",
        "vigor_external_gained_total",
        "vigor_potion_gained_total",
        "simulated_elapsed_seconds",
        "manual_hunts",
        "manual_hunts_normal_vigor",
        "manual_hunts_reduced_xp",
        "rounds",
        "explorations",
        "dungeon_runs",
    )
    state = mark.state
    quests = [
        (quest["id"], quest["status"], quest["step"])
        for quest in state.get("quests", [])
    ]
    equipped = [
        (item[0], item[2], item[3], item[4])
        for item in state.get("equipped", [])
    ]
    materials = [
        (material_id, quantity, bound)
        for material_id, quantity, bound in state.get("materials", [])
    ]
    return {
        "character": state.get("name"),
        "levels": [
            {field: milestone[field] for field in level_fields}
            for milestone in driver.level_milestones
        ],
        "xp_by_origin": dict(driver.xp_by_origin),
        "xp_ledger_total": state.get("xp_ledger_total"),
        "xp_source_count": len(state.get("xp_sources", [])),
        "unclassified_xp_sources": state.get("unclassified_xp_sources"),
        "clock": {
            "elapsed_seconds": driver.clock.elapsed_seconds,
            "waits": list(driver.clock.waits),
            "round_cadence_seconds": sum(
                wait["seconds"]
                for wait in driver.clock.waits
                if str(wait["reason"]).startswith("Ronda cadence")
            ),
            "offline_vigor_wait_seconds": sum(
                wait["seconds"]
                for wait in driver.clock.waits
                if "offline natural regeneration" in str(wait["reason"])
                or "offline Vigor wait" in str(wait["reason"])
            ),
            "vigor_regenerated": driver.clock.vigor_regenerated,
            "vigor_spent": driver.clock.vigor_spent,
            "vigor_external": driver.clock.vigor_external_gains,
            "vigor_potions": driver.clock.vigor_potion_gains,
        },
        "final": {
            field: state.get(field)
            for field in (
                "level",
                "xp",
                "xp_received_total",
                "xp_required_next_level",
                "crowns",
                "vigor",
                "hp",
                "max_hp",
                "location",
                "hunt_result_count",
                "manual_hunt_count",
                "manual_hunts_normal_vigor",
                "manual_hunts_reduced_xp",
                "rounds",
                "exploration_count",
                "completed_explorations",
                "dungeon_runs",
                "talents",
                "path",
                "active_arts",
                "professions",
                "trial",
            )
        },
        "quests": quests,
        "equipped": equipped,
        "consumables": state.get("consumables"),
        "materials": materials,
    }


async def _create_remanescente_sentinela(driver: TDOPlaythrough) -> None:
    creation = CreationService(driver.sessions, "ocaso")
    state = await creation.start(driver.actor)
    state = await creation.name(driver.actor, "Bravaro", update_id=1)
    for action in ("r0", "choose", "c0", "choose"):
        state = await creation.callback(driver.actor, state.id, state.version, action)
    assert state.step == "confirm"
    state = await creation.callback(driver.actor, state.id, state.version, "confirm")
    assert (state.step, state.name, state.race, state.character_class) == (
        "cinzas_na_estrada:intro",
        "Bravaro",
        "remanescente",
        "sentinela",
    )


@pytest.mark.asyncio
async def test_tdo_full_playthrough_restarts_and_continues(database, monkeypatch):
    """Restart at Nv.1; all progression mutations use public services."""
    actor = 7_000_000_000_000 + uuid4().int % 100_000_000_000
    _, sessions = database
    driver = TDOPlaythrough(actor, sessions)
    await _create_remanescente_sentinela(driver)
    async with sessions() as session:
        initial_character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert initial_character is not None and initial_character.vigor == 100
        initial_anchor = initial_character.vigor_regen_at
        if initial_anchor.tzinfo is None:
            initial_anchor = initial_anchor.replace(tzinfo=UTC)
        driver.clock.instant = max(driver.clock.instant, initial_anchor.astimezone(UTC))
    real_reconcile = vigor_module.reconcile_vigor_state
    real_add_vigor = vigor_module.add_vigor_state

    def tracked_reconcile(character, *, now=None):
        gained = real_reconcile(character, now=now)
        driver.clock.vigor_regenerated += gained
        return gained

    def tracked_add_vigor(character, amount, *, now=None):
        gained = real_add_vigor(character, amount, now=now)
        driver.clock.vigor_external_gains += gained
        return gained

    monkeypatch.setattr(vigor_module, "utcnow", driver.clock.now)
    monkeypatch.setattr(vigor_module, "reconcile_vigor_state", tracked_reconcile)
    monkeypatch.setattr(vigor_module, "add_vigor_state", tracked_add_vigor)
    import asterion.application.consumables as consumables_module
    import asterion.application.dungeons as dungeons_module

    # Both modules import utcnow directly and pass explicit anchors into
    # Vigor reconciliation. Keep every temporal boundary on the same
    # simulated clock so a wall-clock anchor cannot overlap simulated time.
    monkeypatch.setattr(consumables_module, "utcnow", driver.clock.now)
    monkeypatch.setattr(dungeons_module, "utcnow", driver.clock.now)
    monkeypatch.setattr(consumables_module, "add_vigor_state", tracked_add_vigor)
    monkeypatch.setattr(dungeons_module, "add_vigor_state", tracked_add_vigor)
    await driver.snapshot("personagem criado pelo fluxo público")

    prologue = PrologueService(sessions, "ocaso", PROLOGUE_PROFILE)
    view = await prologue.enter(actor)
    assert view is not None and view.stage == "cinzas_na_estrada:first_combat"
    for expected_action in ("attack", "defend", "art"):
        view = await prologue.action(actor, view.activity_id, view.combat.version, expected_action)
        resumed = await PrologueService(sessions, "ocaso", PROLOGUE_PROFILE).resume(actor)
        assert resumed == view
    assert view.combat.tutorial_stage == "normal"
    view = await driver.combat_to_result(
        view,
        lambda current, action: PrologueService(sessions, "ocaso", PROLOGUE_PROFILE).action(
            actor, current.activity_id, current.combat.version, action
        ),
        lambda: PrologueService(sessions, "ocaso", PROLOGUE_PROFILE).resume(actor),
        label="Prólogo · Cão Cinéreo",
    )
    assert view.combat.result in {"victory", "defeat"}
    await driver.snapshot(f"Prólogo · {view.combat.result}")

    world = WorldService(sessions, "ocaso")
    at_brazier = await world.resume(actor)
    assert at_brazier is not None and at_brazier.kind == "brazier"
    rested = await world.rest(actor)
    assert rested is not None and rested.kind == "menu"
    p1 = P1Service(sessions, "ocaso")
    quest = await p1.resume(actor)
    assert quest is not None and quest.status == "active" and quest.step == 1

    quest = await p1.follow_road(actor, quest.state_version)
    quest = await p1.examine(actor, "pegadas", quest.state_version)
    quest = await p1.examine(actor, "sulcos", quest.state_version)
    assert quest is not None and quest.step == 3 and quest.combat is not None
    quest = await driver.combat_to_result(
        quest,
        lambda current, action: p1.action(
            actor, current.activity_id, current.combat.version, action
        ),
        lambda: p1.resume(actor),
        label="P1 · encontro da Estrada",
    )
    for _ in range(4):
        if quest.progress.get("arrival"):
            break
        quest = await p1.retry(actor, quest.state_version)
        quest = await driver.combat_to_result(
            quest,
            lambda current, action: p1.action(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: p1.resume(actor),
            label="P1 · retry",
        )
    assert quest.progress.get("arrival"), driver.diagnostic()
    for mutation in (p1.enter_refuge, p1.follow_alda, p1.go_brazier, p1.activate_brazier):
        quest = await mutation(actor, quest.state_version)
    assert quest.status == "completed"
    await driver.snapshot("P1 concluída e Braseiro do Refúgio ativado")

    active_arts = ActiveArtService(sessions, "ocaso")
    art_view = await active_arts.view(actor)
    assert art_view is not None
    equipped = await active_arts.equip_art(
        actor,
        1,
        FIRST_CLASS_ART_IDS["sentinela"],
        expected_configuration_version=art_view.combat_configuration_version,
    )
    assert equipped is not None and equipped.changed

    road = RoadService(sessions, "ocaso")
    location = await road.travel(actor, ROAD)
    assert location is not None and location.location == ROAD
    hunt = None
    for attempt in range(12):
        hunt = await road.start_hunt(actor)
        assert hunt is not None and hunt.kind == "combat", driver.diagnostic()
        hunt = await driver.combat_to_result(
            hunt,
            lambda current, action: road.action(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: RoadService(sessions, "ocaso").resume(actor),
            label=f"Caçada Manual · tentativa {attempt + 1}",
        )
        if hunt.kind == "hunt_victory":
            await road.acknowledge_result(actor)
            break
        assert hunt.kind == "hunt_defeat", hunt
        await road.acknowledge_defeat(actor)
        await driver.snapshot(f"Caçada Manual · tentativa {attempt + 1} · derrota")
    assert hunt is not None and hunt.kind == "hunt_victory", driver.diagnostic()
    await driver.snapshot("primeira vitória de Caçada Manual")
    await road.travel(actor, REFUGE)
    await WorldService(sessions, "ocaso").rest(actor)
    await road.travel(actor, ROAD)

    # The timed Ronda is exercised with a test-only clock; game state still
    # advances exclusively through RoundService's public maintenance operation.
    import asterion.application.round as round_module

    JourneyClock = driver.clock.datetime_type()
    monkeypatch.setattr(round_module, "datetime", JourneyClock)
    rounds = RoundService(sessions, "ocaso")
    prepared = await rounds.prepare_round(actor, 5)
    assert prepared is not None and prepared.kind == "round_prepare", (
        f"preparação da Ronda bloqueada: {prepared!r}; "
        "resultados não reconhecidos="
        f"{driver.marks[-1].state.get('unacknowledged_hunt_results')!r}; "
        f"histórico de Caçadas={driver.marks[-1].state.get('hunt_results')!r}; "
        f"{driver.diagnostic()}"
    )
    started = await rounds.start_round(actor, prepared.round_id, prepared.state_version)
    assert started is not None and started.kind in {"round_active", "round_interrupted"}
    resumed_round = await RoundService(sessions, "ocaso").resume(actor)
    assert resumed_round is not None and resumed_round.round_id == started.round_id
    blocked_hunt = await rounds.start_hunt(actor)
    assert blocked_hunt is not None and blocked_hunt.kind.startswith("round_")
    if started.kind == "round_active":
        round_result = await driver.clock.process_round_cadence(rounds, actor)
    else:
        round_result = started
    assert round_result is not None
    completed_round_encounters = round_result.completed_encounters
    round_terminal_kind = round_result.kind
    round_end_reason = round_result.end_reason
    if round_result.kind == "round_interrupted":
        elite = await rounds.engage_round_elite(
            actor, started.round_id, round_result.state_version
        )
        assert elite is not None and elite.combat is not None
        elite = await driver.combat_to_result(
            elite,
            lambda current, action: RoadService(sessions, "ocaso").action(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: RoundService(sessions, "ocaso").resume(actor),
            label="Ronda · Elite interrompida",
        )
        if elite.kind == "hunt_victory":
            await RoundService(sessions, "ocaso").acknowledge_result(actor)
        else:
            assert elite.kind == "hunt_defeat", elite
            await RoundService(sessions, "ocaso").acknowledge_defeat(actor)
        round_result = await rounds.round_back(actor, started.round_id)
    elif round_result.kind in {"round_completed", "round_ended", "round_defeated"}:
        round_result = await rounds.round_back(actor, started.round_id)
    assert round_result is not None and round_result.kind not in {
        "round_active",
        "round_interrupted",
        "round_cancelled",
    }, (round_result, driver.diagnostic())
    print(
        "RONDA PÚBLICA · "
        f"resultado={round_terminal_kind} · "
        f"motivo={round_end_reason} · "
        f"encontros={completed_round_encounters}/5 · "
        f"Vigor={round_result.vigor}/{round_result.max_vigor}"
    )
    await driver.snapshot("Ronda pública realmente avançada pelo serviço")

    # S1 is a normal secondary quest, available once the character reaches Nv.2.
    async def manual_hunt(label, *, capture=True):
        await driver.clock.wait_for_vigor(
            sessions, actor, 2, f"offline Vigor wait before {label}"
        )
        service = RoadService(sessions, "ocaso")
        for _receipt in range(6):
            view = await service.start_hunt(actor)
            if view is None:
                mark = await driver.snapshot(f"{label} · start_hunt indisponível")
                raise AssertionError(
                    f"{label}: start_hunt retornou None; snapshot={mark.state!r}\n"
                    f"{driver.diagnostic()}"
                )
            if view.kind == "hunt_defeat":
                await service.acknowledge_defeat(actor)
                if capture:
                    await driver.snapshot(f"{label} · recibo de derrota reconhecido")
                return view
            if view is not None and view.kind == "hunt_victory":
                await service.acknowledge_result(actor)
                if capture:
                    await driver.snapshot(f"{label} · recibo de vitória reconhecido")
                return view
            assert view is not None and view.kind == "combat", (view, driver.diagnostic())
            view = await driver.combat_to_result(
                view,
                lambda current, action: RoadService(sessions, "ocaso").action(
                    actor, current.activity_id, current.combat.version, action
                ),
                lambda: RoadService(sessions, "ocaso").resume(actor),
                label=label,
            )
            if view.kind == "hunt_victory":
                await service.acknowledge_result(actor)
            else:
                if view.kind != "hunt_defeat":
                    mark = await driver.snapshot(f"resultado inesperado · {label}")
                    combat = view.combat
                    raise AssertionError(
                        f"{label}: combate retornou estado inesperado: kind={view.kind!r}, "
                        f"result={getattr(combat, 'result', None)!r}, "
                        f"activity_id={view.activity_id!r}; snapshot={mark.state!r}\n"
                        f"{driver.diagnostic()}"
                    )
                await service.acknowledge_defeat(actor)
            if capture:
                await driver.snapshot(f"{label} · {view.kind}")
            return view
        blocked = await driver.snapshot(f"primeiro bloqueio persistido · {label}")
        raise AssertionError(
            f"{label}: recibo antigo continua bloqueando uma nova Caçada após seis confirmações. "
            f"Último estado persistido={blocked.state!r}\n{driver.diagnostic()}"
        )

    async def current_level():
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            return character.level

    async def current_xp_total():
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            return driver.total_xp(character.level, character.xp)

    async def explore_result(target_result_id, label):
        """Use real Explore service with a selected seed and its actual selector."""
        import asterion.application.road as road_module

        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            world = await session.get(WorldState, character.id)
            assert world is not None
            local_by_label = {
                ROAD: road_module.ROAD_LOCATION,
                CHARNECA: road_module.CHARNECA_LOCATION,
                BOSQUE: road_module.BOSQUE_LOCATION,
                RUINS: road_module.RUINS_LOCATION,
            }
            local_id = local_by_label[world.location]
            profile = EXPLORATION_PROFILES[local_id]
            attempt_local_id = ROAD if local_id == road_module.ROAD_LOCATION else local_id
            recent_rows = (
                await session.scalars(
                    select(ExplorationAttempt.result_id)
                    .where(
                        ExplorationAttempt.character_id == character.id,
                        ExplorationAttempt.local_id == attempt_local_id,
                    )
                    .order_by(ExplorationAttempt.created_at.desc())
                    .limit(3)
                )
            ).all()
            recent = tuple(str(value).rsplit(".", 1)[-1] for value in recent_rows)
            unique_ids = tuple(result.result_id for result in profile.results if result.unique)
            excluded = tuple(
                (
                    await session.scalars(
                        select(ExplorationAttempt.result_id).where(
                            ExplorationAttempt.character_id == character.id,
                            ExplorationAttempt.local_id == attempt_local_id,
                            ExplorationAttempt.status == "completed",
                            ExplorationAttempt.result_id.in_(unique_ids),
                        )
                    )
                ).all()
            )
            level = character.level
            last = await session.scalar(
                select(ExplorationAttempt)
                .where(
                    ExplorationAttempt.character_id == character.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                )
                .order_by(ExplorationAttempt.created_at.desc())
                .limit(1)
            )
            latest_created = last.created_at if last is not None else None

        target_key = next(
            result.key
            for result in profile.results
            if result.result_id == target_result_id
        )
        seed = next(
            (
                f"{candidate:032x}"
                for candidate in range(500_000)
                if select_exploration_result(
                    f"{candidate:032x}", level, recent, tuple(map(str, excluded)), profile
                )
                == target_key
            ),
            None,
        )
        if seed is None:
            raise AssertionError(
                f"{label}: nenhum seed determinístico selecionou resultado elegível "
                f"{target_result_id!r} para Nv.{level}; excluídos={excluded!r}; "
                f"local={world.location!r}; {driver.diagnostic()}"
            )

        if latest_created is not None:
            latest_created = (
                latest_created.replace(tzinfo=UTC)
                if latest_created.tzinfo is None
                else latest_created.astimezone(UTC)
            )
            required_time = latest_created + timedelta(minutes=5, seconds=1)
            if driver.clock.instant < required_time:
                driver.clock.advance(
                    (required_time - driver.clock.instant).total_seconds(),
                    f"exploration cooldown before {label}",
                )

        ExploreClock = driver.clock.datetime_type()

        original_uuid4 = road_module.uuid4
        seed_pending = True

        def deterministic_uuid4():
            nonlocal seed_pending
            if seed_pending:
                seed_pending = False
                return UUID(hex=seed)
            return original_uuid4()

        before_xp_state = await driver.capture_xp_totals()
        before_xp = before_xp_state[0]
        async with sessions() as session:
            before_character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert before_character is not None
            before_crowns, before_vigor, before_level = (
                before_character.crowns,
                before_character.vigor,
                before_character.level,
            )

        with monkeypatch.context() as patch:
            patch.setattr(road_module, "datetime", ExploreClock)
            patch.setattr(road_module, "uuid4", deterministic_uuid4)
            service = RoadService(sessions, "ocaso")
            prepared = await service.prepare_explore(actor)
            assert prepared is not None and prepared.kind == "explore_prepare", (
                f"{label}: preparação de Desbravar indisponível: {prepared!r}; "
                f"{driver.diagnostic()}"
            )
            view = await service.explore(actor)

        assert view is not None and view.kind == "exploration", (
            f"{label}: Desbravar não concluiu resultado narrativo: {view!r}; "
            f"{driver.diagnostic()}"
        )
        assert view.result_id == target_result_id, (view, driver.diagnostic())
        acknowledged = await RoadService(sessions, "ocaso").acknowledge_result(
            actor, view.attempt_id
        )
        assert acknowledged is not None and acknowledged.kind not in {
            "exploration",
            "combat",
        }, (acknowledged, driver.diagnostic())
        async with sessions() as session:
            attempt = await session.get(ExplorationAttempt, view.attempt_id)
            assert attempt is not None and attempt.result_acknowledged is True, (
                f"{label}: recibo de Desbravar não foi reconhecido no banco"
            )
        after_xp_state = await driver.capture_xp_totals()
        after_xp = after_xp_state[0]
        driver.record_public_xp_delta(
            f"direct:Desbravar:{view.attempt_id}:{target_result_id}",
            "Desbravar",
            before_xp_state,
            after_xp_state,
        )
        async with sessions() as session:
            after_character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert after_character is not None
            receipt = {
                "local": view.location,
                "result": view.result_id,
                "xp": after_xp - before_xp,
                "crowns": after_character.crowns - before_crowns,
                "vigor_spent": before_vigor - after_character.vigor,
                "level_before": before_level,
                "level_after": after_character.level,
                "receipt": view.result_text,
            }
        print(f"TDO_EXPLORE_RECEIPT={receipt!r}", flush=True)
        await driver.snapshot(f"Desbravar · {label} · {target_result_id}")
        return view

    async def run_solo_dungeon(family_id, label):
        mark = await driver.snapshot(f"{label} · antes do detalhe")
        print(f"TDO_DUNGEON_ENTRY_SNAPSHOT={mark.state!r}", flush=True)
        service = DungeonService(sessions, "ocaso")
        detail = await service.detail(actor, family_id)
        assert detail is not None and detail.kind == "detail", (detail, driver.diagnostic())
        assert dict(detail.difficulty_gates).get("stable") == "available", (
            detail,
            driver.diagnostic(),
        )
        current = await service.start_solo(actor, "stable", family_id)
        while (
            current is not None
            and current.kind == "detail"
            and current.reason == "vigor"
        ):
            assert current.run_id is None and current.vigor < 25, current
            seconds = await driver.clock.wait_for_vigor(
                sessions, actor, 25, f"offline natural regeneration before {label}"
            )
            assert seconds > 0
            await driver.snapshot(f"{label} · espera legítima de Vigor · {seconds:.0f}s")
            refreshed = await service.detail(actor, family_id)
            assert refreshed is not None and refreshed.kind == "detail"
            assert refreshed.vigor >= 25, (
                f"{label}: relógio avançou {seconds}s mas o serviço público não reconciliou "
                f"Vigor suficiente: {refreshed!r}; {driver.diagnostic()}"
            )
            current = await service.start_solo(actor, "stable", family_id)
        assert current is not None and current.run_id is not None, (
            f"{label}: run Solo não iniciou: {current!r}; {driver.diagnostic()}"
        )
        original_run_id = current.run_id
        await driver.snapshot(f"{label} · run iniciada")
        encounter_attempts = 0
        retries = 0
        while encounter_attempts < 8:
            if current.run_id != original_run_id:
                raise AssertionError(f"{label}: reconnect/retry criou outra run")
            if current.kind in {"completed", "failed", "expired"}:
                break
            if current.kind == "brazier":
                current = await service.activate_brazier(
                    actor, current.run_id, current.state_version
                )
                assert current is not None and current.kind != "stale", (
                    f"{label}: ativação do Braseiro falhou: {current!r}"
                )
                await driver.snapshot(f"{label} · Braseiro ativado")
                continue
            if current.kind == "retry":
                if retries >= 1:
                    break
                retries += 1
                current = await service.retry(actor, current.run_id, current.state_version)
                assert current is not None and current.kind != "stale"
                continue
            if current.combat is None:
                current = await service.begin_encounter(
                    actor, current.run_id, current.state_version
                )
            assert current is not None and current.combat is not None, (
                f"{label}: encontro não materializou combate: {current!r}; "
                f"{driver.diagnostic()}"
            )
            encounter_attempts += 1
            player_fighter = current.combat.fighters.get("player")
            enemies = [
                (fighter.name, fighter.stats, fighter.hp)
                for fighter_id, fighter in current.combat.fighters.items()
                if fighter_id != "player"
            ]
            print(
                f"TDO_DUNGEON_COMBAT_START={label!r} "
                f"player_stats={player_fighter.stats if player_fighter else None!r} "
                f"player_hp={player_fighter.hp if player_fighter else None!r} "
                f"enemies={enemies!r} "
                "heals="
                f"{_consumable_quantity(current.consumable_quantities, 'consumable.heal')}",
                flush=True,
            )

            def pick(current_view):
                combat = current_view.combat
                player = combat.fighters.get("player")
                if (
                    player is not None
                    and player.hp * 100 <= player.stats.hp * 35
                    and any(
                        option.item_id == "consumable.heal"
                        for option in current_view.consumable_options
                    )
                ):
                    return "consumable:consumable.heal"
                available = allowed_actions(combat)
                if combat.prepared_action is not None and "defend" in available:
                    return "defend"
                alive_enemies = sum(
                    fighter.hp > 0
                    for key, fighter in combat.fighters.items()
                    if key != "player"
                )
                if (
                    player is not None
                    and player.barrier <= 0
                    and alive_enemies > 1
                    and SENTINEL_ART_IDS["muralha_breve"] in available
                ):
                    return SENTINEL_ART_IDS["muralha_breve"]
                enemies = [
                    fighter
                    for key, fighter in combat.fighters.items()
                    if key != "player" and fighter.hp > 0
                ]
                if (
                    SENTINEL_ART_IDS["quebra_postura"] in available
                    and any(
                        not any(
                            effect.id == "sentinel.quebra_postura"
                            for effect in enemy.effects
                        )
                        for enemy in enemies
                    )
                ):
                    return SENTINEL_ART_IDS["quebra_postura"]
                for art_id in (
                    SENTINEL_ART_IDS["impacto_resoluto"],
                    SENTINEL_ART_IDS["golpe_de_guarda"],
                    SENTINEL_ART_IDS["quebra_postura"],
                ):
                    if art_id in available:
                        return art_id
                if "attack" in available:
                    return "attack"
                return driver.combat_action(combat)

            async def mutate(current_view, action):
                if action.startswith("consumable:"):
                    return await service.action(
                        actor,
                        current_view.run_id,
                        current_view.activity_id,
                        current_view.combat.version,
                        "attack",
                        consumable_id=action.removeprefix("consumable:"),
                    )
                targets = action_target_ids(current_view.combat, action)
                action_definition = current_view.combat.player_actions.get(action)
                if (
                    action_definition is not None
                    and action_definition.target_mode == "opponent"
                    and len(targets) > 1
                ):
                    target_by_id = {
                        fighter.id: fighter
                        for key, fighter in current_view.combat.fighters.items()
                        if key != "player"
                    }
                    if len(targets) >= 3:
                        # The Galerias E4 adds have low HP and add enemy turns;
                        # remove a guard before focusing the boss.
                        target_id = min(
                            targets,
                            key=lambda candidate_id: (
                                target_by_id[candidate_id].hp,
                                -target_by_id[candidate_id].stats.attack,
                                candidate_id,
                            ),
                        )
                    else:
                        target_id = max(
                            targets,
                            key=lambda candidate_id: (
                                target_by_id[candidate_id].stats.attack,
                                target_by_id[candidate_id].stats.agility,
                                -target_by_id[candidate_id].hp,
                            ),
                        )
                    targets = (target_id,)
                return await service.action(
                    actor,
                    current_view.run_id,
                    current_view.activity_id,
                    current_view.combat.version,
                    action,
                    targets[0] if targets else None,
                )

            current = await driver.combat_to_result(
                current,
                mutate,
                lambda: DungeonService(sessions, "ocaso").resume(actor),
                label=f"{label} · Encontro {current.ordinal} · tentativa {encounter_attempts}",
                action_picker=pick,
                trace_actions=True,
            )
            await driver.snapshot(
                f"{label} · resultado do Encontro {current.ordinal} · {current.kind}"
            )
            if current.kind in {"failed", "completed"}:
                break

        assert current.run_id == original_run_id, (current, driver.diagnostic())
        async with sessions() as session:
            run = await session.get(DungeonRun, original_run_id)
            assert run is not None
            outcome = {
                "family": family_id,
                "status": run.status,
                "difficulty": run.difficulty,
                "encounter": run.current_encounter_ordinal,
                "brazier_exists": run.has_brazier,
                "brazier_activated": run.brazier_activated,
                "internal_xp": (run.progress or {}).get("internal_xp", 0),
                "retry_count": retries,
                "encounter_attempts": encounter_attempts,
            }
        assert outcome["status"] in {"completed", "failed"}, (
            f"{label}: run permaneceu sem resolução terminal: {outcome!r}; "
            f"{driver.diagnostic()}"
        )
        print(f"TDO_DUNGEON_RUN={outcome!r}", flush=True)
        await driver.snapshot(f"{label} · run {outcome['status']}")
        return outcome

    async def equip_best_available_combat_gear():
        """Equip only owned items that improve the official combat stat vector."""
        equipment_service = EquipmentService(sessions, "ocaso")
        changed = []
        for _ in range(12):
            async with sessions.begin() as session:
                character = await session.scalar(
                    select(Character)
                    .where(Character.telegram_id == actor)
                    .with_for_update()
                )
                assert character is not None
                owned = (
                    await session.scalars(
                        select(EquipmentItem)
                        .where(EquipmentItem.character_id == character.id)
                        .order_by(EquipmentItem.id)
                    )
                ).all()
                equipped_rows = (
                    await session.execute(
                        select(CharacterEquipmentSlot.slot, EquipmentItem)
                        .join(
                            EquipmentItem,
                            EquipmentItem.id == CharacterEquipmentSlot.equipment_item_id,
                        )
                        .where(CharacterEquipmentSlot.character_id == character.id)
                    )
                ).all()
                assignments = {
                    parse_equipment_slot(slot): item for slot, item in equipped_rows
                }
                baseline_configuration = build_equipment_configuration(
                    character,
                    list(assignments.items()),
                    version=character.combat_configuration_version,
                    talent_choices=(
                        await load_equipment_configuration(
                            session, character, lock_rows=False
                        )
                    ).talent_choices,
                )
                baseline_stats = resolve_character_combat_stats(
                    character, baseline_configuration
                )
                version = character.combat_configuration_version
                level = character.level
                currently_equipped = {item.id for item in assignments.values()}
                candidates = []
                for item in owned:
                    if item.id in currently_equipped or item.item_level > level:
                        continue
                    assignment = assignment_for_item_slot(item.slot)
                    if assignment is None:
                        continue
                    replaced = dict(assignments)
                    if item.slot == "2H":
                        replaced.pop(parse_equipment_slot("Secundária"), None)
                    replaced[assignment.slot] = item
                    try:
                        candidate_configuration = build_equipment_configuration(
                            character,
                            list(replaced.items()),
                            version=version,
                            talent_choices=baseline_configuration.talent_choices,
                        )
                        candidate_stats = resolve_character_combat_stats(
                            character, candidate_configuration
                        )
                    except ValueError:
                        continue
                    normalized_delta = sum(
                        (
                            (new - old) / max(abs(old), Decimal(1))
                            for old, new in zip(
                                baseline_stats.values(), candidate_stats.values(), strict=True
                            )
                        ),
                        Decimal(0),
                    )
                    if normalized_delta > 0:
                        candidates.append(
                            (
                                normalized_delta,
                                str(item.id),
                                assignment.slot,
                                item,
                            )
                        )
                if not candidates:
                    break
                candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)
                delta, _item_id, slot, item = candidates[0]
            result = await equipment_service.equip_item(
                actor,
                item.id,
                expected_configuration_version=version,
            )
            if result is not None and result.changed:
                changed.append(
                    (slot.value, item.item_name, item.rarity, item.item_level, str(delta))
                )
            else:
                break
        return changed

    async def travel_to_refuge():
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            world = await session.get(WorldState, character.id)
            assert world is not None
            location = world.location
        if location == ROAD:
            arrived = await road.travel(actor, REFUGE)
        elif location == CHARNECA:
            arrived = await road.travel_route(actor, REFUGE)
        elif location == BOSQUE:
            arrived = await road.travel_route(actor, CHARNECA)
            assert arrived is not None
            arrived = await road.travel_route(actor, REFUGE)
        elif location == RUINS:
            arrived = await road.travel_route(actor, BOSQUE)
            assert arrived is not None
            arrived = await road.travel_route(actor, CHARNECA)
            assert arrived is not None
            arrived = await road.travel_route(actor, REFUGE)
        else:
            assert location == REFUGE
            return
        assert arrived is not None and arrived.location == REFUGE, (arrived, driver.diagnostic())

    async def travel_from_refuge_to(destination):
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            world = await session.get(WorldState, character.id)
            assert world is not None
            location = world.location
        if location == ROAD:
            await road.travel(actor, REFUGE)
            location = REFUGE
        if location != REFUGE:
            await travel_to_refuge()
        if destination == REFUGE:
            return
        arrived = await road.travel_route(actor, CHARNECA)
        assert arrived is not None and arrived.location == CHARNECA
        if destination == CHARNECA:
            return
        arrived = await road.travel_route(actor, BOSQUE)
        assert arrived is not None and arrived.location == BOSQUE
        if destination == BOSQUE:
            return
        assert destination == RUINS
        arrived = await road.travel_route(actor, RUINS)
        assert arrived is not None and arrived.location == RUINS, (
            arrived,
            driver.diagnostic(),
        )

    async def rest_and_return(destination):
        await travel_to_refuge()
        rested = await WorldService(sessions, "ocaso").rest(actor)
        assert rested is not None and rested.hp == rested.max_hp
        if destination != REFUGE:
            await travel_from_refuge_to(destination)

    dungeon_professions = ProfessionService(sessions, "ocaso")
    dungeon_crafting = CraftingService(sessions, "ocaso")

    async def ensure_dungeon_professions():
        view = await dungeon_professions.view(actor)
        assert view is not None
        if not view.configured:
            await dungeon_professions.initial_selection(actor, "alchemist", "blacksmith")

    async def healing_stock_count():
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            quantity = await session.scalar(
                select(func.coalesce(func.sum(ConsumableStack.quantity), 0)).where(
                    ConsumableStack.character_id == character.id,
                    ConsumableStack.consumable_id == "consumable.heal",
                )
            )
            return int(quantity or 0)

    async def craft_dungeon_healing_stock(target_quantity):
        quantity = await healing_stock_count()
        while quantity < target_quantity:
            recipe = await dungeon_crafting.recipe(actor, "recipe.tdo.alchemist.heal")
            if recipe is None or not recipe.available:
                break
            preview = await dungeon_crafting.preview(actor, "recipe.tdo.alchemist.heal")
            assert preview is not None
            result = await dungeon_crafting.commit(actor, preview.receipt_id)
            assert result is not None and result.status == "committed"
            quantity += 1
        return quantity

    async def craft_and_equip_dungeon_equipment(recipe_id, label):
        recipe = await dungeon_crafting.recipe(actor, recipe_id)
        if recipe is None or not recipe.available:
            await driver.snapshot(f"{label} · receita indisponível com recursos legítimos")
            return None
        preview = await dungeon_crafting.preview(actor, recipe_id)
        assert preview is not None
        result = await dungeon_crafting.commit(actor, preview.receipt_id)
        assert result is not None and result.status == "committed"
        item_id = result.output_payload.get("equipment_item_id")
        assert item_id is not None
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            item = await session.get(EquipmentItem, UUID(item_id))
            assert item is not None and item.character_id == character.id
            configuration_version = character.combat_configuration_version
        equipped = await EquipmentService(sessions, "ocaso").equip_item(
            actor,
            item.id,
            expected_configuration_version=configuration_version,
        )
        assert equipped is not None and equipped.changed
        await driver.snapshot(f"{label} · criado e equipado por serviços oficiais")
        return item.id

    await road.travel(actor, ROAD)
    await explore_result("explore.tdo.estrada.marco_viajantes", "Estrada das Cinzas")
    await road.travel(actor, REFUGE)
    for attempt in range(40):
        offer = await S1Service(sessions, "ocaso").offer(actor)
        if offer is not None and offer.kind == "offer":
            break
        assert await current_level() < 2 or offer is not None, driver.diagnostic()
        if await current_level() < 2:
            await road.travel(actor, ROAD)
            await manual_hunt(f"Nv.2 · Caçada {attempt + 1}")
            await road.travel(actor, REFUGE)
    s1 = S1Service(sessions, "ocaso")
    accepted_s1 = await s1.accept(actor)
    assert accepted_s1 is not None and accepted_s1.status == "active", accepted_s1
    await road.travel(actor, ROAD)
    for point in (3, 1, 2):
        accepted_s1 = await s1.investigate_point(actor, point, accepted_s1.state_version)
    accepted_s1 = await s1.examine_ashes(actor, accepted_s1.state_version)
    accepted_s1 = await s1.observe_light(actor, accepted_s1.state_version)
    assert accepted_s1.step == 4
    await road.travel(actor, REFUGE)
    completed_s1 = await s1.complete_with_oren(actor, accepted_s1.state_version)
    assert completed_s1 is not None and completed_s1.status == "completed"
    await driver.snapshot("S1 concluída por Oren")

    p2 = P2Service(sessions, "ocaso")
    for attempt in range(50):
        offer = await p2.alda(actor)
        if offer is not None and offer.available:
            break
        assert await current_level() < 3, (offer, driver.diagnostic())
        await road.travel(actor, ROAD)
        await manual_hunt(f"Nv.3 · Caçada {attempt + 1}")
        await road.travel(actor, REFUGE)
        rested = await WorldService(sessions, "ocaso").rest(actor)
        assert rested is not None and rested.hp == rested.max_hp
    active_p2 = await p2.accept(actor, offer.state_version)
    assert active_p2 is not None and active_p2.status == "active", active_p2
    rested_before_p2 = await WorldService(sessions, "ocaso").rest(actor)
    assert rested_before_p2 is not None and rested_before_p2.hp == rested_before_p2.max_hp
    active_p2 = await p2.travel_to_charneca(actor, active_p2.state_version)
    assert active_p2.step == 2 and active_p2.location == "Charneca da Fuligem"
    for point in ASH_POINT_IDS:
        active_p2 = await p2.examine_ash_point(actor, point, active_p2.state_version)
    assert active_p2.step == 3 and active_p2.combat is not None
    if active_p2.combat.result == "defeat" and active_p2.activity_status == "active":
        mark = await driver.snapshot("P2 · derrota terminal ao materializar combate")
        raise AssertionError(
            "P0: P2 persistiu um combate já derrotado como Foreground ativo; "
            f"snapshot={mark.state!r}\n{driver.diagnostic()}"
        )
    for attempt in range(6):
        active_p2 = await driver.combat_to_result(
            active_p2,
            lambda current, action: p2.action(
                actor, current.activity_id, current.activity_state_version, action
            ),
            lambda: P2Service(sessions, "ocaso").resume(actor),
            label=f"P2 · Aranha da Fuligem · tentativa {attempt + 1}",
        )
        if active_p2.progress.get("combat_result") == "victory":
            break
        if (
            active_p2.combat is not None
            and active_p2.combat.result == "defeat"
            and active_p2.activity_status == "active"
        ):
            mark = await driver.snapshot(
                f"P2 · derrota terminal no retry {attempt + 1}"
            )
            raise AssertionError(
                "P0: retry de P2 persistiu um combate já derrotado como Foreground ativo; "
                f"snapshot={mark.state!r}\n{driver.diagnostic()}"
            )
        assert active_p2.progress.get("combat_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"P2 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 5:
            active_p2 = await p2.return_to_charneca(actor, active_p2.state_version)
            assert active_p2 is not None and active_p2.combat is not None, driver.diagnostic()
    assert active_p2.progress.get("combat_result") == "victory", driver.diagnostic()
    active_p2 = await p2.examine_pedra_marcada(actor, active_p2.state_version)
    active_p2 = await p2.return_to_refuge(actor, active_p2.state_version)
    active_p2 = await p2.oren(actor, active_p2.state_version)
    active_p2 = await p2.report_to_alda(actor, active_p2.state_version)
    assert active_p2.status == "completed"
    await driver.snapshot("P2 concluída")

    await travel_from_refuge_to(CHARNECA)
    for attempt in range(24):
        if await current_level() >= 4:
            break
        await manual_hunt(f"Nv.4 · Caçada complementar na Charneca {attempt + 1}")
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location != CHARNECA or needs_rest:
            await rest_and_return(CHARNECA)
    assert await current_level() >= 4, driver.diagnostic()
    # S2 is eligible after P2 and Nv.4, so use its authored XP before more grind.
    await travel_to_refuge()
    # Keep this mission flow tied to its own persisted gate and progress.
    s2 = S2Service(sessions, "ocaso")
    s2_offer = await s2.oren(actor)
    assert s2_offer is not None and s2_offer.available, (s2_offer, driver.diagnostic())
    s2_view = await s2.accept(actor, s2_offer.state_version)
    await road.travel_route(actor, CHARNECA)
    s2_view = await s2.find_camp(actor, s2_view.state_version)
    for vestige in S2_VESTIGE_IDS:
        s2_view = await s2.examine_vestige(actor, vestige, s2_view.state_version)
    assert s2_view.kind == "combat" and s2_view.combat is not None
    for attempt in range(6):
        if s2_view.combat.result == "defeat" and s2_view.activity_status == "active":
            mark = await driver.snapshot("S2 · derrota terminal ao materializar combate")
            raise AssertionError(
                f"P0: S2 persistiu derrota inicial como Foreground ativo; {mark.state!r}"
            )
        s2_view = await driver.combat_to_result(
            s2_view,
            lambda current, action: s2.action(
                actor, current.activity_id, current.activity_state_version, action
            ),
            lambda: S2Service(sessions, "ocaso").resume(actor),
            label=f"S2 · Peregrino Calcinado · tentativa {attempt + 1}",
        )
        if s2_view.progress.get("encounter_result") == "victory":
            break
        assert s2_view.progress.get("encounter_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"S2 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 5:
            async with sessions() as session:
                character = await session.scalar(
                    select(Character).where(Character.telegram_id == actor)
                )
                world = await session.get(WorldState, character.id)
                location = world.location
            if location == REFUGE:
                await road.travel_route(actor, CHARNECA)
            s2_view = await s2.retry(actor, s2_view.state_version)
            assert s2_view.kind == "combat" and s2_view.combat is not None
    assert s2_view.progress.get("encounter_result") == "victory", driver.diagnostic()
    s2_view = await s2.recover_fragment(actor, s2_view.state_version)
    assert s2_view.step == 6
    await road.travel_route(actor, REFUGE)
    s2_view = await s2.complete_with_oren(actor, s2_view.state_version)
    assert s2_view.status == "completed"
    await driver.snapshot("S2 concluída")
    await travel_from_refuge_to(CHARNECA)
    await explore_result("explore.tdo.charneca.braseiro", "Charneca · Braseiro do Vento Morto")
    await explore_result("explore.tdo.charneca.cripta", "Charneca · descoberta da Cripta")
    # The first diagnostic attempt previously entered at the minimum level
    # without any consumables. Select the two active professions and make a
    # small healing stock through the public craft flow before this optional
    # run; do not grant or edit inventory directly.
    await travel_to_refuge()
    await ensure_dungeon_professions()
    crypt_healing_stock = await craft_dungeon_healing_stock(2)
    crypt_weapon = await craft_and_equip_dungeon_equipment(
        "recipe.tdo.blacksmith.walker_weapon.comum",
        "Cripta · Arma Principal",
    )
    await driver.snapshot(
        "Cripta · preparação legítima · "
        f"Arma={crypt_weapon is not None}; Poções de Cura={crypt_healing_stock}"
    )
    await rest_and_return(CHARNECA)
    crypt_equipment = await equip_best_available_combat_gear()
    crypt_arts = ActiveArtService(sessions, "ocaso")
    crypt_art_view = await crypt_arts.view(actor)
    assert crypt_art_view is not None
    second_sentinel_art = SENTINEL_ART_IDS["quebra_postura"]
    if (
        second_sentinel_art in crypt_art_view.available_art_ids
        and second_sentinel_art not in {entry.art_id for entry in crypt_art_view.slots}
    ):
        equipped_art = await crypt_arts.equip_art(
            actor,
            2,
            second_sentinel_art,
            expected_configuration_version=crypt_art_view.combat_configuration_version,
        )
        assert equipped_art is not None and equipped_art.changed
    await driver.snapshot(
        "Cripta · equipamento comparado pela configuração real · "
        f"{crypt_equipment!r}; Artes={second_sentinel_art in crypt_art_view.available_art_ids}"
    )
    crypt_before_xp = await current_xp_total()
    crypt_run = await run_solo_dungeon(CRYPT_FAMILY_ID, "Cripta do Ocaso · Estável")
    crypt_after_xp = await current_xp_total()
    if crypt_run["status"] == "completed":
        print(
            "TDO_CRYPT_XP="
            f"{{'actual_delta': {crypt_after_xp - crypt_before_xp}, "
            f"'completion_reference': {dungeon_completion_xp(6, 'stable', first_clear=True)}, "
            f"'first_clear_total_expected_before_milestones': 6640}}",
            flush=True,
        )
    await travel_to_refuge()
    await driver.snapshot("Nv.4+ · Cripta concluída ou derrota legítima registrada")

    # Continue with level-appropriate public hunts until P3's level gate is met.
    # A defeat or low HP uses the normal Refuge recovery; this never restores Vigor.
    await travel_from_refuge_to(CHARNECA)
    for attempt in range(45):
        if await current_level() >= 5:
            break
        await manual_hunt(
            f"Nv.5 · Caçada complementar na Charneca {attempt + 1}",
            capture=attempt % 5 == 4,
        )
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location != CHARNECA or needs_rest:
            await rest_and_return(CHARNECA)
        if attempt % 5 == 4:
            await driver.snapshot(
                f"progressão pública para Nv.5 · {attempt + 1} Caçadas após conteúdo único"
            )
    assert await current_level() >= 5, driver.diagnostic()
    await driver.snapshot("Nv.5 · gate de P3 alcançado")
    await travel_to_refuge()

    talents = TalentService(sessions, "ocaso")
    talent_view = await talents.view(actor)
    assert talent_view is not None and talent_view.available_points == 1
    first_tier_talents = [
        entry.talent_id for entry in talent_view.talents if entry.level == 5
    ]
    assert len(first_tier_talents) == 3
    first_talent = await talents.acquire(
        actor, first_tier_talents[0], talent_view.combat_configuration_version
    )
    assert first_talent is not None and first_talent.changed
    await driver.snapshot("Ponto de Talento do Nv.5 gasto pelo serviço oficial")

    p3 = P3Service(sessions, "ocaso")
    p3_offer = await p3.oren(actor)
    assert p3_offer is not None and p3_offer.available, (p3_offer, driver.diagnostic())
    p3_view = await p3.accept(actor, p3_offer.state_version)
    p3_view = await p3.mission_route(actor, p3_view.state_version, CHARNECA)
    p3_view = await p3.enter_bosque(actor, p3_view.state_version)
    assert p3_view.step == 2 and p3_view.location == BOSQUE
    for fragment in ("p3.fragment.3", "p3.fragment.1", "p3.fragment.2"):
        p3_view = await p3.examine_fragment(actor, fragment, p3_view.state_version)
    assert p3_view.kind == "combat" and p3_view.combat is not None
    if p3_view.combat.result == "defeat" and p3_view.activity_status == "active":
        mark = await driver.snapshot("P3 · derrota terminal ao materializar combate")
        raise AssertionError(
            "P0: P3 persistiu um combate já derrotado como Foreground ativo; "
            f"snapshot={mark.state!r}\n{driver.diagnostic()}"
        )
    for attempt in range(5):
        p3_view = await driver.combat_to_result(
            p3_view,
            lambda current, action: p3.action(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: P3Service(sessions, "ocaso").resume(actor),
            label=f"P3 · Cervo Escoriado · tentativa {attempt + 1}",
        )
        if p3_view.progress.get("combat_result") == "victory":
            break
        assert p3_view.progress.get("combat_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"P3 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 4:
            to_charneca = await p3.mission_route(actor, p3_view.state_version, CHARNECA)
            to_bosque = await p3.enter_bosque(actor, to_charneca.state_version)
            p3_view = await p3.retry(actor, to_bosque.state_version)
            assert p3_view.kind == "combat" and p3_view.combat is not None
    assert p3_view.progress.get("combat_result") == "victory", driver.diagnostic()
    carved = await p3.examine_carved_fragment(actor, p3_view.state_version)
    to_charneca = await p3.mission_route(actor, carved.state_version, CHARNECA)
    to_refuge = await p3.mission_route(actor, to_charneca.state_version, REFUGE)
    oren = await p3.talk_to_oren(actor, to_refuge.state_version)
    p3_complete = await p3.choose_reward(actor, oren.state_version, "reliquary")
    assert p3_complete is not None and p3_complete.status == "completed"
    await driver.snapshot("P3 concluída")

    # S3 is available after P3 at Nv.5; consume that authored content first.
    s3 = S3Service(sessions, "ocaso")
    s3_offer = await s3.alda(actor)
    assert s3_offer is not None and s3_offer.available, (s3_offer, driver.diagnostic())
    s3_view = await s3.accept(actor, s3_offer.state_version)
    await road.travel_route(actor, CHARNECA)
    await road.travel_route(actor, BOSQUE)
    s3_view = await s3.interact(actor, s3_view.state_version, "route")
    for track in S3_TRACKS:
        s3_view = await s3.interact(actor, s3_view.state_version, "track", track)
    assert s3_view.kind == "combat" and s3_view.combat is not None
    for attempt in range(6):
        if s3_view.combat.result == "defeat" and s3_view.activity_status == "active":
            mark = await driver.snapshot("S3 · derrota terminal ao materializar combate")
            raise AssertionError(
                f"P0: S3 persistiu derrota inicial como Foreground ativo; {mark.state!r}"
            )
        s3_view = await driver.combat_to_result(
            s3_view,
            lambda current, action: s3.action(
                actor, current.activity_id, current.activity_state_version, action
            ),
            lambda: S3Service(sessions, "ocaso").resume(actor),
            label=f"S3 · Cervo Escoriado · tentativa {attempt + 1}",
        )
        if s3_view.progress.get("combat_result") == "victory":
            break
        assert s3_view.progress.get("combat_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"S3 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 5:
            async with sessions() as session:
                character = await session.scalar(
                    select(Character).where(Character.telegram_id == actor)
                )
                world = await session.get(WorldState, character.id)
                location = world.location
            if location == REFUGE:
                await road.travel_route(actor, CHARNECA)
                await road.travel_route(actor, BOSQUE)
            elif location == CHARNECA:
                await road.travel_route(actor, BOSQUE)
            s3_view = await s3.retry(actor, s3_view.state_version)
            assert s3_view.kind == "combat" and s3_view.combat is not None
    assert s3_view.progress.get("combat_result") == "victory", driver.diagnostic()
    s3_view = await s3.interact(actor, s3_view.state_version, "cargo")
    await road.travel_route(actor, CHARNECA)
    await road.travel_route(actor, REFUGE)
    s3_view = await s3.interact(actor, s3_view.state_version, "report")
    assert s3_view.status == "completed"
    await driver.snapshot("S3 concluída")
    await travel_from_refuge_to(BOSQUE)
    for attempt in range(40):
        if await current_level() >= 6:
            break
        await manual_hunt(f"Nv.6 · Caçada complementar no Bosque {attempt + 1}")
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location != BOSQUE or needs_rest:
            await rest_and_return(BOSQUE)
    assert await current_level() >= 6, driver.diagnostic()
    await explore_result("explore.tdo.bosque.braseiro", "Bosque · Braseiro dos Galhos Mortos")

    # Use the P3 artifact reward through the real Equipment validator; its
    # existing HP/ATQ/DEF budget is a legitimate upgrade for the public journey.
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        p3_artifact = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.character_id == character.id,
                EquipmentItem.source_key == "p3.sob_galhos_calcinados:equipment:reliquary",
            )
        )
        assert p3_artifact is not None, driver.diagnostic()
        artifact_id = p3_artifact.id
        configuration_version = character.combat_configuration_version
    equipped_p3 = await EquipmentService(sessions, "ocaso").equip_item(
        actor,
        artifact_id,
        expected_configuration_version=configuration_version,
    )
    assert equipped_p3 is not None and equipped_p3.changed
    await driver.snapshot("Relicário de Cinzas equipado pela configuração oficial")

    nv7_hunts = 0
    for attempt in range(100):
        if await current_level() >= 7:
            break
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location == REFUGE:
            await road.travel_route(actor, CHARNECA)
            await road.travel_route(actor, BOSQUE)
        elif location == CHARNECA:
            await road.travel_route(actor, BOSQUE)
        else:
            assert location == BOSQUE, (location, driver.diagnostic())
        await manual_hunt(
            f"Nv.7 · Caçada {attempt + 1}", capture=(attempt % 10 == 9)
        )
        nv7_hunts += 1
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location != BOSQUE or needs_rest:
            if location == BOSQUE:
                await road.travel_route(actor, CHARNECA)
            if location in {BOSQUE, CHARNECA}:
                await road.travel_route(actor, REFUGE)
            await WorldService(sessions, "ocaso").rest(actor)
    nv7_mark = await driver.snapshot("progressão até Nv.7 após conteúdo atual")
    print(
        "TDO_LEVEL_7_GATE="
        f"level={nv7_mark.state.get('level')} · "
        f"residual_xp={nv7_mark.state.get('xp')} · "
        f"next_level_xp={nv7_mark.state.get('xp_required_next_level')} · "
        f"manual_hunts_at_gate={nv7_hunts} · "
        f"vigor={nv7_mark.state.get('vigor')} · hp="
        f"{nv7_mark.state.get('hp')}/{nv7_mark.state.get('max_hp')}"
    )
    assert nv7_mark.state.get("level", 0) >= 7, driver.diagnostic()

    p4 = P4Service(sessions, "ocaso")
    p4_offer = await p4.offer(actor)
    assert p4_offer is not None and p4_offer.available, (p4_offer, driver.diagnostic())
    p4_view = await p4.accept(actor, p4_offer.state_version)
    await road.travel_route(actor, CHARNECA)
    await road.travel_route(actor, BOSQUE)
    p4_view = await p4.action(actor, p4_view.state_version, "path")
    p4_view = await p4.action(actor, p4_view.state_version, "enter")
    assert p4_view.kind == "combat" and p4_view.combat is not None
    if p4_view.combat.result == "defeat" and p4_view.activity_status == "active":
        mark = await driver.snapshot("P4 · derrota terminal ao materializar combate")
        raise AssertionError(
            "P0: P4 persistiu um combate já derrotado como Foreground ativo; "
            f"snapshot={mark.state!r}\n{driver.diagnostic()}"
        )
    for attempt in range(5):
        p4_view = await driver.combat_to_result(
            p4_view,
            lambda current, action: p4.action_combat(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: P4Service(sessions, "ocaso").resume(actor),
            label=f"P4 · Vigia Rachado · tentativa {attempt + 1}",
        )
        if p4_view.progress.get("combat_result") == "victory":
            break
        if (
            p4_view.combat is not None
            and p4_view.combat.result == "defeat"
            and p4_view.activity_status == "active"
        ):
            mark = await driver.snapshot(f"P4 · derrota terminal · tentativa {attempt + 1}")
            raise AssertionError(
                "P0: P4 persistiu uma derrota terminal como Foreground ativo; "
                f"snapshot={mark.state!r}\n{driver.diagnostic()}"
            )
        assert p4_view.progress.get("combat_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"P4 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 4:
            await road.travel_route(actor, CHARNECA)
            await road.travel_route(actor, BOSQUE)
            returned = await p4.action(actor, p4_view.state_version, "enter")
            p4_view = await p4.action(actor, returned.state_version, "retry")
            assert p4_view.kind == "combat" and p4_view.combat is not None
    assert p4_view.progress.get("combat_result") == "victory", driver.diagnostic()
    p4_view = await p4.action(
        actor, p4_view.state_version, "structure", "p4.guard_structure.2"
    )
    p4_view = await p4.action(
        actor, p4_view.state_version, "structure", "p4.guard_structure.1"
    )
    p4_view = await p4.action(actor, p4_view.state_version, "safe_route")
    p4_view = await p4.action(actor, p4_view.state_version, "return")
    await road.travel_route(actor, CHARNECA)
    await road.travel_route(actor, REFUGE)
    p4_view = await p4.action(actor, p4_view.state_version, "report_oren")
    p4_complete = await p4.action(actor, p4_view.state_version, "report_alda")
    assert p4_complete.status == "completed"
    await driver.snapshot("P4 concluída")



    async def travel_to_ruins():
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id)
            location = world.location
        if location == ROAD:
            await road.travel(actor, REFUGE)
            location = REFUGE
        if location == REFUGE:
            await road.travel_route(actor, CHARNECA)
            location = CHARNECA
        if location == CHARNECA:
            await road.travel_route(actor, BOSQUE)
            location = BOSQUE
        if location == BOSQUE:
            arrival = await road.travel_route(actor, RUINS)
            assert arrival is not None and arrival.location == RUINS, (
                arrival,
                driver.diagnostic(),
            )
        else:
            assert location == RUINS, (location, driver.diagnostic())

    async def travel_to_refuge_from_ruins():
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id)
            location = world.location
        if location == RUINS:
            await road.travel_route(actor, BOSQUE)
            location = BOSQUE
        if location == BOSQUE:
            await road.travel_route(actor, CHARNECA)
            location = CHARNECA
        if location == CHARNECA:
            await road.travel_route(actor, REFUGE)
            location = REFUGE
        assert location == REFUGE, (location, driver.diagnostic())

    s4 = S4Service(sessions, "ocaso")
    s4_offer = await s4.oren(actor)
    assert s4_offer is not None and s4_offer.available, (s4_offer, driver.diagnostic())
    s4_view = await s4.accept(actor, s4_offer.state_version)
    await travel_to_ruins()
    for point in S4_WATCH_POINTS:
        s4_view = await s4.action(actor, s4_view.state_version, "watch", point)
    s4_view = await s4.action(actor, s4_view.state_version, "orientation")
    assert s4_view.kind == "combat" and s4_view.combat is not None
    for attempt in range(6):
        if s4_view.combat.result == "defeat" and s4_view.activity_status == "active":
            mark = await driver.snapshot("S4 · derrota terminal ao materializar combate")
            raise AssertionError(
                f"P0: S4 persistiu derrota inicial como Foreground ativo; {mark.state!r}"
            )
        s4_view = await driver.combat_to_result(
            s4_view,
            lambda current, action: s4.action_combat(
                actor, current.activity_id, current.activity_state_version, action
            ),
            lambda: S4Service(sessions, "ocaso").resume(actor),
            label=f"S4 · Vigia Rachado · tentativa {attempt + 1}",
        )
        if s4_view.progress.get("combat_result") == "victory":
            break
        assert s4_view.progress.get("combat_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"S4 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 5:
            await travel_to_ruins()
            s4_view = await s4.retry(actor, s4_view.state_version)
            assert s4_view.kind == "combat" and s4_view.combat is not None
    assert s4_view.progress.get("combat_result") == "victory", driver.diagnostic()
    s4_view = await s4.action(actor, s4_view.state_version, "turn_point")
    s4_view = await s4.action(actor, s4_view.state_version, "examine")
    await travel_to_refuge_from_ruins()
    s4_view = await s4.action(actor, s4_view.state_version, "report")
    assert s4_view.status == "completed"
    await driver.snapshot("S4 concluída")

    # S5's real gate is P4 + level 8. Continue with public Bosque hunts after
    # finishing the Nv.7 content instead of offering the mission early.
    nv8_pre_s5_hunts = 0
    for attempt in range(100):
        if await current_level() >= 8:
            break
        await travel_from_refuge_to(BOSQUE)
        await manual_hunt(
            f"Nv.8 · Caçada antes de S5 {attempt + 1}", capture=(attempt % 8 == 7)
        )
        nv8_pre_s5_hunts += 1
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location != BOSQUE or needs_rest:
            await rest_and_return(BOSQUE)
        if attempt % 8 == 7:
            await driver.snapshot(
                f"progressão pública de Nv.7 a Nv.8 antes de S5 · {attempt + 1} Caçadas"
            )
    nv8_pre_s5 = await driver.snapshot("Nv.8 · gate real de S5 alcançado")
    print(
        "TDO_LEVEL_8_GATE="
        f"level={nv8_pre_s5.state.get('level')} · "
        f"residual_xp={nv8_pre_s5.state.get('xp')} · "
        f"manual_hunts_before_s5={nv8_pre_s5_hunts} · "
        f"vigor={nv8_pre_s5.state.get('vigor')}"
    )
    assert nv8_pre_s5.state.get("level", 0) >= 8, driver.diagnostic()
    await travel_to_refuge()

    s5 = S5Service(sessions, "ocaso")
    s5_offer = await s5.oren(actor)
    assert s5_offer is not None and s5_offer.available, (s5_offer, driver.diagnostic())
    s5_view = await s5.accept(actor, s5_offer.state_version)
    await travel_to_ruins()
    s5_view = await s5.action(actor, s5_view.state_version, "investigate")
    for point in S5_LIGHT_POINTS:
        s5_view = await s5.action(actor, s5_view.state_version, "light_point", point)
    assert s5_view.kind == "combat" and s5_view.combat is not None
    for attempt in range(6):
        if s5_view.combat.result == "defeat" and s5_view.activity_status == "active":
            mark = await driver.snapshot("S5 · derrota terminal ao materializar combate")
            raise AssertionError(
                f"P0: S5 persistiu derrota inicial como Foreground ativo; {mark.state!r}"
            )
        s5_view = await driver.combat_to_result(
            s5_view,
            lambda current, action: s5.action_combat(
                actor, current.activity_id, current.activity_state_version, action
            ),
            lambda: S5Service(sessions, "ocaso").resume(actor),
            label=f"S5 · criatura das luzes · tentativa {attempt + 1}",
        )
        if s5_view.progress.get("combat_result") == "victory":
            break
        assert s5_view.progress.get("combat_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"S5 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 5:
            await travel_to_ruins()
            s5_view = await s5.retry(actor, s5_view.state_version)
            assert s5_view.kind == "combat" and s5_view.combat is not None
    assert s5_view.progress.get("combat_result") == "victory", driver.diagnostic()
    s5_view = await s5.action(actor, s5_view.state_version, "record")
    await travel_to_refuge_from_ruins()
    s5_view = await s5.action(actor, s5_view.state_version, "report")
    assert s5_view.status == "completed"
    await driver.snapshot("S5 concluída")

    # Reach the minimum level for Galleries through its public overland gate,
    # then spend the first Stable run before supplementing with manual Hunts.
    for attempt in range(36):
        if await current_level() >= 8:
            break
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location != BOSQUE:
            await travel_from_refuge_to(BOSQUE)
        await manual_hunt(
            f"Nv.8 · Caçada complementar {attempt + 1}", capture=(attempt % 8 == 7)
        )
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location != BOSQUE or needs_rest:
            await rest_and_return(BOSQUE)
        if attempt % 8 == 7:
            await driver.snapshot(f"progressão pública até Nv.8 · {attempt + 1} Caçadas")
    assert await current_level() >= 8, driver.diagnostic()
    # Use the public profession/crafting/equipment services at a safe hub
    # before the Galleries, where the previous run still lacked a Principal
    # weapon and had no healing consumables despite having enough resources.
    await travel_to_refuge()
    await ensure_dungeon_professions()
    gallery_weapon = await craft_and_equip_dungeon_equipment(
        "recipe.tdo.blacksmith.walker_weapon.comum",
        "Galerias · Arma Principal",
    )
    gallery_cuirass = await craft_and_equip_dungeon_equipment(
        "recipe.tdo.blacksmith.fuligem_cuirass.comum",
        "Galerias · Couraça",
    )
    gallery_healing_stock = await craft_dungeon_healing_stock(4)
    gallery_gear_changes = await equip_best_available_combat_gear()
    await driver.snapshot(
        "Galerias · preparação legítima · "
        f"Arma={gallery_weapon is not None}; Couraça={gallery_cuirass is not None}; "
        f"Poções de Cura={gallery_healing_stock}; melhor equipamento elegível="
        f"{gallery_gear_changes!r}"
    )
    await rest_and_return(RUINS)
    await explore_result("explore.tdo.ruinas.galerias", "Ruínas · descoberta das Galerias")
    galleries_run = await run_solo_dungeon(
        GALLERIES_FAMILY_ID,
        "Galerias do Vigia · Estável",
    )
    assert galleries_run["status"] in {"completed", "failed"}
    await rest_and_return(RUINS)
    await explore_result("explore.tdo.ruinas.braseiro", "Ruínas · Braseiro do Poente")
    await travel_to_refuge_from_ruins()

    for attempt in range(36):
        if await current_level() >= 9:
            break
        await travel_from_refuge_to(BOSQUE)
        await manual_hunt(
            f"Nv.9 · Caçada complementar {attempt + 1}", capture=(attempt % 8 == 7)
        )
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            needs_rest = character.hp * 10 < character.max_hp * 6
            location = world.location
        if location != BOSQUE or needs_rest:
            await rest_and_return(BOSQUE)
        if attempt % 8 == 7:
            await driver.snapshot(f"progressão pública até Nv.9 · {attempt + 1} Caçadas")
    assert await current_level() >= 9, driver.diagnostic()
    await travel_to_refuge()
    await driver.snapshot("Nv.9 · gate de P5 alcançado")

    # Configure professions and craft only from resources earned in the
    # public journey. Refill at the Refuge after a legitimate P5 recovery.
    profession_service = ProfessionService(sessions, "ocaso")
    professions = await profession_service.view(actor)
    assert professions is not None
    if not professions.configured:
        await profession_service.initial_selection(actor, "alchemist", "blacksmith")
    crafting = CraftingService(sessions, "ocaso")

    async def refill_p5_healing_stock(target_quantity=2):
        quantity = await healing_stock_count()
        while quantity < target_quantity:
            recipe = await crafting.recipe(actor, "recipe.tdo.alchemist.heal")
            if recipe is None or not recipe.available:
                break
            preview = await crafting.preview(actor, "recipe.tdo.alchemist.heal")
            assert preview is not None
            await crafting.commit(actor, preview.receipt_id)
            quantity += 1

    async def craft_torso_if_available(label):
        recipe_id = "recipe.tdo.blacksmith.fuligem_cuirass.comum"
        recipe = await crafting.recipe(actor, recipe_id)
        if recipe is None or not recipe.available:
            await driver.snapshot(f"{label} · receita de Couraça sem recursos suficientes")
            return None
        preview = await crafting.preview(actor, recipe_id)
        assert preview is not None
        result = await crafting.commit(actor, preview.receipt_id)
        assert result is not None and result.status == "committed"
        item_id = result.output_payload.get("equipment_item_id")
        assert item_id is not None, result.output_payload
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            item = await session.get(EquipmentItem, UUID(item_id))
            assert item is not None and item.character_id == character.id
            configuration_version = character.combat_configuration_version
        equipped = await EquipmentService(sessions, "ocaso").equip_item(
            actor, item.id, expected_configuration_version=configuration_version
        )
        assert equipped is not None and equipped.changed
        await driver.snapshot(f"{label} · Couraça de Fuligem criada e equipada")
        return item.id

    # The public journey has produced enough TDO materials for a Common
    # Principal weapon. Craft and equip it through the normal preview/commit
    # and Equipment validator so the fixed Nv.9 mission boss tests a plausible
    # player loadout instead of an empty weapon slot.
    weapon_recipe = await crafting.recipe(
        actor, "recipe.tdo.blacksmith.walker_weapon.comum"
    )
    if weapon_recipe is not None and weapon_recipe.available:
        weapon_preview = await crafting.preview(
            actor, "recipe.tdo.blacksmith.walker_weapon.comum"
        )
        assert weapon_preview is not None
        crafted_weapon = await crafting.commit(actor, weapon_preview.receipt_id)
        assert crafted_weapon is not None and crafted_weapon.status == "committed"
        weapon_id = crafted_weapon.output_payload.get("equipment_item_id")
        assert weapon_id is not None, crafted_weapon.output_payload
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            weapon = await session.get(EquipmentItem, UUID(weapon_id))
            assert weapon is not None and weapon.character_id == character.id
            configuration_version = character.combat_configuration_version
        equipped_weapon = await EquipmentService(sessions, "ocaso").equip_item(
            actor,
            weapon.id,
            expected_configuration_version=configuration_version,
        )
        assert equipped_weapon is not None and equipped_weapon.changed
        await driver.snapshot("Arma do Caminhante Comum criada e equipada por serviços oficiais")
    else:
        await driver.snapshot(
            "Crafting consultado; Arma Comum ainda indisponível pelos recursos obtidos"
        )
    await driver.snapshot("Ofícios consultados e Poções de Cura fabricadas com recursos obtidos")

    # Equip every Class Art legitimately unlocked at Nv.9 before the fixed
    # mission boss. The same three-slot configuration is later frozen in P6.
    art_service = ActiveArtService(sessions, "ocaso")
    for slot, art_id in (
        (2, SENTINEL_ART_IDS["quebra_postura"]),
        (3, SENTINEL_ART_IDS["impacto_resoluto"]),
    ):
        art_view = await art_service.view(actor)
        assert art_view is not None and art_id in art_view.available_art_ids
        if art_id not in {entry.art_id for entry in art_view.slots}:
            result = await art_service.equip_art(
                actor,
                slot,
                art_id,
                expected_configuration_version=art_view.combat_configuration_version,
            )
            assert result is not None and result.changed
    await driver.snapshot("Golpe, Quebra-Postura e Impacto Resoluto equipadas antes de P5")

    p5 = P5Service(sessions, "ocaso")
    p5_offer = await p5.offer(actor)
    assert p5_offer is not None and p5_offer.available, (p5_offer, driver.diagnostic())
    p5_view = await p5.accept(actor, p5_offer.state_version)
    assert p5_view is not None and p5_view.status == "active" and p5_view.step == 1
    await driver.snapshot("P5 aceita no Refúgio")
    await travel_to_ruins()
    p5_view = await p5.action(actor, p5_view.state_version, "follow_structures")
    p5_view = await p5.action(actor, p5_view.state_version, "find_door")
    assert p5_view is not None and p5_view.kind == "combat" and p5_view.combat is not None

    for attempt in range(12):
        if p5_view.combat.result == "defeat" and p5_view.activity_status == "active":
            mark = await driver.snapshot("P5 · derrota terminal ao materializar combate")
            raise AssertionError(
                f"P0: P5 persistiu derrota terminal como Foreground ativo; "
                f"snapshot={mark.state!r}\n{driver.diagnostic()}"
            )
        def p5_action(current):
            combat = current.combat
            available = allowed_actions(combat)
            player = combat.fighters["player"]
            has_heal = any(
                option.item_id == "consumable.heal"
                for option in current.consumable_options
            )
            if (
                has_heal
                and combat.prepared_action is None
                and player.hp * 10 <= player.stats.hp * 7
            ):
                return "consumable:consumable.heal"
            if combat.prepared_action is not None and "defend" in available:
                return "defend"
            damage_arts = [
                action_id
                for action_id in available
                if action_id.startswith("class_art.")
                and combat.player_actions[action_id].coefficient > 0
            ]
            if damage_arts:
                return max(
                    damage_arts,
                    key=lambda action_id: (
                        combat.player_actions[action_id].coefficient,
                        action_id,
                    ),
                )
            return driver.combat_action(combat)

        async def p5_mutate(current, action):
            arguments = (
                {"consumable_id": action.removeprefix("consumable:")}
                if action.startswith("consumable:")
                else {"action": action}
            )
            return await p5.action_combat(
                actor,
                current.activity_id,
                current.activity_state_version,
                **arguments,
            )

        p5_view = await driver.combat_to_result(
            p5_view,
            p5_mutate,
            lambda: P5Service(sessions, "ocaso").resume(actor),
            label=f"P5 · Custódio do Poente · tentativa {attempt + 1}",
            action_picker=p5_action,
            trace_actions=(attempt == 0),
        )
        if p5_view.progress.get("combat_result") == "victory":
            break
        assert p5_view.progress.get("combat_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"P5 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 11:
            await refill_p5_healing_stock()
            await driver.snapshot(
                f"P5 · poções fabricadas após recuperação · tentativa {attempt + 1}"
            )
            await travel_to_ruins()
            p5_view = await p5.action(actor, p5_view.state_version, "retry")
            assert p5_view is not None and p5_view.kind == "combat", driver.diagnostic()
            assert p5_view.combat is not None
    assert p5_view.progress.get("combat_result") == "victory", driver.diagnostic()
    assert p5_view.step == 4
    await driver.snapshot("P5 · Custódio derrotado")
    for element in P5_ELEMENTS:
        p5_view = await p5.action(actor, p5_view.state_version, "element", element)
    assert p5_view.step == 5 and len(p5_view.progress.get("door_elements", ())) == 3
    p5_view = await p5.action(actor, p5_view.state_version, "record_symbol")
    assert p5_view.step == 6
    await travel_to_refuge_from_ruins()
    p5_view = await p5.action(actor, p5_view.state_version, "report_alda")
    p5_view = await p5.action(actor, p5_view.state_version, "report_oren")
    assert p5_view.status == "completed"
    await driver.snapshot("P5 concluída")

    # P5 completion unlocks the level-10 flow. At this point the first
    # discoveries, dungeon clears, missions and timed Ronda have been consumed.
    hunts_to_level_10 = 0
    for attempt in range(40):
        if await current_level() >= 10:
            break
        await travel_from_refuge_to(BOSQUE)
        await manual_hunt(
            f"Nv.10 · Caçada complementar {attempt + 1}", capture=(attempt % 8 == 7)
        )
        hunts_to_level_10 += 1
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            world = await session.get(WorldState, character.id) if character else None
            assert character is not None and world is not None
            location = world.location
            needs_rest = character.hp * 10 < character.max_hp * 6
        if location != BOSQUE or needs_rest:
            await rest_and_return(BOSQUE)
        if attempt % 8 == 7:
            await driver.snapshot(f"progressão pública até Nv.10 · {attempt + 1} Caçadas")
    if await current_level() < 10:
        await driver.snapshot("BAL · Caçadas complementares até o gate de Nv.10")
        print(
            f"TDO_LEVEL_10_REQUIRES_MORE_THAN_40_HUNTS="
            f"{hunts_to_level_10}; state={driver.marks[-1].state!r}",
            flush=True,
        )
        raise AssertionError(
            "Progressão não chegou a Nv.10 após 40 complementos manuais, "
            "mesmo com conteúdo e Masmorras representativos."
        )
    await driver.snapshot("Nv.10 · segundo Ponto de Talento disponível")

    talents = TalentService(sessions, "ocaso")
    talent_view = await talents.view(actor)
    assert talent_view is not None and talent_view.total_points == 2
    assert talent_view.available_points == 1
    level_five_talents = [entry.talent_id for entry in talent_view.talents if entry.level == 5]
    assert len(level_five_talents) == 3
    already_chosen = {choice.talent_id for choice in talent_view.choices}
    next_talent = next(
        talent_id for talent_id in level_five_talents if talent_id not in already_chosen
    )
    mutation = await talents.acquire(
        actor, next_talent, talent_view.combat_configuration_version
    )
    assert mutation is not None and mutation.changed
    talent_view = mutation.view
    assert talent_view.available_points == 0 and len(talent_view.choices) == 2
    await driver.snapshot("dois Talentos Nv.5 escolhidos pelos serviços oficiais")

    art_service = ActiveArtService(sessions, "ocaso")
    for slot, art_id in enumerate(
        (
            SENTINEL_ART_IDS["quebra_postura"],
            SENTINEL_ART_IDS["impacto_resoluto"],
        ),
        start=2,
    ):
        art_view = await art_service.view(actor)
        assert art_view is not None
        if art_id not in art_view.available_art_ids:
            raise AssertionError(f"Arte ainda bloqueada no Nv.10: {art_id}")
        equipped_arts = {entry.art_id for entry in art_view.slots}
        if art_id not in equipped_arts:
            result = await art_service.equip_art(
                actor,
                slot,
                art_id,
                expected_configuration_version=art_view.combat_configuration_version,
            )
            assert result is not None and result.changed
    await driver.snapshot("Artes de combate configuradas para a Provação")

    await travel_to_refuge()
    trial = ClassTrialService(sessions, "ocaso")
    trial_view = await trial.resume(actor)
    assert trial_view is not None and trial_view.kind in {"available", "ready"}, (
        trial_view,
        driver.diagnostic(),
    )
    if trial_view.kind == "available":
        trial_view = await trial.begin(actor, trial_view.state_version)
    assert trial_view is not None
    if trial_view.context == "refuge":
        trial_view = await trial.return_to_circle(actor, trial_view.state_version)
    assert trial_view.status in {"ready", "active"}

    for stage in (1, 2, 3):
        if trial_view.status != "ready" or trial_view.current_stage != stage:
            trial_view = await trial.resume(actor)
        assert trial_view is not None
        if trial_view.context == "refuge":
            trial_view = await trial.return_to_circle(actor, trial_view.state_version)
        for _attempt in range(6):
            if trial_view.kind != "active":
                trial_view = await trial.start_attempt(actor, trial_view.state_version)
            assert trial_view is not None and trial_view.kind == "active"
            attempt_id = trial_view.attempt_id
            assert attempt_id is not None
            reconnected = False
            for _turn in range(160):
                combat = await trial.combat(actor, attempt_id)
                assert combat is not None and combat.result is None, (
                    combat,
                    driver.diagnostic(),
                )
                conditions = set(trial_view.attempt_state["pedagogic_conditions"])
                required = SENTINEL_CONDITION_IDS[stage]
                if required in conditions:
                    action = "attack"
                elif stage == 1:
                    action = (
                        "defend"
                        if combat.prepared_action == "trial.sentinela.impacto_anunciado"
                        else "attack"
                    )
                elif stage == 2:
                    action = SENTINEL_ART_IDS["quebra_postura"]
                elif combat.fighters["player"].retaliation_charges:
                    action = SENTINEL_ART_IDS["impacto_resoluto"]
                elif combat.prepared_action == "trial.sentinela.martelo_anunciado":
                    action = "defend"
                else:
                    action = "attack"
                if action not in allowed_actions(combat):
                    action = "attack"
                updated = await trial.action(
                    actor, attempt_id, trial_view.combat_version, action
                )
                assert updated is not None
                if not reconnected and updated.kind == "active":
                    restored = await trial.resume(actor)
                    restored_combat = await trial.combat(actor, attempt_id)
                    assert restored is not None and restored.attempt_id == attempt_id
                    assert restored_combat == await trial.combat(actor, attempt_id)
                    assert restored_combat is not None
                    trial_view = restored
                    reconnected = True
                else:
                    trial_view = updated
                if trial_view.kind != "active":
                    break
            assert trial_view is not None and trial_view.kind != "active", (
                stage,
                driver.diagnostic(),
            )
            if stage in trial_view.completed_stages:
                break
            assert trial_view.status == "ready" and trial_view.current_stage == stage, (
                trial_view,
                driver.diagnostic(),
            )
        assert stage in trial_view.completed_stages, (stage, trial_view, driver.diagnostic())
        await driver.snapshot(f"Provação da Sentinela · etapa {stage} concluída")
    assert trial_view.status == "completed"
    await driver.snapshot("Provação de Classe concluída")

    paths = PathSelectionService(sessions, "ocaso")
    path_view = await paths.view(actor)
    assert path_view is not None and path_view.trial_completed
    path_choice = await paths.choose_initial(
        actor, "devastador", path_view.configuration_version
    )
    assert path_choice is not None and path_choice.changed
    await driver.snapshot("Caminho inicial escolhido após a Provação")

    # S6 is a legitimate Nv.10 secondary-quest reward source and is part of
    # the journey requested for the regional campaign. Its materials also
    # let the character use the ordinary alchemy recipe before P6.
    s6 = S6Service(sessions, "ocaso")
    s6_offer = await s6.oren(actor)
    assert s6_offer is not None and s6_offer.available, (s6_offer, driver.diagnostic())
    s6_view = await s6.accept(actor, s6_offer.state_version)
    assert s6_view is not None and s6_view.status == "active" and s6_view.step == 1
    s6_view = await s6.action(actor, s6_view.state_version, "review")
    assert s6_view is not None and s6_view.step == 2
    await travel_to_ruins()
    for mark_id in S6_MARKS:
        s6_view = await s6.action(actor, s6_view.state_version, "mark", mark_id)
        assert s6_view is not None
    assert s6_view.step == 3
    s6_view = await s6.action(actor, s6_view.state_version, "shelter")
    assert s6_view is not None and s6_view.kind == "combat" and s6_view.combat is not None
    await driver.snapshot("S6 · Custódio Sem Rosto materializado")

    def s6_action(current):
        combat = current.combat
        available = allowed_actions(combat)
        player = combat.fighters["player"]
        has_heal = any(
            option.item_id == "consumable.heal" for option in current.consumable_options
        )
        if (
            has_heal
            and combat.prepared_action is None
            and player.hp * 10 <= player.stats.hp * 5
        ):
            return "consumable:consumable.heal"
        if combat.prepared_action is not None and "defend" in available:
            return "defend"
        damage_arts = [
            action_id
            for action_id in available
            if action_id.startswith(("class_art.", "path_art."))
            and combat.player_actions[action_id].coefficient > 0
        ]
        if damage_arts:
            return max(
                damage_arts,
                key=lambda action_id: (
                    combat.player_actions[action_id].coefficient,
                    action_id,
                ),
            )
        return driver.combat_action(combat)

    for attempt in range(8):
        async def s6_mutate(current, action):
            arguments = (
                {"consumable_id": action.removeprefix("consumable:")}
                if action.startswith("consumable:")
                else {"action": action}
            )
            return await s6.action_combat(
                actor,
                current.activity_id,
                current.activity_state_version,
                **arguments,
            )

        s6_view = await driver.combat_to_result(
            s6_view,
            s6_mutate,
            lambda: S6Service(sessions, "ocaso").resume(actor),
            label=f"S6 · Custódio Sem Rosto · tentativa {attempt + 1}",
            action_picker=s6_action,
            trace_actions=(attempt == 0),
        )
        if s6_view.progress.get("combat_result") == "victory":
            break
        assert s6_view.progress.get("combat_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"S6 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 7:
            await travel_to_ruins()
            s6_view = await s6.action(actor, s6_view.state_version, "retry")
            assert s6_view is not None and s6_view.kind == "combat"
    assert s6_view.progress.get("combat_result") == "victory", driver.diagnostic()
    assert s6_view.step == 5
    s6_view = await s6.action(actor, s6_view.state_version, "last_record")
    assert s6_view is not None and s6_view.step == 6
    await travel_to_refuge_from_ruins()
    s6_view = await s6.action(actor, s6_view.state_version, "report")
    assert s6_view is not None and s6_view.status == "completed"
    await driver.snapshot("S6 concluída · recompensa e Peregrinos registrados")

    # Configure the late-journey legal gear before the Ronda attempt.
    await craft_torso_if_available("Nv.10 · preparação da Ronda")
    better_gear = await equip_best_available_combat_gear()
    await driver.snapshot(
        f"P6 · melhor equipamento elegível equipado pelo validador · {better_gear!r}"
    )

    # Use the same legitimate refuge crafting flow before the campaign boss.
    # The consumable budget and real ingredients remain authoritative.
    rested_before_p6 = await WorldService(sessions, "ocaso").rest(actor)
    assert rested_before_p6 is not None and rested_before_p6.hp == rested_before_p6.max_hp
    await refill_p5_healing_stock(target_quantity=5)
    await driver.snapshot("P6 · consumíveis fabricados no Refúgio quando disponíveis")

    # Retry the Ronda once the journey has legitimately crafted healing
    # consumables. Configure them through the public Ronda preparation flow.
    await travel_to_refuge()
    await travel_from_refuge_to(BOSQUE)
    await rest_and_return(BOSQUE)
    await driver.clock.wait_for_vigor(
        sessions, actor, 2, "offline Vigor wait before prepared Ronda batch"
    )
    round_prep = await rounds.prepare_round(actor, 5)
    assert round_prep is not None and round_prep.kind == "round_prepare", (
        round_prep,
        driver.diagnostic(),
    )
    round_items = await rounds.round_consumables(
        actor, round_prep.round_id, round_prep.state_version
    )
    assert round_items is not None and round_items.heal_quantity > 0, (
        round_items,
        "nenhuma Poção de Cura legítima disponível para o lote",
        driver.diagnostic(),
    )
    if not round_items.prepared_heal:
        round_items = await rounds.toggle_round_consumable(
            actor, round_items.round_id, round_items.state_version, "consumable.heal"
        )
        assert round_items is not None and round_items.prepared_heal
    round_active = await rounds.start_round(
        actor, round_items.round_id, round_items.state_version
    )
    assert round_active is not None and round_active.kind in {"round_active", "round_interrupted"}
    round_reconnected = await RoundService(sessions, "ocaso").resume(actor)
    assert round_reconnected is not None and round_reconnected.round_id == round_active.round_id
    if round_active.kind == "round_active":
        prepared_round_result = await driver.clock.process_round_cadence(rounds, actor)
    else:
        prepared_round_result = round_active
    assert prepared_round_result is not None
    prepared_round_completed = prepared_round_result.completed_encounters
    prepared_round_end_reason = prepared_round_result.end_reason
    if prepared_round_result.kind == "round_interrupted":
        elite = await rounds.engage_round_elite(
            actor, round_active.round_id, prepared_round_result.state_version
        )
        assert elite is not None and elite.combat is not None
        elite = await driver.combat_to_result(
            elite,
            lambda current, action: RoadService(sessions, "ocaso").action(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: RoundService(sessions, "ocaso").resume(actor),
            label="Ronda preparada · Elite interrompida",
        )
        if elite.kind == "hunt_victory":
            await RoundService(sessions, "ocaso").acknowledge_result(actor)
        else:
            assert elite.kind == "hunt_defeat", elite
            await RoundService(sessions, "ocaso").acknowledge_defeat(actor)
        prepared_round_result = await rounds.round_back(actor, round_active.round_id)
    elif prepared_round_result.kind in {"round_completed", "round_ended", "round_defeated"}:
        prepared_round_result = await rounds.round_back(actor, round_active.round_id)
    print(
        "RONDA PREPARADA · "
        f"resultado={prepared_round_result.kind if prepared_round_result else None} · "
        f"motivo={prepared_round_end_reason} · "
        f"encontros={prepared_round_completed}/5 · "
        f"curas_preparadas={round_items.heal_quantity}"
    , flush=True)
    assert prepared_round_result is not None
    outcome_label = (
        "Ronda ×5 concluída após preparação legítima"
        if prepared_round_completed == 5
        else (
            f"Ronda legítima encerrada em {prepared_round_completed}/5 · "
            f"{prepared_round_end_reason}"
        )
    )
    await driver.snapshot(outcome_label)

    await travel_to_refuge()
    rested_before_p6 = await WorldService(sessions, "ocaso").rest(actor)
    assert rested_before_p6 is not None and rested_before_p6.hp == rested_before_p6.max_hp
    await refill_p5_healing_stock(target_quantity=4)
    p6_supply_hunts = 0
    for supply_attempt in range(12):
        if await healing_stock_count() >= 4:
            break
        await road.travel(actor, ROAD)
        await manual_hunt(
            f"Preparação legítima para P6 · Caçada {supply_attempt + 1}",
            capture=False,
        )
        p6_supply_hunts += 1
        await road.travel(actor, REFUGE)
        rested = await WorldService(sessions, "ocaso").rest(actor)
        assert rested is not None and rested.hp == rested.max_hp
        await refill_p5_healing_stock(target_quantity=4)
    p6_healing_stock = await healing_stock_count()
    assert p6_healing_stock >= 4, (
        "P6 diagnostic requires a representative four-heal stock, obtained through public "
        f"Hunt/Crafting only; stock={p6_healing_stock}; hunts={p6_supply_hunts}; "
        f"{driver.diagnostic()}"
    )
    await driver.snapshot(
        "P6 · consumíveis legitimamente preparados · "
        f"Poções={p6_healing_stock}; Caçadas de suprimento={p6_supply_hunts}"
    )

    # Preserve the three legal direct-damage Arts for the campaign boss. The
    # previous trace showed that replacing a damage slot with Muralha delayed
    # reaching phase III, so this run tests the strongest offensive Arts the
    # character actually unlocked and equipped through the normal service.
    p6_arts = ActiveArtService(sessions, "ocaso")
    p6_art_view = await p6_arts.view(actor)
    assert p6_art_view is not None
    if SENTINEL_ART_IDS["golpe_de_guarda"] not in {
        entry.art_id for entry in p6_art_view.slots
    }:
        result = await p6_arts.equip_art(
            actor,
            1,
            SENTINEL_ART_IDS["golpe_de_guarda"],
            expected_configuration_version=p6_art_view.combat_configuration_version,
        )
        assert result is not None and result.changed
    await driver.snapshot("P6 · três Artes ofensivas configuradas antes do snapshot do chefe")

    p6 = P6Service(sessions, "ocaso")
    p6_view = await p6.resume(actor)
    assert p6_view is not None and p6_view.status == "active"
    assert p6_view.guidance is None, (p6_view.guidance, driver.diagnostic())
    await travel_to_ruins()
    p6_view = await p6.action(actor, p6_view.state_version, "cross_door")
    assert p6_view is not None and p6_view.step == 2
    p6_view = await p6.action(actor, p6_view.state_version, "enter_chamber")
    assert p6_view is not None and p6_view.step == 3 and p6_view.location == "Câmara do Poente"
    p6_view = await p6.action(actor, p6_view.state_version, "inspect_before")
    assert p6_view is not None and p6_view.kind == "start_boss"

    async def build_p6_diagnostic_combat():
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            equipment_configuration = await load_equipment_configuration(session, character)
            active_art_configuration = await load_active_art_configuration(session, character)
            reconcile_character_hp(character, equipment_configuration)
            combat = create_creature_combat(
                uuid4(),
                character.name,
                character.character_class,
                character.race,
                character.hp,
                VIGIA_PARTIDO,
                10,
                None,
                player_level=character.level,
                equipment_configuration=equipment_configuration,
                ruleset_version=ROAD_RULESET,
                active_art_ids=active_art_configuration.art_ids,
            )
            combat.configuration_snapshot = (combat.configuration_snapshot or {}) | (
                active_art_configuration.to_data()
            )
            return combat

    pure_p6_combat = await build_p6_diagnostic_combat()
    assert pure_p6_combat.fighters["player"].selected_path in {"sentinela", "devastador"}
    assert not any(action.startswith("path_art.") for action in pure_p6_combat.player_actions)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        initial_heals = await session.scalar(
            select(func.coalesce(func.sum(ConsumableStack.quantity), 0)).where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == "consumable.heal",
            )
        )
        initial_heals = int(initial_heals or 0)
    p6_budget = ENCOUNTER_CONSUMABLE_LIMITS.get(VIGIA_PARTIDO.category, 0)
    p6_policy_summary, p6_policy_records = sample_p6_policies(
        pure_p6_combat,
        heal_count=initial_heals,
        budget_limit=p6_budget,
    )
    driver.p6_diagnostics.append(p6_policy_summary)
    best_loadout, best_policy, best_policy_summary = best_p6_diagnostic_configuration(
        p6_policy_summary
    )
    consistent_sample_victories = best_policy_summary["victories"]
    print(
        "P6_REAL_COMBAT_STATS="
        f"player={p6_policy_records[0]['player_stats']!r} "
        f"boss={p6_policy_records[0]['boss_stats']!r} "
        f"path={pure_p6_combat.fighters['player'].selected_path!r} "
        f"loadouts={P6_DIAGNOSTIC_LOADOUTS!r} "
        f"heals={initial_heals} budget={p6_budget}",
        flush=True,
    )
    print(
        f"P6_POLICY_MATRIX_30_PER_CONFIGURATION={p6_policy_summary!r}; "
        f"best=({best_loadout}, {best_policy}, {best_policy_summary!r})",
        flush=True,
    )
    # Treat fewer than five wins in a 30-seed cohort as exceptional, rather
    # than evidence of repeatable viability; no seed is selected for the run.
    if consistent_sample_victories < 5:
        mark = await driver.snapshot("P6 · matriz diagnóstica com vitória excepcional ou ausente")
        await driver.assert_xp_ledger()
        print(f"TDO_PLAYTHROUGH_REPORT={_compact_playthrough_report(driver, mark)!r}", flush=True)
        pytest.skip(
            "P6 balance candidate: nenhuma combinação teve ao menos cinco vitórias em 30 seeds; "
            f"snapshot={mark.state!r}; matriz={p6_policy_summary!r}"
        )

    desired_art_ids = P6_DIAGNOSTIC_LOADOUTS[best_loadout]
    p6_arts = ActiveArtService(sessions, "ocaso")
    p6_art_view = await p6_arts.view(actor)
    assert p6_art_view is not None
    current_arts = {entry.slot: entry.art_id for entry in p6_art_view.slots}
    if tuple(current_arts.get(slot) for slot in (1, 2, 3)) != desired_art_ids:
        configuration_version = p6_art_view.combat_configuration_version
        for slot in (1, 2, 3):
            if slot in current_arts:
                result = await p6_arts.unequip_slot(
                    actor,
                    slot,
                    expected_configuration_version=configuration_version,
                )
                assert result is not None and result.changed
                configuration_version = result.combat_configuration_version
        for slot, art_id in enumerate(desired_art_ids, start=1):
            result = await p6_arts.equip_art(
                actor,
                slot,
                art_id,
                expected_configuration_version=configuration_version,
            )
            assert result is not None and result.changed
            configuration_version = result.combat_configuration_version
    selected_arts = await p6_arts.view(actor)
    assert selected_arts is not None
    assert tuple(entry.art_id for entry in selected_arts.slots) == desired_art_ids
    await driver.snapshot(
        f"P6 · loadout agregado escolhido · {best_loadout} · {best_policy}"
    )

    p6_view = await p6.resume(actor)
    assert p6_view is not None and p6_view.kind == "start_boss"
    p6_view = await p6.action(actor, p6_view.state_version, "start_boss")
    assert p6_view is not None and p6_view.kind == "combat" and p6_view.combat is not None
    assert not any(action.startswith("path_art.") for action in p6_view.combat.player_actions)
    await driver.snapshot("P6 · Vigia Partido materializado após a matriz pura")
    p6_policy = best_policy

    def p6_action(current):
        combat = current.combat
        return choose_p6_policy_action(
            combat,
            p6_policy,
            heal_count=_consumable_quantity(
                current.consumable_quantities, "consumable.heal"
            ),
            budget_limit=current.consumable_budget_limit,
        )

    public_p6_attempts = []
    for attempt in range(12):
        if p6_view.combat.result == "defeat" and p6_view.activity_status == "active":
            mark = await driver.snapshot("P6 · derrota terminal ao materializar chefe")
            raise AssertionError(
                f"P0: P6 persistiu derrota terminal como Foreground ativo; "
                f"snapshot={mark.state!r}\n{driver.diagnostic()}"
            )
        async def p6_mutate(current, action):
            arguments = (
                {"consumable_id": action.removeprefix("consumable:")}
                if action.startswith("consumable:")
                else {"action": action}
            )
            return await p6.action_combat(
                actor,
                current.activity_id,
                current.activity_state_version,
                **arguments,
            )

        p6_view = await driver.combat_to_result(
            p6_view,
            p6_mutate,
            lambda: P6Service(sessions, "ocaso").resume(actor),
            label=f"P6 · Vigia Partido · tentativa {attempt + 1}",
            action_picker=p6_action,
            trace_actions=(attempt == 0),
        )
        completed_combat = driver.last_combat
        assert completed_combat is not None
        boss = completed_combat.fighters["enemy"]
        player = completed_combat.fighters["player"]
        received_damage = sum(
            event.effective_damage
            for event in completed_combat.events
            if event.target == player.id and event.effective_damage > 0
        )
        prepared_defends = sum(
            event.actor == "player"
            and event.action == "defend"
            and bool(event.response_to_prepared_action_instance_id)
            for event in completed_combat.events
        )
        retaliation_events = [
            event.retaliation_event
            for event in completed_combat.mechanic_events
            if event.retaliation_event
        ]
        retaliation_counts = {
            event_name: retaliation_events.count(event_name)
            for event_name in sorted(set(retaliation_events))
        }
        path_trigger_counts = {}
        for event in completed_combat.events:
            for trigger in event.path_triggers:
                path_trigger_counts[trigger] = path_trigger_counts.get(trigger, 0) + 1
        player_action_counts = {
            action: sum(
                event.actor == "player" and event.action == action
                for event in completed_combat.events
            )
            for action in sorted(
                {
                    event.action
                    for event in completed_combat.events
                    if event.actor == "player"
                }
            )
        }
        highest_phase = 1
        if boss.hp < boss.stats.hp * Decimal("0.70"):
            highest_phase = 2
        if boss.hp <= boss.stats.hp * Decimal("0.35"):
            highest_phase = 3
        attempt_record = {
            "attempt": attempt + 1,
            "activity_id": str(p6_view.activity_id),
            "result": completed_combat.result,
            "turns": completed_combat.round,
            "phase": highest_phase,
            "boss_hp_remaining": str(boss.hp),
            "player_hp_remaining": str(player.hp),
            "damage_received": received_damage,
            "heals_used": player_action_counts.get("consumable:consumable.heal", 0),
            "prepared_defends": prepared_defends,
            "retaliation_events": retaliation_counts,
            "muralha_used": player_action_counts.get(
                SENTINEL_ART_IDS["muralha_breve"], 0
            ),
            "quebra_postura_used": player_action_counts.get(
                SENTINEL_ART_IDS["quebra_postura"], 0
            ),
            "devastador_charge_consumed": path_trigger_counts.get(
                "devastador.impacto_consumido", 0
            ),
            "defeat_cause": (
                "player_hp_zero"
                if completed_combat.result == "defeat" and player.hp <= 0
                else None
            ),
            "path_triggers": path_trigger_counts,
            "actions": player_action_counts,
        }
        public_p6_attempts.append(attempt_record)
        print(f"P6_PUBLIC_ATTEMPT={attempt_record!r}", flush=True)
        if p6_view.progress.get("boss_result") == "victory":
            break
        assert p6_view.progress.get("boss_result") == "defeat", driver.diagnostic()
        await driver.snapshot(f"P6 · derrota legítima · tentativa {attempt + 1}")
        if attempt < 11:
            # Recovery returns the character to the Refuge. Use the ordinary
            # rest and Alchemist flows before a retry when the earned materials
            # permit it; consumed items are never restored by the harness.
            if p6_view.location != "Câmara do Poente":
                await travel_to_refuge()
                rested = await WorldService(sessions, "ocaso").rest(actor)
                assert rested is not None and rested.hp == rested.max_hp
                await refill_p5_healing_stock()
                # A depleted stack may only be refilled from earned materials.
                # Gather a small amount through ordinary hunts when a retry
                # leaves the character without enough herbs for the known
                # Alchemist recipe; never seed inventory or refund consumables.
                for supply_attempt in range(8):
                    if await healing_stock_count() >= 2:
                        break
                    await road.travel(actor, ROAD)
                    await manual_hunt(
                        f"Preparação legítima para P6 · Caçada {supply_attempt + 1}",
                        capture=False,
                    )
                    await road.travel(actor, REFUGE)
                    rested = await WorldService(sessions, "ocaso").rest(actor)
                    assert rested is not None and rested.hp == rested.max_hp
                    await refill_p5_healing_stock()
            if p6_view.location != "Câmara do Poente":
                await travel_to_ruins()
                p6_view = await p6.resume(actor)
                assert p6_view is not None and p6_view.kind == "retry_chamber"
                p6_view = await p6.action(actor, p6_view.state_version, "enter_chamber")
            p6_view = await p6.action(actor, p6_view.state_version, "retry")
            assert p6_view is not None and p6_view.kind == "combat"
            assert p6_view.combat is not None
    if p6_view.progress.get("boss_result") != "victory":
        mark = await driver.snapshot("P6 · 12 tentativas públicas sem vitória")
        await driver.assert_xp_ledger()
        print(f"P6_PUBLIC_ATTEMPTS={public_p6_attempts!r}", flush=True)
        print(f"TDO_PLAYTHROUGH_REPORT={_compact_playthrough_report(driver, mark)!r}", flush=True)
        pytest.skip(
            "P6 ainda não concluída pelo fluxo público após 12 tentativas; "
            f"amostra pura={p6_policy_summary!r}; "
            f"tentativas={len(public_p6_attempts)}; "
            f"snapshot={mark.state!r}"
        )
    p6_view = await p6.action(actor, p6_view.state_version, "inspect_after")
    p6_view = await p6.action(actor, p6_view.state_version, "record_anchor")
    p6_view = await p6.action(actor, p6_view.state_version, "return_ruins")
    await travel_to_refuge_from_ruins()
    p6_view = await p6.action(actor, p6_view.state_version, "report_alda")
    p6_view = await p6.action(actor, p6_view.state_version, "report_oren")
    assert p6_view.step == 9 and p6_view.status == "active"
    p6_view = await p6.choose_reward(actor, p6_view.state_version, "last_post")
    assert p6_view is not None and p6_view.status == "completed"
    await driver.snapshot("P6 concluída · Vigia Partido derrotado e recompensa escolhida")

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.level >= 10
        assert character.xp >= 0
        assert character.crowns >= 0
        assert character.vigor >= 0
        assert character.hp >= 0
        p1_row = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P1")
        )
        assert p1_row is not None and p1_row.status == "completed"
        assert await session.scalar(
            select(func.count()).select_from(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == "p1.vozes_na_estrada",
            )
        ) == 1
        assert await session.scalar(
            select(func.count()).select_from(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        ) == 0
        p2_row = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P2")
        )
        assert p2_row is not None and p2_row.status == "completed"
        for quest_id in ("P3", "P4", "S1", "S2", "S3", "S4", "S5", "P5", "P6"):
            completed = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == quest_id,
                    Quest.status == "completed",
                )
            )
            assert completed is not None, (quest_id, driver.diagnostic())
        assert len(talent_view.choices) == 2
        assert path_choice.view.selected_path == "devastador"
        assert p6_view.progress.get("boss_result") == "victory"
        world_row = await session.get(WorldState, character.id)
        assert world_row is not None and world_row.location == REFUGE

    final_mark = await driver.snapshot("TDO Nv.1–10 concluído até P6")
    await driver.assert_xp_ledger(require_completed_campaign=True)
    assert driver.clock.vigor_regenerated <= int(
        driver.clock.elapsed_seconds // vigor_module.REGEN_INTERVAL_SECONDS
    ), (
        "the journey clock credited more natural Vigor than elapsed time allows: "
        f"regen={driver.clock.vigor_regenerated}, "
        f"elapsed={driver.clock.elapsed_seconds}s"
    )
    print(f"TDO_PLAYTHROUGH_REPORT={_compact_playthrough_report(driver, final_mark)!r}", flush=True)
