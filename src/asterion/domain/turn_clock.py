"""Server-side turn clock shared by every combat mode.

The engine owns the deadline: it is stamped into the combat state when a player's
turn opens and checked on every action, so the Telegram layer cannot extend it.
Nothing here sleeps; time is only compared when something happens.
"""

import time
from collections.abc import Callable

TURN_SECONDS = 10

_clock: Callable[[], float] = time.time


def now() -> float:
    return _clock()


def set_clock(clock: Callable[[], float] | None) -> None:
    """Replace the clock (tests); ``None`` restores wall time."""
    global _clock
    _clock = clock or time.time


def whole_seconds(seconds: float | int | None) -> int:
    """Seconds shown to the player: rounded up, so a fresh turn reads 10 and 0 means over."""
    return 0 if seconds is None else max(0, int(seconds + 0.999))


def format_remaining(seconds: float | int | None) -> str:
    whole = whole_seconds(seconds)
    return f"{whole // 60:02d}:{whole % 60:02d}"


def format_turn_seconds(seconds: float | int | None) -> str:
    """Turn timer as the combat HUD shows it: ``10s`` down to ``0s``."""
    return f"{whole_seconds(seconds)}s"
