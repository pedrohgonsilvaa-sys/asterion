import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import event, select, text

from asterion.application.consumables import ConsumableService
from asterion.application.prologue import PrologueService
from asterion.application.round import RoundService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import CombatConsumableFlowCallback, event_line
from asterion.bot.road_ui import render_road
from asterion.domain.combat import (
    Action,
    ActionCondition,
    ActionConditionalModifier,
    ActionResourceUse,
    DotState,
    Effect,
)
from asterion.domain.combat_math import Stats
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    CombatRecord,
    ConsumableStack,
    GameActivity,
    HuntContext,
)
from tests.test_creation_ui import callback_update
from tests.test_road_integration import ROAD, _seed_road


async def _stock(database, actor: int, items: dict[str, int], *, hp: int | None = None):
    _, sessions = database
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        if hp is not None:
            character.hp = Decimal(hp)
        for item_id, quantity in items.items():
            session.add(
                ConsumableStack(
                    character_id=character.id,
                    consumable_id=item_id,
                    quantity=quantity,
                )
            )
        await session.commit()


async def _combat(database, actor: int, items: dict[str, int], *, hp: int = 500):
    _, service = await _seed_road(database, actor=actor)
    await _stock(database, actor, items, hp=hp)
    await service.travel(actor, ROAD)
    view = await service.start_hunt(actor)
    assert view is not None and view.kind == "combat"
    return service, view


async def _stack_quantity(database, actor: int, item_id: str) -> int:
    _, sessions = database
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        quantity = await session.scalar(
            select(ConsumableStack.quantity).where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == item_id,
            )
        )
        return int(quantity)


async def _stack_quantities(database, actor: int, item_ids: tuple[str, ...]) -> dict[str, int]:
    return {
        item_id: await _stack_quantity(database, actor, item_id)
        for item_id in item_ids
    }


async def _save_combat(database, view, update):
    """Persist an authoritative concurrent combat change and advance its version."""
    _, sessions = database
    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity)
            .where(GameActivity.id == view.activity_id)
            .with_for_update()
        )
        record = await session.scalar(
            select(CombatRecord)
            .where(CombatRecord.id == view.combat_id)
            .with_for_update()
        )
        assert activity is not None and record is not None
        combat = decode(
            record.snapshot,
            record.id,
            activity.ruleset_version,
            activity.state_version,
        )
        update(combat)
        combat.version += 1
        activity.state_version = combat.version
        record.snapshot = encode(combat)
        return combat.version


async def _wait_for_postgres_lock(database, query_fragment: str) -> None:
    """Observe the competing SQL statement waiting on a real PostgreSQL lock."""
    _, sessions = database
    deadline = asyncio.get_running_loop().time() + 5
    statement = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid <> pg_backend_pid()
              AND wait_event_type = 'Lock'
              AND query ILIKE :query_pattern
        )
        """
    )
    while asyncio.get_running_loop().time() < deadline:
        async with sessions() as observer:
            waiting = await observer.scalar(
                statement, {"query_pattern": f"%{query_fragment}%"}
            )
        if waiting:
            return
        # Poll PostgreSQL's lock table; the row lock, not this interval,
        # controls when the competing transaction can proceed.
        await asyncio.sleep(0.01)
    raise AssertionError(f"No PostgreSQL lock wait observed for {query_fragment}")


async def _race_actions(service, actor, view, item_ids: tuple[str, str]):
    barrier = asyncio.Barrier(2)

    async def submit(item_id: str):
        await barrier.wait()
        return await service.action(
            actor,
            view.activity_id,
            view.combat.version,
            consumable_id=item_id,
        )

    return await asyncio.gather(*(submit(item_id) for item_id in item_ids))


@pytest.mark.asyncio
async def test_last_unit_and_duplicate_retry_commit_once_across_reconnect(database):
    actor = 770301
    service, view = await _combat(database, actor, {"consumable.heal": 1})
    assert any(option.item_id == "consumable.heal" for option in view.consumable_options)

    submissions = await asyncio.gather(
        service.action(
            actor,
            view.activity_id,
            view.combat.version,
            consumable_id="consumable.heal",
        ),
        service.action(
            actor,
            view.activity_id,
            view.combat.version,
            consumable_id="consumable.heal",
        ),
    )
    assert all(result is not None and result.kind == "combat" for result in submissions)
    assert await _stack_quantity(database, actor, "consumable.heal") == 0

    latest = await RoundService(database[1], "ocaso").resume(actor)
    assert latest is not None and latest.kind == "combat"
    assert latest.combat.consumable_uses == 1
    assert sum(
        event.action == "consumable:consumable.heal" for event in latest.combat.events
    ) == 1

    stale_retry = await service.action(
        actor,
        view.activity_id,
        view.combat.version,
        consumable_id="consumable.heal",
    )
    assert stale_retry is not None and stale_retry.combat.version == latest.combat.version
    assert await _stack_quantity(database, actor, "consumable.heal") == 0


@pytest.mark.asyncio
async def test_declared_class_resource_snapshot_and_after_resolution_payment_survive_reconnect(
    database, monkeypatch
):
    actor = 770399
    service, view = await _combat(database, actor, {})

    def install_synthetic_terminal(combat):
        player = combat.fighters["player"]
        target = combat.fighters["enemy"]
        player.character_class = "vigia"
        player.selected_path = "atirador"
        target.path_state["aim_from"] = {
            player.id: {
                "stacks": 4,
                "remaining": 2,
                "applied_opportunity": player.opportunity,
            }
        }
        combat.player_actions["synthetic_terminal"] = Action(
            "class_art.test.synthetic_terminal",
            "Finalização Sintética de Teste",
            Decimal("0.20"),
            cooldown=2,
            hit_count=2,
            resource_uses=(
                ActionResourceUse(
                    "aim",
                    minimum=4,
                    consume=4,
                    consume_at="after_resolution",
                    target_selector="primary_target",
                    required=True,
                ),
            ),
            conditional_modifiers=(
                ActionConditionalModifier(
                    "test.terminal.four_aim_crit",
                    ActionCondition(
                        "class_resource_at_least",
                        resource="aim",
                        minimum=4,
                    ),
                    "crit_bonus",
                    Decimal(15),
                    target_scope="primary_target",
                ),
            ),
        )

    await _save_combat(database, view, install_synthetic_terminal)
    before = await service.resume(actor)
    assert before is not None and before.kind == "combat"
    action = before.combat.player_actions["synthetic_terminal"]
    assert action.resource_uses[0].consume_at == "after_resolution"
    assert action.conditional_modifiers[0].condition.minimum == 4

    original_record_bestiary = service._record_bestiary_combat_events

    async def fail_after_combat_snapshot(*args, **kwargs):
        raise RuntimeError("injected before-commit failure")

    monkeypatch.setattr(
        service, "_record_bestiary_combat_events", fail_after_combat_snapshot
    )
    with pytest.raises(RuntimeError, match="injected before-commit failure"):
        await service.action(
            actor,
            before.activity_id,
            before.combat.version,
            action="synthetic_terminal",
            target_id="enemy",
        )
    rolled_back = await service.resume(actor)
    assert rolled_back is not None and rolled_back.kind == "combat"
    assert rolled_back.combat.version == before.combat.version
    assert rolled_back.combat.fighters["enemy"].path_state["aim_from"][
        rolled_back.combat.fighters["player"].id
    ]["stacks"] == 4
    assert not any(
        event.action == "synthetic_terminal" for event in rolled_back.combat.events
    )
    monkeypatch.setattr(
        service, "_record_bestiary_combat_events", original_record_bestiary
    )

    submissions = await asyncio.gather(
        service.action(
            actor,
            before.activity_id,
            before.combat.version,
            action="synthetic_terminal",
            target_id="enemy",
        ),
        service.action(
            actor,
            before.activity_id,
            before.combat.version,
            action="synthetic_terminal",
            target_id="enemy",
        ),
    )
    assert all(result is not None and result.kind == "combat" for result in submissions)
    after = await service.resume(actor)
    assert after is not None and after.kind == "combat"
    assert "aim_from" not in after.combat.fighters["enemy"].path_state
    assert after.combat.fighters["player"].cooldowns["synthetic_terminal"] > 0
    action_events = [
        event
        for event in after.combat.events
        if event.action == "synthetic_terminal"
    ]
    assert len(action_events) == 2
    assert action_events[0].class_resource_changes == (("aim", "enemy", 4, 0),)
    assert action_events[1].class_resource_changes == ()

    stale = await service.action(
        actor,
        before.activity_id,
        before.combat.version,
        action="synthetic_terminal",
        target_id="enemy",
    )
    assert stale is not None and stale.combat.version == after.combat.version
    latest = await service.resume(actor)
    assert latest is not None and latest.combat.version == after.combat.version
    assert len(
        [event for event in latest.combat.events if event.action == "synthetic_terminal"]
    ) == 2


@pytest.mark.asyncio
async def test_cd2_rejection_keeps_other_combat_item_and_budget(database):
    actor = 770302
    service, view = await _combat(
        database,
        actor,
        {"consumable.heal": 1, "consumable.protection.vde.ii": 1},
    )
    async with database[1]() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == view.activity_id)
        )
        assert context is not None
        context.category = "elite"  # Keep one budget slot after the successful use.
        await session.commit()

    used = await service.action(
        actor,
        view.activity_id,
        view.combat.version,
        consumable_id="consumable.heal",
    )
    assert used is not None and used.combat.consumable_uses == 1
    assert used.combat.fighters["player"].cooldowns["consumable"] > (
        used.combat.fighters["player"].opportunity
    )

    rejected = await service.action(
        actor,
        view.activity_id,
        used.combat.version,
        consumable_id="consumable.protection.vde.ii",
    )
    assert rejected is not None and rejected.combat.version == used.combat.version
    assert rejected.combat.consumable_uses == 1
    assert rejected.combat.fighters["player"].barrier == Decimal(0)
    assert await _stack_quantity(database, actor, "consumable.protection.vde.ii") == 1


@pytest.mark.asyncio
async def test_common_encounter_budget_rejection_does_not_consume_stock(database):
    actor = 770303
    service, view = await _combat(
        database,
        actor,
        {"consumable.protection.vde.ii": 1},
    )
    async with database[1]() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == view.activity_id)
        )
        encounter = await session.scalar(
            select(CombatRecord).where(CombatRecord.id == view.combat_id)
        )
        assert context is not None and encounter is not None
        context.category = "common"
        combat = decode(
            encounter.snapshot,
            encounter.id,
            view.combat.ruleset,
            view.combat.version,
        )
        combat.consumable_uses = 1
        combat.fighters["player"].cooldowns["consumable"] = 0
        encounter.snapshot = encode(combat)
        await session.commit()

    rejected = await service.action(
        actor,
        view.activity_id,
        view.combat.version,
        consumable_id="consumable.protection.vde.ii",
    )
    assert rejected is not None and rejected.combat.version == view.combat.version
    assert rejected.combat.consumable_uses == 1
    assert await _stack_quantity(database, actor, "consumable.protection.vde.ii") == 1


@pytest.mark.asyncio
async def test_failed_combat_snapshot_write_rolls_back_stock_and_character(database):
    actor = 770304
    service, view = await _combat(database, actor, {"consumable.heal": 1})
    engine = database[0]

    def fail_snapshot_write(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().lower().startswith("update combats"):
            raise RuntimeError("injected combat snapshot persistence failure")

    event.listen(engine.sync_engine, "before_cursor_execute", fail_snapshot_write)
    try:
        with pytest.raises(RuntimeError, match="injected combat snapshot persistence failure"):
            await service.action(
                actor,
                view.activity_id,
                view.combat.version,
                consumable_id="consumable.heal",
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", fail_snapshot_write)

    assert await _stack_quantity(database, actor, "consumable.heal") == 1
    latest = await RoundService(database[1], "ocaso").resume(actor)
    assert latest is not None and latest.kind == "combat"
    assert latest.combat.version == view.combat.version
    assert latest.combat.consumable_uses == 0
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        # Starting this new combat reconciles legacy max HP while preserving
        # the old current-HP ratio (500/702 of the new racial max HP).
        assert character is not None and character.hp == Decimal(507)


@pytest.mark.asyncio
async def test_vigor_consumable_is_once_per_daily_cycle_under_concurrency(database):
    actor = 770305
    _, service = await _seed_road(database, actor=actor, vigor=80)
    await _stock(database, actor, {"consumable.vigor.tdo.i": 1})
    consumables = ConsumableService(database[1], "ocaso")
    now = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)

    results = await asyncio.gather(
        consumables.use_vigor_potion(actor, "consumable.vigor.tdo.i", now=now),
        consumables.use_vigor_potion(actor, "consumable.vigor.tdo.i", now=now),
    )
    assert sorted(result is None for result in results) == [False, True]
    assert await _stack_quantity(database, actor, "consumable.vigor.tdo.i") == 0
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.vigor == 100
        assert character.vigor_consumable_cycle == date(2026, 9, 24)


@pytest.mark.asyncio
async def test_vigor_rejects_combat_or_more_than_eighty_without_consuming(database):
    actor = 770306
    _, service = await _seed_road(database, actor=actor, vigor=80)
    await _stock(database, actor, {"consumable.vigor.tdo.i": 2})
    consumables = ConsumableService(database[1], "ocaso")
    now = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)

    await service.travel(actor, ROAD)
    combat = await service.start_hunt(actor)
    assert combat.kind == "combat"
    assert await consumables.use_vigor_potion(
        actor, "consumable.vigor.tdo.i", now=now
    ) is None
    assert await _stack_quantity(database, actor, "consumable.vigor.tdo.i") == 2

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.vigor = 81
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == combat.activity_id)
        )
        assert context is not None
        # The active-combat rejection has already been proven; remove it to
        # exercise the independent Vigor threshold on the same character.
        game_activity = await session.get(GameActivity, context.game_activity_id)
        assert game_activity is not None
        game_activity.status = "completed"
        await session.commit()

    assert await consumables.use_vigor_potion(
        actor, "consumable.vigor.tdo.i", now=now
    ) is None
    assert await _stack_quantity(database, actor, "consumable.vigor.tdo.i") == 2


@pytest.mark.asyncio
async def test_postgres_concurrent_combat_items_serialize_shared_cd2(database):
    actor = 770307
    item_ids = ("consumable.heal", "consumable.protection.vde.ii")
    service, view = await _combat(database, actor, dict.fromkeys(item_ids, 1), hp=500)
    assert all(
        any(option.item_id == item_id for option in view.consumable_options)
        for item_id in item_ids
    )
    async with database[1]() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == view.activity_id)
        )
        assert context is not None
        context.category = "elite"  # Isolate the race from the common 1-use limit.
        await session.commit()

    results = await _race_actions(service, actor, view, item_ids)
    assert all(result is not None for result in results)

    latest = await service.resume(actor)
    assert latest is not None and latest.kind == "combat"
    combat = latest.combat
    consumable_events = [
        event for event in combat.events if event.action.startswith("consumable:")
    ]
    assert len(consumable_events) == 1
    assert combat.consumable_uses == 1
    assert combat.version == view.combat.version + 1
    assert combat.fighters["player"].cooldowns["consumable"] > (
        combat.fighters["player"].opportunity
    )
    quantities = await _stack_quantities(database, actor, item_ids)
    assert sum(quantities.values()) == 1
    assert all(quantity >= 0 for quantity in quantities.values())
    winner = consumable_events[0]
    assert winner.action in {f"consumable:{item_id}" for item_id in item_ids}
    if winner.action == "consumable:consumable.heal":
        assert winner.healed > 0
    else:
        assert winner.barrier_value > 0


@pytest.mark.asyncio
async def test_postgres_concurrent_items_cannot_exceed_last_budget_slot(database):
    actor = 770308
    item_ids = ("consumable.heal", "consumable.protection.vde.ii")
    service, view = await _combat(database, actor, dict.fromkeys(item_ids, 1), hp=500)
    async with database[1]() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == view.activity_id)
        )
        assert context is not None
        context.category = "common"  # The whole starting budget is one use.
        await session.commit()

    results = await _race_actions(service, actor, view, item_ids)
    assert all(result is not None for result in results)

    latest = await service.resume(actor)
    assert latest is not None and latest.kind == "combat"
    combat = latest.combat
    assert combat.consumable_uses == 1
    assert combat.version == view.combat.version + 1
    consumable_events = [
        event for event in combat.events if event.action.startswith("consumable:")
    ]
    assert len(consumable_events) == 1
    quantities = await _stack_quantities(database, actor, item_ids)
    assert sum(quantities.values()) == 1
    assert all(quantity >= 0 for quantity in quantities.values())


@pytest.mark.asyncio
async def test_postgres_stock_change_under_lock_rejects_old_callback(database):
    actor = 770309
    item_id = "consumable.heal"
    service, view = await _combat(database, actor, {item_id: 1}, hp=500)
    assert any(option.item_id == item_id for option in view.consumable_options)
    _, sessions = database
    writer = sessions()
    action_task = None
    await writer.begin()
    try:
        character = await writer.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        stack = await writer.scalar(
            select(ConsumableStack)
            .where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == item_id,
            )
            .with_for_update()
        )
        assert stack is not None and stack.quantity == 1
        stack.quantity = 0
        await writer.flush()

        action_task = asyncio.create_task(
            service.action(
                actor,
                view.activity_id,
                view.combat.version,
                consumable_id=item_id,
            )
        )
        await _wait_for_postgres_lock(database, "consumable_stacks")
        await writer.commit()
        rejected = await action_task
    finally:
        if action_task is not None and not action_task.done():
            action_task.cancel()
            await asyncio.gather(action_task, return_exceptions=True)
        if writer.in_transaction():
            await writer.rollback()
        await writer.close()

    assert rejected is not None and rejected.kind == "combat"
    assert await _stack_quantity(database, actor, item_id) == 0
    latest = await service.resume(actor)
    assert latest is not None and latest.kind == "combat"
    assert latest.combat.version == view.combat.version
    assert latest.combat.consumable_uses == 0
    assert not any(
        event.action.startswith("consumable:") for event in latest.combat.events
    )


@pytest.mark.asyncio
async def test_postgres_expired_effect_callback_does_not_retarget_or_consume(database):
    actor = 770310
    item_id = "consumable.purification"
    service, view = await _combat(database, actor, {item_id: 1})

    def expire_selected_effect(combat):
        combat.order = ("player", "enemy")
        combat.turn_index = 0
        player = combat.fighters["player"]
        player.effects = [
            Effect(
                "weak",
                "attack",
                Decimal("0.1"),
                1,
                player.opportunity - 1,
                instance_id="effect-expiring",
            ),
            Effect(
                "other-weak",
                "attack",
                Decimal("0.2"),
                3,
                player.opportunity - 1,
                instance_id="effect-remains",
            ),
        ]

    await _save_combat(database, view, expire_selected_effect)
    selected_view = await service.resume(actor)
    assert selected_view is not None and selected_view.kind == "combat"
    assert any(
        option.item_id == item_id and option.effect_id == "effect-expiring"
        for option in selected_view.consumable_options
    )

    advanced = await service.action(
        actor,
        selected_view.activity_id,
        selected_view.combat.version,
        action="defend",
    )
    assert advanced is not None and advanced.kind == "combat"
    assert all(
        effect.instance_id != "effect-expiring"
        for effect in advanced.combat.fighters["player"].effects
    )
    assert any(
        effect.instance_id == "effect-remains"
        for effect in advanced.combat.fighters["player"].effects
    )

    stale = await service.action(
        actor,
        selected_view.activity_id,
        selected_view.combat.version,
        consumable_id=item_id,
        effect_id="effect-expiring",
    )
    assert stale is not None and stale.kind == "combat"
    assert await _stack_quantity(database, actor, item_id) == 1
    latest = await service.resume(actor)
    assert latest is not None and latest.kind == "combat"
    assert latest.combat.consumable_uses == 0
    assert not any(
        event.action.startswith("consumable:") for event in latest.combat.events
    )
    assert any(
        effect.instance_id == "effect-remains"
        for effect in latest.combat.fighters["player"].effects
    )


@pytest.mark.asyncio
async def test_postgres_dead_target_callback_does_not_retarget_or_consume(database):
    actor = 770311
    item_id = "consumable.dispeller.iii"
    service, view = await _combat(database, actor, {item_id: 1})

    def invalidate_selected_target(combat):
        combat.order = ("player", "enemy")
        combat.turn_index = 0
        player = combat.fighters["player"]
        player.stats = Stats(
            player.stats.hp,
            Decimal("10000"),
            player.stats.defense,
            player.stats.agility,
        )
        enemy = combat.fighters["enemy"]
        enemy.hp = Decimal(1)
        enemy.effects = [
            Effect(
                "guard-up",
                "defense",
                Decimal("0.1"),
                3,
                enemy.opportunity,
                kind="buff",
                instance_id="target-buff",
            )
        ]

    await _save_combat(database, view, invalidate_selected_target)
    selected_view = await service.resume(actor)
    assert selected_view is not None and selected_view.kind == "combat"
    assert any(
        option.item_id == item_id
        and option.target_id == "enemy"
        and option.effect_id == "target-buff"
        for option in selected_view.consumable_options
    )

    defeated = await service.action(
        actor,
        selected_view.activity_id,
        selected_view.combat.version,
        action="attack",
    )
    assert defeated is not None and defeated.kind == "hunt_victory"
    stale = await service.action(
        actor,
        selected_view.activity_id,
        selected_view.combat.version,
        consumable_id=item_id,
        target_id="enemy",
        effect_id="target-buff",
    )
    assert stale is not None and stale.kind == "hunt_victory"
    assert await _stack_quantity(database, actor, item_id) == 1

    _, sessions = database
    async with sessions() as session:
        activity = await session.get(GameActivity, selected_view.activity_id)
        record = await session.get(CombatRecord, selected_view.combat_id)
        assert activity is not None and record is not None
        combat = decode(
            record.snapshot,
            record.id,
            activity.ruleset_version,
            activity.state_version,
        )
        assert combat.consumable_uses == 0
        assert not any(
            event.action.startswith("consumable:") for event in combat.events
        )


@pytest.mark.asyncio
async def test_multidevice_callback_after_menu_open_is_idempotent_and_reconnects(database):
    actor = 770701
    service, initial = await _combat(database, actor, {"consumable.heal": 1})
    prologue = PrologueService(database[1], "ocaso", PROFILE)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(combat_router(prologue, {}, road=service))
    telegram = Bot("123456:local-test-token")
    telegram.session.make_request = AsyncMock(return_value=True)

    hud = render_road(initial)
    open_callback = next(
        button.callback_data
        for row in hud.keyboard.inline_keyboard
        for button in row
        if button.text == "Consumível"
    )
    await dispatcher.feed_raw_update(
        telegram,
        callback_update(open_callback, update_id=881, actor=actor),
    )
    menu_request = telegram.session.make_request.call_args.args[1]
    item_callback = menu_request.reply_markup.inline_keyboard[0][0].callback_data
    item_choice = CombatConsumableFlowCallback.unpack(item_callback)
    assert item_choice.step == "i"
    assert item_choice.item_id == "consumable.heal"

    before_use = await service.resume(actor)
    assert before_use is not None and before_use.combat.version == initial.combat.version
    assert await _stack_quantity(database, actor, "consumable.heal") == 1

    # Both devices act from the same screen. The first click commits; the other is stale.
    await dispatcher.feed_raw_update(
        telegram,
        callback_update(item_callback, update_id=882, actor=actor),
    )
    await dispatcher.feed_raw_update(
        telegram,
        callback_update(item_callback, update_id=883, actor=actor),
    )
    stale_request = telegram.session.make_request.call_args.args[1]
    assert "⏳ Consumíveis · Em Recarga" in stale_request.text

    latest = await service.resume(actor)
    assert latest is not None and latest.kind == "combat"
    assert latest.combat.consumable_uses == 1
    assert sum(
        event.action == "consumable:consumable.heal" for event in latest.combat.events
    ) == 1
    assert await _stack_quantity(database, actor, "consumable.heal") == 0

    reconnected = render_road(await service.resume(actor))
    assert "📜 Registro de Combate · Recentes" in reconnected.text
    assert reconnected.text.count("usa <b>Poção de Cura</b>") == 1
    assert not any(
        button.text == "Consumível"
        for row in reconnected.keyboard.inline_keyboard
        for button in row
    )


@pytest.mark.asyncio
async def test_multi_effect_selections_use_stable_ids_without_consuming_on_navigation(database):
    actor = 770702
    item_ids = ("consumable.purification", "consumable.antidote.tdo.i")
    service, initial = await _combat(database, actor, {item_id: 1 for item_id in item_ids})

    def add_choices(combat):
        combat.fighters["player"].effects.clear()
        combat.fighters["player"].effects.extend(
            [
                Effect("weak", "attack", Decimal("0.1"), 3, 0, instance_id="e1"),
                Effect("slow", "defense", Decimal("0.1"), 2, 0, instance_id="e2"),
            ]
        )
        combat.dot_states["player"] = [
            DotState(
                "poison",
                2,
                2,
                Decimal("20"),
                "enemy",
                stack_snapshots=[Decimal("20"), Decimal("20")],
                instance_id="d1",
            ),
            DotState(
                "burn",
                1,
                2,
                Decimal("30"),
                "enemy",
                stack_snapshots=[Decimal("30")],
                instance_id="d2",
            ),
        ]

    await _save_combat(database, initial, add_choices)
    current = await service.resume(actor)
    assert current is not None
    menu = await service.consumable_selection(
        actor, current.activity_id, current.combat.version, screen="items"
    )
    assert menu is not None and menu.consumable_screen == "items"
    assert menu.combat.version == current.combat.version
    assert await _stack_quantities(database, actor, item_ids) == dict.fromkeys(item_ids, 1)

    purification = await service.consumable_selection(
        actor,
        current.activity_id,
        current.combat.version,
        screen="choose_item",
        item_id="consumable.purification",
    )
    assert purification is not None and purification.consumable_screen == "effects"
    purification_screen = render_road(purification)
    purification_choices = [
        CombatConsumableFlowCallback.unpack(button.callback_data).effect_id
        for row in purification_screen.keyboard.inline_keyboard
        for button in row
        if button.text.isdigit()
    ]
    assert purification_choices == ["d1", "d2", "e1", "e2"]

    antidote = await service.consumable_selection(
        actor,
        current.activity_id,
        current.combat.version,
        screen="choose_item",
        item_id="consumable.antidote.tdo.i",
    )
    assert antidote is not None and antidote.consumable_screen == "effects"
    antidote_screen = render_road(antidote)
    antidote_choices = [
        CombatConsumableFlowCallback.unpack(button.callback_data).effect_id
        for row in antidote_screen.keyboard.inline_keyboard
        for button in row
        if button.text.isdigit()
    ]
    assert antidote_choices == ["d1", "d2"]
    assert await _stack_quantities(database, actor, item_ids) == dict.fromkeys(item_ids, 1)
    assert (await service.resume(actor)).combat.consumable_uses == 0


@pytest.mark.asyncio
async def test_single_effect_selection_skips_screen_and_stale_callback_is_rejected(database):
    actor = 770703
    item_id = "consumable.purification"
    service, initial = await _combat(database, actor, {item_id: 1})

    def add_single_choices(combat):
        combat.fighters["player"].effects.clear()
        combat.fighters["player"].effects.append(
            Effect("weak", "attack", Decimal("0.1"), 2, 0, instance_id="e1")
        )

    await _save_combat(database, initial, add_single_choices)
    current = await service.resume(actor)
    assert current is not None
    purification = await service.consumable_selection(
        actor,
        current.activity_id,
        current.combat.version,
        screen="choose_item",
        item_id="consumable.purification",
    )
    assert purification is not None and purification.ready_consumable_option.effect_id == "e1"
    assert purification.consumable_screen is None

    await _save_combat(
        database,
        current,
        lambda combat: combat.fighters["player"].effects.clear(),
    )
    rejected = await service.action(
        actor,
        current.activity_id,
        current.combat.version,
        consumable_id="consumable.purification",
        target_id="player",
        effect_id="e1",
    )
    assert rejected is not None and rejected.combat.consumable_uses == 0
    assert await _stack_quantity(database, actor, item_id) == 1
    player = rejected.combat.fighters["player"]
    assert player.cooldowns.get("consumable", 0) <= player.opportunity


@pytest.mark.asyncio
async def test_single_antidote_choice_skips_redundant_selection(database):
    actor = 770704
    item_id = "consumable.antidote.tdo.i"
    service, initial = await _combat(database, actor, {item_id: 1})

    def add_dot(combat):
        combat.dot_states["player"] = [
            DotState(
                "poison",
                2,
                2,
                Decimal("20"),
                "enemy",
                stack_snapshots=[Decimal("20"), Decimal("20")],
                instance_id="d1",
            )
        ]

    await _save_combat(database, initial, add_dot)
    current = await service.resume(actor)
    assert current is not None
    antidote = await service.consumable_selection(
        actor,
        current.activity_id,
        current.combat.version,
        screen="choose_item",
        item_id=item_id,
    )
    assert antidote is not None and antidote.consumable_screen is None
    assert antidote.ready_consumable_option.effect_id == "d1"
    assert await _stack_quantity(database, actor, item_id) == 1


@pytest.mark.asyncio
async def test_postgres_dissipator_event_remains_stable_after_reapplication_and_reconnect(database):
    actor = 770705
    item_id = "consumable.dispeller.iii"
    service, initial = await _combat(database, actor, {item_id: 1})

    def add_buff(combat):
        combat.enemy_actions["rally"] = Action("rally", "Brado de Guerra", Decimal(0))
        enemy = combat.fighters["enemy"]
        enemy.effects = [
            Effect(
                "rally",
                "attack",
                Decimal("0.1"),
                3,
                enemy.opportunity,
                kind="buff",
                instance_id="rally-original",
            )
        ]

    await _save_combat(database, initial, add_buff)
    selected = await service.resume(actor)
    assert selected is not None and selected.kind == "combat"
    assert any(
        option.item_id == item_id
        and option.target_id == "enemy"
        and option.effect_id == "rally-original"
        for option in selected.consumable_options
    )

    used = await service.action(
        actor,
        selected.activity_id,
        selected.combat.version,
        consumable_id=item_id,
        target_id="enemy",
        effect_id="rally-original",
    )
    assert used is not None and used.kind == "combat"
    recorded = next(
        event for event in used.combat.events if event.action == f"consumable:{item_id}"
    )
    assert recorded.effect_removal_kind == "effect"
    original_line = event_line(used.combat, recorded)
    assert original_line.endswith("✨ <b>Brado de Guerra</b> · Removido")
    assert await _stack_quantity(database, actor, item_id) == 0

    def reapply_same_buff(combat):
        enemy = combat.fighters["enemy"]
        enemy.effects.append(
            Effect(
                "rally",
                "attack",
                Decimal("0.1"),
                3,
                enemy.opportunity,
                kind="buff",
                instance_id="rally-reapplied",
            )
        )

    await _save_combat(database, used, reapply_same_buff)
    reconnected = await service.resume(actor)
    assert reconnected is not None and reconnected.kind == "combat"
    persisted_event = next(
        event for event in reconnected.combat.events if event.action == f"consumable:{item_id}"
    )
    assert persisted_event.effect_removal_kind == "effect"
    assert event_line(reconnected.combat, persisted_event) == original_line
    assert original_line.endswith("· Removido")
