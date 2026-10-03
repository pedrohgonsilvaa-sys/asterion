"""Read-only player surfaces for character stats and acquired knowledge."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BESTIARY_STAGE_LABELS
from asterion.application.cosmetic_catalog import COSMETICS_BY_ID
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    resolve_character_combat_stats,
)
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_BY_ID,
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
    CREATURE_NOTES,
    CREATURE_PRESENTATION,
    HABITAT_EVIDENCE_TO_LOCATION,
    MATERIAL_LABELS,
    VARIANT_LABELS,
)
from asterion.application.tdo_feats import reconcile_tdo_feats
from asterion.domain.road import creature_for
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CharacterCosmeticSelection,
    CharacterPendingInput,
    CharacterProfile,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
)

MAX_HISTORY_CHARACTERS = 1200


@dataclass(frozen=True, slots=True)
class AttributesView:
    name: str
    level: int
    character_class: str
    selected_path: str | None
    hp: Decimal
    max_hp: Decimal
    vigor: int
    max_vigor: int
    attack: Decimal
    defense: Decimal
    agility: Decimal
    perception: Decimal
    critical: Decimal
    evasion: Decimal
    block: Decimal


@dataclass(frozen=True, slots=True)
class ProfileView:
    name: str
    level: int
    character_class: str
    selected_path: str | None
    history: str | None
    revision: int
    selected_title: str | None = None


@dataclass(frozen=True, slots=True)
class CodexFragmentView:
    fragment_id: str
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class CodexEntryView:
    entry_id: str
    title: str
    category: str
    order: int
    location_id: str | None
    fragments: tuple[CodexFragmentView, ...]


@dataclass(frozen=True, slots=True)
class BestiaryRecordView:
    creature_id: str
    name: str
    stage: str
    stage_label: str
    habitats: tuple[str, ...]
    variants: tuple[str, ...]
    materials: tuple[str, ...]
    observed_actions: tuple[str, ...]
    note: str | None = None


@dataclass(frozen=True, slots=True)
class AchievementView:
    achievement_id: str
    name: str
    category: str
    description: str
    reward: str | None


@dataclass(frozen=True, slots=True)
class KnowledgeView:
    character_class: str
    codex_entries: tuple[CodexEntryView, ...]
    bestiary: tuple[BestiaryRecordView, ...]
    achievements: tuple[AchievementView, ...]
    known_locations: frozenset[str]


class HistoryInputResult:
    SAVED = "saved"
    STALE = "stale"
    TOO_LONG = "too_long"
    EMPTY = "empty"
    MISSING_CHARACTER = "missing_character"


class CharacterSurfacesService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str) -> None:
        self.sessions = sessions
        self.server_id = server_id

    async def attributes(self, actor_id: int) -> AttributesView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor_id)
            if character is None:
                return None
            configuration = await load_equipment_configuration(session, character, lock_rows=False)
            stats = resolve_character_combat_stats(character, configuration)
            return AttributesView(
                name=character.name,
                level=character.level,
                character_class=character.character_class,
                selected_path=character.selected_path,
                hp=Decimal(character.hp),
                max_hp=stats.hp,
                vigor=character.vigor,
                max_vigor=character.max_vigor,
                attack=stats.attack,
                defense=stats.defense,
                agility=stats.agility,
                perception=stats.per,
                critical=stats.crit,
                evasion=stats.evasion,
                block=stats.block,
            )

    async def profile(self, actor_id: int) -> ProfileView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor_id)
            if character is None:
                return None
            await reconcile_tdo_feats(session, character)
            profile = await session.scalar(
                select(CharacterProfile).where(CharacterProfile.character_id == character.id)
            )
            selected_title_id = await session.scalar(
                select(CharacterCosmeticSelection.cosmetic_id).where(
                    CharacterCosmeticSelection.character_id == character.id,
                    CharacterCosmeticSelection.cosmetic_type == "title",
                )
            )
            selected_title = (
                COSMETICS_BY_ID[selected_title_id].name
                if selected_title_id in COSMETICS_BY_ID
                else None
            )
            return self._profile_view(character, profile, selected_title)

    async def begin_history_input(
        self, actor_id: int, expected_revision: int, prompt_message_id: int
    ) -> bool:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor_id, lock=True)
            if character is None:
                return False
            profile = await session.scalar(
                select(CharacterProfile)
                .where(CharacterProfile.character_id == character.id)
                .with_for_update()
            )
            if profile is None:
                profile = CharacterProfile(character_id=character.id, revision=0)
                session.add(profile)
                await session.flush()
            if profile.revision != expected_revision:
                return False
            lease = await session.scalar(
                select(CharacterPendingInput)
                .where(CharacterPendingInput.character_id == character.id)
                .with_for_update()
            )
            if lease is not None and lease.input_kind != "history":
                return False
            if lease is None:
                lease = CharacterPendingInput(
                    character_id=character.id,
                    input_kind="history",
                    prompt_message_id=prompt_message_id,
                )
                session.add(lease)
            else:
                lease.prompt_message_id = prompt_message_id
                lease.updated_at = datetime.now(UTC)
            profile.history_prompt_message_id = prompt_message_id
            profile.updated_at = datetime.now(UTC)
            return True

    async def cancel_history_input(self, actor_id: int) -> bool:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor_id, lock=True)
            if character is None:
                return False
            profile = await session.scalar(
                select(CharacterProfile)
                .where(CharacterProfile.character_id == character.id)
                .with_for_update()
            )
            if profile is None or profile.history_prompt_message_id is None:
                history_cleared = False
            else:
                profile.history_prompt_message_id = None
                profile.updated_at = datetime.now(UTC)
                history_cleared = True
            lease = await session.scalar(
                select(CharacterPendingInput)
                .where(
                    CharacterPendingInput.character_id == character.id,
                    CharacterPendingInput.input_kind == "history",
                )
                .with_for_update()
            )
            if lease is not None:
                await session.delete(lease)
                return True
            return history_cleared

    async def save_history(self, actor_id: int, prompt_message_id: int, raw_text: str) -> str:
        text = _clean_history(raw_text)
        if not text:
            return HistoryInputResult.EMPTY
        if len(text) > MAX_HISTORY_CHARACTERS:
            return HistoryInputResult.TOO_LONG
        async with self.sessions.begin() as session:
            character = await self._character(session, actor_id, lock=True)
            if character is None:
                return HistoryInputResult.MISSING_CHARACTER
            profile = await session.scalar(
                select(CharacterProfile)
                .where(CharacterProfile.character_id == character.id)
                .with_for_update()
            )
            if profile is None or profile.history_prompt_message_id != prompt_message_id:
                return HistoryInputResult.STALE
            lease = await session.scalar(
                select(CharacterPendingInput)
                .where(
                    CharacterPendingInput.character_id == character.id,
                    CharacterPendingInput.input_kind == "history",
                    CharacterPendingInput.prompt_message_id == prompt_message_id,
                )
                .with_for_update()
            )
            if lease is None:
                return HistoryInputResult.STALE
            profile.history = text
            profile.revision += 1
            profile.history_prompt_message_id = None
            profile.updated_at = datetime.now(UTC)
            await session.delete(lease)
            return HistoryInputResult.SAVED

    async def knowledge(self, actor_id: int) -> KnowledgeView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor_id)
            if character is None:
                return None
            await reconcile_tdo_feats(session, character)
            character_id = character.id
            codex_rows = list(
                (
                    await session.scalars(
                        select(CodexEntry)
                        .where(CodexEntry.character_id == character_id)
                        .order_by(CodexEntry.entry_id)
                    )
                ).all()
            )
            fragment_rows = list(
                (
                    await session.scalars(
                        select(CodexFragment)
                        .where(CodexFragment.character_id == character_id)
                        .order_by(CodexFragment.fragment_id)
                    )
                ).all()
            )
            location_rows = list(
                (
                    await session.scalars(
                        select(LocationDiscovery.location_id).where(
                            LocationDiscovery.character_id == character_id
                        )
                    )
                ).all()
            )
            known_locations = frozenset(location_rows)
            bestiary_rows = list(
                (
                    await session.scalars(
                        select(BestiaryEntry)
                        .where(BestiaryEntry.character_id == character_id)
                        .order_by(BestiaryEntry.creature_id)
                    )
                ).all()
            )
            evidence_rows = list(
                (
                    await session.scalars(
                        select(BestiaryEvidence)
                        .where(BestiaryEvidence.character_id == character_id)
                        .order_by(BestiaryEvidence.creature_id, BestiaryEvidence.evidence_id)
                    )
                ).all()
            )
            achievement_rows = list(
                (
                    await session.scalars(
                        select(Achievement.achievement_id).where(
                            Achievement.character_id == character_id
                        )
                    )
                ).all()
            )

            fragments_by_entry: dict[str, list[CodexFragmentView]] = {}
            for row in fragment_rows:
                definition = CODEX_FRAGMENTS.get(row.fragment_id)
                if definition is None:
                    continue
                fragments_by_entry.setdefault(row.entry_id, []).append(
                    CodexFragmentView(row.fragment_id, definition.title, definition.text)
                )
            codex_entries = []
            for row in codex_rows:
                definition = CODEX_BY_ID.get(row.entry_id)
                if definition is None:
                    continue
                if definition.location_id and definition.location_id not in known_locations:
                    continue
                codex_entries.append(
                    CodexEntryView(
                        entry_id=row.entry_id,
                        title=definition.title,
                        category=definition.category,
                        order=definition.order,
                        location_id=definition.location_id,
                        fragments=tuple(fragments_by_entry.get(row.entry_id, ())),
                    )
                )

            evidence_by_creature: dict[str, list[BestiaryEvidence]] = {}
            for row in evidence_rows:
                evidence_by_creature.setdefault(row.creature_id, []).append(row)
            bestiary = []
            for row in bestiary_rows:
                presentation = CREATURE_PRESENTATION.get(row.creature_id)
                if presentation is None:
                    continue
                try:
                    creature = creature_for(row.creature_id)
                except StopIteration:
                    continue
                creature_evidence = evidence_by_creature.get(row.creature_id, [])
                evidence_ids = {item.evidence_id for item in creature_evidence}
                habitats = set()
                for evidence_id in evidence_ids:
                    if not evidence_id.startswith("habitat:"):
                        continue
                    habitat_key = evidence_id.removeprefix("habitat:")
                    location_id = HABITAT_EVIDENCE_TO_LOCATION.get(habitat_key)
                    if location_id in known_locations and location_id in presentation.habitats:
                        habitats.add(location_id)
                variants = tuple(
                    label
                    for evidence_id in sorted(evidence_ids)
                    if evidence_id.startswith("variant:")
                    if (label := VARIANT_LABELS.get(evidence_id.removeprefix("variant:")))
                )
                materials = set()
                for item in creature_evidence:
                    if item.category != "material":
                        continue
                    material_id = item.evidence_id.removeprefix("material:")
                    label = MATERIAL_LABELS.get(material_id)
                    if label:
                        materials.add(label)
                action_names = {
                    str(action[0]): str(action[1])
                    for action in creature.actions
                    if isinstance(action, tuple) and len(action) >= 2
                }
                observed_actions = tuple(
                    action_names[action_id]
                    for action_id in sorted(action_names)
                    if f"action:{action_id}" in evidence_ids
                )
                bestiary.append(
                    BestiaryRecordView(
                        creature_id=row.creature_id,
                        name=creature.name,
                        stage=row.stage if row.stage in BESTIARY_STAGE_LABELS else "observed",
                        stage_label=BESTIARY_STAGE_LABELS.get(row.stage, "Observado"),
                        habitats=tuple(
                            location_id
                            for location_id in presentation.habitats
                            if location_id in habitats
                        ),
                        variants=variants,
                        materials=tuple(sorted(materials)),
                        observed_actions=observed_actions,
                        note=CREATURE_NOTES.get(row.creature_id),
                    )
                )

            achievements = []
            for achievement_id in achievement_rows:
                definition = ACHIEVEMENT_BY_ID.get(achievement_id)
                if definition is None or not definition.player_facing:
                    continue
                achievements.append(
                    AchievementView(
                        definition.achievement_id,
                        definition.name,
                        definition.category,
                        definition.description,
                        definition.reward,
                    )
                )
            achievements.sort(key=lambda item: (item.category, item.name.casefold()))

            return KnowledgeView(
                character_class=character.character_class,
                codex_entries=tuple(
                    sorted(codex_entries, key=lambda item: (item.category, item.order))
                ),
                bestiary=tuple(sorted(bestiary, key=lambda item: item.name.casefold())),
                achievements=tuple(achievements),
                known_locations=known_locations,
            )

    async def _character(
        self, session: AsyncSession, actor_id: int, *, lock: bool = False
    ) -> Character | None:
        statement = select(Character).where(
            Character.telegram_id == actor_id,
            Character.server_id == self.server_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    @staticmethod
    def _profile_view(
        character: Character,
        profile: CharacterProfile | None,
        selected_title: str | None = None,
    ) -> ProfileView:
        return ProfileView(
            name=character.name,
            level=character.level,
            character_class=character.character_class,
            selected_path=character.selected_path,
            history=profile.history if profile else None,
            revision=profile.revision if profile else 0,
            selected_title=selected_title,
        )


def _clean_history(raw_text: str) -> str:
    normalized = unicodedata.normalize("NFC", raw_text)
    cleaned = "".join(
        character
        for character in normalized
        if character in "\n\t" or unicodedata.category(character) != "Cc"
    ).strip()
    return re.sub(r"[ \t]+\n", "\n", cleaned)
