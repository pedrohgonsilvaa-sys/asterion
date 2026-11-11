"""Build one character's narrative context from the existing per-character tables.

No new table: Race and Class come from ``characters``, mission state from
``quests``, consequences from ``unlocks``, knowledge from ``codex_entries``,
``location_discoveries`` and ``braziers``, and the current Local from
``world_states``. Every query filters by one ``character_id``, so a cooperative
roster never mixes the host's and the helper's narrative.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.narrative_identity import (
    NARRATIVE_SCENES,
    NarrativeContext,
    QuestState,
    ResolvedScene,
    resolve_scene,
)
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    CodexEntry,
    LocationDiscovery,
    Quest,
    Unlock,
    WorldState,
)


async def load_narrative_context(
    session: AsyncSession, character_id: UUID
) -> NarrativeContext | None:
    character = await session.get(Character, character_id)
    if character is None:
        return None
    quests = {
        row.quest_id: QuestState(status=row.status, step=row.step)
        for row in (
            await session.scalars(select(Quest).where(Quest.character_id == character_id))
        ).all()
    }
    flags = frozenset(
        (
            await session.scalars(
                select(Unlock.unlock_id).where(Unlock.character_id == character_id)
            )
        ).all()
    )
    discoveries: set[str] = set()
    for column, owner in (
        (CodexEntry.entry_id, CodexEntry.character_id),
        (LocationDiscovery.location_id, LocationDiscovery.character_id),
        (Brazier.brazier_id, Brazier.character_id),
    ):
        rows = await session.scalars(select(column).where(owner == character_id))
        discoveries.update(rows.all())
    location = await session.scalar(
        select(WorldState.location).where(WorldState.character_id == character_id)
    )
    return NarrativeContext(
        character_id=str(character.id),
        race=character.race,
        character_class=character.character_class,
        quests=quests,
        flags=flags,
        discoveries=frozenset(discoveries),
        location=location,
    )


async def resolve_character_scene(
    session: AsyncSession, character_id: UUID, scene_id: str, scenes=NARRATIVE_SCENES
) -> ResolvedScene | None:
    scene = scenes.get(scene_id)
    if scene is None:
        return None
    context = await load_narrative_context(session, character_id)
    if context is None:
        return None
    return resolve_scene(scene, context)
