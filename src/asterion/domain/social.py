"""Vínculos limits and Relato text rules. Sources: GDD v1.6.0 §31, §31.1 and §49.18."""

from __future__ import annotations

from datetime import timedelta

from asterion.domain.market import contains_link

MAX_FRIENDS = 100
MAX_SENT_REQUESTS = 20
MAX_RECEIVED_REQUESTS = 30
MAX_RECENTS = 30
RECENT_WINDOW = timedelta(days=14)
MAX_BLOCKED = 100
SEARCH_LIMIT_PER_MINUTE = 20
SEARCH_WINDOW = timedelta(minutes=1)
MAX_STORY_CHARACTERS = 600
STORY_SHARE_COOLDOWN = timedelta(hours=6)

# Not game values: how many rows one Telegram screen shows and how short a name
# query may be before it stops being a search and becomes a listing of players.
PAGE_SIZE = 10
SEARCH_RESULT_LIMIT = 10
SEARCH_MIN_CHARACTERS = 2


def story_is_allowed(text: str) -> bool:
    """Author decision 2026-11-08: links and @mentions are refused when saving."""
    return not contains_link(text)


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
