"""Bloco UI 1 §7: turno + timer real de 10 s, lido do prazo autoritativo do motor."""

from types import SimpleNamespace

import pytest
from aiogram.types import InlineKeyboardMarkup

from asterion.bot.combat_timer import TIMEOUT_ACTION, CombatTicker, Tick
from asterion.bot.creation_ui import Screen
from asterion.bot.prologue_ui import turn_line
from asterion.domain import turn_clock
from asterion.domain.combat import turn_seconds_left


class Clock:
    def __init__(self):
        self.now = 1_000.0

    def __call__(self):
        return self.now


class FakeBot:
    def __init__(self):
        self.captions: list[str] = []

    async def edit_message_caption(self, *, caption, **_):
        self.captions.append(caption)

    async def edit_message_text(self, *, text, **_):  # pragma: no cover - caption path
        self.captions.append(text)


@pytest.fixture
def clock(_frozen_turn_clock):
    fake = Clock()
    turn_clock.set_clock(fake)
    return fake


def test_turn_line_shows_only_the_turn_number():
    """The 10 s rule still applies, but the HUD no longer shows a countdown."""
    assert turn_line(1, None) == "🌐 <b>Turno 1</b>"
    assert turn_line(2, 8.6) == "🌐 <b>Turno 2</b>"
    assert turn_line(3, 0) == "🌐 <b>Turno 3</b>"
    assert turn_clock.format_turn_seconds(10) == "10s"


async def test_watch_sleeps_to_the_deadline_and_redraws_only_when_the_turn_changes(clock):
    """One timeout per expired turn; the HUD is edited on turn change, never per second."""
    state = SimpleNamespace(result=None, turn_deadline=clock.now + turn_clock.TURN_SECONDS)
    turn = {"n": 1}
    expired: list[int] = []
    sleeps: list[float] = []

    async def refresh():
        if turn["n"] > 2:
            state.result = "victory"
        text = turn_line(turn["n"], turn_seconds_left(state))
        return Tick(Screen(text, "combat", InlineKeyboardMarkup(inline_keyboard=[])), state)

    async def expire():
        expired.append(turn["n"])
        turn["n"] += 1
        state.turn_deadline = clock.now + turn_clock.TURN_SECONDS

    async def sleep(seconds):
        sleeps.append(seconds)
        clock.now += seconds

    bot = FakeBot()
    await CombatTicker(sleep=sleep)._run(bot, 1, 1, refresh, expire)

    assert expired == [1, 2]
    assert bot.captions == [turn_line(1, None), turn_line(2, None), turn_line(3, None)]
    assert sleeps[0] == pytest.approx(turn_clock.TURN_SECONDS + 0.05)


async def test_ticker_stops_when_combat_has_no_open_timed_turn(clock):
    state = SimpleNamespace(result=None, turn_deadline=None)
    calls = []

    async def refresh():
        calls.append(1)
        return Tick(Screen("x", "combat", None), state)

    async def expire():  # pragma: no cover - must not run
        raise AssertionError("no timeout without a deadline")

    bot = FakeBot()
    await CombatTicker(sleep=lambda _: None)._run(bot, 1, 1, refresh, expire)
    assert calls == [1] and bot.captions == ["x"]


def test_timeout_action_is_a_noop_while_turn_is_open_and_a_timeout_after(_frozen_turn_clock):
    """The countdown never forges a player choice: the engine decides by the deadline."""
    from uuid import uuid4

    from asterion.domain.combat import act
    from asterion.domain.combat_math import resolve_combat_stats
    from asterion.domain.prologue import PROFILE

    stats = resolve_combat_stats("vigia", 1, "velado")
    combat = PROFILE.create(uuid4(), "Heroa", "vigia", "velado", stats.hp)
    assert combat.turn_deadline is not None
    assert act(combat, TIMEOUT_ACTION).version == combat.version
    _frozen_turn_clock["t"] = combat.turn_deadline + 0.5
    timed_out = act(combat, TIMEOUT_ACTION)
    assert timed_out.version == combat.version + 1
    assert any(event.action == "hold" for event in timed_out.events)
