"""Anti-spam técnico de 3 s e "1 em resolução" (TdO v1.0.18 33.2, L13).

Compartilhado por Explorar e Desbravar. Persistido por personagem. Não é regra
econômica: nunca altera recompensa. Chame dentro da transação que já travou o
personagem (``SELECT ... FOR UPDATE``).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.tdo_explore import explore_cooldown_remaining
from asterion.infrastructure.db.models import CharacterActionThrottle

ACTION_EXPLORE = "explore_location"
ACTION_DESBRAVAR = "desbravar"


@dataclass(frozen=True)
class ThrottleDecision:
    allowed: bool
    reason: str | None = None  # "cooldown" | "resolving"
    retry_after: timedelta = timedelta(0)


async def acquire_action_slot(
    session: AsyncSession, character_id: UUID, action: str, now: datetime
) -> ThrottleDecision:
    """Registra o clique e marca "em resolução"; recusa sem alterar o horário gravado."""
    await session.execute(
        pg_insert(CharacterActionThrottle)
        .values(
            character_id=character_id,
            last_action=action,
            last_click_at=now - timedelta(days=1),
            resolving=False,
        )
        .on_conflict_do_nothing(index_elements=["character_id"])
    )
    row = await session.scalar(
        select(CharacterActionThrottle)
        .where(CharacterActionThrottle.character_id == character_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row.resolving:
        return ThrottleDecision(False, "resolving")
    remaining = explore_cooldown_remaining(row.last_click_at, now)
    if remaining > timedelta(0):
        return ThrottleDecision(False, "cooldown", remaining)
    row.last_action = action
    row.last_click_at = now
    row.resolving = True
    return ThrottleDecision(True)


async def release_action_slot(session: AsyncSession, character_id: UUID) -> None:
    """Fim da resolução; mantém o horário do último clique."""
    row = await session.get(CharacterActionThrottle, character_id, with_for_update=True)
    if row is not None:
        row.resolving = False
