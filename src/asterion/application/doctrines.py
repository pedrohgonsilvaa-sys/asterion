"""Saved reference-based combat configurations (Doutrinas)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    find_combat_configuration_blocker,
    lock_for_combat_configuration_mutation,
)
from asterion.application.equipment_configuration import (
    build_equipment_configuration,
    hp_after_equipment_change,
    load_equipment_configuration,
    resolve_character_combat_stats,
)
from asterion.application.weapon_metadata import resolve_equipment_weapon
from asterion.domain.arts import active_art_definition, weapon_requirement_satisfied
from asterion.domain.economy import crowns_per_level, path_switch_cost
from asterion.domain.equipment import EquipmentSlot, parse_equipment_slot
from asterion.domain.paths import path_belongs_to_class
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TALENT_POINT_LEVELS,
    talent_points_at_level,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterActiveArtSlot,
    CharacterDoctrine,
    CharacterDoctrineInput,
    CharacterEquipmentSlot,
    CharacterPendingInput,
    CharacterTalentChoice,
    ClassTrialState,
    EquipmentItem,
    Unlock,
    WorldState,
)

MAX_DOCTRINES = 5
MAX_DOCTRINE_NAME_CHARACTERS = 40
SAFE_CONFIGURATION_LOCATIONS = frozenset({"Refúgio do Ocaso"})
COMPLETED_TRIAL_UNLOCK = "class_trial_completed"


class DoctrineRejected(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class DoctrineView:
    doctrine_id: UUID
    name: str
    revision: int
    configuration: dict
    is_current: bool
    incomplete_reason: str | None
    can_apply: bool
    equipment_names: tuple[tuple[str, str | None], ...] = ()


@dataclass(frozen=True, slots=True)
class DoctrineCollectionView:
    character_name: str
    character_class: str
    selected_path: str | None
    configuration_version: int
    foreground: bool
    current_configuration: dict
    doctrines: tuple[DoctrineView, ...]
    crowns: int
    level: int


@dataclass(frozen=True, slots=True)
class DoctrineMutation:
    changed: bool
    configuration_version: int
    doctrine_id: UUID | None = None


def clean_doctrine_name(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    result = "".join(
        char for char in normalized if unicodedata.category(char) not in {"Cc", "Cf"}
    ).strip()
    if not result or len(result) > MAX_DOCTRINE_NAME_CHARACTERS:
        raise DoctrineRejected("invalid_name")
    return result


def _canonical(value: dict) -> dict:
    return {
        "path": value.get("path"),
        "equipment": {
            str(key): str(item_id)
            for key, item_id in sorted((value.get("equipment") or {}).items())
        },
        "arts": {
            str(key): str(art_id) for key, art_id in sorted((value.get("arts") or {}).items())
        },
        "talents": sorted(
            (
                {"point_slot": int(item["point_slot"]), "talent_id": str(item["talent_id"])}
                for item in value.get("talents", ())
            ),
            key=lambda item: item["point_slot"],
        ),
    }


class DoctrineService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> DoctrineCollectionView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            current = await self._current_configuration(session, character)
            blocker = await find_combat_configuration_blocker(session, character.id)
            rows = list(
                (
                    await session.scalars(
                        select(CharacterDoctrine)
                        .where(CharacterDoctrine.character_id == character.id)
                        .order_by(CharacterDoctrine.created_at, CharacterDoctrine.id)
                    )
                ).all()
            )
            referenced_ids = set()
            for row in rows:
                for value in (row.configuration or {}).get("equipment", {}).values():
                    try:
                        referenced_ids.add(UUID(str(value)))
                    except (ValueError, TypeError):
                        pass
            item_rows = (
                list(
                    (
                        await session.scalars(
                            select(EquipmentItem).where(
                                EquipmentItem.character_id == character.id,
                                EquipmentItem.id.in_(referenced_ids),
                            )
                        )
                    ).all()
                )
                if referenced_ids
                else []
            )
            item_names = {str(item.id): item.item_name for item in item_rows}
            doctrines = []
            for row in rows:
                config = _canonical(row.configuration or {})
                reason = await self._apply_reason(
                    session, character, config, current, blocker is not None
                )
                doctrines.append(
                    DoctrineView(
                        row.id,
                        row.name,
                        row.revision,
                        config,
                        config == current,
                        reason,
                        reason is None and config != current and blocker is None,
                        tuple(
                            (slot, item_names.get(item_id))
                            for slot, item_id in config["equipment"].items()
                        ),
                    )
                )
            return DoctrineCollectionView(
                character.name,
                character.character_class,
                character.selected_path,
                character.combat_configuration_version,
                blocker is not None,
                current,
                tuple(doctrines),
                character.crowns,
                character.level,
            )

    async def create(
        self, actor: int, name: str, expected_configuration_version: int
    ) -> DoctrineMutation | None:
        name = clean_doctrine_name(name)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            rows = list(
                (
                    await session.scalars(
                        select(CharacterDoctrine)
                        .where(CharacterDoctrine.character_id == character.id)
                        .with_for_update()
                    )
                ).all()
            )
            if len(rows) >= MAX_DOCTRINES:
                raise DoctrineRejected("limit")
            config = await self._current_configuration(session, character, lock_rows=True)
            row = CharacterDoctrine(
                character_id=character.id, name=name, configuration=config, revision=0
            )
            session.add(row)
            try:
                await session.flush()
            except IntegrityError as exc:
                raise DoctrineRejected("duplicate_name") from exc
            return DoctrineMutation(True, character.combat_configuration_version, row.id)

    async def begin_name_input(
        self,
        actor: int,
        action: str,
        prompt_message_id: int,
        expected_configuration_version: int,
        doctrine_id: UUID | None = None,
        expected_revision: int = 0,
    ) -> bool:
        if action not in {"create", "rename"} or (action == "create") != (doctrine_id is None):
            return False
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return False
            self._check_version(character, expected_configuration_version)
            if action == "create":
                count = await session.scalar(
                    select(func.count())
                    .select_from(CharacterDoctrine)
                    .where(CharacterDoctrine.character_id == character.id)
                )
                if count >= MAX_DOCTRINES:
                    raise DoctrineRejected("limit")
            else:
                doctrine = await session.scalar(
                    select(CharacterDoctrine)
                    .where(
                        CharacterDoctrine.id == doctrine_id,
                        CharacterDoctrine.character_id == character.id,
                    )
                    .with_for_update()
                )
                if doctrine is None or doctrine.revision != expected_revision:
                    return False
            lease = await session.scalar(
                select(CharacterPendingInput)
                .where(CharacterPendingInput.character_id == character.id)
                .with_for_update()
            )
            if lease is not None and lease.input_kind != "doctrine_name":
                return False
            state = await session.scalar(
                select(CharacterDoctrineInput)
                .where(CharacterDoctrineInput.character_id == character.id)
                .with_for_update()
            )
            if state is None:
                state = CharacterDoctrineInput(character_id=character.id)
                session.add(state)
            state.action = action
            state.doctrine_id = doctrine_id
            state.expected_revision = expected_revision
            state.expected_configuration_version = expected_configuration_version
            state.prompt_message_id = prompt_message_id
            state.updated_at = datetime.now(UTC)
            if lease is None:
                session.add(
                    CharacterPendingInput(
                        character_id=character.id,
                        input_kind="doctrine_name",
                        prompt_message_id=prompt_message_id,
                    )
                )
            else:
                lease.prompt_message_id = prompt_message_id
                lease.updated_at = datetime.now(UTC)
            return True

    async def save_name_reply(
        self, actor: int, prompt_message_id: int, raw_name: str
    ) -> DoctrineMutation | None:
        name = clean_doctrine_name(raw_name)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            state = await session.scalar(
                select(CharacterDoctrineInput)
                .where(CharacterDoctrineInput.character_id == character.id)
                .with_for_update()
            )
            if state is None or state.prompt_message_id != prompt_message_id:
                raise DoctrineRejected("stale_input")
            lease = await session.scalar(
                select(CharacterPendingInput)
                .where(
                    CharacterPendingInput.character_id == character.id,
                    CharacterPendingInput.input_kind == "doctrine_name",
                    CharacterPendingInput.prompt_message_id == prompt_message_id,
                )
                .with_for_update()
            )
            if lease is None:
                raise DoctrineRejected("stale_input")
            if state.expected_configuration_version != character.combat_configuration_version:
                await session.delete(state)
                await session.delete(lease)
                raise DoctrineRejected("stale_configuration")
            if state.action == "create":
                rows = list(
                    (
                        await session.scalars(
                            select(CharacterDoctrine)
                            .where(CharacterDoctrine.character_id == character.id)
                            .with_for_update()
                        )
                    ).all()
                )
                if len(rows) >= MAX_DOCTRINES:
                    await session.delete(state)
                    await session.delete(lease)
                    raise DoctrineRejected("limit")
                config = await self._current_configuration(session, character, lock_rows=True)
                row = CharacterDoctrine(
                    character_id=character.id, name=name, configuration=config, revision=0
                )
                session.add(row)
            else:
                row = await session.scalar(
                    select(CharacterDoctrine)
                    .where(
                        CharacterDoctrine.id == state.doctrine_id,
                        CharacterDoctrine.character_id == character.id,
                    )
                    .with_for_update()
                )
                if row is None or row.revision != state.expected_revision:
                    await session.delete(state)
                    await session.delete(lease)
                    raise DoctrineRejected("stale_doctrine")
                row.name = name
                row.revision += 1
                row.updated_at = datetime.now(UTC)
            await session.delete(state)
            await session.delete(lease)
            try:
                await session.flush()
            except IntegrityError as exc:
                raise DoctrineRejected("duplicate_name") from exc
            return DoctrineMutation(True, character.combat_configuration_version, row.id)

    async def cancel_name_input(self, actor: int) -> bool:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return False
            state = await session.scalar(
                select(CharacterDoctrineInput)
                .where(CharacterDoctrineInput.character_id == character.id)
                .with_for_update()
            )
            lease = await session.scalar(
                select(CharacterPendingInput)
                .where(
                    CharacterPendingInput.character_id == character.id,
                    CharacterPendingInput.input_kind == "doctrine_name",
                )
                .with_for_update()
            )
            if state is None and lease is None:
                return False
            if state is not None:
                await session.delete(state)
            if lease is not None:
                await session.delete(lease)
            return True

    async def overwrite_current(
        self,
        actor: int,
        doctrine_id: UUID,
        expected_revision: int,
        expected_configuration_version: int,
    ) -> DoctrineMutation | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            row = await self._doctrine(session, character.id, doctrine_id, lock=True)
            if row is None or row.revision != expected_revision:
                raise DoctrineRejected("stale_doctrine")
            config = await self._current_configuration(session, character, lock_rows=True)
            if _canonical(row.configuration or {}) == config:
                return DoctrineMutation(False, character.combat_configuration_version, row.id)
            row.configuration = config
            row.revision += 1
            row.updated_at = datetime.now(UTC)
            return DoctrineMutation(True, character.combat_configuration_version, row.id)

    async def delete(
        self, actor: int, doctrine_id: UUID, expected_revision: int
    ) -> DoctrineMutation | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            row = await self._doctrine(session, character.id, doctrine_id, lock=True)
            if row is None or row.revision != expected_revision:
                raise DoctrineRejected("stale_doctrine")
            await session.delete(row)
            return DoctrineMutation(True, character.combat_configuration_version, row.id)

    async def update_component(
        self,
        actor: int,
        doctrine_id: UUID,
        expected_revision: int,
        expected_configuration_version: int,
        component: str,
        value,
    ) -> DoctrineMutation | None:
        if component not in {"path", "equipment", "arts", "talents"}:
            raise DoctrineRejected("invalid_component")
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            row = await self._doctrine(session, character.id, doctrine_id, lock=True)
            if row is None or row.revision != expected_revision:
                raise DoctrineRejected("stale_doctrine")
            config = _canonical(row.configuration or {})
            if component == "path":
                if value is not None and not path_belongs_to_class(
                    str(value), character.character_class
                ):
                    raise DoctrineRejected("wrong_path")
                config["path"] = value
            elif component == "equipment":
                slot, item_id = value
                slot = str(slot)
                if parse_equipment_slot(slot) is None:
                    raise DoctrineRejected("invalid_slot")
                if item_id is None:
                    config["equipment"].pop(slot, None)
                else:
                    owned = await session.scalar(
                        select(EquipmentItem.id).where(
                            EquipmentItem.id == item_id, EquipmentItem.character_id == character.id
                        )
                    )
                    if owned is None:
                        raise DoctrineRejected("item_unavailable")
                    config["equipment"][slot] = str(item_id)
            elif component == "arts":
                slot, art_id = value
                slot = str(slot)
                if slot not in {"1", "2", "3"}:
                    raise DoctrineRejected("invalid_slot")
                if art_id is None:
                    config["arts"].pop(slot, None)
                else:
                    definition = active_art_definition(str(art_id))
                    if (
                        definition is None
                        or definition.character_class != character.character_class
                    ):
                        raise DoctrineRejected("invalid_art")
                    config["arts"][slot] = str(art_id)
                    if len(set(config["arts"].values())) != len(config["arts"]):
                        raise DoctrineRejected("duplicate_art")
            else:
                config["talents"] = value
            updated_configuration = _canonical(config)
            if updated_configuration == _canonical(row.configuration or {}):
                return DoctrineMutation(False, character.combat_configuration_version, row.id)
            row.configuration = updated_configuration
            row.revision += 1
            row.updated_at = datetime.now(UTC)
            return DoctrineMutation(True, character.combat_configuration_version, row.id)

    async def apply(
        self,
        actor: int,
        doctrine_id: UUID,
        expected_revision: int,
        expected_configuration_version: int,
    ) -> DoctrineMutation | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            row = await self._doctrine(session, character.id, doctrine_id, lock=True)
            if row is None or row.revision != expected_revision:
                raise DoctrineRejected("stale_doctrine")
            target = _canonical(row.configuration or {})
            current = await self._current_configuration(session, character, lock_rows=True)
            reason = await self._incomplete_reason(session, character, target)
            if reason:
                raise DoctrineRejected(reason)
            if target == current:
                return DoctrineMutation(False, character.combat_configuration_version, row.id)

            path_changed = target["path"] != character.selected_path
            if character.selected_path is not None and target["path"] is None:
                raise DoctrineRejected("path_cannot_be_cleared")
            current_talent_rows = list(
                (
                    await session.scalars(
                        select(CharacterTalentChoice)
                        .where(CharacterTalentChoice.character_id == character.id)
                        .order_by(CharacterTalentChoice.point_slot)
                        .with_for_update()
                    )
                ).all()
            )
            target_talents = target["talents"]
            existing_talents = [
                {"point_slot": item.point_slot, "talent_id": item.talent_id}
                for item in current_talent_rows
            ]
            talents_changed = target_talents != existing_talents

            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id).with_for_update()
            )
            paid_path_change = path_changed and character.selected_path is not None
            current_talent_pairs = {
                (item.point_slot, item.talent_id) for item in current_talent_rows
            }
            target_talent_pairs = {
                (item["point_slot"], item["talent_id"]) for item in target_talents
            }
            talent_respec = talents_changed and not current_talent_pairs.issubset(
                target_talent_pairs
            )
            if paid_path_change or talent_respec:
                if world is None or world.location not in SAFE_CONFIGURATION_LOCATIONS:
                    raise DoctrineRejected("safe_location_required")
                if paid_path_change and not await self._trial_completed(session, character.id):
                    raise DoctrineRejected("trial_required")
            cost = path_switch_cost(character.level) if paid_path_change else 0
            if talent_respec:
                cost += 2 * crowns_per_level(character.level)
            if character.crowns < cost:
                raise DoctrineRejected("insufficient_crowns")

            equipment = {
                EquipmentSlot(key): UUID(value) for key, value in target["equipment"].items()
            }
            item_ids = tuple(sorted(set(equipment.values()), key=str))
            item_rows = (
                list(
                    (
                        await session.scalars(
                            select(EquipmentItem)
                            .where(
                                EquipmentItem.character_id == character.id,
                                EquipmentItem.id.in_(item_ids),
                            )
                            .order_by(EquipmentItem.id)
                            .with_for_update()
                        )
                    ).all()
                )
                if item_ids
                else []
            )
            item_by_id = {item.id: item for item in item_rows}
            if len(item_by_id) != len(item_ids):
                raise DoctrineRejected("item_unavailable")
            art_map = {int(slot): art_id for slot, art_id in target["arts"].items()}
            if len(set(art_map.values())) != len(art_map):
                raise DoctrineRejected("duplicate_art")
            for art_id in art_map.values():
                definition = active_art_definition(art_id)
                if (
                    definition is None
                    or definition.character_class != character.character_class
                    or character.level < definition.min_level
                    or (definition.path_id is not None and definition.path_id != target["path"])
                ):
                    raise DoctrineRejected("invalid_art")
            if target["path"] is not None and not await self._trial_completed(
                session, character.id
            ):
                raise DoctrineRejected("trial_required")

            character.crowns -= cost
            character.selected_path = target["path"]
            await session.execute(
                delete(CharacterEquipmentSlot).where(
                    CharacterEquipmentSlot.character_id == character.id
                )
            )
            await session.execute(
                delete(CharacterActiveArtSlot).where(
                    CharacterActiveArtSlot.character_id == character.id
                )
            )
            await session.execute(
                delete(CharacterTalentChoice).where(
                    CharacterTalentChoice.character_id == character.id
                )
            )
            await session.flush()
            for slot, item_id in equipment.items():
                session.add(
                    CharacterEquipmentSlot(
                        character_id=character.id, slot=slot.value, equipment_item_id=item_id
                    )
                )
            for slot, art_id in art_map.items():
                session.add(
                    CharacterActiveArtSlot(character_id=character.id, slot=slot, art_id=art_id)
                )
            for talent in target_talents:
                session.add(
                    CharacterTalentChoice(
                        character_id=character.id,
                        point_slot=talent["point_slot"],
                        talent_id=talent["talent_id"],
                    )
                )
            await session.flush()
            try:
                new_configuration = await load_equipment_configuration(session, character)
                stats = resolve_character_combat_stats(character, new_configuration)
            except ValueError as exc:
                raise DoctrineRejected("invalid_configuration") from exc
            character.hp = hp_after_equipment_change(character, stats.hp)
            character.max_hp = stats.hp
            character.combat_configuration_version += 1
            await session.flush()
            return DoctrineMutation(True, character.combat_configuration_version, row.id)

    async def _current_configuration(self, session, character, *, lock_rows=False) -> dict:
        snapshot = await load_equipment_configuration(session, character, lock_rows=lock_rows)
        equipment = {item.slot: item.item_instance_id for item in snapshot.items}
        art_stmt = (
            select(CharacterActiveArtSlot)
            .where(CharacterActiveArtSlot.character_id == character.id)
            .order_by(CharacterActiveArtSlot.slot)
        )
        talent_stmt = (
            select(CharacterTalentChoice)
            .where(CharacterTalentChoice.character_id == character.id)
            .order_by(CharacterTalentChoice.point_slot)
        )
        if lock_rows:
            art_stmt = art_stmt.with_for_update()
            talent_stmt = talent_stmt.with_for_update()
        arts = list((await session.scalars(art_stmt)).all())
        talents = list((await session.scalars(talent_stmt)).all())
        return _canonical(
            {
                "path": character.selected_path,
                "equipment": equipment,
                "arts": {str(item.slot): item.art_id for item in arts},
                "talents": [
                    {"point_slot": item.point_slot, "talent_id": item.talent_id} for item in talents
                ],
            }
        )

    async def _apply_reason(self, session, character, target, current, foreground):
        reason = await self._incomplete_reason(session, character, target)
        if reason:
            return reason
        if target == current:
            return None
        if foreground:
            return "foreground"
        if character.selected_path is not None and target["path"] is None:
            return "path_cannot_be_cleared"
        path_changed = target["path"] != character.selected_path
        current_talents = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice).where(
                        CharacterTalentChoice.character_id == character.id
                    )
                )
            ).all()
        )
        current_talent_data = [
            {"point_slot": item.point_slot, "talent_id": item.talent_id} for item in current_talents
        ]
        talents_changed = target["talents"] != current_talent_data
        paid_path = path_changed and character.selected_path is not None
        current_talent_pairs = {
            (item["point_slot"], item["talent_id"]) for item in current_talent_data
        }
        target_talent_pairs = {
            (item["point_slot"], item["talent_id"]) for item in target["talents"]
        }
        paid_respec = talents_changed and not current_talent_pairs.issubset(target_talent_pairs)
        if not (paid_path or paid_respec):
            return None
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        if world is None or world.location not in SAFE_CONFIGURATION_LOCATIONS:
            return "safe_location_required"
        if paid_path and not await self._trial_completed(session, character.id):
            return "trial_required"
        cost = path_switch_cost(character.level) if paid_path else 0
        if paid_respec:
            cost += 2 * crowns_per_level(character.level)
        if character.crowns < cost:
            return "insufficient_crowns"
        return None

    async def owned_equipment(self, actor: int):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            rows = list(
                (
                    await session.scalars(
                        select(EquipmentItem)
                        .where(EquipmentItem.character_id == character.id)
                        .order_by(EquipmentItem.slot, EquipmentItem.item_name, EquipmentItem.id)
                    )
                ).all()
            )
            return tuple((item.id, item.item_name, item.slot, item.item_level) for item in rows)

    async def _incomplete_reason(self, session, character, config: dict) -> str | None:
        config = _canonical(config)
        path = config["path"]
        if path is not None and not path_belongs_to_class(path, character.character_class):
            return "wrong_path"
        if path is not None and not await self._trial_completed(session, character.id):
            return "trial_required"
        try:
            equipment = {
                EquipmentSlot(slot): UUID(item_id) for slot, item_id in config["equipment"].items()
            }
        except (ValueError, TypeError):
            return "invalid_equipment"
        ids = tuple(sorted(set(equipment.values()), key=str))
        items = (
            list(
                (
                    await session.scalars(
                        select(EquipmentItem).where(
                            EquipmentItem.character_id == character.id, EquipmentItem.id.in_(ids)
                        )
                    )
                ).all()
            )
            if ids
            else []
        )
        item_by_id = {item.id: item for item in items}
        if len(item_by_id) != len(ids):
            return "item_unavailable"
        weapon_compatibility_tags: set[str] = set()
        for item in item_by_id.values():
            weapon = await resolve_equipment_weapon(session, item)
            if weapon is not None:
                weapon_compatibility_tags.update(weapon.compatibility_tags)
        try:
            build_equipment_configuration(
                character,
                [(slot, item_by_id[item_id]) for slot, item_id in equipment.items()],
                version=character.combat_configuration_version,
                talent_choices=tuple(
                    (item["point_slot"], item["talent_id"]) for item in config["talents"]
                ),
            )
        except (ValueError, KeyError, TypeError):
            return "invalid_equipment"

        art_values = list(config["arts"].items())
        if len({value for _, value in art_values}) != len(art_values):
            return "duplicate_art"
        for raw_slot, art_id in art_values:
            try:
                slot = int(raw_slot)
            except ValueError:
                return "invalid_art"
            definition = active_art_definition(art_id)
            if (
                slot not in {1, 2, 3}
                or definition is None
                or definition.character_class != character.character_class
                or character.level < definition.min_level
                or (definition.path_id is not None and definition.path_id != path)
            ):
                return "invalid_art"
            if not weapon_requirement_satisfied(definition, weapon_compatibility_tags):
                return "weapon_requirement"

        talents = config["talents"]
        if len(talents) > talent_points_at_level(character.level):
            return "talent_points"
        seen_slots, seen_ids = set(), set()
        for item in talents:
            try:
                slot, talent_id = int(item["point_slot"]), str(item["talent_id"])
            except (KeyError, ValueError, TypeError):
                return "invalid_talents"
            definition = TALENT_DEFINITIONS.get(talent_id)
            if (
                slot < 1
                or slot > talent_points_at_level(character.level)
                or slot > len(TALENT_POINT_LEVELS)
                or slot in seen_slots
                or talent_id in seen_ids
                or definition is None
                or definition.character_class != character.character_class
                or definition.level > TALENT_POINT_LEVELS[slot - 1]
                or character.level < definition.level
                or definition.level not in IMPLEMENTED_TALENT_LEVELS
            ):
                return "invalid_talents"
            seen_slots.add(slot)
            seen_ids.add(talent_id)
        return None

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _lock_character(self, session, actor):
        character_id = await session.scalar(
            select(Character.id).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )
        if character_id is None:
            return None
        try:
            return await lock_for_combat_configuration_mutation(session, character_id)
        except CombatConfigurationLocked as exc:
            raise DoctrineRejected("foreground") from exc

    @staticmethod
    def _check_version(character, expected):
        if character.combat_configuration_version != expected:
            raise DoctrineRejected("stale_configuration")

    @staticmethod
    async def _doctrine(session, character_id, doctrine_id, *, lock):
        statement = select(CharacterDoctrine).where(
            CharacterDoctrine.id == doctrine_id,
            CharacterDoctrine.character_id == character_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    @staticmethod
    async def _trial_completed(session, character_id) -> bool:
        if await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id, Unlock.unlock_id == COMPLETED_TRIAL_UNLOCK
            )
        ):
            return True
        return (
            await session.scalar(
                select(ClassTrialState.status).where(ClassTrialState.character_id == character_id)
            )
            == "completed"
        )
