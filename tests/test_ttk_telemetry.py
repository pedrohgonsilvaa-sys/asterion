"""Telemetria de TTK do Beta (docs/TTK_DESENHO.md): uma linha por combate, só observação."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select

import asterion.application.ttk_telemetry as ttk
from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.prologue import PrologueService
from asterion.application.road import ROAD, RoadService
from asterion.domain.combat import allowed_actions
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import (
    Character,
    CombatRecord,
    CombatTtkRecord,
    Encounter,
    GameActivity,
    HuntContext,
    RewardEvent,
)
from tests.test_prologue_persistence import character as prologue_character
from tests.test_prologue_persistence import win as prologue_win
from tests.test_road_integration import _seed_road
from tests.test_round_integration import _force_safe_common, _seed_round


@pytest.fixture(autouse=True)
def _telemetry_state():
    """Each test starts with the flag off; tests that need it switch it on."""
    before = dict(ttk._state)
    ttk.configure(enabled=False)
    yield
    ttk._state.update(before)


async def _rows(database):
    async with database[1]() as session:
        return list((await session.scalars(select(CombatTtkRecord))).all())


async def _play_to_end(service, actor, view, limit=100):
    for _ in range(limit):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    return view


# --- pure -----------------------------------------------------------------------------


def test_flag_is_off_by_default_and_configure_sets_build_version():
    from asterion.config import Settings

    assert Settings.model_fields["ttk_telemetry"].default is False
    assert Settings.model_fields["build_version"].default == "unknown"
    ttk.configure(enabled=True, build_version="abc1234")
    assert ttk.is_enabled() and ttk._state["build_version"] == "abc1234"
    ttk.configure(enabled=False)
    assert not ttk.is_enabled() and ttk._state["build_version"] == "unknown"


@pytest.mark.asyncio
async def test_pvpve_prey_and_missing_context_are_skipped_without_touching_the_session():
    prey = SimpleNamespace(pvpve_collision_id="x")
    # `self`, session and combat are never used on these early returns.
    for context in (None, prey):
        await RoadService._record_ttk(
            None, None, None, context, None, source=ttk.SOURCE_HUNT_MANUAL
        )


# --- Caçada Manual --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_combat_version_baseline_and_actions_are_pinned(database):
    actor, service = await _seed_road(database, 773001)
    await service.travel(actor, ROAD)
    view = await service.start_hunt(actor)
    assert view.kind == "combat"
    assert view.combat.version == ttk.START_VERSION == 0
    assert ttk.player_actions(view.combat) == 0
    view = await service.action(actor, view.activity_id, view.combat.version, "attack")
    assert view.combat.version == 1 and ttk.player_actions(view.combat) == 1
    view = await service.action(actor, view.activity_id, view.combat.version, "defend")
    assert ttk.player_actions(view.combat) == 2


@pytest.mark.asyncio
async def test_manual_victory_records_exactly_one_row(database):
    ttk.configure(enabled=True, build_version="build-test")
    actor, service = await _seed_road(database, 773002)
    await service.travel(actor, ROAD)
    view = await service.start_hunt(actor)
    view = await _play_to_end(service, actor, view)
    assert view.kind == "hunt_victory"
    rows = await _rows(database)
    assert len(rows) == 1
    row = rows[0]
    assert (row.source, row.result) == ("hunt_manual", "victory")
    async with database[1]() as session:
        record = await session.get(CombatRecord, row.combat_id)
        activity = await session.get(GameActivity, view.activity_id)
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == view.activity_id)
        )
        character = await session.get(Character, row.character_id)
    assert record is not None and row.combat_id == record.id
    assert row.player_actions == activity.state_version > 0
    assert row.rounds >= 1 and row.consumable_uses >= 0
    assert (row.creature_id, row.creature_category, row.enemy_level) == (
        context.creature_id,
        context.category,
        context.enemy_level,
    )
    assert row.region_id == "tdo" and row.party_size == 1
    assert row.character_class == character.character_class == "sentinela"
    assert row.player_level >= 1
    assert row.started_at is not None and row.duration_seconds is not None
    assert row.duration_seconds >= 0
    assert row.ruleset_version == activity.ruleset_version
    assert row.build_version == "build-test"
    # A late callback and a re-read of the receipt never add a second row.
    await service.action(actor, view.activity_id, row.player_actions, "attack")
    await service.resume(actor)
    assert len(await _rows(database)) == 1


@pytest.mark.asyncio
async def test_record_is_idempotent_per_combat_id(database):
    ttk.configure(enabled=True)
    actor, service = await _seed_road(database, 773003)
    await service.travel(actor, ROAD)
    view = await _play_to_end(service, actor, await service.start_hunt(actor))
    assert view.kind == "hunt_victory"
    (row,) = await _rows(database)
    async with database[1].begin() as session:
        character = await session.get(Character, row.character_id)
        activity = await session.get(GameActivity, view.activity_id)
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == view.activity_id)
        )
        from asterion.infrastructure.db.combat_codec import decode
        from asterion.infrastructure.db.combat_repository import CombatRepository

        _enc, record = await CombatRepository(session).combat(activity)
        combat = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        again = await ttk.record_hunt(
            session,
            character,
            context,
            combat,
            source=ttk.SOURCE_HUNT_MANUAL,
            region_id="tdo",
        )
    assert again is False
    assert len(await _rows(database)) == 1


@pytest.mark.asyncio
async def test_opening_defeat_is_recorded_once_with_zero_actions(database, monkeypatch):
    import asterion.application.road as road_module
    from asterion.domain.road import creature_for

    ttk.configure(enabled=True)
    actor, service = await _seed_road(database, 773004)
    async with database[1].begin() as session:
        c = await session.scalar(
            select(Character).where(Character.telegram_id == actor).with_for_update()
        )
        c.hp = c.hp * 0 + 4
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module, "select_creature", lambda *args, **kwargs: creature_for("dog_cinereo")
    )
    monkeypatch.setattr(road_module, "select_variant", lambda *args, **kwargs: None)
    view = await service.start_hunt(actor)
    assert view.kind == "hunt_defeat"
    rows = await _rows(database)
    assert len(rows) == 1
    assert (rows[0].result, rows[0].player_actions, rows[0].source) == (
        "defeat",
        0,
        "hunt_manual",
    )
    await service.resume(actor)
    await service.acknowledge_defeat(actor)
    assert len(await _rows(database)) == 1


@pytest.mark.asyncio
async def test_expired_hunt_is_recorded_once_as_abandoned(database):
    ttk.configure(enabled=True)
    actor, service = await _seed_road(database, 773005)
    await service.travel(actor, ROAD)
    combat = await service.start_hunt(actor)
    combat = await service.action(actor, combat.activity_id, combat.combat.version, "attack")
    assert combat.kind == "combat"
    async with database[1]() as session:
        activity = await session.get(GameActivity, combat.activity_id)
        activity.last_valid_action_at = datetime.now(UTC) - timedelta(minutes=31)
        await session.commit()
    assert (await service.resume(actor)).kind == "hunt_defeat"
    stale = await service.action(actor, combat.activity_id, combat.combat.version, "attack")
    assert stale.kind == "hunt_defeat"
    await service.resume(actor)
    rows = await _rows(database)
    assert len(rows) == 1
    assert (rows[0].result, rows[0].player_actions) == ("abandoned", 1)
    assert rows[0].duration_seconds is None and rows[0].started_at is not None


@pytest.mark.asyncio
async def test_exploration_combat_is_not_recorded(database, monkeypatch):
    import asterion.application.road as road_module

    ttk.configure(enabled=True)
    actor, service = await _seed_road(database, 773006)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("combat", "explore.tdo.estrada.combat.dog_cinereo", "Cão"),
    )
    view = await service.explore(actor)
    assert view.kind == "combat"
    await _play_to_end(service, actor, view)
    assert await _rows(database) == []


# --- Ronda ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_round_encounter_is_recorded_once_as_round_auto(database, monkeypatch):
    import asterion.application.round as round_module
    from asterion.infrastructure.db.models import HuntRound

    ttk.configure(enabled=True)
    actor, service = await _seed_round(database, 773007)
    _force_safe_common(monkeypatch, round_module)
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    assert await service.advance_due_rounds() == 1
    rows = await _rows(database)
    assert len(rows) == 1
    row = rows[0]
    assert (row.source, row.result) == ("round_auto", "victory")
    assert row.player_actions > 0 and row.region_id == "tdo"
    assert row.started_at is None and row.duration_seconds is None
    # Nothing re-records on a resume or an idle scheduler tick.
    await service.resume(actor)
    await service.advance_due_rounds()
    assert len(await _rows(database)) == 1


# --- Sem efeito no jogo ---------------------------------------------------------------


async def _fingerprint(database, actor, view):
    """Outcome of one scripted hunt with ids normalised, so two runs can be compared."""
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        record = await session.scalar(
            select(CombatRecord)
            .join(Encounter, Encounter.id == CombatRecord.encounter_id)
            .where(Encounter.game_activity_id == view.activity_id)
        )
        events = (
            await session.scalars(
                select(RewardEvent)
                .where(RewardEvent.character_id == character.id)
                .order_by(RewardEvent.source_id, RewardEvent.id)
            )
        ).all()
        snapshot = json.dumps(record.snapshot, sort_keys=True, default=str).replace(
            str(character.id), "CHAR"
        )
        return {
            "kind": view.kind,
            # Receipt lines come back in database order (random row ids): compare as a set.
            "reward_lines": sorted(view.reward_lines),
            "xp": character.xp,
            "crowns": character.crowns,
            "hp": str(character.hp),
            "vigor": character.vigor,
            "level": character.level,
            "snapshot": snapshot,
            "reward_events": sorted(
                (e.kind if hasattr(e, "kind") else "", str(getattr(e, "quantity", "")))
                for e in events
            ),
        }


@pytest.mark.asyncio
async def test_hunt_is_identical_with_telemetry_on_and_off(database, monkeypatch):
    import asterion.application.road as road_module

    fixed_combat_id = UUID("00000000-0000-4000-8000-000000077701")
    original_materialize = RoadService._materialize_manual_hunt
    original_create = road_module.create_road_combat

    async def fixed_seed(self, *args, **kwargs):
        kwargs["seed"] = "ttk-equivalence-seed"
        return await original_materialize(self, *args, **kwargs)

    def fixed_combat(_combat_id, *args, **kwargs):
        return original_create(fixed_combat_id, *args, **kwargs)

    monkeypatch.setattr(RoadService, "_materialize_manual_hunt", fixed_seed)
    monkeypatch.setattr(road_module, "create_road_combat", fixed_combat)

    results = {}
    # Same combat id and seed in both runs (the RNG is keyed on them); the first run's whole
    # character graph is deleted before the second. 26 apart gives both heroes the same name.
    for enabled, actor in ((False, 773011), (True, 773037)):
        ttk.configure(enabled=enabled)
        actor, service = await _seed_road(database, actor)
        await service.travel(actor, ROAD)
        view = await _play_to_end(service, actor, await service.start_hunt(actor))
        assert view.kind in {"hunt_victory", "hunt_defeat"}
        results[enabled] = await _fingerprint(database, actor, view)
        rows = await _rows(database)
        assert len(rows) == (1 if enabled else 0)
        if not enabled:
            async with database[1].begin() as session:
                character = await session.scalar(
                    select(Character).where(Character.telegram_id == actor)
                )
                await delete_character_owned_data(session, character.id)
                await session.execute(delete(Character).where(Character.id == character.id))
    assert results[False]["snapshot"] == results[True]["snapshot"]
    assert results[False] == results[True]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["insert_raises", "database_rejects"])
async def test_telemetry_failure_does_not_stop_settlement(database, monkeypatch, failure):
    ttk.configure(enabled=True)
    if failure == "insert_raises":

        def boom(*_args, **_kwargs):
            raise RuntimeError("telemetry down")

        monkeypatch.setattr(ttk, "insert", boom)
    else:  # the database refuses the row inside the savepoint
        ttk._state["build_version"] = "x" * 200
    actor, service = await _seed_road(database, 773013)
    await service.travel(actor, ROAD)
    view = await _play_to_end(service, actor, await service.start_hunt(actor))
    assert view.kind == "hunt_victory"
    assert (await service.resume(actor)).kind == "hunt_victory"
    async with database[1]() as session:
        assert await session.scalar(select(func.count(RewardEvent.id))) > 0
        activity = await session.get(GameActivity, view.activity_id)
        assert activity.status == "completed"
    assert await _rows(database) == []


@pytest.mark.asyncio
async def test_prologue_combat_never_records(database):
    ttk.configure(enabled=True)
    service = PrologueService(database[1], "ocaso", PROFILE)
    await prologue_character(database)
    view = await service.enter(1)
    await prologue_win(service, view)
    assert await _rows(database) == []


@pytest.mark.asyncio
async def test_deleting_the_character_keeps_the_row_without_the_link(database):
    ttk.configure(enabled=True)
    actor, service = await _seed_road(database, 773014)
    await service.travel(actor, ROAD)
    view = await _play_to_end(service, actor, await service.start_hunt(actor))
    assert view.kind == "hunt_victory"
    (row,) = await _rows(database)
    async with database[1].begin() as session:
        await delete_character_owned_data(session, row.character_id)
        await session.execute(delete(Character).where(Character.id == row.character_id))
    (kept,) = await _rows(database)
    assert kept.combat_id == row.combat_id and kept.character_id is None


# --- Relatórios -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_queries_run_against_the_table(database):
    from pathlib import Path

    engine = database[0]
    text = Path("scripts/ttk_reports.sql").read_text(encoding="utf-8")
    statements = [
        part.strip()
        for part in "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("--")
        ).split(";")
        if part.strip()
    ]
    assert len(statements) == 5
    async with engine.connect() as connection:
        for statement in statements:
            await connection.exec_driver_sql(statement)
