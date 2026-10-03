from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from sqlalchemy import select

from asterion.application.account import (
    AccountRejected,
    AccountService,
    finalize_due_character_deletions,
    notification_enabled,
)
from asterion.application.character_names import name_available
from asterion.application.character_surfaces import CharacterSurfacesService
from asterion.application.creation import CreationService
from asterion.application.world import WorldService
from asterion.bot.character_surfaces_handlers import character_surfaces_router
from asterion.bot.settings_handlers import settings_router
from asterion.bot.world_handlers import world_router
from asterion.domain.creation import NamePolicy
from asterion.infrastructure.db.models import (
    Account,
    Achievement,
    Character,
    CharacterDeletionRequest,
    CharacterNameReservation,
    CharacterNotificationPreference,
    CharacterPendingInput,
    CharacterProfile,
    CharacterRenameHistory,
    GameActivity,
)
from tests.test_character_surfaces_telegram import _button, _last_screen, _message_update
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road


def _service(sessions):
    return AccountService(sessions, "ocaso", NamePolicy())


@pytest.mark.asyncio
async def test_settings_notifications_are_sparse_persistent_and_stale_safe(database):
    actor = 893001
    await _seed_road(database, actor=actor)
    service = _service(database[1])

    default = await service.notification(actor, "essentials")
    assert default is not None and default.enabled and default.revision == 0
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert await notification_enabled(session, character.id, "essentials")
    disabled = await service.set_notification(
        actor,
        "essentials",
        expected_revision=0,
        expected_enabled=True,
        enabled=False,
    )
    assert disabled is not None and not disabled.enabled and disabled.revision == 1
    stale = await service.set_notification(
        actor,
        "essentials",
        expected_revision=0,
        expected_enabled=True,
        enabled=False,
    )
    assert stale == disabled
    enabled = await service.set_notification(
        actor,
        "essentials",
        expected_revision=1,
        expected_enabled=False,
        enabled=True,
    )
    assert enabled is not None and enabled.enabled and enabled.revision == 2
    async with database[1]() as session:
        rows = list((await session.scalars(select(CharacterNotificationPreference))).all())
    assert len(rows) == 1 and rows[0].enabled and rows[0].revision == 2


@pytest.mark.asyncio
async def test_rename_preview_commit_reservation_cooldown_and_duplicate_callback(database):
    actor = 893002
    await _seed_road(database, actor=actor)
    sessions = database[1]
    now = datetime.now(UTC)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.crowns = 5000

    service = _service(sessions)
    await service.begin_rename(actor, 9901, now=now)
    preview = await service.preview_rename(actor, 9901, 1234, "Nova", now=now)
    assert preview.status == "preview" and preview.new_name == "Nova"
    async with sessions() as session:
        assert await name_available(session, server_id="ocaso", name="Nova", now=now)

    assert await service.confirm_rename(actor, preview.revision, now=now) == "Nova"
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        reservation = await session.get(CharacterNameReservation, ("ocaso", "heroa"))
        history = await session.scalar(
            select(CharacterRenameHistory).where(
                CharacterRenameHistory.character_id == character.id
            )
        )
    assert character.name == "Nova" and character.crowns == 2500
    assert reservation is not None and reservation.source == "rename"
    assert reservation.reserved_until == now + timedelta(days=30)
    assert history.old_name == "Heroa" and history.new_name == "Nova"
    with pytest.raises(AccountRejected, match="stale_preview"):
        await service.confirm_rename(actor, preview.revision, now=now)
    view = await service.account(actor, now=now)
    assert view is not None and view.rename_available_at == now + timedelta(days=30)
    async with sessions() as session:
        assert not await name_available(session, server_id="ocaso", name="Heroa", now=now)


@pytest.mark.asyncio
async def test_rename_revalidates_policy_crowns_reservation_and_foreground(database):
    actor = 893003
    await _seed_road(database, actor=actor)
    sessions = database[1]
    service = _service(sessions)
    now = datetime.now(UTC)
    await service.begin_rename(actor, 9902, now=now)
    invalid = await service.preview_rename(actor, 9902, 1235, "No!", now=now)
    assert invalid.status == "invalid"
    await service.begin_rename(actor, 9903, now=now)
    preview = await service.preview_rename(actor, 9903, 1236, "Other", now=now)
    assert preview.status == "preview"
    with pytest.raises(AccountRejected, match="insufficient_crowns"):
        await service.confirm_rename(actor, preview.revision, now=now)

    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.crowns = 2500
        session.add(
            GameActivity(
                character_id=character.id,
                content_id="test_active_foreground",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    with pytest.raises(AccountRejected, match="foreground"):
        await service.confirm_rename(actor, preview.revision, now=now)
    with pytest.raises(AccountRejected, match="foreground"):
        await service.start_deletion_confirmation(actor, now=now)


@pytest.mark.asyncio
async def test_pending_deletion_cancel_and_stale_preview_are_safe(database):
    actor = 893004
    await _seed_road(database, actor=actor)
    service = _service(database[1])
    now = datetime.now(UTC)

    confirmation = await service.start_deletion_confirmation(actor, now=now)
    assert confirmation.deletion_preview_id is not None
    result = await service.request_deletion(
        actor, confirmation.name, confirmation.deletion_preview_id, now=now
    )
    assert result.pending and result.due_at == now + timedelta(days=7)
    assert await finalize_due_character_deletions(
        database[1], "ocaso", now=now + timedelta(days=6)
    ) == 0
    pending = await service.account(actor, now=now + timedelta(days=6))
    assert pending is not None and pending.deletion_pending
    assert await service.cancel_deletion(actor, result.revision, now=now + timedelta(days=6))
    repeated_cancel = await service.cancel_deletion(
        actor, result.revision, now=now + timedelta(days=6)
    )
    assert not repeated_cancel.changed
    with pytest.raises(AccountRejected, match="stale_confirmation"):
        await service.request_deletion(
            actor, confirmation.name, confirmation.deletion_preview_id, now=now + timedelta(days=6)
        )


@pytest.mark.asyncio
async def test_due_deletion_cleans_character_graph_and_reserves_final_name(database):
    actor = 893005
    await _seed_road(database, actor=actor)
    sessions = database[1]
    now = datetime.now(UTC)
    service = _service(sessions)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character_id = character.id
        session.add(
            CharacterProfile(
                character_id=character.id,
                history="A história fica até o prazo encerrar.",
            )
        )
        session.add(
            Achievement(character_id=character.id, achievement_id="feat.tdo.cinzas_na_estrada")
        )

    confirmation = await service.start_deletion_confirmation(actor, now=now)
    pending = await service.request_deletion(
        actor, confirmation.name, confirmation.deletion_preview_id, now=now
    )
    due = pending.due_at
    assert due is not None
    assert (
        await finalize_due_character_deletions(
            sessions, "ocaso", now=due - timedelta(seconds=1)
        )
        == 0
    )
    assert await finalize_due_character_deletions(sessions, "ocaso", now=due) == 1
    assert await finalize_due_character_deletions(sessions, "ocaso", now=due) == 0

    async with sessions() as session:
        assert await session.get(Character, character_id) is None
        assert (
            await session.scalar(
                select(CharacterProfile).where(CharacterProfile.character_id == character_id)
            )
            is None
        )
        assert (
            await session.scalar(
                select(Achievement).where(Achievement.character_id == character_id)
            )
            is None
        )
        account = await session.get(Account, actor)
        reservation = await session.get(CharacterNameReservation, ("ocaso", "heroa"))
        request = await session.scalar(
            select(CharacterDeletionRequest).where(
                CharacterDeletionRequest.character_id == character_id
            )
        )
        assert account is not None
        assert reservation is not None and reservation.source == "deletion"
        assert reservation.reserved_until == due + timedelta(days=30)
        assert request is not None and request.status == "completed"
        assert not await name_available(session, server_id="ocaso", name="Heroa", now=due)
        assert not await name_available(
            session, server_id="ocaso", name="Heroa", now=due + timedelta(days=29)
        )
        assert await name_available(
            session, server_id="ocaso", name="Heroa", now=due + timedelta(days=30)
        )
    creation = CreationService(sessions, "ocaso", NamePolicy())
    async with sessions.begin() as session:
        assert not await creation._name_allowed(session, "Heroa")


@pytest.mark.asyncio
async def test_cancelar_clears_persistent_transient_input_coordinator(database):
    actor = 893006
    await _seed_road(database, actor=actor)
    service = _service(database[1])
    now = datetime.now(UTC)
    await service.begin_rename(actor, 9904, now=now)
    assert await service.cancel_transient_inputs(actor)
    assert not await service.cancel_transient_inputs(actor)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert await session.get(CharacterPendingInput, character.id) is None


@pytest.mark.asyncio
async def test_settings_commands_navigation_and_no_noop_buttons(database):
    actor = 893007
    await _seed_road(database, actor=actor)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(
            Achievement(character_id=character.id, achievement_id="feat.tdo.cinzas_na_estrada")
        )
    account_service = _service(sessions)
    surfaces = CharacterSurfacesService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(settings_router(account_service, surfaces, {}))
    dispatcher.include_router(character_surfaces_router(surfaces, {}))
    dispatcher.include_router(world_router(WorldService(sessions, "ocaso"), {}))
    bot = Bot("123456:local-test-token")
    message_ids = iter(range(1200, 1250))

    async def telegram_response(_bot, method, **_kwargs):
        if isinstance(method, SendMessage):
            return TelegramMessage(
                message_id=next(message_ids),
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        if isinstance(method, EditMessageText):
            return TelegramMessage(
                message_id=method.message_id,
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        return True

    bot.session.make_request = AsyncMock(side_effect=telegram_response)
    update_id = 1
    await dispatcher.feed_raw_update(
        bot, _message_update("/menu", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    assert {button.text for row in screen.reply_markup.inline_keyboard for button in row} == {
        "Aventura",
        "Personagem",
        "Códice",
        "Configurações",
    }
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("world:adventure", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    assert "Eventos" not in screen.text and "PvP" not in screen.text
    assert "Caçadas" in screen.text and "Desbravar" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("settings:root", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    assert "Configurações" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("settings:notifications", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    assert "Essenciais" in screen.text
    toggle = _button(screen, "Desativar")
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update(toggle.callback_data, actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    assert "Silenciadas" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("help:root", actor=actor, update_id=update_id)
    )
    assert "🛟 Ajuda" in _last_screen(bot).text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, _message_update("/ajuda", actor=actor, update_id=update_id)
    )
    assert "🛟 Ajuda" in _last_screen(bot).text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, _message_update("/perfil", actor=actor, update_id=update_id)
    )
    assert "📇 Perfil" in _last_screen(bot).text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, _message_update("/cancelar", actor=actor, update_id=update_id)
    )
    assert "Não há entrada cancelável" in _last_screen(bot).text
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        active = GameActivity(
            character_id=character.id,
            content_id="test_query_commands_keep_foreground",
            status="active",
            state_version=0,
            ruleset_version="test",
        )
        session.add(active)
        await session.flush()
        activity_id = active.id
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, _message_update("/ajuda", actor=actor, update_id=update_id)
    )
    assert "🛟 Ajuda" in _last_screen(bot).text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, _message_update("/perfil", actor=actor, update_id=update_id)
    )
    assert "📇 Perfil" in _last_screen(bot).text
    async with sessions() as session:
        active_after_queries = await session.get(GameActivity, activity_id)
        assert active_after_queries is not None and active_after_queries.status == "active"
    for call in bot.session.make_request.call_args_list:
        method = call.args[1]
        markup = getattr(method, "reply_markup", None)
        for row in getattr(markup, "inline_keyboard", ()):
            for button in row:
                assert button.callback_data != "menu:noop"
                assert len(button.callback_data.encode()) < 64
    await bot.session.close()


@pytest.mark.asyncio
async def test_menu_explains_missing_character_after_account_cleanup(database):
    actor = 893009
    sessions = database[1]
    service = _service(sessions)
    surfaces = CharacterSurfacesService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(settings_router(service, surfaces, {}))
    bot = Bot("123456:local-test-token")
    responses = iter(range(1400, 1410))

    async def telegram_response(_bot, method, **_kwargs):
        if isinstance(method, SendMessage):
            return TelegramMessage(
                message_id=next(responses),
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        return True

    bot.session.make_request = AsyncMock(side_effect=telegram_response)
    await dispatcher.feed_raw_update(bot, _message_update("/menu", actor=actor, update_id=90))
    assert "Use /start para começar" in _last_screen(bot).text
    await bot.session.close()


@pytest.mark.asyncio
async def test_start_and_menu_show_pending_deletion_until_cancelled(database):
    actor = 893008
    await _seed_road(database, actor=actor)
    service = _service(database[1])
    now = datetime.now(UTC)
    confirmation = await service.start_deletion_confirmation(actor, now=now)
    await service.request_deletion(
        actor, confirmation.name, confirmation.deletion_preview_id, now=now
    )
    surfaces = CharacterSurfacesService(database[1], "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(settings_router(service, surfaces, {}))
    bot = Bot("123456:local-test-token")
    responses = iter(range(1300, 1320))

    async def telegram_response(_bot, method, **_kwargs):
        if isinstance(method, SendMessage):
            return TelegramMessage(
                message_id=next(responses),
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        return True

    bot.session.make_request = AsyncMock(side_effect=telegram_response)
    await dispatcher.feed_raw_update(bot, _message_update("/start", actor=actor, update_id=80))
    screen = _last_screen(bot)
    assert "Exclusão Pendente" in screen.text
    back_to_account = _button(screen, "← Conta")
    await dispatcher.feed_raw_update(
        bot, callback_update(back_to_account.callback_data, actor=actor, update_id=81)
    )
    account_screen = _last_screen(bot)
    assert "👤 Conta" in account_screen.text and "Exclusão Pendente" in account_screen.text
    follow_pending = _button(account_screen, "Acompanhar Exclusão")
    await dispatcher.feed_raw_update(
        bot, callback_update(follow_pending.callback_data, actor=actor, update_id=82)
    )
    screen = _last_screen(bot)
    cancel = _button(screen, "Cancelar Exclusão")
    await dispatcher.feed_raw_update(
        bot, callback_update(cancel.callback_data, actor=actor, update_id=83)
    )
    screen = _last_screen(bot)
    assert "Conta" in screen.text and "Exclusão Pendente" not in screen.text
    await bot.session.close()
