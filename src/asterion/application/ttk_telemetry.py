"""Telemetria mínima de TTK do Beta (docs/TTK_DESENHO.md).

Grava uma linha por combate de Caçada Manual ou Ronda quando ele termina. É só
observação: nunca altera regra de combate, XP, loot nem liquidação, e uma falha aqui
nunca desfaz a liquidação (o INSERT roda num savepoint e o erro vira log).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.combat import Combat
from asterion.infrastructure.db.models import CombatTtkRecord

logger = logging.getLogger(__name__)

SOURCE_HUNT_MANUAL = "hunt_manual"
SOURCE_ROUND_AUTO = "round_auto"
RESULT_ABANDONED = "abandoned"

# ``Combat.version`` is 0 when ``start_combat`` returns and grows by one per valid
# player action (attack, defend, art or consumable). Pinned by tests/test_ttk_telemetry.py.
START_VERSION = 0

_state: dict[str, Any] = {"enabled": False, "build_version": "unknown"}


def configure(*, enabled: bool, build_version: str = "unknown") -> None:
    _state["enabled"] = bool(enabled)
    _state["build_version"] = build_version or "unknown"


def is_enabled() -> bool:
    return _state["enabled"]


def player_actions(combat: Combat) -> int:
    """Valid player actions so far; a proxy for the GDD's "ações equivalentes", not the same."""
    return max(combat.version - START_VERSION, 0)


async def record_ttk(
    session: AsyncSession,
    *,
    source: str,
    combat: Combat,
    character_id: Any,
    creature_id: str,
    creature_category: str,
    enemy_level: int,
    region_id: str,
    result: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> bool:
    """Insert the combat's record once; True only when this call created the row.

    ``result`` defaults to the combat's own result; pass ``abandoned`` for an expired
    activity. Duration is stored for finished combats with a trusted start only: an
    abandoned combat has none (it ends when the expiry is noticed, not when play stopped).
    """
    if not is_enabled():
        return False
    try:
        outcome = result or combat.result
        if outcome not in {"victory", "defeat", RESULT_ABANDONED}:
            return False
        finished = finished_at or datetime.now(UTC)
        player = combat.fighters["player"]
        duration = (
            Decimal(str((finished - started_at).total_seconds())).quantize(Decimal("0.001"))
            if started_at is not None and outcome != RESULT_ABANDONED
            else None
        )
        values = {
            "combat_id": combat.id,
            "source": source,
            "character_id": character_id,
            "character_class": player.character_class,
            "player_level": player.level,
            "creature_id": creature_id,
            "creature_category": creature_category,
            "enemy_level": enemy_level,
            "region_id": region_id,
            "party_size": 1,
            "result": outcome,
            "player_actions": player_actions(combat),
            "rounds": combat.round,
            "consumable_uses": combat.consumable_uses,
            "started_at": started_at,
            "finished_at": finished,
            "duration_seconds": duration,
            "ruleset_version": combat.ruleset,
            "build_version": _state["build_version"],
        }
        async with session.begin_nested():
            created = await session.scalar(
                insert(CombatTtkRecord)
                .values(**values)
                .on_conflict_do_nothing(index_elements=[CombatTtkRecord.combat_id])
                .returning(CombatTtkRecord.combat_id)
            )
        return created is not None
    except Exception:  # telemetry must never break settlement
        logger.warning("TTK telemetry write failed", exc_info=True)
        return False


async def record_hunt(
    session: AsyncSession,
    character: Any,
    context: Any,
    combat: Combat,
    *,
    source: str,
    region_id: str,
    result: str | None = None,
    started_at: datetime | None = None,
) -> bool:
    """``record_ttk`` for a ``HuntContext`` (creature, category and level live there)."""
    return await record_ttk(
        session,
        source=source,
        combat=combat,
        character_id=character.id,
        creature_id=context.creature_id,
        creature_category=context.category,
        enemy_level=context.enemy_level,
        region_id=region_id,
        result=result,
        started_at=started_at,
    )


async def record_abandoned_hunt(
    session: AsyncSession, character: Any, activity: Any, context: Any, *, region_id: str
) -> bool:
    """An expired manual hunt: load its last persisted state and record it as abandoned."""
    if not is_enabled():
        return False
    try:
        from asterion.infrastructure.db.combat_codec import decode
        from asterion.infrastructure.db.combat_repository import CombatRepository

        _encounter, record = await CombatRepository(session).combat(activity)
        combat = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
    except Exception:
        logger.warning("TTK telemetry could not load the abandoned combat", exc_info=True)
        return False
    return await record_hunt(
        session,
        character,
        context,
        combat,
        source=SOURCE_HUNT_MANUAL,
        region_id=region_id,
        result=RESULT_ABANDONED,
        started_at=context.started_at,
    )
