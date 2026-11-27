"""Read-only player surfaces for character stats and acquired knowledge."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BESTIARY_STAGE_LABELS
from asterion.application.chronicle_codex import sync_chronicle_codex
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
from asterion.application.progression import level_xp
from asterion.application.tdo_feats import reconcile_tdo_feats
from asterion.application.vigor import reconcile_character_vigor
from asterion.domain.flagelos import REGIONS as FLAGELO_REGIONS
from asterion.domain.road import creature_for
from asterion.domain.social import MAX_STORY_CHARACTERS, story_is_allowed
from asterion.domain.veu_bestiary import VEU_CREATURES
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CharacterCosmeticSelection,
    CharacterDoctrineInput,
    CharacterPendingInput,
    CharacterProfile,
    CodexEntry,
    CodexFragment,
    Guild,
    GuildMember,
    LocationDiscovery,
)

MAX_HISTORY_CHARACTERS = MAX_STORY_CHARACTERS  # §49.18


@dataclass(frozen=True, slots=True)
class IdentityView:
    """Identidade padrão do personagem (Contrato Mestre de Telas UI v1.0.0 §4)."""

    name: str
    character_class: str
    level: int
    legacy_level: int
    selected_title: str | None
    guild_tag: str | None


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
    xp: int = 0
    xp_required: int = 0
    crowns: int = 0


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
class _EventCreature:
    """Criatura do Bestiário do Véu com o mesmo contorno que a UI lê de ``road.Creature``."""

    name: str
    actions: tuple[tuple[str, str], ...]


def _creature_for(creature_id: str):
    if creature_id.startswith("bestiary.veu."):
        found = next(c for c in VEU_CREATURES if c.bestiary_key == creature_id)
        return _EventCreature(found.name, tuple((a.key, a.label) for a in found.actions))
    if creature_id.startswith("bestiary.flagelo."):
        flagelo = next(
            r.flagelo for r in FLAGELO_REGIONS if r.flagelo.bestiary_key == creature_id
        )
        return _EventCreature(flagelo.name, tuple((a.key, a.label) for a in flagelo.actions))
    return creature_for(creature_id)


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
    rarity: str | None = None
    origin: str | None = None
    emoji: str | None = None


# Origem de um Feito sem Origem própria na Fonte: a Região do seu identificador.
ACHIEVEMENT_REGION_ORIGINS = {
    "tdo": "Terras do Ocaso",
    "vde": "Vales dos Enforcados",
    "nareth": "Planícies de Nareth",
    "varzeas": "Várzeas Carmesins",
    "altos": "Altos Cinéreos",
    "confins": "Confins do Véu",
}


def achievement_origin(definition) -> str | None:
    if definition.origin:
        return definition.origin
    parts = definition.achievement_id.split(".")
    return ACHIEVEMENT_REGION_ORIGINS.get(parts[1]) if len(parts) > 2 else None


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
    FORBIDDEN = "forbidden"
    MISSING_CHARACTER = "missing_character"


class CharacterSurfacesService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str) -> None:
        self.sessions = sessions
        self.server_id = server_id

    async def attributes(self, actor_id: int) -> AttributesView | None:
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor_id, Character.server_id == self.server_id)
                .with_for_update()
            )
            if character is None:
                return None
            await reconcile_character_vigor(session, character)
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
                xp=character.xp,
                xp_required=level_xp(character.level) if character.level < 60 else 0,
                crowns=character.crowns,
            )

    async def identity(self, actor_id: int) -> IdentityView | None:
        """Read-only: nome, Classe, Nível, Legado, Título escolhido e TAG da Guilda."""
        async with self.sessions() as session:
            character = await self._character(session, actor_id)
            if character is None:
                return None
            selected_title_id = await session.scalar(
                select(CharacterCosmeticSelection.cosmetic_id).where(
                    CharacterCosmeticSelection.character_id == character.id,
                    CharacterCosmeticSelection.cosmetic_type == "title",
                )
            )
            guild_tag = await session.scalar(
                select(Guild.tag)
                .join(GuildMember, GuildMember.guild_id == Guild.id)
                .where(GuildMember.character_id == character.id, Guild.status == "active")
            )
            return IdentityView(
                name=character.name,
                character_class=character.character_class,
                level=character.level,
                legacy_level=character.legacy_level,
                selected_title=(
                    COSMETICS_BY_ID[selected_title_id].name
                    if selected_title_id in COSMETICS_BY_ID
                    else character.title
                ),
                guild_tag=guild_tag,
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
                else character.title
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
            if lease is not None and lease.input_kind == "doctrine_name":
                # O pedido mais recente vence: o pedido de nome de Doutrina é encerrado.
                await session.execute(
                    delete(CharacterDoctrineInput).where(
                        CharacterDoctrineInput.character_id == character.id
                    )
                )
                lease.input_kind = "history"
            elif lease is not None and lease.input_kind != "history":
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

    async def remove_history(self, actor_id: int, expected_revision: int) -> bool:
        """§31.1: the player may remove their own História."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor_id, lock=True)
            if character is None:
                return False
            profile = await session.scalar(
                select(CharacterProfile)
                .where(CharacterProfile.character_id == character.id)
                .with_for_update()
            )
            if profile is None or profile.revision != expected_revision:
                return False
            profile.history = None
            profile.revision += 1
            profile.updated_at = datetime.now(UTC)
            return True

    async def save_history(self, actor_id: int, prompt_message_id: int, raw_text: str) -> str:
        text = _clean_history(raw_text)
        if not text:
            return HistoryInputResult.EMPTY
        if len(text) > MAX_HISTORY_CHARACTERS:
            return HistoryInputResult.TOO_LONG
        if not story_is_allowed(text):
            return HistoryInputResult.FORBIDDEN
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
            await sync_chronicle_codex(session, character, datetime.now(UTC))
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
                    creature = _creature_for(row.creature_id)
                except (StopIteration, KeyError):
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
                        definition.rarity,
                        achievement_origin(definition),
                        definition.emoji,
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
