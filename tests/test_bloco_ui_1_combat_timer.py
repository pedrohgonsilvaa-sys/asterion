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


def test_turn_line_keeps_turn_and_shows_seconds():
    assert turn_line(1, None) == "🌐 <b>Turno 1</b> · ⏱️ <code>10s</code>"
    assert turn_line(2, 9.2) == "🌐 <b>Turno 2</b> · ⏱️ <code>10s</code>"
    assert turn_line(2, 8.6) == "🌐 <b>Turno 2</b> · ⏱️ <code>9s</code>"
    assert turn_line(3, 0) == "🌐 <b>Turno 3</b> · ⏱️ <code>0s</code>"
    assert turn_clock.format_turn_seconds(10) == "10s"


async def test_ticker_counts_down_times_out_at_zero_and_restarts_next_turn(clock):
    """10s → 9s → … → 0s, timeout rule once, then Turno 2 back at 10s."""
    state = SimpleNamespace(result=None, turn_deadline=clock.now + turn_clock.TURN_SECONDS)
    turn = {"n": 1}
    expired: list[int] = []

    async def refresh():
        if turn["n"] > 2:
            state.result = "victory"
        text = turn_line(turn["n"], turn_seconds_left(state))
        return Tick(Screen(text, "combat", InlineKeyboardMarkup(inline_keyboard=[])), state)

    async def expire():
        # The engine's timeout: the overdue turn is spent and a fresh one opens.
        expired.append(turn["n"])
        turn["n"] += 1
        state.turn_deadline = clock.now + turn_clock.TURN_SECONDS

    async def sleep(seconds):
        clock.now += seconds

    bot = FakeBot()
    await CombatTicker(sleep=sleep)._run(bot, 1, 1, refresh, expire)

    first_turn = [c for c in bot.captions if "Turno 1" in c]
    shown = [c.rsplit("<code>", 1)[1].removesuffix("</code>") for c in first_turn]
    assert shown == [f"{n}s" for n in range(10, -1, -1)]
    assert expired == [1, 2]
    second_turn = [c for c in bot.captions if "Turno 2" in c]
    assert second_turn[0].endswith("<code>10s</code>")
    assert second_turn[-1].endswith("<code>0s</code>")


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
