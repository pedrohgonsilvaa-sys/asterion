"""Regressão: o HUD de combate com cronômetro não pisca nem regride.

Causas cobertas (ver o relatório da correção):
- a ação do jogador e o cronômetro editavam a mesma mensagem sem ordem: duas escritas
  em voo ao mesmo tempo e uma leitura antiga podia sobrescrever a mais nova;
- após cada ação o cronômetro reiniciava e reenviava exatamente o mesmo texto;
- em PvE sem encontro a arte era sorteada a cada render e trocava a foto a cada ação.
"""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from aiogram.types import InlineKeyboardMarkup

from asterion.bot import creation_handlers
from asterion.bot.combat_timer import SKIPPED, CombatTicker, Tick, fingerprint, ticker
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.prologue_ui import turn_line
from asterion.domain import turn_clock
from asterion.domain.combat import turn_seconds_left


class Clock:
    def __init__(self):
        self.now = 2_000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(_frozen_turn_clock):
    fake = Clock()
    turn_clock.set_clock(fake)
    return fake


@pytest.fixture
def ids():
    """Unique chat/message ids so the process-wide ticker never shares state between tests."""
    return SimpleNamespace(chat=uuid4().int % 10**9, message=uuid4().int % 10**6)


def _screen(text: str, timer: str | None = None) -> Screen:
    return Screen(text, "combat", InlineKeyboardMarkup(inline_keyboard=[]), timer=timer)


class CaptionBot:
    """Records every caption that reaches Telegram and how many edits overlap."""

    def __init__(self, latency: float = 0.0):
        self.captions: list[str] = []
        self.inflight = 0
        self.max_inflight = 0
        self.latency = latency

    async def edit_message_caption(self, *, caption, **_):
        self.inflight += 1
        self.max_inflight = max(self.max_inflight, self.inflight)
        if self.latency:
            await asyncio.sleep(self.latency)
        self.captions.append(caption)
        self.inflight -= 1


def _no_duplicate_in_a_row(items: list[str]) -> bool:
    return all(a != b for a, b in zip(items, items[1:], strict=False))


async def test_countdown_restart_after_an_action_does_not_resend_the_same_hud(clock, ids):
    """The action's render is already on the message; the restarted countdown must not repeat it."""
    state = SimpleNamespace(result=None, turn_deadline=clock.now + 10)
    bot = CaptionBot()
    ticker_under_test = CombatTicker(sleep=lambda s: _advance(clock, s))
    key = (ids.chat, ids.message)
    hud = turn_line(1, 10)

    # The action's own render, drawn at 10s before the countdown restarts.
    await ticker_under_test.write(
        *key, ticker_under_test.begin(), _screen(hud), lambda: _caption(bot, hud)
    )

    ticks = {"n": 0}

    async def refresh():
        ticks["n"] += 1
        if ticks["n"] > 1:
            return None
        return Tick(_screen(turn_line(1, turn_seconds_left(state))), state)

    await ticker_under_test._run(bot, *key, refresh, _never_expire)

    assert bot.captions.count(hud) == 1, "the restarted countdown resent the action's HUD"
    assert _no_duplicate_in_a_row(bot.captions)


async def test_stale_countdown_read_cannot_overwrite_a_newer_action_render(clock, ids):
    ticker_under_test = CombatTicker()
    bot = CaptionBot()
    key = (ids.chat, ids.message)

    stale_ticket = ticker_under_test.begin()  # countdown read started before the action
    fresh_ticket = ticker_under_test.begin()  # the action's render (read after commit)

    newer = await ticker_under_test.write(
        *key, fresh_ticket, _screen("v2 · 7s"), lambda: _caption(bot, "v2 · 7s")
    )
    stale = await ticker_under_test.write(
        *key, stale_ticket, _screen("v1 · 3s"), lambda: _caption(bot, "v1 · 3s")
    )

    assert newer is True
    assert stale is SKIPPED
    assert bot.captions == ["v2 · 7s"]


async def test_writes_to_one_message_never_overlap_in_telegram(ids):
    ticker_under_test = CombatTicker()
    bot = CaptionBot(latency=0.01)
    key = (ids.chat, ids.message)
    older = ticker_under_test.begin()
    newer = ticker_under_test.begin()

    await asyncio.gather(
        ticker_under_test.write(*key, older, _screen("old"), lambda: _caption(bot, "old")),
        ticker_under_test.write(*key, newer, _screen("new"), lambda: _caption(bot, "new")),
    )

    assert bot.max_inflight == 1, "two edits of the same message were in flight at once"
    assert bot.captions[-1] == "new"


async def test_countdown_edits_only_when_the_turn_changes(clock, ids):
    """No per-second edits: the watch sleeps to the deadline and redraws on turn change."""
    state = SimpleNamespace(result=None, turn_deadline=clock.now + 10, turn=1)
    bot = CaptionBot()
    ticker_under_test = CombatTicker(sleep=lambda s: _advance(clock, s))
    key = (ids.chat, ids.message)
    expired: list[int] = []

    async def refresh():
        if state.turn > 2:
            return None
        return Tick(_screen(turn_line(state.turn)), state)

    async def expire():
        expired.append(state.turn)
        state.turn += 1
        state.turn_deadline = clock.now + 10

    await ticker_under_test._run(bot, *key, refresh, expire)

    assert expired == [1, 2]
    assert bot.captions == [turn_line(1), turn_line(2)]
    assert bot.max_inflight == 1


async def test_present_redraws_on_every_tap_like_before(ids):
    """Callbacks keep their contract: a tap (even a stale one) redraws the current HUD."""
    message = _FakeMessage(ids)
    screen = _screen(turn_line(1, 10), timer="prologue:" + uuid4().hex)

    await present(message, screen, {}, edit=True)
    await present(message, screen, {}, edit=True)

    assert message.edits == [turn_line(1, 10), turn_line(1, 10)]


async def test_countdown_restart_after_present_does_not_repeat_the_hud(ids):
    """Action present, then the countdown restarts: its first tick must not resend the HUD."""
    message = _FakeMessage(ids)
    screen = _screen(turn_line(1, 10), timer=f"prologue:{uuid4().hex}")
    await present(message, screen, {}, edit=True)

    # The restarted countdown's first write is not forced (it only redraws on change).
    result = await ticker.write(
        ids.chat, ids.message, ticker.begin(), screen,
        lambda: _caption_text(message, "repeated"),
    )

    assert result is SKIPPED
    assert message.edits == [turn_line(1, 10)]


async def test_present_does_not_regress_to_an_older_read(ids):
    message = _FakeMessage(ids)
    stale_ticket = ticker.begin()
    activity = uuid4().hex

    await present(message, _screen("Turno 2", timer=f"prologue:{activity}"), {}, edit=True)
    await ticker.write(
        ids.chat, ids.message, stale_ticket, _screen("Turno 1"),
        lambda: _caption_text(message, "Turno 1"),
    )

    assert message.edits == ["Turno 2"]


async def test_timed_combat_keeps_one_picture_for_the_whole_activity(tmp_path, monkeypatch):
    """Without a seed each action re-drew a random variant (a photo swap every action)."""
    art = tmp_path / "combat"
    art.mkdir()
    for index in range(8):
        (art / f"var{index}.png").write_bytes(b"png")
    monkeypatch.setenv("ASTERION_ASSETS_DIR", str(tmp_path))

    async def no_persisted_file_id(_path):
        return None

    monkeypatch.setattr(creation_handlers, "_load_persisted_file_id", no_persisted_file_id)
    images = {"combat": "file:combat/*.png"}
    chat = SimpleNamespace(type="private", id=1)
    timed = _screen("Turno 1", timer=f"road:{uuid4().hex}")

    paths = set()
    for _ in range(6):
        _media, _key, path = await creation_handlers._screen_media(timed, images, chat)
        paths.add(path)

    assert len(paths) == 1


# ---- helpers -------------------------------------------------------------


async def _advance(clock, seconds):
    clock.now += seconds
    await asyncio.sleep(0)


async def _never_expire():
    raise AssertionError("the turn should not time out in this test")


async def _caption(bot: CaptionBot, text: str):
    await bot.edit_message_caption(caption=text, reply_markup=None)
    return True


async def _caption_text(message, text: str):
    message.edits.append(text)
    return message.message_id


class _FakeMessage:
    """Just enough of aiogram's Message for ``present`` on a text-only combat HUD."""

    def __init__(self, ids):
        self.chat = SimpleNamespace(id=ids.chat, type="private")
        self.message_id = ids.message
        self.photo = None
        self.bot = None
        self.edits: list[str] = []

    async def edit_text(self, text, **_):
        self.edits.append(text)
        return self


def test_fingerprint_changes_with_text_and_keyboard_only():
    assert fingerprint(_screen("a")) == fingerprint(_screen("a"))
    assert fingerprint(_screen("a")) != fingerprint(_screen("b"))
