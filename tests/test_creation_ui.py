import json
import re
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import EditMessageText, SendPhoto

from asterion.bot.creation_handlers import creation_router, present
from asterion.bot.creation_ui import COPY, PROLOGUE_TEXT, CreationCallback, render
from asterion.domain.creation import CLASSES, PROLOGUE, RACES, Creation


def test_all_copy_matches_authoritative_spec_verbatim():
    spec = Path("docs/specs/CHARACTER_CREATION_UI.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```text\n(.*?)\n```", spec, re.S)
    expected = [
        "\n".join(line for line in block.splitlines() if not line.startswith("[")).strip()
        for block in blocks
    ]
    assert list(COPY.values()) == expected
    assert len(COPY) == 17


@pytest.mark.parametrize(
    "step",
    ["name", "race", "class", "confirm", PROLOGUE]
    + [f"race:{race}" for race in RACES]
    + [f"class:{cls}" for cls in CLASSES],
)
def test_render_all_pages_with_telegram_limits_and_no_image_placeholders(step):
    screen = render(
        Creation(
            uuid4(),
            version=2_147_483_647,
            step=step,
            name="Luiken",
            race="remanescente",
            character_class="errante",
        )
    )
    assert len(screen.text.encode("utf-16-le")) // 2 <= 1024
    assert "[Imagem" not in screen.text
    assert "Guilda" not in screen.text and "Aparência" not in screen.text
    if screen.keyboard:
        for row in screen.keyboard.inline_keyboard:
            for button in row:
                assert len(button.callback_data.encode()) <= 64
                if step != PROLOGUE:
                    data = CreationCallback.unpack(button.callback_data)
                    assert data.version == 2_147_483_647


def test_name_errors_and_confirmation_exact_copy():
    base = Creation(uuid4(), name="Luiken", race="remanescente", character_class="errante")
    assert render(base).text == COPY["name"]
    assert render(replace(base, error="format")).text == COPY["format"]
    assert (
        render(replace(base, error="unavailable", rejected_name="Luiken")).text
        == (COPY["unavailable"])
    )
    confirm = render(replace(base, step="confirm"))
    assert confirm.text == COPY["confirm"]
    assert [[button.text for button in row] for row in confirm.keyboard.inline_keyboard] == [
        ["Confirmar Personagem"],
        ["Nome", "Raça", "Classe"],
        ["← Classes"],
    ]
    assert "Caminhos" not in confirm.text


@pytest.mark.parametrize("race", RACES)
@pytest.mark.parametrize("cls", CLASSES)
def test_confirmation_uses_selected_race_passive_and_class(race, cls):
    screen = render(
        Creation(
            uuid4(),
            step="confirm",
            name="Aster",
            race=race,
            character_class=cls,
        )
    )
    passive = next(line for line in COPY[f"race:{race}"].splitlines() if "Passiva Racial" in line)
    assert passive in screen.text
    assert COPY[f"class:{cls}"].splitlines()[0].split(" ", 1)[1] in screen.text
    assert "🏷️ Nome · Aster" in screen.text


async def test_present_optional_media_text_only_and_message_edits():
    message = AsyncMock()
    message.photo = None
    screen = render(Creation(uuid4(), step="race"))
    await present(message, screen, {})
    message.answer.assert_awaited_once_with(
        screen.text,
        reply_markup=screen.keyboard,
        parse_mode=None,
    )
    assert not message.answer_photo.called
    await present(message, screen, {}, edit=True)
    message.edit_text.assert_awaited_once()
    await present(message, screen, {"race": "official-telegram-file-id"}, edit=True)
    message.edit_media.assert_awaited_once()
    media = message.edit_media.call_args.args[0]
    assert media.media == "official-telegram-file-id" and media.caption == screen.text


@pytest.mark.parametrize("reason", ["message to edit not found", "message can't be edited"])
async def test_uneditable_message_falls_back_without_losing_state(reason):
    message = AsyncMock()
    message.photo = None
    message.edit_text.side_effect = TelegramBadRequest(
        method=EditMessageText(text="x"),
        message=reason,
    )
    await present(message, render(Creation(uuid4(), step="race")), {}, edit=True)
    message.answer.assert_awaited_once()


async def test_unchanged_message_does_not_send_duplicate():
    message = AsyncMock()
    message.photo = None
    message.edit_text.side_effect = TelegramBadRequest(
        method=EditMessageText(text="x"),
        message="message is not modified",
    )
    await present(message, render(Creation(uuid4(), step="race")), {}, edit=True)
    assert not message.answer.called


async def test_missing_official_file_uses_text_fallback():
    message = AsyncMock()
    screen = render(Creation(uuid4()))
    await present(
        message,
        screen,
        {"name": "file:tests/__missing_official_image_for_fallback_test__.png"},
    )
    message.answer.assert_awaited_once()
    assert not message.answer_photo.called


@pytest.mark.parametrize("edit", [False, True])
async def test_unavailable_telegram_asset_uses_text_fallback(edit):
    message = AsyncMock()
    message.photo = None
    error = TelegramBadRequest(
        method=SendPhoto(chat_id=1, photo="unavailable-file-id"),
        message="wrong file identifier/HTTP URL specified",
    )
    message.edit_media.side_effect = error
    message.answer_photo.side_effect = error
    screen = render(Creation(uuid4()))
    await present(message, screen, {"name": "unavailable-file-id"}, edit=edit)
    message.answer.assert_awaited_once_with(
        screen.text,
        reply_markup=screen.keyboard,
        parse_mode=None,
    )


def message_update(text, update_id=1, actor=10, chat_type="private"):
    return {
        "update_id": update_id,
        "message": {
            "message_id": 100,
            "date": 1,
            "from": {"id": actor, "is_bot": False, "first_name": "Player"},
            "chat": {"id": actor, "type": chat_type},
            "text": text,
            "entities": [{"type": "bot_command", "offset": 0, "length": 6}]
            if text == "/start"
            else [],
        },
    }


def callback_update(data, update_id=2, actor=10):
    message = message_update("bot screen", actor=actor)["message"]
    message["from"] = {"id": 123456, "is_bot": True, "first_name": "Asterion"}
    return {
        "update_id": update_id,
        "callback_query": {
            "id": str(update_id),
            "from": {"id": actor, "is_bot": False, "first_name": "P"},
            "chat_instance": "device-independent",
            "data": data,
            "message": message,
        },
    }


@pytest.fixture
def telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


async def test_real_dispatcher_uses_sender_and_backend_state(telegram):
    service = AsyncMock()
    state = Creation(uuid4())
    service.start.return_value = state
    service.name.return_value = replace(state, step="race")
    service.callback.return_value = replace(state, step="race:remanescente")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(creation_router(service, {}))
    await dispatcher.feed_raw_update(telegram, message_update("/start"))
    service.start.assert_awaited_once_with(10)
    await dispatcher.feed_raw_update(telegram, message_update("Luiken", 2))
    service.name.assert_awaited_once_with(10, "Luiken", 2)
    data = CreationCallback(draft=state.id.hex, version=7, action="r0").pack()
    await dispatcher.feed_raw_update(telegram, callback_update(data))
    service.callback.assert_awaited_once_with(10, state.id, 7, "r0")
    service.reset_mock()
    await dispatcher.feed_raw_update(telegram, message_update("/start", chat_type="group"))
    assert not service.start.called
    for malformed in ("cc:broken", "cc:no-uuid:1:r0", "cc:bad:negative:r0"):
        await dispatcher.feed_raw_update(telegram, callback_update(malformed))
    assert not service.callback.called


async def test_dispatcher_start_restores_each_persistent_screen(service, telegram):
    from tests.test_creation_persistence import click

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(creation_router(service, {}))
    state = await service.start(10)
    for action in (None, "name-input", "r2", "choose", "c3", "choose", "confirm"):
        if action == "name-input":
            state = await service.name(10, "Luiken", 1)
        elif action:
            state = await click(service, 10, state, action)
        telegram.session.make_request.reset_mock()
        await dispatcher.feed_raw_update(telegram, message_update("/start"))
        sent = telegram.session.make_request.call_args.args[1]
        assert sent.text == render(state).text
    assert state.step == PROLOGUE


async def test_telegram_failure_after_commit_is_recoverable(service, telegram):
    from tests.test_creation_persistence import ready

    state = await ready(service, 10)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(creation_router(service, {}))
    data = CreationCallback(draft=state.id.hex, version=state.version, action="confirm").pack()
    telegram.session.make_request.side_effect = TelegramForbiddenError(
        method=EditMessageText(text="x"),
        message="bot blocked",
    )
    with pytest.raises(TelegramForbiddenError):
        await dispatcher.feed_raw_update(telegram, callback_update(data))
    assert (await service.start(10)).step == PROLOGUE
    telegram.session.make_request.side_effect = None
    await dispatcher.feed_raw_update(telegram, message_update("/start"))
    assert telegram.session.make_request.call_args.args[1].text == PROLOGUE_TEXT


def test_packaged_copy_is_valid_json():
    assert (
        json.loads(Path("src/asterion/bot/creation_copy.json").read_text(encoding="utf-8")) == COPY
    )
