"""PostgreSQL integration tests for Eventos Mundiais (GDD v1.6.0 §21, §36, §49.15)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update

from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.prologue import CombatView
from asterion.application.world_events import (
    WorldEventError,
    WorldEventHubView,
    WorldEventResultView,
    WorldEventService,
)
from asterion.bot.combat_ui import class_trial_action_ids
from asterion.domain.road import Creature
from asterion.domain.world_events import (
    WorldEventDefinition,
    WorldEventPhase,
    boss_stats,
    occurrence_key,
)
from asterion.infrastructure.db.models import (
    Account,
    AccountLink,
    AccountRiskFlag,
    Character,
    ConsumableStack,
    GameActivity,
    WorldEventOccurrence,
    WorldEventParticipation,
)

D = Decimal
# Tuesday 2026-11-10, 12:00 in Sao Paulo.
OPENING = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
FIGHTING = OPENING + timedelta(minutes=6)
A, B, C = 870001, 870002, 870003

BOSS = Creature(
    "teste_chefe",
    "Chefe de Teste",
    "boss",
    "balanced",
    1,
    60,
    0,
    ("golpe",),
    (("golpe", "Golpe Pesado", D("1.00"), 0, D(0), 0),),
)
PHASE = WorldEventPhase(BOSS, "O ar pesa.")
EVENT = WorldEventDefinition(
    "evento_teste",
    "Evento de Teste",
    "Terras do Ocaso",
    10,
    (PHASE, PHASE, PHASE),
    "O silêncio volta.",
)
ATTUNED = WorldEventDefinition(
    "evento_sintonizado",
    "Evento Sintonizado",
    "Terras do Ocaso",
    10,
    (PHASE, PHASE, PHASE),
    "x",
    attuned=True,
)


async def _seed(database, level: int = 30) -> None:
    async with database[1].begin() as session:
        for actor, name in ((A, "Alfa"), (B, "Beta"), (C, "Gama")):
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=name,
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu",
                    ruleset_version="tdo-1.0.15",
                    level=level,
                    hp=D("50"),
                    max_hp=D("500"),
                    vigor=100,
                    max_vigor=100,
                )
            )


def _service(database, catalog=(EVENT,)) -> WorldEventService:
    return WorldEventService(database[1], "ocaso", catalog)


async def _code(awaitable) -> str:
    with pytest.raises(WorldEventError) as error:
        await awaitable
    return error.value.code


async def _char(session, actor: int) -> Character:
    return await session.scalar(select(Character).where(Character.telegram_id == actor))


async def _open(service, now=OPENING):
    await service.run_maintenance(now=now)
    view = await service.hub(A, now=now)
    assert view.status is not None
    return view.status.occurrence_id


async def _row(database, occurrence_id) -> WorldEventOccurrence:
    async with database[1]() as session:
        return await session.get(WorldEventOccurrence, occurrence_id)


async def _part(database, occurrence_id, actor) -> WorldEventParticipation:
    async with database[1]() as session:
        character = await _char(session, actor)
        return await session.get(WorldEventParticipation, (occurrence_id, character.id))


async def _set_boss_hp(database, occurrence_id, value) -> None:
    async with database[1].begin() as session:
        await session.execute(
            update(WorldEventOccurrence)
            .where(WorldEventOccurrence.id == occurrence_id)
            .values(boss_hp=D(value))
        )


async def _make_tough(database, occurrence_id, actor) -> None:
    """Enough HP to survive long scripted fights."""
    async with database[1].begin() as session:
        character = await _char(session, actor)
        await session.execute(
            update(WorldEventParticipation)
            .where(
                WorldEventParticipation.occurrence_id == occurrence_id,
                WorldEventParticipation.character_id == character.id,
            )
            .values(hp=D("500"))
        )


def _attack_index(view: CombatView) -> int:
    return list(class_trial_action_ids(view.combat, actor_key="player")).index("attack")


async def _strike(service, actor, occurrence_id, now=FIGHTING):
    view = await service.fight(actor, occurrence_id, now=now)
    assert isinstance(view, CombatView)
    return await service.action(
        actor, view.activity_id, view.combat.version, _attack_index(view), "x", now=now
    )


async def _clear_phase(database, service, occurrence_id, actor, now=FIGHTING):
    """One strike that surely closes the phase: the Chefe is left with 1 HP."""
    await _set_boss_hp(database, occurrence_id, 1)
    return await _strike(service, actor, occurrence_id, now=now)


async def _flags(database) -> int:
    async with database[1]() as session:
        return await session.scalar(select(func.count()).select_from(AccountRiskFlag))


@pytest.mark.asyncio
async def test_empty_catalog_never_creates_an_occurrence(database):
    await _seed(database)
    service = _service(database, catalog=())
    await service.run_maintenance(now=OPENING)
    view = await service.hub(A, now=OPENING)
    assert view.status is None and view.next_opening is None
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(WorldEventOccurrence)) == 0


@pytest.mark.asyncio
async def test_restart_does_not_duplicate_the_occurrence(database):
    await _seed(database)
    await asyncio.gather(*(_service(database).run_maintenance(now=OPENING) for _ in range(6)))
    await _service(database).run_maintenance(now=OPENING + timedelta(minutes=1))
    async with database[1]() as session:
        rows = (await session.scalars(select(WorldEventOccurrence))).all()
    assert len(rows) == 1
    assert rows[0].occurrence_key == occurrence_key(OPENING)
    assert rows[0].event_id == "evento_teste"


@pytest.mark.asyncio
async def test_no_occurrence_outside_the_schedule_or_after_the_deadline(database):
    await _seed(database)
    service = _service(database)
    await service.run_maintenance(now=OPENING + timedelta(minutes=61))
    await service.run_maintenance(now=OPENING - timedelta(minutes=1))
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(WorldEventOccurrence)) == 0
    assert (await service.hub(A, now=OPENING - timedelta(minutes=1))).next_opening == OPENING


@pytest.mark.asyncio
async def test_entry_reserves_vigor_once_and_reentering_does_not_duplicate(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.enter(A, occurrence_id, now=OPENING)
    async with database[1]() as session:
        assert (await _char(session, A)).vigor == 90
        assert await session.scalar(select(func.count()).select_from(WorldEventParticipation)) == 1


@pytest.mark.asyncio
async def test_concurrent_entries_charge_a_single_vigor(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await asyncio.gather(*(service.enter(A, occurrence_id, now=OPENING) for _ in range(8)))
    async with database[1]() as session:
        assert (await _char(session, A)).vigor == 90
        assert await session.scalar(select(func.count()).select_from(WorldEventParticipation)) == 1


@pytest.mark.asyncio
async def test_entry_needs_vigor(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    async with database[1].begin() as session:
        character = await _char(session, A)
        character.vigor = 9
        character.vigor_regen_at = OPENING
    assert await _code(service.enter(A, occurrence_id, now=OPENING)) == "vigor"


@pytest.mark.asyncio
async def test_entry_closes_after_15_minutes(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    late = OPENING + timedelta(minutes=15)
    await service.hub(A, now=late)
    assert await _code(service.enter(B, occurrence_id, now=late)) == "entry_closed"


@pytest.mark.asyncio
async def test_entry_closes_at_the_final_phase_even_inside_the_window(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await _clear_phase(database, service, occurrence_id, A)
    await _make_tough(database, occurrence_id, A)
    await _clear_phase(database, service, occurrence_id, A)
    assert (await _row(database, occurrence_id)).phase == 3
    assert await _code(service.enter(B, occurrence_id, now=FIGHTING)) == "entry_closed"


@pytest.mark.asyncio
async def test_fighting_waits_for_the_gathering(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    assert await _code(service.fight(A, occurrence_id, now=OPENING)) == "gathering"


@pytest.mark.asyncio
async def test_phase_scaling_is_frozen_and_recalculated_on_the_next_phase(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    first = await _row(database, occurrence_id)
    assert first.participants_snapshot == 1
    assert first.boss_max_hp == boss_stats(BOSS, 10, 1).hp
    await service.enter(B, occurrence_id, now=FIGHTING)
    await service.enter(C, occurrence_id, now=FIGHTING)
    assert (await _row(database, occurrence_id)).boss_max_hp == first.boss_max_hp
    await _clear_phase(database, service, occurrence_id, A)
    second = await _row(database, occurrence_id)
    assert second.phase == 2
    assert second.participants_snapshot == 3
    assert second.boss_max_hp == boss_stats(BOSS, 10, 3).hp
    assert second.boss_hp == second.boss_max_hp


@pytest.mark.asyncio
async def test_new_phase_does_not_restore_lost_hp(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await _make_tough(database, occurrence_id, A)
    async with database[1].begin() as session:
        await session.execute(
            update(WorldEventParticipation)
            .where(WorldEventParticipation.occurrence_id == occurrence_id)
            .values(hp=D("321"))
        )
    await _clear_phase(database, service, occurrence_id, A)
    assert (await _part(database, occurrence_id, A)).hp <= D("321")
    view = await service.fight(A, occurrence_id, now=FIGHTING)
    assert view.combat.fighters["player"].hp == (await _part(database, occurrence_id, A)).hp


@pytest.mark.asyncio
async def test_shared_boss_dies_once_under_concurrent_strikes(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    for actor in (A, B, C):
        await service.enter(actor, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    views = {}
    for actor in (A, B, C):
        await _make_tough(database, occurrence_id, actor)
        views[actor] = await service.fight(actor, occurrence_id, now=FIGHTING)
    await _set_boss_hp(database, occurrence_id, 1)
    await asyncio.gather(
        *(
            service.action(
                actor,
                views[actor].activity_id,
                views[actor].combat.version,
                _attack_index(views[actor]),
                "x",
                now=FIGHTING,
            )
            for actor in (A, B, C)
        )
    )
    occurrence = await _row(database, occurrence_id)
    assert occurrence.phase == 2
    parts = [await _part(database, occurrence_id, actor) for actor in (A, B, C)]
    assert sum(part.major_contributions for part in parts) == 1
    assert all(part.activity_id is None for part in parts)


@pytest.mark.asyncio
async def test_resumed_instance_shows_the_shared_boss_bar_and_frozen_stats(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.enter(B, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await _make_tough(database, occurrence_id, A)
    await _make_tough(database, occurrence_id, B)
    await service.fight(A, occurrence_id, now=FIGHTING)
    await _set_boss_hp(database, occurrence_id, 777)
    resumed = await service.fight(A, occurrence_id, now=FIGHTING)
    enemy = resumed.combat.fighters["enemy"]
    assert enemy.hp == D(777)
    assert enemy.stats.hp == boss_stats(BOSS, 10, 2).hp
    assert enemy.stats.attack == boss_stats(BOSS, 10, 2).attack


@pytest.mark.asyncio
async def test_a_stale_instance_cannot_hit_after_the_phase_changed(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.enter(B, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    stale = await service.fight(B, occurrence_id, now=FIGHTING)
    await _clear_phase(database, service, occurrence_id, A)
    before = (await _row(database, occurrence_id)).boss_hp
    view = await service.action(
        B, stale.activity_id, stale.combat.version, _attack_index(stale), "x", now=FIGHTING
    )
    assert isinstance(view, WorldEventHubView)
    assert (await _row(database, occurrence_id)).boss_hp == before
    async with database[1]() as session:
        activity = await session.get(GameActivity, stale.activity_id)
    assert activity.status == "completed"


@pytest.mark.asyncio
async def test_defeat_allows_reentry_after_two_minutes_with_the_same_participation(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    async with database[1].begin() as session:
        await session.execute(
            update(WorldEventParticipation)
            .where(WorldEventParticipation.occurrence_id == occurrence_id)
            .values(hp=D("1"))
        )
    view = await _strike(service, A, occurrence_id)
    assert isinstance(view, WorldEventHubView)
    part = await _part(database, occurrence_id, A)
    assert part.reentry_at == FIGHTING + timedelta(minutes=2)
    assert part.hp == 0
    assert await _code(service.fight(A, occurrence_id, now=FIGHTING + timedelta(seconds=119))) == (
        "reentry_wait"
    )
    back = await service.fight(A, occurrence_id, now=FIGHTING + timedelta(minutes=2))
    assert isinstance(back, CombatView)
    player = back.combat.fighters["player"]
    assert player.hp == player.stats.hp
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(WorldEventParticipation)) == 1
        assert (await _char(session, A)).hp == D("50")


@pytest.mark.asyncio
async def test_configuration_lock_lasts_the_whole_participation(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)

    async def locked():
        async with database[1].begin() as session:
            character = await _char(session, A)
            await lock_for_combat_configuration_mutation(session, character.id)

    with pytest.raises(CombatConfigurationLocked) as error:
        await locked()
    assert error.value.blocker.kind == "world_event"
    await service.withdraw(A, occurrence_id, now=OPENING)
    await locked()


@pytest.mark.asyncio
async def test_foreground_only_during_combat(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)

    async def active_count():
        async with database[1]() as session:
            return await session.scalar(
                select(func.count())
                .select_from(GameActivity)
                .where(GameActivity.status == "active")
            )

    assert await active_count() == 0
    assert await service.foreground(A, now=FIGHTING) is None
    await service.fight(A, occurrence_id, now=FIGHTING)
    assert await active_count() == 1
    assert isinstance(await service.foreground(A, now=FIGHTING), CombatView)


@pytest.mark.asyncio
async def test_withdraw_ends_reentry_and_cannot_rejoin(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await service.fight(A, occurrence_id, now=FIGHTING)
    await service.withdraw(A, occurrence_id, now=FIGHTING)
    assert await _code(service.fight(A, occurrence_id, now=FIGHTING)) == "not_joined"
    assert await _code(service.enter(A, occurrence_id, now=FIGHTING)) == "withdrawn"
    async with database[1]() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(GameActivity)
                .where(GameActivity.status == "active")
            )
            == 0
        )


async def _complete(database, service, occurrence_id, actor):
    """Kill the three phases with the same character."""
    await service.hub(actor, now=FIGHTING)
    for _ in range(3):
        await _make_tough(database, occurrence_id, actor)
        await _clear_phase(database, service, occurrence_id, actor)


@pytest.mark.asyncio
async def test_eligible_participant_is_paid_once_with_the_event_economy(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await _complete(database, service, occurrence_id, A)
    occurrence = await _row(database, occurrence_id)
    assert occurrence.status == "completed"
    async with database[1]() as session:
        before = await _char(session, A)
        crowns, xp = before.crowns, before.xp
    notices = await service.run_maintenance(now=FIGHTING)
    assert [notice.telegram_id for notice in notices] == [A]
    view = notices[0].view
    assert isinstance(view, WorldEventResultView) and view.eligible and view.completed
    assert view.crowns == 100
    assert {item.quantity for item in view.items} == {1}
    assert len(view.items) == 3  # 1 Metal, 1 Couro, 1 Fragmento
    assert await service.run_maintenance(now=FIGHTING) == []
    async with database[1]() as session:
        after = await _char(session, A)
    assert after.crowns == crowns + 100
    assert after.xp + after.level > 0
    assert after.xp != xp or after.level != 30
    part = await _part(database, occurrence_id, A)
    assert part.status == "settled" and part.eligible is True
    assert isinstance(await service.last_result(A), WorldEventResultView)


@pytest.mark.asyncio
async def test_lock_is_released_after_settlement(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await _complete(database, service, occurrence_id, A)
    await service.run_maintenance(now=FIGHTING)
    async with database[1].begin() as session:
        character = await _char(session, A)
        await lock_for_combat_configuration_mutation(session, character.id)


@pytest.mark.asyncio
async def test_one_hit_and_leaving_gets_vigor_back_and_no_reward(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.enter(B, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await _make_tough(database, occurrence_id, B)
    await _strike(service, B, occurrence_id)
    await service.withdraw(B, occurrence_id, now=FIGHTING)
    await _complete(database, service, occurrence_id, A)
    notices = await service.run_maintenance(now=FIGHTING)
    by_actor = {notice.telegram_id: notice.view for notice in notices}
    assert by_actor[B].eligible is False and by_actor[B].completed is True
    assert by_actor[B].crowns == 0 and by_actor[B].items == ()
    async with database[1]() as session:
        assert (await _char(session, B)).vigor == 100
        assert (await _char(session, B)).crowns == 0


@pytest.mark.asyncio
async def test_withdrawn_participant_with_substantial_contribution_is_still_paid(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await _complete(database, service, occurrence_id, A)
    await service.withdraw(A, occurrence_id, now=FIGHTING)
    notices = await service.run_maintenance(now=FIGHTING)
    assert notices[0].view.eligible is True
    assert (await _part(database, occurrence_id, A)).status == "withdrawn"


@pytest.mark.asyncio
async def test_deadline_fails_the_event_refunds_and_releases(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await service.fight(A, occurrence_id, now=FIGHTING)
    late = OPENING + timedelta(minutes=60)
    notices = await service.run_maintenance(now=late)
    assert notices[0].view.completed is False
    occurrence = await _row(database, occurrence_id)
    assert occurrence.status == "failed" and occurrence.settled_at is not None
    async with database[1]() as session:
        assert (await _char(session, A)).vigor == 100
        assert (
            await session.scalar(
                select(func.count())
                .select_from(GameActivity)
                .where(GameActivity.status == "active")
            )
            == 0
        )


@pytest.mark.asyncio
async def test_event_without_participants_expires_at_the_deadline(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.run_maintenance(now=FIGHTING)
    assert (await _row(database, occurrence_id)).status == "active"
    assert await service.run_maintenance(now=OPENING + timedelta(minutes=60)) == []
    occurrence = await _row(database, occurrence_id)
    assert occurrence.status == "failed" and occurrence.settled_at is not None


@pytest.mark.asyncio
async def test_action_after_the_deadline_deals_no_damage(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    view = await service.fight(A, occurrence_id, now=FIGHTING)
    before = (await _row(database, occurrence_id)).boss_hp
    late = OPENING + timedelta(minutes=60)
    result = await service.action(
        A, view.activity_id, view.combat.version, _attack_index(view), "x", now=late
    )
    assert isinstance(result, WorldEventHubView)
    assert (await _row(database, occurrence_id)).boss_hp == before


@pytest.mark.asyncio
async def test_consumables_stop_at_two_per_occurrence(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await _make_tough(database, occurrence_id, A)
    async with database[1].begin() as session:
        character = await _char(session, A)
        session.add(
            ConsumableStack(character_id=character.id, consumable_id="consumable.heal", quantity=5)
        )
    view = await service.fight(A, occurrence_id, now=FIGHTING)
    assert view.consumable_budget_limit == 2
    used = await service.consume_for_activity(
        A,
        view.activity_id,
        view.combat.version,
        item_id="consumable.heal",
        target_id="player",
        effect_id=None,
        now=FIGHTING,
    )
    assert isinstance(used, CombatView)
    assert used.consumable_budget_limit == 1
    async with database[1].begin() as session:
        await session.execute(
            update(WorldEventParticipation)
            .where(WorldEventParticipation.occurrence_id == occurrence_id)
            .values(consumable_uses=2)
        )
    blocked = await service.consume_for_activity(
        A,
        view.activity_id,
        used.combat.version,
        item_id="consumable.heal",
        target_id="player",
        effect_id=None,
        now=FIGHTING,
    )
    assert blocked.consumable_budget_limit == 0
    async with database[1]() as session:
        character = await _char(session, A)
        stack = await session.scalar(
            select(ConsumableStack).where(ConsumableStack.character_id == character.id)
        )
    assert stack.quantity == 4


@pytest.mark.asyncio
async def test_consumable_of_another_activity_is_not_handled(database):
    await _seed(database)
    from uuid import uuid4

    service = _service(database)
    assert (
        await service.consume_for_activity(
            A, uuid4(), 1, item_id="x", target_id="player", effect_id=None
        )
        is None
    )
    assert await service.consumable_selection(A, uuid4(), 1) is None


@pytest.mark.asyncio
async def test_defend_is_not_a_significant_action(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await _make_tough(database, occurrence_id, A)
    view = await service.fight(A, occurrence_id, now=FIGHTING)
    index = list(class_trial_action_ids(view.combat, actor_key="player")).index("defend")
    await service.action(A, view.activity_id, view.combat.version, index, "x", now=FIGHTING)
    assert (await _part(database, occurrence_id, A)).significant_actions == 0


@pytest.mark.asyncio
async def test_attunement_lowers_the_veteran_only_in_marked_events(database):
    await _seed(database, level=60)
    service = _service(database, catalog=(ATTUNED,))
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await _make_tough(database, occurrence_id, A)
    attuned = await service.fight(A, occurrence_id, now=FIGHTING)
    assert attuned.combat.fighters["player"].level == 15


@pytest.mark.asyncio
async def test_unmarked_event_keeps_the_real_level(database):
    await _seed(database, level=60)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await _make_tough(database, occurrence_id, A)
    view = await service.fight(A, occurrence_id, now=FIGHTING)
    assert view.combat.fighters["player"].level == 60


@pytest.mark.asyncio
async def test_linked_accounts_are_only_flagged(database):
    await _seed(database)
    async with database[1].begin() as session:
        session.add(AccountLink(account_a=A, account_b=B))
    service = _service(database)
    occurrence_id = await _open(service)
    for actor in (A, B, C):
        await service.enter(actor, occurrence_id, now=OPENING)
    await _complete(database, service, occurrence_id, A)
    await service.run_maintenance(now=FIGHTING)
    assert await _flags(database) == 1
    async with database[1]() as session:
        flag = await session.scalar(select(AccountRiskFlag))
    assert flag.activity_kind == "world_event"
    assert (flag.account_a, flag.account_b) == (A, B)
    assert await service.run_maintenance(now=FIGHTING) == []
    assert await _flags(database) == 1


@pytest.mark.asyncio
async def test_a_large_event_does_not_exceed_the_driver_parameter_limit(database):
    """200 accounts would be 19.900 pairs if nobody filtered them first."""
    await _seed(database)
    base = 880000
    async with database[1].begin() as session:
        for index in range(200):
            actor = base + index
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=f"Multidao{chr(97 + index // 26)}{chr(97 + index % 26)}",
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu",
                    ruleset_version="tdo-1.0.15",
                    level=20,
                    hp=D("50"),
                    max_hp=D("500"),
                    vigor=100,
                    max_vigor=100,
                )
            )
        session.add(AccountLink(account_a=base, account_b=base + 1))
    service = _service(database)
    occurrence_id = await _open(service)
    for index in range(200):
        await service.enter(base + index, occurrence_id, now=OPENING)
    await service.run_maintenance(now=OPENING + timedelta(minutes=60))
    assert await _flags(database) == 1


@pytest.mark.asyncio
async def test_character_deletion_removes_the_participation(database):
    await _seed(database)
    service = _service(database)
    occurrence_id = await _open(service)
    await service.enter(A, occurrence_id, now=OPENING)
    await service.hub(A, now=FIGHTING)
    await service.fight(A, occurrence_id, now=FIGHTING)
    async with database[1].begin() as session:
        character = await _char(session, A)
        await delete_character_owned_data(session, character.id)
        await session.delete(character)
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(WorldEventParticipation)) == 0
