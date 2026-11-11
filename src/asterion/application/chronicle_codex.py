"""Register the Códice of Crônica I a character's progress allows (proposal §6).

Called after a chapter conclusion and whenever the Códice is opened, so a layer
reached later (P6, P18, P24, P29, P35), a Region discovered later and the desfecho
published at T show up without a job. Inserts are idempotent per
``character_id + fragment_id`` (GDD §33.2), and Trechos are never removed.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.chronicle import completed_quests, load_cycle
from asterion.domain.chronicle import CHAPTER_CONCLUSION_IDS, CHRONICLE_ID, Outcome, layers_for
from asterion.domain.chronicle_codex import (
    CODEX_PREFIX,
    REGION_LOCATION_PREFIX,
    allowed_fragments,
)
from asterion.infrastructure.db.models import (
    Character,
    ChronicleCompletion,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
)


async def sync_chronicle_codex(session: AsyncSession, character: Character, now: datetime) -> int:
    """Register the missing Entries and Trechos; returns how many Trechos were new."""
    concluded = (
        await session.scalars(
            select(ChronicleCompletion.objective_id).where(
                ChronicleCompletion.character_id == character.id,
                ChronicleCompletion.chronicle_id == CHRONICLE_ID,
                ChronicleCompletion.objective_id.in_(list(CHAPTER_CONCLUSION_IDS)),
            )
        )
    ).all()
    if not concluded:
        return 0
    chapters = {CHAPTER_CONCLUSION_IDS[item] for item in concluded}
    layers = layers_for(await completed_quests(session, character.id))
    discovered = (
        await session.scalars(
            select(LocationDiscovery.location_id).where(
                LocationDiscovery.character_id == character.id,
                or_(
                    *(
                        LocationDiscovery.location_id.startswith(prefix)
                        for prefix in REGION_LOCATION_PREFIX.values()
                    )
                ),
            )
        )
    ).all()
    regions = frozenset(
        region
        for region, prefix in REGION_LOCATION_PREFIX.items()
        if any(location.startswith(prefix) for location in discovered)
    )
    cycle = await load_cycle(session, character.server_id)
    # The result is published at T (§4), like the epilogue on the Crônica screen.
    outcome = (
        Outcome(cycle.outcome)
        if cycle is not None and cycle.outcome is not None and now >= cycle.end_at
        else None
    )
    wanted = allowed_fragments(chapters, layers, regions, outcome)
    held = set(
        (
            await session.scalars(
                select(CodexFragment.fragment_id).where(
                    CodexFragment.character_id == character.id,
                    CodexFragment.fragment_id.startswith(CODEX_PREFIX),
                )
            )
        ).all()
    )
    missing = [item for item in wanted if item.fragment_id not in held]
    for entry_id in dict.fromkeys(item.entry_id for item in missing):
        await session.execute(
            insert(CodexEntry)
            .values(character_id=character.id, entry_id=entry_id)
            .on_conflict_do_nothing(constraint="uq_character_codex")
        )
    for item in missing:
        await session.execute(
            insert(CodexFragment)
            .values(
                character_id=character.id,
                entry_id=item.entry_id,
                fragment_id=item.fragment_id,
            )
            .on_conflict_do_nothing(constraint="uq_character_fragment")
        )
    return len(missing)
