"""Persist narrative choices once and answer what a future scene may legitimately know.

Every function runs inside the caller's transaction and touches one
``character_id`` only, so a cooperative roster can never write the host's
choice for a helper (or the reverse). Nothing here writes XP, Coroas,
Materiais, Equipamentos, ``quests.progress`` or ``world_states``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.narrative_choices import (
    BACKFILL_OPTION,
    BACKFILL_SOURCE,
    CATALOG_VERSION,
    DEFAULT_RAPPORT,
    PLAYER_SOURCE,
    ChoiceCatalog,
    ChoiceNode,
    ChoiceOption,
    CommittedChoice,
    ReactionLine,
    legitimate_reaction,
    narrative_catalog,
    prologue_catalog,
    resolve_hook,
)
from asterion.domain.prologue import POST_COMBAT_STAGE
from asterion.infrastructure.db.models import (
    Character,
    CharacterNarrativeMemory,
    NarrativeChoiceRecord,
    NpcNarrativeMemory,
    NpcRapport,
    Quest,
)


class NarrativeChoiceError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class CommitResult:
    choice_id: str
    selected_option: str
    created: bool


async def _record(session: AsyncSession, character_id: UUID, choice_id: str):
    return await session.scalar(
        select(NarrativeChoiceRecord).where(
            NarrativeChoiceRecord.character_id == character_id,
            NarrativeChoiceRecord.choice_id == choice_id,
        )
    )


def _node(catalog: ChoiceCatalog, choice_id: str) -> ChoiceNode:
    node = catalog.nodes.get(choice_id)
    if node is None:
        raise NarrativeChoiceError("choice_unknown")
    return node


async def _write_choice(
    session: AsyncSession,
    character: Character,
    node: ChoiceNode,
    option: ChoiceOption,
    *,
    now: datetime | None,
) -> CommitResult:
    """Insert record and memories once; a conflicting insert returns the first choice."""
    choice_id = node.choice_id
    now = now or datetime.now(UTC)
    inserted = await session.scalar(
        insert(NarrativeChoiceRecord)
        .values(
            id=uuid4(),
            character_id=character.id,
            choice_id=node.choice_id,
            mission_id=node.mission_id,
            step_context=node.step_context,
            selected_option=option.option_id,
            source=PLAYER_SOURCE,
            catalog_version=CATALOG_VERSION,
            character_memory_tags=list(option.character_memory_tags),
            npc_memory_targets=[
                {"npc_id": item.npc_id, "tag": item.tag, "knowledge": item.knowledge}
                for item in option.npc_memory_targets
            ],
            future_hooks=[hook.hook_id for hook in node.future_hooks],
            identity_conditions=list(
                node.matched_identity(character.race, character.character_class)
            ),
            committed_at=now,
        )
        .on_conflict_do_nothing(constraint="uq_narrative_choice")
        .returning(NarrativeChoiceRecord.id)
    )
    if inserted is None:
        existing = await _record(session, character.id, choice_id)
        return CommitResult(choice_id, existing.selected_option, created=False)

    for tag in option.character_memory_tags:
        await session.execute(
            insert(CharacterNarrativeMemory)
            .values(
                id=uuid4(),
                character_id=character.id,
                tag=tag,
                source_choice_id=node.choice_id,
                recorded_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_character_narrative_memory")
        )
    for target in option.npc_memory_targets:
        await session.execute(
            insert(NpcNarrativeMemory)
            .values(
                id=uuid4(),
                character_id=character.id,
                npc_id=target.npc_id,
                tag=target.tag,
                source_choice_id=node.choice_id,
                knowledge=target.knowledge,
                recorded_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_npc_narrative_memory")
        )
        # Rapport stays neutral until the author defines transitions (decision 2026-11-12).
        await session.execute(
            insert(NpcRapport)
            .values(
                character_id=character.id,
                npc_id=target.npc_id,
                rapport_state=DEFAULT_RAPPORT,
                updated_at=now,
            )
            .on_conflict_do_nothing(constraint="pk_npc_rapport_states")
        )
    return CommitResult(choice_id, option.option_id, created=True)


async def commit_narrative_choice(
    session: AsyncSession,
    character: Character,
    quest: Quest,
    choice_id: str,
    option_id: str,
    *,
    catalog: ChoiceCatalog | None = None,
    now: datetime | None = None,
) -> CommitResult:
    """Commit once. A retry, reconnect or duplicated callback returns the first choice.

    The caller has already locked the quest row and checked the step. The
    quest must belong to this character: the guest of a Boss fight never
    commits the host's node.
    """
    catalog = catalog or narrative_catalog()
    node = _node(catalog, choice_id)
    if quest.character_id != character.id or quest.quest_id != node.mission_id:
        raise NarrativeChoiceError("quest_mismatch")
    existing = await _record(session, character.id, choice_id)
    if existing is not None:
        return CommitResult(choice_id, existing.selected_option, created=False)
    if quest.status != "active":
        raise NarrativeChoiceError("quest_not_active")
    option = node.option(option_id)
    if option is None:
        raise NarrativeChoiceError("option_unknown")
    if not option.available_to(character.race, character.character_class):
        raise NarrativeChoiceError("option_unavailable")

    return await _write_choice(session, character, node, option, now=now)


async def backfill_neutral_choice(
    session: AsyncSession,
    character_id: UUID,
    choice_id: str,
    *,
    catalog: ChoiceCatalog | None = None,
    now: datetime | None = None,
) -> bool:
    """Mark a node passed before this system existed. No memory, no consequence (§9)."""
    catalog = catalog or narrative_catalog()
    node = _node(catalog, choice_id)
    inserted = await session.scalar(
        insert(NarrativeChoiceRecord)
        .values(
            id=uuid4(),
            character_id=character_id,
            choice_id=node.choice_id,
            mission_id=node.mission_id,
            step_context=node.step_context,
            selected_option=BACKFILL_OPTION,
            source=BACKFILL_SOURCE,
            catalog_version=CATALOG_VERSION,
            character_memory_tags=[],
            npc_memory_targets=[],
            future_hooks=[],
            identity_conditions=[],
            committed_at=now or datetime.now(UTC),
        )
        .on_conflict_do_nothing(constraint="uq_narrative_choice")
        .returning(NarrativeChoiceRecord.id)
    )
    return inserted is not None


async def selected_option(
    session: AsyncSession, character_id: UUID, choice_id: str
) -> str | None:
    record = await _record(session, character_id, choice_id)
    return record.selected_option if record is not None else None


async def load_committed_choice(
    session: AsyncSession, character_id: UUID, choice_id: str
) -> CommittedChoice | None:
    record = await _record(session, character_id, choice_id)
    if record is None:
        return None
    rows = (
        await session.execute(
            select(NpcNarrativeMemory.npc_id, NpcNarrativeMemory.tag).where(
                NpcNarrativeMemory.character_id == character_id,
                NpcNarrativeMemory.source_choice_id == choice_id,
            )
        )
    ).all()
    return CommittedChoice(
        choice_id=record.choice_id,
        selected_option=record.selected_option,
        source=record.source,
        npc_memories=frozenset((npc, tag) for npc, tag in rows),
    )


async def resolve_future_hook(
    session: AsyncSession,
    character_id: UUID,
    hook_id: str,
    *,
    catalog: ChoiceCatalog | None = None,
) -> str | None:
    """The option a later scene may react to, or None for the common fallback."""
    catalog = catalog or narrative_catalog()
    found = catalog.hook(hook_id)
    if found is None:
        return None
    node, hook = found
    committed = await load_committed_choice(session, character_id, node.choice_id)
    return resolve_hook(node, hook, committed)


async def resolve_future_reaction(
    session: AsyncSession,
    character_id: UUID,
    hook_id: str,
    *,
    catalog: ChoiceCatalog | None = None,
) -> ReactionLine | None:
    """Approved line for ``hook_id``; None unless its speaker legitimately knows the choice."""
    catalog = catalog or narrative_catalog()
    found = catalog.hook(hook_id)
    if found is None:
        return None
    node, hook = found
    committed = await load_committed_choice(session, character_id, node.choice_id)
    return legitimate_reaction(node, hook, committed)


async def npc_rapport(session: AsyncSession, character_id: UUID, npc_id: str) -> str:
    state = await session.scalar(
        select(NpcRapport.rapport_state).where(
            NpcRapport.character_id == character_id, NpcRapport.npc_id == npc_id
        )
    )
    return state or DEFAULT_RAPPORT


async def audit_character_choices(session: AsyncSession, character_id: UUID) -> list[dict]:
    """Debug chain ``choice_id → option → memories → future_hooks`` (§6.1). Never player-facing."""
    records = (
        await session.scalars(
            select(NarrativeChoiceRecord)
            .where(NarrativeChoiceRecord.character_id == character_id)
            .order_by(NarrativeChoiceRecord.committed_at, NarrativeChoiceRecord.choice_id)
        )
    ).all()
    character_rows = (
        await session.execute(
            select(CharacterNarrativeMemory.source_choice_id, CharacterNarrativeMemory.tag).where(
                CharacterNarrativeMemory.character_id == character_id
            )
        )
    ).all()
    npc_rows = (
        await session.execute(
            select(
                NpcNarrativeMemory.source_choice_id,
                NpcNarrativeMemory.npc_id,
                NpcNarrativeMemory.tag,
                NpcNarrativeMemory.knowledge,
            ).where(NpcNarrativeMemory.character_id == character_id)
        )
    ).all()
    chain = []
    for record in records:
        chain.append(
            {
                "choice_id": record.choice_id,
                "mission_id": record.mission_id,
                "step_context": record.step_context,
                "selected_option": record.selected_option,
                "source": record.source,
                "committed_at": record.committed_at.isoformat(),
                "character_memories": sorted(
                    tag for source, tag in character_rows if source == record.choice_id
                ),
                "npc_memories": sorted(
                    (
                        {"npc_id": npc, "tag": tag, "knowledge": knowledge}
                        for source, npc, tag, knowledge in npc_rows
                        if source == record.choice_id
                    ),
                    key=lambda item: (item["npc_id"], item["tag"]),
                ),
                "future_hooks": list(record.future_hooks),
                "identity_conditions": list(record.identity_conditions),
            }
        )
    return chain


@dataclass(frozen=True, slots=True)
class NarrativeNodeView:
    """What a mission screen needs to show one node. Tags never leave the server."""

    choice_id: str
    selected_option: str | None
    options: tuple[tuple[str, str], ...]

    @property
    def pending(self) -> bool:
        return self.selected_option is None


async def narrative_node_view(
    session: AsyncSession,
    character: Character,
    mission_id: str,
    *,
    catalog: ChoiceCatalog | None = None,
) -> NarrativeNodeView | None:
    catalog = catalog or narrative_catalog()
    node = catalog.by_mission(mission_id)
    if node is None:
        return None
    selected = await selected_option(session, character.id, node.choice_id)
    return NarrativeNodeView(
        choice_id=node.choice_id,
        selected_option=selected,
        options=tuple(
            (item.option_id, item.label)
            for item in node.available_options(character.race, character.character_class)
        ),
    )


async def commit_mission_choice(
    session: AsyncSession,
    character: Character,
    quest: Quest,
    option_id: str,
    *,
    catalog: ChoiceCatalog | None = None,
) -> CommitResult | None:
    """Commit the node of ``quest``'s mission; None for an unknown or unavailable option."""
    catalog = catalog or narrative_catalog()
    node = catalog.by_mission(quest.quest_id)
    if node is None:
        return None
    try:
        return await commit_narrative_choice(
            session, character, quest, node.choice_id, option_id, catalog=catalog
        )
    except NarrativeChoiceError:
        return None


# --- Prologue (Documento A): no Quest, character memory only ---------------------------

PROLOGUE_CHOICE_ORDER = ("PRO_choice_aftermath", "PRO_choice_first_fire")


@dataclass(frozen=True, slots=True)
class PrologueChoiceView:
    """One pending Prologue node as a screen needs it. Tags never leave the server."""

    choice_id: str
    title: str
    context: str
    question: str
    options: tuple[tuple[str, str], ...]


async def prologue_choice_view(
    session: AsyncSession, character: Character
) -> PrologueChoiceView | None:
    """The next unanswered Prologue node, only while the character stands at the first Braseiro."""
    if character.stage != POST_COMBAT_STAGE:
        return None
    catalog = prologue_catalog()
    for choice_id in PROLOGUE_CHOICE_ORDER:
        if await selected_option(session, character.id, choice_id) is None:
            node = catalog.nodes[choice_id]
            return PrologueChoiceView(
                choice_id=choice_id,
                title=node.title,
                context=node.step_context,
                question=node.question,
                options=tuple(
                    (item.option_id, item.label)
                    for item in node.available_options(character.race, character.character_class)
                ),
            )
    return None


async def commit_prologue_choice(
    session: AsyncSession,
    character: Character,
    choice_id: str,
    option_id: str,
    *,
    now: datetime | None = None,
) -> CommitResult | None:
    """Commit one Prologue node once; None when the callback no longer matches the state.

    Only character memory is written. Callers hold the character row lock.
    """
    catalog = prologue_catalog()
    node = catalog.nodes.get(choice_id)
    if node is None:
        return None
    existing = await _record(session, character.id, choice_id)
    if existing is not None:
        return CommitResult(choice_id, existing.selected_option, created=False)
    if character.stage != POST_COMBAT_STAGE:
        return None
    index = PROLOGUE_CHOICE_ORDER.index(choice_id)
    if index and await selected_option(session, character.id, PROLOGUE_CHOICE_ORDER[0]) is None:
        return None
    option = node.option(option_id)
    if option is None or not option.available_to(character.race, character.character_class):
        return None
    return await _write_choice(session, character, node, option, now=now)


async def backfill_prologue_choices(
    session: AsyncSession, character: Character, *, now: datetime | None = None
) -> None:
    """Characters past the Prologue before this system existed carry no preference (§8)."""
    for choice_id in PROLOGUE_CHOICE_ORDER:
        await backfill_neutral_choice(
            session, character.id, choice_id, catalog=prologue_catalog(), now=now
        )
