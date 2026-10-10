from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage

from asterion.application.groups import (
    GroupMemberView,
    GroupService,
    GroupView,
    IncomingInviteView,
)
from asterion.application.world import WorldView
from asterion.bot.groups_handlers import groups_router
from asterion.bot.groups_ui import render_group, render_invites, render_links
from asterion.bot.world_ui import render_world
from tests.test_character_surfaces_telegram import _last_screen, _message_update
from tests.test_creation_ui import callback_update
from tests.test_groups import _seed_characters


def _callbacks(screen):
    return [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]


def test_vinculos_menu_exposes_group_without_root_group_button():
    view = WorldView(
        kind="menu",
        character_id=uuid4(),
        name="Aster",
        race="remanescente",
        character_class="sentinela",
        hp=100,
        max_hp=100,
        vigor=100,
        max_vigor=100,
        xp=0,
        region="Terras do Ocaso",
        location="Refúgio do Ocaso",
        quest_title=None,
    )
    screen = render_world(view)
    assert "Vínculos" in {button.text for row in screen.keyboard.inline_keyboard for button in row}
    assert "Grupo" not in {button.text for row in screen.keyboard.inline_keyboard for button in row}
    assert "links:root" in _callbacks(screen)


def test_group_screens_have_only_compact_callbacks_and_named_back_paths():
    member_id = uuid4()
    group = GroupView(
        group_id=uuid4(),
        revision=2_147_483_647,
        leader_character_id=member_id,
        is_leader=True,
        members=(
            GroupMemberView(
                character_id=member_id,
                name="Aster",
                level=60,
                character_class="sentinela",
                joined_at=datetime.now(UTC),
                is_leader=True,
            ),
            GroupMemberView(
                character_id=uuid4(),
                name="Companheiro",
                level=4,
                character_class="luminar",
                joined_at=datetime.now(UTC),
                is_leader=False,
            ),
        ),
    )
    screens = (
        render_links(group, 2),
        render_group(None),
        render_group(group),
        render_invites(
            (
                IncomingInviteView(
                    invite_id=uuid4(),
                    revision=2_147_483_647,
                    group_id=uuid4(),
                    group_leader_name="Aster",
                    inviter_name="Aster",
                    expires_at=datetime.now(UTC),
                ),
            )
        ),
    )
    for screen in screens:
        assert _callbacks(screen)
        assert all(len(callback.encode("utf-8")) <= 64 for callback in _callbacks(screen))
    group_buttons = {
        button.text for row in screens[2].keyboard.inline_keyboard for button in row
    }
    invite_buttons = {
        button.text for row in screens[3].keyboard.inline_keyboard for button in row
    }
    assert "← Vínculos" in group_buttons
    assert "← Grupo" in invite_buttons


@pytest.mark.asyncio
async def test_group_telegram_create_and_stale_leave_refresh(database):
    actors = await _seed_characters(database)
    actor = actors["Alpha"]
    sessions = database[1]
    service = GroupService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(groups_router(service, {}))
    bot = Bot("123456:local-test-token")
    response_ids = iter(range(1200, 1220))

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
    await dispatcher.feed_raw_update(
        bot, _message_update("/grupo", actor=actor, update_id=1)
    )
    screen = _last_screen(bot)
    assert "Crie um Grupo persistente" in screen.text

    await dispatcher.feed_raw_update(
        bot, callback_update("group:create", actor=actor, update_id=2)
    )
    screen = _last_screen(bot)
    assert "Grupo · 1/4" in screen.text
    leave_button = next(
        button
        for row in screen.reply_markup.inline_keyboard
        for button in row
        if button.text == "Sair do Grupo"
    )

    group = await service.group(actor)
    assert group is not None
    await service.invite(
        actor, "Bravo", expected_group_revision=group.revision
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(leave_button.callback_data, actor=actor, update_id=3)
    )
    screen = _last_screen(bot)
    assert "Ação Expirada" in screen.text
    assert await service.group(actor) is not None
