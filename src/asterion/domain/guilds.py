"""Pure Guild rules: names, TAGs, roles, permissions and §49.18 limits.

Sources: GDD Estrutural v1.6.0 §30, §44.1, §49.10, §49.18 and §55.5.
"""

from __future__ import annotations

import re
from datetime import timedelta
from enum import StrEnum

GUILD_NAME_RE = re.compile(r"^[A-Za-z]{3,16}$")
GUILD_TAG_RE = re.compile(r"^[A-Za-z]{3}$")

# §30 / §55.5: launch cap. §49.10: Alojamentos base 5 -> 7 -> 9 -> 10 -> 11 -> 12.
GUILD_MAX_MEMBERS = 12
LODGING_CAPACITY = (5, 7, 9, 10, 11, 12)

# §49.18
GUILD_SWITCH_COOLDOWN = timedelta(hours=12)
MAX_PENDING_APPLICATIONS = 3
MAX_NEW_APPLICATIONS_PER_WINDOW = 6
NEW_APPLICATIONS_WINDOW = timedelta(minutes=60)
SAME_GUILD_APPLICATION_INTERVAL = timedelta(minutes=10)


class GuildRole(StrEnum):
    LEADER = "leader"
    OFFICER = "officer"
    MEMBER = "member"


class Recruitment(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class GuildNameError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def normalize_guild_name(raw: str) -> str:
    """Return the display name; uniqueness compares it case-insensitively."""
    name = raw.strip()
    if not GUILD_NAME_RE.fullmatch(name):
        raise GuildNameError("invalid_name")
    return name


def normalize_guild_tag(raw: str) -> str:
    tag = raw.strip()
    if not GUILD_TAG_RE.fullmatch(tag):
        raise GuildNameError("invalid_tag")
    return tag.upper()


def capacity_for_lodging(level: int) -> int:
    if not 0 <= level < len(LODGING_CAPACITY):
        raise ValueError("lodging level must be 0..5")
    return LODGING_CAPACITY[level]


def accepts_entry(member_count: int, capacity: int) -> bool:
    """A full or over-cap Guild accepts nobody (§30.1)."""
    return member_count < capacity


def is_over_cap(member_count: int, capacity: int) -> bool:
    return member_count > capacity


# Permissions (§30, §55.5). The service re-checks them at commit time.


def can_invite(role: GuildRole) -> bool:
    return role in (GuildRole.LEADER, GuildRole.OFFICER)


def can_manage_recruitment(role: GuildRole) -> bool:
    return role in (GuildRole.LEADER, GuildRole.OFFICER)


def can_review_applications(role: GuildRole) -> bool:
    return role in (GuildRole.LEADER, GuildRole.OFFICER)


def can_change_officers(role: GuildRole) -> bool:
    return role is GuildRole.LEADER


def can_transfer_leadership(role: GuildRole) -> bool:
    return role is GuildRole.LEADER


def can_remove(actor: GuildRole, target: GuildRole) -> bool:
    """Leader removes Officer or Member; Officer removes only a common Member."""
    if target is GuildRole.LEADER:
        return False
    if actor is GuildRole.LEADER:
        return True
    return actor is GuildRole.OFFICER and target is GuildRole.MEMBER
