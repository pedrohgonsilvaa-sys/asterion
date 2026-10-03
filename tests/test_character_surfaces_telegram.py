from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from sqlalchemy import select

from asterion.application.character_surfaces import CharacterSurfacesService
from asterion.application.p2 import CHARNECA_LOCATION_ID
from asterion.application.world import WorldService
from asterion.bot.character_surfaces_handlers import character_surfaces_router
from asterion.bot.world_handlers import world_router
from asterion.infrastructure.db.models import (
    Achievement,
    Character,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
)
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road


def _message_update(text, *, actor, update_id, reply_to=None):
    message = {
        "message_id": 801,
        "date": 1,
        "from": {"id": actor, "is_bot": False, "first_name": "Player"},
        "chat": {"id": actor, "type": "private"},
        "text": text,
        "entities": [],
    }
    if reply_to is not None:
        message["reply_to_message"] = reply_to
    return {"update_id": update_id, "message": message}


def _last_screen(bot):
    for call in reversed(bot.session.make_request.call_args_list):
        method = call.args[1]
        if isinstance(method, (SendMessage, EditMessageText)) and getattr(method, "text", None):
            return method
    raise AssertionError("Telegram did not receive a screen update")


def _button(screen, label):
    for row in screen.reply_markup.inline_keyboard:
        for button in row:
            if button.text == label:
                return button
    raise AssertionError(f"Button {label!r} not found in current Telegram screen")


def _check_callbacks(screen):
    for row in screen.reply_markup.inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode("utf-8")) < 64


@pytest.mark.asyncio
async def test_character_knowledge_telegram_navigation_and_history_reply(database):
    actor = 890201
    actor, _road = await _seed_road(database, actor=actor)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character_id = character.id
        session.add_all(
            [
                CodexEntry(character_id=character_id, entry_id="codex.history.antigos_asterianos"),
                CodexFragment(
                    character_id=character_id,
                    entry_id="codex.history.antigos_asterianos",
                    fragment_id="codex.fragment.bosque.estrutura_enterrada",
                ),
                LocationDiscovery(character_id=character_id, location_id=CHARNECA_LOCATION_ID),
                Achievement(character_id=character_id, achievement_id="feat.tdo.cinzas_na_estrada"),
            ]
        )

    service = CharacterSurfacesService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(character_surfaces_router(service, {}))
    dispatcher.include_router(world_router(WorldService(sessions, "ocaso"), {}))
    bot = Bot("123456:local-test-token")
    response_ids = iter(range(900, 920))

    async def telegram_response(_bot, method, **_kwargs):
        if isinstance(method, SendMessage):
            return TelegramMessage(
                message_id=next(response_ids),
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
    assert "Asterion" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot,
        callback_update("knowledge:codex", actor=actor, update_id=update_id),
    )
    screen = _last_screen(bot)
    assert "Códice" in screen.text
    assert "Mistérios e Fenômenos" not in screen.text
    _check_callbacks(screen)

    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("kb:c:h", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    assert "Antigos Asterianos" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot,
        callback_update("kb:e:antigos_asterianos", actor=actor, update_id=update_id),
    )
    screen = _last_screen(bot)
    assert "Estrutura enterrada" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(bot, callback_update("kb:b", actor=actor, update_id=update_id))
    screen = _last_screen(bot)
    assert "2 Criaturas Conhecidas" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("kb:br:tdo", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    dog_button = _button(screen, "2")
    update_id += 1
    await dispatcher.feed_raw_update(
        bot,
        callback_update(dog_button.callback_data, actor=actor, update_id=update_id),
    )
    screen = _last_screen(bot)
    assert "Cão Cinéreo" in screen.text and "Observado" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(bot, callback_update("kb:a", actor=actor, update_id=update_id))
    screen = _last_screen(bot)
    assert "Feitos" in screen.text
    category_button = _button(screen, "1")
    update_id += 1
    await dispatcher.feed_raw_update(
        bot,
        callback_update(category_button.callback_data, actor=actor, update_id=update_id),
    )
    screen = _last_screen(bot)
    assert "Cinzas na Estrada" in screen.text
    assert "A Última Guarda" not in screen.text
    _check_callbacks(screen)

    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("character:root", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    assert "Atributos" in screen.text and "Perfil" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot,
        callback_update("character:attributes", actor=actor, update_id=update_id),
    )
    screen = _last_screen(bot)
    assert "❤️ HP" in screen.text and "⚡ Vigor" in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("character:root", actor=actor, update_id=update_id)
    )
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("character:profile", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    assert "📇 Perfil" in screen.text
    assert "Guilda" not in screen.text and "Elo" not in screen.text and "Título" not in screen.text
    update_id += 1
    await dispatcher.feed_raw_update(
        bot, callback_update("profile:edit:0", actor=actor, update_id=update_id)
    )
    prompt = next(
        call.args[1]
        for call in reversed(bot.session.make_request.call_args_list)
        if isinstance(call.args[1], SendMessage)
    )
    prompt_message_id = max(900, next(response_ids) - 1)
    assert "Escreva a História" in (prompt.reply_markup.input_field_placeholder or "")
    update_id += 1
    reply = {
        "message_id": prompt_message_id,
        "date": 1,
        "from": {"id": 123456, "is_bot": True, "first_name": "Asterion"},
        "chat": {"id": actor, "type": "private"},
        "text": prompt.text,
    }
    await dispatcher.feed_raw_update(
        bot,
        _message_update(
            "Uma história <cinzenta> & livre", actor=actor, update_id=update_id, reply_to=reply
        ),
    )
    screen = _last_screen(bot)
    assert "Uma história &lt;cinzenta&gt; &amp; livre" in screen.text
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        from asterion.infrastructure.db.models import CharacterProfile

        profile = await session.get(CharacterProfile, character.id)
        assert profile.history == "Uma história <cinzenta> & livre"

    for call in bot.session.make_request.call_args_list:
        method = call.args[1]
        if getattr(method, "reply_markup", None) and getattr(
            method.reply_markup, "inline_keyboard", None
        ):
            _check_callbacks(type("ScreenProxy", (), {"reply_markup": method.reply_markup})())

    await bot.session.close()
