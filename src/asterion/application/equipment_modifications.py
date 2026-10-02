"""Transactional equipment modifications backed by the existing item instance."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.equipment_configuration import (
    build_equipment_configuration,
    hp_after_equipment_change,
    load_equipment_configuration,
    reconcile_character_hp,
    resolve_character_combat_stats,
)
from asterion.application.equipment_view import EquipmentItemView, EquipmentViewService
from asterion.application.inventory import INVENTORY_CAPACITY
from asterion.application.professions import REFUGE
from asterion.domain.equipment import assignment_for_item_slot, parse_equipment_slot
from asterion.domain.equipment_modifications import (
    dismantle_quantities,
    effective_enchantment_potency,
    enchantment_compatible,
    enchantment_potency_for,
    enhancement_crown_cost,
    enhancement_fragment_cost,
    equipment_grade,
    reroll_candidates,
    reroll_crown_cost,
    reroll_secondary,
    rune_compatible,
)
from asterion.domain.equipment_stats import (
    equipment_stat_contribution,
    item_snapshot_from_persisted,
)
from asterion.domain.professions import (
    IRON,
    MATERIAL_NAMES,
    RECIPE_BY_ID,
    RESIDUE,
    SLOT_CAPS,
    MaterialRequirement,
    ProfessionSlot,
    apply_profession_pxp,
    recipe_pxp,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    CharacterProfession,
    DungeonRun,
    DungeonRunMember,
    EquipmentItem,
    MaterialStack,
    RuneStack,
    Unlock,
    WorldState,
)


class EquipmentModificationRejected(ValueError):
    """A stale, invalid or unaffordable equipment mutation was rejected."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class OperationPreview:
    item: EquipmentItemView
    item_version: int
    combat_configuration_version: int
    available: bool
    reason: str | None
    details: dict[str, Any]


class EquipmentModificationService:
    """One lock, item-local revision and configuration reconciliation for C2."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.views = EquipmentViewService(sessions, server_id)

    async def enhancement_preview(self, actor: int, item_id: UUID) -> OperationPreview | None:
        async with self.sessions() as session:
            context = await self._read_context(session, actor, item_id)
            if context is None:
                return None
            character, item, equipped = context
            payload = dict(item.payload or {})
            current = int(payload.get("enhancement", 0))
            target = current + 1
            if current >= 10:
                return self._preview(character, item, equipped, False, "MAX_ENHANCEMENT", {})
            grade = equipment_grade(item.item_level)
            grade_id = ("i", "ii", "iii", "iv", "v", "vi")[grade - 1]
            fragment_id = f"material.tdo.fragmento_aprimoramento_{grade_id}"
            required = enhancement_fragment_cost(item.slot, target)
            owned = await self._material_total(session, character.id, fragment_id)
            cost = enhancement_crown_cost(item.item_level, item.slot, item.rarity, target)
            now = self._contribution(item, payload)
            next_payload = {**payload, "enhancement": target}
            next_stats = self._contribution(item, next_payload)
            reason = None
            if await self._mutation_blocked(session, character.id):
                reason = "FOREGROUND"
            elif owned < required:
                reason = "FRAGMENTS"
            elif character.crowns < cost:
                reason = "CROWNS"
            return self._preview(
                character,
                item,
                equipped,
                reason is None,
                reason,
                {
                    "target_enhancement": target,
                    "current_contribution": now,
                    "next_contribution": next_stats,
                    "fragment_id": fragment_id,
                    "fragment_owned": owned,
                    "fragment_required": required,
                    "crown_cost": cost,
                },
            )

    async def runes(
        self, actor: int, item_id: UUID, affinity: str = "A"
    ) -> OperationPreview | None:
        async with self.sessions() as session:
            context = await self._read_context(session, actor, item_id)
            if context is None:
                return None
            character, item, equipped = context
            if affinity not in self._affinities(item):
                return self._preview(character, item, equipped, False, "AFFINITY", {})
            current = self._installed_rune(item, affinity)
            stacks = (
                await session.scalars(
                    select(RuneStack)
                    .where(RuneStack.character_id == character.id, RuneStack.quantity > 0)
                    .order_by(RuneStack.family, RuneStack.rarity, RuneStack.grade, RuneStack.id)
                )
            ).all()
            candidates = [
                self._rune_data(row)
                for row in stacks
                if row.grade <= equipment_grade(item.item_level)
                and rune_compatible(item.slot, row.family, affinity)
            ]
            can_remove = current is not None and await self._rune_return_fits(
                session, character.id, current, release_stack=False
            )
            reason = "FOREGROUND" if await self._mutation_blocked(session, character.id) else None
            return self._preview(
                character,
                item,
                equipped,
                reason is None,
                reason,
                {
                    "affinity": affinity,
                    "current": current,
                    "candidates": candidates,
                    "can_remove": can_remove,
                },
            )

    async def rune_preview(
        self, actor: int, item_id: UUID, affinity: str, stack_id: UUID
    ) -> OperationPreview | None:
        view = await self.runes(actor, item_id, affinity)
        if view is None:
            return None
        candidate = next(
            (row for row in view.details.get("candidates", ()) if row["stack_id"] == stack_id), None
        )
        if candidate is None:
            return OperationPreview(
                view.item,
                view.item_version,
                view.combat_configuration_version,
                False,
                "RUNE_UNAVAILABLE",
                {"affinity": affinity},
            )
        async with self.sessions() as session:
            character_id = await self._character_id(session, actor)
            release = candidate["quantity"] == 1
            fits = await self._rune_return_fits(
                session, character_id, view.details.get("current"), release_stack=release
            )
        reason = view.reason or (None if fits else "INVENTORY_FULL")
        return OperationPreview(
            view.item,
            view.item_version,
            view.combat_configuration_version,
            reason is None,
            reason,
            {
                "affinity": affinity,
                "current": view.details["current"],
                "candidate": candidate,
                "replacement": view.details["current"] is not None,
            },
        )

    async def enchantments(self, actor: int, item_id: UUID) -> OperationPreview | None:
        async with self.sessions() as session:
            context = await self._read_context(session, actor, item_id)
            if context is None:
                return None
            character, item, equipped = context
            profession = await session.scalar(
                select(CharacterProfession).where(
                    CharacterProfession.character_id == character.id,
                    CharacterProfession.profession_id == "artificer",
                )
            )
            unlocks = set(
                (
                    await session.scalars(
                        select(Unlock.unlock_id).where(Unlock.character_id == character.id)
                    )
                ).all()
            )
            candidates = []
            for recipe in RECIPE_BY_ID.values():
                if recipe.output_kind != "enchantment":
                    continue
                if recipe.unlock_id is not None and recipe.unlock_id not in unlocks:
                    continue
                if not enchantment_compatible(item.slot, recipe.output_family or ""):
                    continue
                if recipe.grade > equipment_grade(item.item_level):
                    continue
                candidates.append(
                    {
                        "recipe_id": recipe.recipe_id,
                        "name": recipe.name,
                        "rarity": recipe.rarity,
                        "grade": recipe.grade,
                        "stat": recipe.output_id,
                        "potency": effective_enchantment_potency(
                            item.slot,
                            recipe.output_family or "",
                            recipe.rarity or "",
                            recipe.grade,
                        ),
                        "craftable": bool(profession and profession.level >= recipe.required_level),
                    }
                )
            reason = "FOREGROUND" if await self._mutation_blocked(session, character.id) else None
            if reason is None and not await self._safe_location(session, character.id):
                reason = "LOCATION"
            return self._preview(
                character,
                item,
                equipped,
                reason is None,
                reason,
                {
                    "current": (item.payload or {}).get("enchantment"),
                    "candidates": candidates,
                },
            )

    async def enchantment_preview(
        self, actor: int, item_id: UUID, recipe_id: str
    ) -> OperationPreview | None:
        async with self.sessions() as session:
            context = await self._read_context(session, actor, item_id)
            if context is None:
                return None
            character, item, equipped = context
            recipe = RECIPE_BY_ID.get(recipe_id)
            if recipe is None or recipe.output_kind != "enchantment":
                return self._preview(character, item, equipped, False, "RECIPE", {})
            profession = await session.scalar(
                select(CharacterProfession).where(
                    CharacterProfession.character_id == character.id,
                    CharacterProfession.profession_id == "artificer",
                )
            )
            known = (
                recipe.unlock_id is None
                or await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id, Unlock.unlock_id == recipe.unlock_id
                    )
                )
                is not None
            )
            requirements = tuple(recipe.fixed_materials)
            materials, result_bound = await self._ingredient_preview(
                session, character.id, requirements
            )
            token = self._ingredient_token(materials, recipe_id, item, character)
            reason = None
            if await self._mutation_blocked(session, character.id):
                reason = "FOREGROUND"
            elif not await self._safe_location(session, character.id):
                reason = "LOCATION"
            elif not known:
                reason = "RECIPE"
            elif profession is None or profession.level < recipe.required_level:
                reason = "PROFESSION"
            elif recipe.grade > equipment_grade(item.item_level) or not enchantment_compatible(
                item.slot, recipe.output_family or ""
            ):
                reason = "INCOMPATIBLE"
            elif any(row["owned"] < row["required"] for row in materials):
                reason = "MATERIALS"
            elif character.crowns < (recipe.fixed_crown_cost or 0):
                reason = "CROWNS"
            return self._preview(
                character,
                item,
                equipped,
                reason is None,
                reason,
                {
                    "current": (item.payload or {}).get("enchantment"),
                    "candidate": {
                        "recipe_id": recipe.recipe_id,
                        "name": recipe.name,
                        "rarity": recipe.rarity,
                        "grade": recipe.grade,
                        "stat": recipe.output_id,
                        "potency": effective_enchantment_potency(
                            item.slot,
                            recipe.output_family or "",
                            recipe.rarity or "",
                            recipe.grade,
                        ),
                    },
                    "materials": materials,
                    "crown_cost": recipe.fixed_crown_cost or 0,
                    "result_bound": result_bound or item.bound,
                    "token": token,
                },
            )

    async def reroll_preview(
        self, actor: int, item_id: UUID, index: int
    ) -> OperationPreview | None:
        async with self.sessions() as session:
            context = await self._read_context(session, actor, item_id)
            if context is None:
                return None
            character, item, equipped = context
            payload = item.payload or {}
            secondaries = payload.get("secondaries", [])
            possible = reroll_candidates(item.slot, secondaries, index)
            cost = reroll_crown_cost(item.item_level, int(payload.get("reroll_count", 0)))
            reason = None
            if await self._mutation_blocked(session, character.id):
                reason = "FOREGROUND"
            elif not possible:
                reason = "NO_CANDIDATES"
            elif character.crowns < cost:
                reason = "CROWNS"
            return self._preview(
                character,
                item,
                equipped,
                reason is None,
                reason,
                {
                    "index": index,
                    "current": secondaries[index] if 0 <= index < len(secondaries) else None,
                    "possible": tuple(possible),
                    "crown_cost": cost,
                },
            )

    async def dismantle_preview(self, actor: int, item_id: UUID) -> OperationPreview | None:
        async with self.sessions() as session:
            context = await self._read_context(session, actor, item_id)
            if context is None:
                return None
            character, item, equipped = context
            materials = self._dismantle_materials(item)
            reason = None
            if await self._mutation_blocked(session, character.id):
                reason = "FOREGROUND"
            elif (item.payload or {}).get("favorite"):
                reason = "FAVORITE"
            elif (item.payload or {}).get("locked"):
                reason = "LOCKED"
            elif self._has_rune(item):
                reason = "EXTRACT_RUNES"
            elif not await self._materials_fit_after_dismantle(
                session, character.id, materials, item.bound
            ):
                reason = "INVENTORY_FULL"
            return self._preview(
                character,
                item,
                equipped,
                reason is None,
                reason,
                {
                    "materials": [
                        {
                            "name": MATERIAL_NAMES.get(mid, mid),
                            "material_id": mid,
                            "quantity": amount,
                            "bound": item.bound,
                        }
                        for mid, amount in materials
                    ],
                    "needs_mythic_confirmation": item.rarity.casefold() in {"mítico", "mythic"},
                },
            )

    async def enhance(
        self,
        actor: int,
        item_id: UUID,
        *,
        expected_item_version: int,
        expected_configuration_version: int,
    ) -> OperationPreview | None:
        async with self.sessions.begin() as session:
            context = await self._locked_context(
                session, actor, item_id, expected_item_version, expected_configuration_version
            )
            if context is None:
                return None
            character, item, equipped = context
            payload = dict(item.payload or {})
            target = int(payload.get("enhancement", 0)) + 1
            if target > 10:
                raise EquipmentModificationRejected("MAX_ENHANCEMENT")
            cost = enhancement_crown_cost(item.item_level, item.slot, item.rarity, target)
            grade = equipment_grade(item.item_level)
            grade_id = ("i", "ii", "iii", "iv", "v", "vi")[grade - 1]
            fragment_id = f"material.tdo.fragmento_aprimoramento_{grade_id}"
            required = enhancement_fragment_cost(item.slot, target)
            if character.crowns < cost:
                raise EquipmentModificationRejected("CROWNS")
            old_configuration = await self._old_configuration(session, character, equipped)
            await self._consume_material(session, character.id, fragment_id, required)
            character.crowns -= cost
            payload["enhancement"] = target
            self._save_payload(item, payload)
            await self._update_active_configuration(session, character, equipped, old_configuration)
        return await self.enhancement_preview(actor, item_id)

    async def install_rune(
        self,
        actor: int,
        item_id: UUID,
        affinity: str,
        stack_id: UUID,
        *,
        expected_item_version: int,
        expected_configuration_version: int,
    ) -> OperationPreview | None:
        async with self.sessions.begin() as session:
            context = await self._locked_context(
                session, actor, item_id, expected_item_version, expected_configuration_version
            )
            if context is None:
                return None
            character, item, equipped = context
            if affinity not in self._affinities(item):
                raise EquipmentModificationRejected("AFFINITY")
            stack = await session.scalar(
                select(RuneStack)
                .where(
                    RuneStack.id == stack_id,
                    RuneStack.character_id == character.id,
                )
                .with_for_update()
            )
            if stack is None or stack.quantity <= 0:
                raise EquipmentModificationRejected("RUNE_UNAVAILABLE")
            if stack.grade > equipment_grade(item.item_level) or not rune_compatible(
                item.slot, stack.family, affinity
            ):
                raise EquipmentModificationRejected("INCOMPATIBLE")
            old = self._installed_rune(item, affinity)
            new = self._rune_data(stack)
            if old is not None and self._same_rune(old, new):
                raise EquipmentModificationRejected("SAME_RUNE")
            if not await self._rune_return_fits(
                session, character.id, old, release_stack=stack.quantity == 1
            ):
                raise EquipmentModificationRejected("INVENTORY_FULL")
            old_configuration = await self._old_configuration(session, character, equipped)
            stack.quantity -= 1
            if stack.quantity == 0:
                await session.delete(stack)
                await session.flush()
            if old is not None:
                await self._put_rune(session, character.id, old)
            payload = dict(item.payload or {})
            self._set_installed_rune(
                payload,
                item,
                affinity,
                {key: new[key] for key in ("family", "rarity", "grade", "potency", "bound")},
            )
            self._save_payload(item, payload)
            await self._update_active_configuration(session, character, equipped, old_configuration)
        return await self.runes(actor, item_id, affinity)

    async def remove_rune(
        self,
        actor: int,
        item_id: UUID,
        affinity: str,
        *,
        expected_item_version: int,
        expected_configuration_version: int,
    ) -> OperationPreview | None:
        async with self.sessions.begin() as session:
            context = await self._locked_context(
                session, actor, item_id, expected_item_version, expected_configuration_version
            )
            if context is None:
                return None
            character, item, equipped = context
            if affinity not in self._affinities(item):
                raise EquipmentModificationRejected("AFFINITY")
            old = self._installed_rune(item, affinity)
            if old is None:
                raise EquipmentModificationRejected("NO_RUNE")
            if not await self._rune_return_fits(session, character.id, old, release_stack=False):
                raise EquipmentModificationRejected("INVENTORY_FULL")
            old_configuration = await self._old_configuration(session, character, equipped)
            await self._put_rune(session, character.id, old)
            payload = dict(item.payload or {})
            self._set_installed_rune(payload, item, affinity, None)
            self._save_payload(item, payload)
            await self._update_active_configuration(session, character, equipped, old_configuration)
        return await self.runes(actor, item_id, affinity)

    async def apply_enchantment(
        self,
        actor: int,
        item_id: UUID,
        recipe_id: str,
        *,
        expected_item_version: int,
        expected_configuration_version: int,
        expected_preview_token: str,
    ) -> OperationPreview | None:
        async with self.sessions.begin() as session:
            context = await self._locked_context(
                session, actor, item_id, expected_item_version, expected_configuration_version
            )
            if context is None:
                return None
            character, item, equipped = context
            await self._require_safe_location(session, character.id)
            recipe = RECIPE_BY_ID.get(recipe_id)
            if recipe is None or recipe.output_kind != "enchantment":
                raise EquipmentModificationRejected("RECIPE")
            if (
                recipe.unlock_id is not None
                and await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == recipe.unlock_id,
                    )
                )
                is None
            ):
                raise EquipmentModificationRejected("RECIPE")
            profession = await session.scalar(
                select(CharacterProfession)
                .where(
                    CharacterProfession.character_id == character.id,
                    CharacterProfession.profession_id == "artificer",
                )
                .with_for_update()
            )
            if profession is None or profession.level < recipe.required_level:
                raise EquipmentModificationRejected("PROFESSION")
            if recipe.grade > equipment_grade(item.item_level) or not enchantment_compatible(
                item.slot, recipe.output_family or ""
            ):
                raise EquipmentModificationRejected("INCOMPATIBLE")
            cost = recipe.fixed_crown_cost or 0
            if character.crowns < cost:
                raise EquipmentModificationRejected("CROWNS")
            ingredients, result_bound = await self._ingredient_preview(
                session, character.id, tuple(recipe.fixed_materials), lock=True
            )
            if any(row["owned"] < row["required"] for row in ingredients):
                raise EquipmentModificationRejected("MATERIALS")
            if (
                self._ingredient_token(ingredients, recipe_id, item, character)
                != expected_preview_token
            ):
                raise EquipmentModificationRejected("STALE")
            old_configuration = await self._old_configuration(session, character, equipped)
            for row in ingredients:
                await self._consume_exact_stacks(session, row["stacks"])
            character.crowns -= cost
            payload = dict(item.payload or {})
            payload["enchantment"] = {
                "enchantment_id": recipe.recipe_id,
                "name": recipe.name,
                "family": recipe.output_family,
                "rarity": recipe.rarity,
                "grade": recipe.grade,
                "potency": enchantment_potency_for(
                    recipe.output_family or "", recipe.rarity or "", recipe.grade
                ),
                "bound": result_bound,
            }
            if result_bound:
                item.bound = True
                payload["bound"] = True
            self._save_payload(item, payload)
            gained = recipe_pxp(recipe.required_level, profession.level, recipe.grade)
            next_level, next_pxp = apply_profession_pxp(
                profession.level, profession.pxp, gained, SLOT_CAPS[ProfessionSlot(profession.slot)]
            )
            profession.level, profession.pxp = next_level, next_pxp
            await self._update_active_configuration(session, character, equipped, old_configuration)
        return await self.enchantments(actor, item_id)

    async def reroll(
        self,
        actor: int,
        item_id: UUID,
        index: int,
        *,
        expected_item_version: int,
        expected_configuration_version: int,
    ) -> OperationPreview | None:
        async with self.sessions.begin() as session:
            context = await self._locked_context(
                session, actor, item_id, expected_item_version, expected_configuration_version
            )
            if context is None:
                return None
            character, item, equipped = context
            payload = dict(item.payload or {})
            secondaries = list(payload.get("secondaries", []))
            if not reroll_candidates(item.slot, secondaries, index):
                raise EquipmentModificationRejected("NO_CANDIDATES")
            count = int(payload.get("reroll_count", 0))
            cost = reroll_crown_cost(item.item_level, count)
            if character.crowns < cost:
                raise EquipmentModificationRejected("CROWNS")
            old_configuration = await self._old_configuration(session, character, equipped)
            replacement = reroll_secondary(
                str(item.id),
                item.slot,
                item.rarity,
                item.item_level,
                secondaries,
                index,
                count + 1,
            )
            secondaries[index] = replacement
            payload["secondaries"] = secondaries
            payload["reroll_count"] = count + 1
            character.crowns -= cost
            self._save_payload(item, payload)
            await self._update_active_configuration(session, character, equipped, old_configuration)
        return await self.reroll_preview(actor, item_id, index)

    async def dismantle(
        self,
        actor: int,
        item_id: UUID,
        *,
        expected_item_version: int,
        expected_configuration_version: int,
        confirm_mythic: bool = False,
    ) -> None:
        async with self.sessions.begin() as session:
            context = await self._locked_context(
                session, actor, item_id, expected_item_version, expected_configuration_version
            )
            if context is None:
                raise EquipmentModificationRejected("ITEM_UNAVAILABLE")
            character, item, equipped = context
            payload = item.payload or {}
            if payload.get("favorite"):
                raise EquipmentModificationRejected("FAVORITE")
            if payload.get("locked"):
                raise EquipmentModificationRejected("LOCKED")
            if self._has_rune(item):
                raise EquipmentModificationRejected("EXTRACT_RUNES")
            if item.rarity.casefold() in {"mítico", "mythic"} and not confirm_mythic:
                raise EquipmentModificationRejected("CONFIRM_MYTHIC")
            materials = self._dismantle_materials(item)
            if not await self._materials_fit_after_dismantle(
                session, character.id, materials, item.bound
            ):
                raise EquipmentModificationRejected("INVENTORY_FULL")
            old_configuration = await self._old_configuration(session, character, equipped)
            if equipped:
                # Validate the complete final equipment arrangement before touching
                # the slot or inventory rows. This is the same validator used by
                # equip/unequip, including level, 2H and Mythic invariants.
                rows = list(
                    (
                        await session.scalars(
                            select(CharacterEquipmentSlot)
                            .where(CharacterEquipmentSlot.character_id == character.id)
                            .with_for_update()
                        )
                    ).all()
                )
                remaining_ids = [
                    row.equipment_item_id for row in rows if row.equipment_item_id != item.id
                ]
                remaining = (
                    list(
                        (
                            await session.scalars(
                                select(EquipmentItem)
                                .where(
                                    EquipmentItem.id.in_(remaining_ids),
                                    EquipmentItem.character_id == character.id,
                                )
                                .with_for_update()
                            )
                        ).all()
                    )
                    if remaining_ids
                    else []
                )
                by_id = {row.id: row for row in remaining}
                if len(by_id) != len(remaining_ids):
                    raise EquipmentModificationRejected("INVALID_CONFIGURATION")
                final = [
                    (parse_equipment_slot(row.slot), by_id[row.equipment_item_id])
                    for row in rows
                    if row.equipment_item_id != item.id
                ]
                if any(slot is None for slot, _ in final):
                    raise EquipmentModificationRejected("INVALID_CONFIGURATION")
                build_equipment_configuration(
                    character,
                    final,
                    version=character.combat_configuration_version + 1,
                    talent_choices=old_configuration.talent_choices,
                )
                target_slot = next((row for row in rows if row.equipment_item_id == item.id), None)
                if target_slot is None:
                    raise EquipmentModificationRejected("INVALID_CONFIGURATION")
                await session.delete(target_slot)
                await session.flush()
            await session.delete(item)
            await session.flush()
            for material_id, quantity in materials:
                await self._put_material(session, character.id, material_id, quantity, item.bound)
            await self._update_active_configuration(session, character, equipped, old_configuration)

    async def set_favorite(
        self,
        actor: int,
        item_id: UUID,
        value: bool,
        *,
        expected_item_version: int,
        expected_configuration_version: int,
    ) -> OperationPreview | None:
        return await self._set_flag(
            actor, item_id, "favorite", value, expected_item_version, expected_configuration_version
        )

    async def set_locked(
        self,
        actor: int,
        item_id: UUID,
        value: bool,
        *,
        expected_item_version: int,
        expected_configuration_version: int,
    ) -> OperationPreview | None:
        return await self._set_flag(
            actor, item_id, "locked", value, expected_item_version, expected_configuration_version
        )

    async def _set_flag(
        self,
        actor: int,
        item_id: UUID,
        key: str,
        value: bool,
        expected_item_version: int,
        expected_configuration_version: int,
    ) -> OperationPreview | None:
        async with self.sessions.begin() as session:
            context = await self._locked_context(
                session, actor, item_id, expected_item_version, expected_configuration_version
            )
            if context is None:
                return None
            character, item, _ = context
            payload = dict(item.payload or {})
            if bool(payload.get(key, False)) == value:
                return self._preview(character, item, None, True, None, {})
            payload[key] = value
            self._save_payload(item, payload)
        return await self.dismantle_preview(actor, item_id)

    async def _read_context(
        self, session: AsyncSession, actor: int, item_id: UUID
    ) -> tuple[Character, EquipmentItem, Any] | None:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )
        if character is None:
            return None
        item = await session.scalar(
            select(EquipmentItem).where(
                EquipmentItem.id == item_id,
                EquipmentItem.character_id == character.id,
            )
        )
        if item is None:
            return None
        equipped = await session.scalar(
            select(CharacterEquipmentSlot).where(
                CharacterEquipmentSlot.character_id == character.id,
                CharacterEquipmentSlot.equipment_item_id == item.id,
            )
        )
        return character, item, equipped

    async def _locked_context(
        self,
        session: AsyncSession,
        actor: int,
        item_id: UUID,
        expected_item_version: int,
        expected_configuration_version: int,
    ) -> tuple[Character, EquipmentItem, Any] | None:
        character_id = await self._character_id(session, actor)
        if character_id is None:
            return None
        try:
            character = await lock_for_combat_configuration_mutation(session, character_id)
        except CombatConfigurationLocked as exc:
            raise EquipmentModificationRejected("FOREGROUND") from exc
        if character is None:
            return None
        if await self._dungeon_active(session, character.id):
            raise EquipmentModificationRejected("FOREGROUND")
        item = await session.scalar(
            select(EquipmentItem)
            .where(
                EquipmentItem.id == item_id,
                EquipmentItem.character_id == character.id,
            )
            .with_for_update()
        )
        if item is None:
            return None
        if (
            character.combat_configuration_version != expected_configuration_version
            or self._item_version(item) != expected_item_version
        ):
            raise EquipmentModificationRejected("STALE")
        equipped = await session.scalar(
            select(CharacterEquipmentSlot)
            .where(
                CharacterEquipmentSlot.character_id == character.id,
                CharacterEquipmentSlot.equipment_item_id == item.id,
            )
            .with_for_update()
        )
        return character, item, equipped

    def _preview(
        self,
        character: Character,
        item: EquipmentItem,
        equipped: Any,
        available: bool,
        reason: str | None,
        details: dict[str, Any],
    ) -> OperationPreview:
        assignment = assignment_for_item_slot(item.slot)
        if assignment is None:
            raise EquipmentModificationRejected("INVALID_ITEM")
        slot = parse_equipment_slot(equipped.slot) if equipped is not None else None
        view = self.views._item_view(item, slot, character.level)
        return OperationPreview(
            view,
            self._item_version(item),
            character.combat_configuration_version,
            available,
            reason,
            details,
        )

    @staticmethod
    def _item_version(item: EquipmentItem) -> int:
        return int((item.payload or {}).get("item_version", 0))

    @staticmethod
    def _save_payload(item: EquipmentItem, payload: dict[str, Any]) -> None:
        payload["item_version"] = int(payload.get("item_version", 0)) + 1
        item.payload = payload

    async def _character_id(self, session: AsyncSession, actor: int) -> UUID | None:
        return await session.scalar(
            select(Character.id).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    @staticmethod
    async def _dungeon_active(session: AsyncSession, character_id: UUID) -> bool:
        return (
            await session.scalar(
                select(DungeonRun.id)
                .join(
                    DungeonRunMember,
                    DungeonRunMember.run_id == DungeonRun.id,
                )
                .where(
                    DungeonRunMember.character_id == character_id,
                    DungeonRunMember.status == "active",
                    DungeonRun.status == "active",
                )
                .limit(1)
            )
            is not None
        )

    async def _mutation_blocked(self, session: AsyncSession, character_id: UUID) -> bool:
        from asterion.application.combat_configuration_guard import (
            find_combat_configuration_blocker,
        )

        return await find_combat_configuration_blocker(
            session, character_id
        ) is not None or await self._dungeon_active(session, character_id)

    @staticmethod
    async def _safe_location(session: AsyncSession, character_id: UUID) -> bool:
        return (
            await session.scalar(
                select(WorldState.location).where(WorldState.character_id == character_id)
            )
            == REFUGE
        )

    async def _require_safe_location(self, session: AsyncSession, character_id: UUID) -> None:
        if not await self._safe_location(session, character_id):
            raise EquipmentModificationRejected("LOCATION")

    async def _old_configuration(self, session, character, equipped):
        if equipped is None:
            return None
        old = await load_equipment_configuration(session, character)
        reconcile_character_hp(character, old)
        return old

    async def _update_active_configuration(self, session, character, equipped, old):
        if equipped is None:
            return
        if old is None:
            raise EquipmentModificationRejected("INVALID_CONFIGURATION")
        new = await load_equipment_configuration(session, character)
        stats = resolve_character_combat_stats(character, new)
        new_hp = hp_after_equipment_change(character, stats.hp)
        character.combat_configuration_version += 1
        character.max_hp = stats.hp
        character.hp = new_hp
        await session.flush()

    @staticmethod
    def _affinities(item: EquipmentItem) -> tuple[str, ...]:
        return ("A", "B") if item.slot == "2H" else ("A",)

    @staticmethod
    def _installed_rune(item: EquipmentItem, affinity: str) -> dict[str, Any] | None:
        payload = item.payload or {}
        if item.slot == "2H":
            return (payload.get("runes") or {}).get(affinity)
        return payload.get("rune") if affinity == "A" else None

    @staticmethod
    def _set_installed_rune(
        payload: dict[str, Any],
        item: EquipmentItem,
        affinity: str,
        rune: dict[str, Any] | None,
    ) -> None:
        if item.slot == "2H":
            runes = dict(payload.get("runes") or {})
            if rune is None:
                runes.pop(affinity, None)
            else:
                runes[affinity] = rune
            payload["runes"] = runes
        else:
            payload["rune"] = rune

    @classmethod
    def _has_rune(cls, item: EquipmentItem) -> bool:
        return any(
            cls._installed_rune(item, affinity) is not None for affinity in cls._affinities(item)
        )

    @staticmethod
    def _rune_data(row: RuneStack) -> dict[str, Any]:
        return {
            "stack_id": row.id,
            "family": row.family,
            "rarity": row.rarity,
            "grade": row.grade,
            "potency": row.potency,
            "bound": row.bound,
            "quantity": row.quantity,
        }

    @staticmethod
    def _same_rune(old: dict[str, Any], new: dict[str, Any]) -> bool:
        return all(
            old.get(key) == new.get(key)
            for key in ("family", "rarity", "grade", "potency", "bound")
        )

    async def _rune_return_fits(
        self,
        session: AsyncSession,
        character_id: UUID,
        old: dict[str, Any] | None,
        *,
        release_stack: bool,
    ) -> bool:
        if old is None:
            return True
        matching = await session.scalar(
            select(RuneStack.id).where(
                RuneStack.character_id == character_id,
                RuneStack.family == old["family"],
                RuneStack.rarity == old["rarity"],
                RuneStack.grade == old["grade"],
                RuneStack.bound.is_(bool(old["bound"])),
            )
        )
        if matching is not None:
            return True
        return (
            await self._inventory_slots(session, character_id) - int(release_stack)
            < INVENTORY_CAPACITY
        )

    @staticmethod
    async def _put_rune(session: AsyncSession, character_id: UUID, rune: dict[str, Any]) -> None:
        stack = await session.scalar(
            select(RuneStack)
            .where(
                RuneStack.character_id == character_id,
                RuneStack.family == rune["family"],
                RuneStack.rarity == rune["rarity"],
                RuneStack.grade == rune["grade"],
                RuneStack.bound.is_(bool(rune["bound"])),
            )
            .with_for_update()
        )
        if stack is None:
            session.add(
                RuneStack(
                    character_id=character_id,
                    family=rune["family"],
                    rarity=rune["rarity"],
                    grade=rune["grade"],
                    potency=rune["potency"],
                    quantity=1,
                    bound=bool(rune["bound"]),
                )
            )
        else:
            if stack.potency != rune["potency"]:
                raise EquipmentModificationRejected("RUNE_IDENTITY")
            stack.quantity += 1

    @staticmethod
    async def _material_total(session: AsyncSession, character_id: UUID, material_id: str) -> int:
        return int(
            await session.scalar(
                select(func.coalesce(func.sum(MaterialStack.quantity), 0)).where(
                    MaterialStack.character_id == character_id,
                    MaterialStack.material_id == material_id,
                )
            )
            or 0
        )

    @staticmethod
    async def _consume_material(
        session: AsyncSession,
        character_id: UUID,
        material_id: str,
        required: int,
    ) -> None:
        rows = list(
            (
                await session.scalars(
                    select(MaterialStack)
                    .where(
                        MaterialStack.character_id == character_id,
                        MaterialStack.material_id == material_id,
                        MaterialStack.quantity > 0,
                    )
                    .order_by(MaterialStack.bound, MaterialStack.id)
                    .with_for_update()
                )
            ).all()
        )
        if sum(row.quantity for row in rows) < required:
            raise EquipmentModificationRejected("MATERIALS")
        remaining = required
        for row in rows:
            amount = min(row.quantity, remaining)
            row.quantity -= amount
            remaining -= amount
            if row.quantity == 0:
                await session.delete(row)
            if remaining == 0:
                break

    @staticmethod
    async def _ingredient_preview(
        session: AsyncSession,
        character_id: UUID,
        requirements: tuple[MaterialRequirement, ...],
        *,
        lock: bool = False,
    ) -> tuple[list[dict[str, Any]], bool]:
        result: list[dict[str, Any]] = []
        bound = False
        for requirement in requirements:
            statement = (
                select(MaterialStack)
                .where(
                    MaterialStack.character_id == character_id,
                    MaterialStack.material_id == requirement.material_id,
                    MaterialStack.quantity > 0,
                )
                .order_by(MaterialStack.bound, MaterialStack.id)
            )
            if lock:
                statement = statement.with_for_update()
            rows = list((await session.scalars(statement)).all())
            owned = sum(row.quantity for row in rows)
            remaining = requirement.quantity
            selected = []
            for row in rows:
                if remaining <= 0:
                    break
                quantity = min(remaining, row.quantity)
                selected.append((row.id, quantity, row.bound))
                if requirement.transmits_bind and row.bound:
                    bound = True
                remaining -= quantity
            result.append(
                {
                    "material_id": requirement.material_id,
                    "name": MATERIAL_NAMES.get(requirement.material_id, requirement.material_id),
                    "owned": owned,
                    "required": requirement.quantity,
                    "stacks": tuple(selected),
                }
            )
        return result, bound

    @staticmethod
    def _ingredient_token(
        ingredients: list[dict[str, Any]],
        recipe_id: str,
        item: EquipmentItem,
        character: Character,
    ) -> str:
        parts = [
            recipe_id,
            str(item.id),
            str(item.item_level),
            str((item.payload or {}).get("item_version", 0)),
            str(character.crowns),
        ]
        for ingredient in ingredients:
            parts.append(ingredient["material_id"])
            parts.append(str(ingredient["required"]))
            parts.append(str(ingredient["owned"]))
            parts.extend(
                f"{stack_id}:{quantity}:{int(bound)}"
                for stack_id, quantity, bound in ingredient["stacks"]
            )
        return sha256("|".join(parts).encode()).hexdigest()[:8]

    @staticmethod
    async def _consume_exact_stacks(
        session: AsyncSession, selected: tuple[tuple[UUID, int, bool], ...]
    ) -> None:
        for row_id, quantity, _bound in selected:
            row = await session.scalar(
                select(MaterialStack).where(MaterialStack.id == row_id).with_for_update()
            )
            if row is None or row.quantity < quantity:
                raise EquipmentModificationRejected("STALE")
            row.quantity -= quantity
            if row.quantity == 0:
                await session.delete(row)

    @staticmethod
    def _contribution(item: EquipmentItem, payload: dict[str, Any]):
        assignment = assignment_for_item_slot(item.slot)
        if assignment is None:
            raise EquipmentModificationRejected("INVALID_ITEM")
        snapshot = item_snapshot_from_persisted(
            item_instance_id=str(item.id),
            equipped_slot=assignment.slot.value,
            item_slot=item.slot,
            item_level=item.item_level,
            rarity=item.rarity,
            payload=payload,
        )
        return equipment_stat_contribution(snapshot)

    @staticmethod
    async def _inventory_slots(session: AsyncSession, character_id: UUID) -> int:
        total = 0
        for model in (EquipmentItem, MaterialStack, RuneStack):
            query = select(func.count(model.id)).where(model.character_id == character_id)
            if model is not EquipmentItem:
                query = query.where(model.quantity > 0)
            total += int(await session.scalar(query) or 0)
        from asterion.infrastructure.db.models import ConsumableStack

        total += int(
            await session.scalar(
                select(func.count(ConsumableStack.id)).where(
                    ConsumableStack.character_id == character_id,
                    ConsumableStack.quantity > 0,
                )
            )
            or 0
        )
        return total

    def _dismantle_materials(self, item: EquipmentItem) -> tuple[tuple[str, int], ...]:
        quantities = dismantle_quantities(item.slot, item.rarity)
        basics = (IRON, "material.tdo.couro_escoriado", "material.tdo.erva_cinzenta", RESIDUE)
        name = item.item_name
        blacksmith_names = {
            recipe.output_name
            for recipe in RECIPE_BY_ID.values()
            if recipe.profession_id == "blacksmith" and recipe.output_kind == "equipment"
        }
        leather_names = {
            recipe.output_name
            for recipe in RECIPE_BY_ID.values()
            if recipe.profession_id == "leatherworker" and recipe.output_kind == "equipment"
        }
        jeweler_names = {
            recipe.output_name
            for recipe in RECIPE_BY_ID.values()
            if recipe.profession_id == "jeweler" and recipe.output_kind == "equipment"
        }
        if name in blacksmith_names or name in jeweler_names:
            chosen = [IRON] * quantities.basics
        elif name in leather_names:
            chosen = [basics[1]] * quantities.basics
        else:
            chosen = [
                basics[
                    int.from_bytes(sha256(f"{item.id}:salvage:{ordinal}".encode()).digest(), "big")
                    % 4
                ]
                for ordinal in range(quantities.basics)
            ]
        tally: dict[str, int] = {}
        for material in chosen:
            tally[material] = tally.get(material, 0) + 1
        grade = equipment_grade(item.item_level)
        roman = ("i", "ii", "iii", "iv", "v", "vi")[grade - 1]
        if quantities.catalysts:
            tally[f"material.tdo.catalisador_elite_{roman}"] = quantities.catalysts
        if quantities.fragments:
            tally[f"material.tdo.fragmento_aprimoramento_{roman}"] = quantities.fragments
        return tuple(sorted(tally.items()))

    async def _materials_fit_after_dismantle(
        self,
        session: AsyncSession,
        character_id: UUID,
        materials: tuple[tuple[str, int], ...],
        bound: bool,
    ) -> bool:
        current = await self._inventory_slots(session, character_id)
        missing = 0
        for material_id, _ in materials:
            existing = await session.scalar(
                select(MaterialStack.id)
                .where(
                    MaterialStack.character_id == character_id,
                    MaterialStack.material_id == material_id,
                    MaterialStack.bound.is_(bound),
                )
                .limit(1)
            )
            if existing is None:
                missing += 1
        return current - 1 + missing <= INVENTORY_CAPACITY

    @staticmethod
    async def _put_material(
        session: AsyncSession,
        character_id: UUID,
        material_id: str,
        quantity: int,
        bound: bool,
    ) -> None:
        row = await session.scalar(
            select(MaterialStack)
            .where(
                MaterialStack.character_id == character_id,
                MaterialStack.material_id == material_id,
                MaterialStack.bound.is_(bound),
            )
            .with_for_update()
        )
        if row is None:
            session.add(
                MaterialStack(
                    character_id=character_id,
                    material_id=material_id,
                    quantity=quantity,
                    bound=bound,
                )
            )
        else:
            row.quantity += quantity
