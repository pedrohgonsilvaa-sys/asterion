import asyncio
from copy import deepcopy
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import EditMessageText
from sqlalchemy import select

from asterion.application.creation import CreationService
from asterion.application.prologue import PrologueService
from asterion.application.world import WorldService, WorldView
from asterion.bot.creation_handlers import creation_router
from asterion.bot.world_handlers import world_router
from asterion.bot.world_ui import render_world
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    Character,
    CombatRecord,
    GameActivity,
    Quest,
    WorldState,
)
from tests.test_creation_ui import callback_update, message_update
from tests.test_prologue_persistence import character, mark_legacy_defeat, win


def world_view(**changes):
    values = dict(
        kind="menu",
        character_id="00000000-0000-0000-0000-000000000001",
        name="Heroa",
        race="remanescente",
        character_class="sentinela",
        hp=Decimal("712.530"),
        max_hp=Decimal("712.530"),
        vigor=100,
        max_vigor=100,
        xp=320,
        region="Terras do Ocaso",
        location="Estrada das Cinzas",
        quest_title="Vozes na Estrada",
    )
    values.update(changes)
    return WorldView(**values)


def test_menu_is_authoritative_and_preserves_fractional_hp():
    text = render_world(world_view()).text
    assert "Terras do Ocaso · Estrada das Cinzas" in text
    assert "❤️ HP · 712.530 / 712.530" in text
    assert "⚡ Vigor · 100 / 100" in text
    assert "✨ XP · 320 / 4.800" in text
    assert "📜 Missão Principal · Vozes na Estrada" in text


def test_vigor_bar_is_derived_not_hardcoded():
    text = render_world(world_view(vigor=72)).text
    assert "⚡ Vigor · 72 / 100\n🟨🟨🟨🟨🟨🟨🟨⬜⬜⬜" in text


def test_brazier_screen_has_discovered_state_and_rest_only():
    screen = render_world(world_view(kind="brazier"))
    assert "🔥 Braseiro · Descoberto" in screen.text
    assert "Ativar Braseiro" not in screen.text
    assert [button.text for button in screen.keyboard.inline_keyboard[0]] == ["Descansar"]


def test_menu_does_not_invent_missing_quest():
    # Application refuses to construct this state from PostgreSQL without P1;
    # the renderer also requires the authoritative title explicitly.
    text = render_world(world_view(quest_title="Vozes na Estrada")).text
    assert "Vozes na Estrada" in text


async def test_victory_creates_only_brazier_and_world_state(database):
    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    view = await service.enter(1)
    view = await win(service, view)
    async with database[1]() as session:
        assert await session.scalar(select(Brazier)) is not None
        assert await session.scalar(select(WorldState)) is not None
        achievement = await session.scalar(select(Achievement))
        assert achievement is not None
        assert achievement.achievement_id == "feat.tdo.cinzas_na_estrada"
        assert await session.scalar(select(Quest)) is None


async def test_rest_creates_p1_and_achievement_once(database):
    await character(database)
    # Seed the post-victory boundary as a migration/backfill would.
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    service = WorldService(database[1], "ocaso")
    view = await service.rest(1)
    assert view is not None and view.kind == "menu"
    # §32.3: the Community invite is sent once, when the Menu opens for the first time.
    assert view.first_menu is True
    assert (await service.rest(1)).first_menu is False
    async with database[1]() as session:
        assert len((await session.scalars(select(Achievement))).all()) == 1
        assert len((await session.scalars(select(Quest))).all()) == 1


async def test_two_rest_calls_are_idempotent_and_both_reconstruct_menu(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    first, second = await asyncio.gather(
        WorldService(database[1], "ocaso").rest(1),
        WorldService(database[1], "ocaso").rest(1),
    )
    assert first is not None and second is not None
    assert first.kind == second.kind == "menu"
    async with database[1]() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        assert row.stage == "menu:ready" and row.vigor == 100 and row.xp == 0
        assert len((await session.scalars(select(Achievement))).all()) == 1
        assert len((await session.scalars(select(Quest))).all()) == 1
        assert len((await session.scalars(select(Brazier))).all()) == 1
        assert len((await session.scalars(select(WorldState))).all()) == 1


async def test_old_rest_callback_after_menu_does_not_heal(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    service = WorldService(database[1], "ocaso")
    await service.rest(1)
    async with database[1].begin() as session:
        row = await session.scalar(
            select(Character).where(Character.telegram_id == 1).with_for_update()
        )
        row.hp -= Decimal("10")
        vigor, xp = row.vigor, row.xp
    result = await service.rest(1)
    assert result is not None and result.kind == "menu"
    async with database[1]() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        assert row.hp < row.max_hp and row.vigor == vigor and row.xp == xp


async def test_rest_requires_persisted_brazier(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    result = await WorldService(database[1], "ocaso").rest(1)
    assert result is None
    async with database[1]() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        assert row.stage == "cinzas_na_estrada:ready_for_first_brazier"
        assert await session.scalar(select(Achievement)) is None
        assert await session.scalar(select(Quest)) is None


async def test_menu_without_p1_is_inconsistent(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "menu:ready"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
        session.add(Achievement(character_id=row.id, achievement_id="feat.tdo.cinzas_na_estrada"))
    assert await WorldService(database[1], "ocaso").resume(1) is None


@pytest.mark.parametrize(
    "legacy_ruleset",
    ("gdd-1.4.2-baseline-1.0", "gdd-1.4.3-baseline-1.0"),
)
async def test_active_legacy_combat_keeps_its_ruleset_until_safe_boundary(
    database, legacy_ruleset
):
    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    view = await service.enter(1)
    async with database[1].begin() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == view.activity_id)
        )
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        record = await session.scalar(select(CombatRecord))
        activity.ruleset_version = legacy_ruleset
        row.ruleset_version = legacy_ruleset
        legacy_snapshot = deepcopy(record.snapshot)
        legacy_snapshot.pop("evasion_streaks", None)
        for fighter in legacy_snapshot["fighters"].values():
            for stat in ("per", "crit", "evasion", "block"):
                fighter["stats"].pop(stat, None)
        for event in legacy_snapshot["events"]:
            event.pop("dodged", None)
            event.pop("blocked", None)
        record.snapshot = legacy_snapshot
    resumed = await service.resume(1)
    assert resumed is not None
    assert resumed.combat.ruleset == legacy_ruleset
    async with database[1]() as session:
        record = await session.scalar(select(CombatRecord))
        assert record.snapshot == legacy_snapshot
    for action in ("attack", "defend", "art"):
        resumed = await service.action(1, resumed.activity_id, resumed.combat.version, action)
    for _ in range(30):
        if resumed.combat.result:
            break
        resumed = await service.action(1, resumed.activity_id, resumed.combat.version, "attack")
    async with database[1]() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == view.activity_id)
        )
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        assert activity.ruleset_version == legacy_ruleset
        assert row.ruleset_version == "gdd-1.4.3-baseline-1.0"


async def test_dispatcher_start_and_menu_recover_brazier_then_menu(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    world = WorldService(database[1], "ocaso")
    dispatcher.include_router(world_router(world, {}))
    dispatcher.include_router(
        creation_router(CreationService(database[1], "ocaso"), {}, world=world)
    )
    await dispatcher.feed_raw_update(bot, message_update("/start", actor=1))
    sent = bot.session.make_request.call_args.args[1]
    assert "Depois da Cinza" in sent.text and "Descansar" not in str(sent.reply_markup)
    await dispatcher.feed_raw_update(bot, callback_update("pro:a:o1", actor=1, update_id=7))
    await dispatcher.feed_raw_update(bot, callback_update("pro:a:o2", actor=1, update_id=8))
    sent = bot.session.make_request.call_args.args[1]
    assert "Diante do Braseiro" in sent.text
    await dispatcher.feed_raw_update(bot, message_update("/menu", actor=1, update_id=2))
    sent = bot.session.make_request.call_args.args[1]
    assert "Diante do Braseiro" in sent.text
    await dispatcher.feed_raw_update(bot, callback_update("world:rest", actor=1, update_id=9))
    sent = bot.session.make_request.call_args.args[1]
    assert "não corresponde" in str(sent) or "Diante do Braseiro" in str(sent)
    await dispatcher.feed_raw_update(bot, callback_update("pro:f:o2", actor=1, update_id=10))
    sent = bot.session.make_request.call_args.args[1]
    assert "🔥 Braseiro · Descoberto" in sent.text and "Descansar" in str(sent.reply_markup)
    await world.rest(1)
    await dispatcher.feed_raw_update(bot, message_update("/start", actor=1, update_id=3))
    sent = bot.session.make_request.call_args.args[1]
    assert "🌑 Asterion" in sent.text and "Vozes na Estrada" in sent.text


async def test_start_and_menu_reconcile_legacy_prologue_defeat(database):
    await character(database)
    prologue = PrologueService(database[1], "ocaso", PROFILE)
    initial = await prologue.enter(1)
    await mark_legacy_defeat(initial, database)

    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    world = WorldService(database[1], "ocaso")
    dispatcher.include_router(world_router(world, {}, prologue=prologue))
    dispatcher.include_router(
        creation_router(
            CreationService(database[1], "ocaso"), {}, prologue=prologue, world=world
        )
    )

    await dispatcher.feed_raw_update(bot, message_update("/start", actor=1))
    sent = bot.session.make_request.call_args.args[1]
    assert "Depois da Cinza" in sent.text
    assert "320 XP" not in sent.text
    await world.choose_prologue(1, "PRO_choice_aftermath", "o1")
    await world.choose_prologue(1, "PRO_choice_first_fire", "o1")
    await dispatcher.feed_raw_update(bot, message_update("/menu", actor=1, update_id=2))
    sent = bot.session.make_request.call_args.args[1]
    assert "🔥 Braseiro · Descoberto" in sent.text

    async with database[1]() as session:
        assert (await session.scalar(select(GameActivity))).status == "completed"


async def test_telegram_failure_after_rest_commit_recovers_menu(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        row.xp = 320
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(
        side_effect=[
            True,
            TelegramForbiddenError(method=EditMessageText(text="x"), message="bot blocked"),
        ]
    )
    dispatcher = Dispatcher(disable_fsm=True)
    world = WorldService(database[1], "ocaso")
    dispatcher.include_router(world_router(world, {}))
    dispatcher.include_router(
        creation_router(CreationService(database[1], "ocaso"), {}, world=world)
    )
    await world.choose_prologue(1, "PRO_choice_aftermath", "o1")
    await world.choose_prologue(1, "PRO_choice_first_fire", "o1")
    with pytest.raises(TelegramForbiddenError):
        await dispatcher.feed_raw_update(bot, callback_update("world:rest", actor=1))
    async with database[1]() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        assert (
            row.stage == "menu:ready"
            and row.hp == row.max_hp
            and row.xp == 320
            and row.vigor == 100
        )
        assert len((await session.scalars(select(Achievement))).all()) == 1
        assert len((await session.scalars(select(Quest))).all()) == 1
    bot.session.make_request = AsyncMock(return_value=True)
    await dispatcher.feed_raw_update(bot, message_update("/start", actor=1, update_id=5))
    sent = bot.session.make_request.call_args.args[1]
    assert "🌑 Asterion" in sent.text
    await dispatcher.feed_raw_update(bot, message_update("/menu", actor=1, update_id=6))
    sent = bot.session.make_request.call_args.args[1]
    assert "🌑 Asterion" in sent.text and "Vozes na Estrada" in sent.text
    await dispatcher.feed_raw_update(bot, message_update("/menu", actor=1, update_id=4))
    sent = bot.session.make_request.call_args.args[1]
    assert "🌑 Asterion" in sent.text and "Vozes na Estrada" in sent.text
