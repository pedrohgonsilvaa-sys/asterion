"""Previewed, atomic, idempotent crafting for the C1 TDO recipe catalog."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    find_combat_configuration_blocker,
    lock_for_combat_configuration_mutation,
)
from asterion.application.equipment import equipment_instance_payload
from asterion.application.professions import (
    REFUGE,
    ProfessionService,
)
from asterion.domain.professions import (
    MATERIAL_NAMES,
    RecipeDefinition,
    canonical_recipe,
    recipe_crown_cost,
    recipe_item_level,
    recipe_materials,
)
from asterion.domain.road import materialize_equipment, rune_potency
from asterion.domain.weapon_metadata import weapon_type_id_for_recipe
from asterion.infrastructure.db.models import (
    BlockedDelivery,
    Character,
    CharacterProfession,
    ConsumableStack,
    CraftingReceipt,
    DungeonRun,
    DungeonRunMember,
    EquipmentItem,
    MaterialStack,
    PendingItem,
    RuneStack,
    Unlock,
    WorldState,
)

INVENTORY_CAPACITY = 60
PENDING_CAPACITY = 20
SAFE_CRAFTING_LOCATIONS = frozenset((REFUGE, "Vigília do Vale"))


class CraftingErrorCode:
    CHARACTER_MISSING = "character_missing"
    UNKNOWN_RECIPE = "unknown_recipe"
    RECIPE_NOT_KNOWN = "recipe_not_known"
    PROFESSION_INACTIVE = "profession_inactive"
    PROFESSION_LEVEL = "profession_level"
    CHARACTER_LEVEL = "character_level"
    WRONG_LOCATION = "wrong_location"
    FOREGROUND = "foreground"
    DELIVERY_BLOCKED = "delivery_blocked"
    INVENTORY_FULL = "inventory_full"
    MATERIALS = "materials"
    CROWNS = "crowns"
    REQUIRES_EQUIPMENT = "requires_equipment"
    STALE_PREVIEW = "stale_preview"
    PREVIEW_CLOSED = "preview_closed"


class CraftingRejected(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class IngredientPreview:
    material_id: str
    name: str
    required: int
    owned: int
    unbound_owned: int
    consumed_stacks: tuple[tuple[str, int, bool], ...] = ()


@dataclass(frozen=True, slots=True)
class RecipeView:
    recipe: RecipeDefinition
    profession_level: int | None
    item_level: int | None
    crown_cost: int
    ingredients: tuple[IngredientPreview, ...]
    known: bool
    available: bool
    reason: str | None
    result_bound: bool
    delivery: str = "Indisponível"


@dataclass(frozen=True, slots=True)
class RecipeListView:
    character_id: UUID
    character_name: str
    character_level: int
    profession_id: str
    profession_level: int | None
    active: bool
    recipes: tuple[RecipeView, ...]


@dataclass(frozen=True, slots=True)
class CraftPreviewView:
    receipt_id: UUID
    recipe: RecipeDefinition
    item_level: int | None
    crown_cost: int
    ingredients: tuple[IngredientPreview, ...]
    result_bound: bool
    profession_level: int
    profession_pxp: int
    delivery: str
    status: str
    output_payload: dict | None = None
    pxp_gained: int = 0
    new_profession_level: int | None = None


class CraftingService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id
        self.professions = ProfessionService(sessions, server_id)

    async def recipes(self, actor: int, profession_id: str) -> RecipeListView | None:
        from asterion.domain.professions import recipes_for

        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            profession_rows = await self._profession_rows(session, character.id)
            active_row = next(
                (row for row in profession_rows if row.profession_id == profession_id), None
            )
            known_special = await self._known_special_ids(session, character.id)
            foreground = await self._has_foreground(session, character.id)
            location = await self._location(session, character.id)
            material_rows = await self._material_rows(session, character.id)
            recipes = []
            for definition in recipes_for(profession_id):
                if definition.unlock_id and definition.unlock_id not in known_special:
                    continue
                recipes.append(
                    await self._recipe_view_for_session(
                        session,
                        character,
                        definition,
                        active_row,
                        material_rows,
                        location,
                        foreground,
                    )
                )
            return RecipeListView(
                character.id,
                character.name,
                character.level,
                profession_id,
                active_row.level if active_row is not None else None,
                active_row is not None,
                tuple(recipes),
            )

    async def recipe(self, actor: int, recipe_id: str) -> RecipeView | None:
        definition = canonical_recipe(recipe_id)
        if definition is None:
            return None
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            if definition.unlock_id and not await self._recipe_known(
                session, character.id, definition
            ):
                return None
            rows = await self._profession_rows(session, character.id)
            active_row = next(
                (row for row in rows if row.profession_id == definition.profession_id), None
            )
            return await self._recipe_view_for_session(
                session,
                character,
                definition,
                active_row,
                await self._material_rows(session, character.id),
                await self._location(session, character.id),
                await self._has_foreground(session, character.id),
            )

    async def preview(self, actor: int, recipe_id: str) -> CraftPreviewView | None:
        definition = canonical_recipe(recipe_id)
        if definition is None:
            raise CraftingRejected(CraftingErrorCode.UNKNOWN_RECIPE)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            rows = await self._profession_rows(session, character.id, lock=True)
            active_row = next(
                (row for row in rows if row.profession_id == definition.profession_id), None
            )
            material_rows = await self._material_rows(session, character.id, lock=True)
            known = await self._recipe_known(session, character.id, definition, lock=True)
            location = await self._location(session, character.id, lock=True)
            foreground = await self._has_foreground(session, character.id)
            recipe_view = await self._recipe_view_for_session(
                session,
                character,
                definition,
                active_row,
                material_rows,
                location,
                foreground,
            )
            # A preview can only be created while Inventory has a valid destination.
            # If capacity changes after the player confirms that preview, recovery
            # may use Pending/BlockedDelivery instead of losing or duplicating output.
            self._require_available(recipe_view, known)
            fingerprint = self._fingerprint(
                character,
                definition,
                rows,
                location,
                material_rows,
                recipe_view.ingredients,
                known,
            )
            existing = await session.scalar(
                select(CraftingReceipt)
                .where(
                    CraftingReceipt.character_id == character.id,
                    CraftingReceipt.recipe_id == recipe_id,
                    CraftingReceipt.status == "preview",
                    CraftingReceipt.preview_fingerprint == fingerprint,
                )
                .order_by(CraftingReceipt.created_at.desc())
                .limit(1)
                .with_for_update()
            )
            if existing is None:
                receipt_id = uuid4()
                existing = CraftingReceipt(
                    id=receipt_id,
                    character_id=character.id,
                    recipe_id=recipe_id,
                    source_key=f"craft:{receipt_id.hex}",
                    status="preview",
                    preview_fingerprint=fingerprint,
                    seed=f"craft:{receipt_id.hex}:materialization",
                )
                session.add(existing)
                await session.flush()
            return self._preview_result(existing, recipe_view, active_row)

    async def commit(self, actor: int, receipt_id: UUID) -> CraftPreviewView | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            receipt = await session.scalar(
                select(CraftingReceipt)
                .where(
                    CraftingReceipt.id == receipt_id,
                    CraftingReceipt.character_id == character.id,
                )
                .with_for_update()
            )
            if receipt is None:
                raise CraftingRejected(CraftingErrorCode.PREVIEW_CLOSED)
            definition = canonical_recipe(receipt.recipe_id)
            if definition is None:
                raise CraftingRejected(CraftingErrorCode.UNKNOWN_RECIPE)
            if receipt.status == "committed":
                return self._committed_result(receipt, definition)
            if receipt.status != "preview":
                raise CraftingRejected(CraftingErrorCode.PREVIEW_CLOSED)

            profession_rows = await self._profession_rows(session, character.id, lock=True)
            active_row = next(
                (row for row in profession_rows if row.profession_id == definition.profession_id),
                None,
            )
            material_rows = await self._material_rows(session, character.id, lock=True)
            known = await self._recipe_known(session, character.id, definition, lock=True)
            location = await self._location(session, character.id, lock=True)
            foreground = await self._has_foreground(session, character.id)
            recipe_view = await self._recipe_view_for_session(
                session,
                character,
                definition,
                active_row,
                material_rows,
                location,
                foreground,
            )
            # Inventory capacity can change after a valid preview. In that
            # case the committed output is recovered through Pending or
            # BlockedDelivery; every other stale condition remains invalid.
            if recipe_view.reason != CraftingErrorCode.INVENTORY_FULL or not known:
                self._require_available(recipe_view, known)
            fingerprint = self._fingerprint(
                character,
                definition,
                profession_rows,
                location,
                material_rows,
                recipe_view.ingredients,
                known,
            )
            if fingerprint != receipt.preview_fingerprint:
                raise CraftingRejected(CraftingErrorCode.STALE_PREVIEW)
            if active_row is None:
                raise CraftingRejected(CraftingErrorCode.PROFESSION_INACTIVE)

            character.crowns -= recipe_view.crown_cost
            await self._consume_materials(session, material_rows, recipe_view.ingredients)
            output = await self._materialize_and_deliver(
                session, character, definition, receipt, recipe_view
            )
            old_profession_level = active_row.level
            old_profession_pxp = active_row.pxp
            progress = await self.professions.progress_after_craft(
                session,
                character,
                definition.profession_id,
                definition.required_level,
                definition.grade,
            )
            pxp_gained = progress[2] if progress is not None else 0
            new_level = progress[1] if progress is not None else active_row.level
            output["craft_details"] = {
                "item_level": recipe_view.item_level,
                "crown_cost": recipe_view.crown_cost,
                "result_bound": recipe_view.result_bound,
                "profession_level": old_profession_level,
                "profession_pxp": old_profession_pxp,
                "pxp_gained": pxp_gained,
                "new_profession_level": new_level,
                "ingredients": [
                    {
                        "material_id": ingredient.material_id,
                        "name": ingredient.name,
                        "required": ingredient.required,
                        "owned": ingredient.owned,
                        "unbound_owned": ingredient.unbound_owned,
                        "consumed_stacks": list(ingredient.consumed_stacks),
                    }
                    for ingredient in recipe_view.ingredients
                ],
            }
            receipt.status = "committed"
            receipt.output_kind = definition.output_kind
            receipt.output_payload = output
            receipt.committed_at = datetime.now(UTC)
            await session.flush()
            return CraftPreviewView(
                receipt_id=receipt.id,
                recipe=definition,
                item_level=recipe_view.item_level,
                crown_cost=recipe_view.crown_cost,
                ingredients=recipe_view.ingredients,
                result_bound=recipe_view.result_bound,
                profession_level=active_row.level,
                profession_pxp=active_row.pxp,
                delivery=str(output.get("delivery", "inventory")),
                status="committed",
                output_payload=output,
                pxp_gained=pxp_gained,
                new_profession_level=new_level,
            )

    @staticmethod
    def _preview_result(
        receipt: CraftingReceipt, recipe_view: RecipeView, active_row: CharacterProfession | None
    ) -> CraftPreviewView:
        if active_row is None:
            raise CraftingRejected(CraftingErrorCode.PROFESSION_INACTIVE)
        return CraftPreviewView(
            receipt.id,
            recipe_view.recipe,
            recipe_view.item_level,
            recipe_view.crown_cost,
            recipe_view.ingredients,
            recipe_view.result_bound,
            active_row.level,
            active_row.pxp,
            recipe_view.delivery,
            receipt.status,
        )

    @staticmethod
    def _committed_result(
        receipt: CraftingReceipt, definition: RecipeDefinition
    ) -> CraftPreviewView:
        payload = dict(receipt.output_payload or {})
        details = payload.get("craft_details", {})
        return CraftPreviewView(
            receipt.id,
            definition,
            details.get("item_level"),
            int(details.get("crown_cost", 0)),
            tuple(
                IngredientPreview(
                    item["material_id"],
                    item["name"],
                    item["required"],
                    item["owned"],
                    item["unbound_owned"],
                    tuple(tuple(consume) for consume in item.get("consumed_stacks", ())),
                )
                for item in details.get("ingredients", ())
            ),
            bool(details.get("result_bound", False)),
            int(details.get("profession_level", 1)),
            int(details.get("profession_pxp", 0)),
            str(payload.get("delivery", "inventory")),
            "committed",
            payload,
            int(details.get("pxp_gained", 0)),
            details.get("new_profession_level"),
        )

    def _recipe_view(
        self, character, recipe, active_row, material_rows, location, foreground
    ) -> RecipeView:
        item_level = None
        reason = None
        if recipe.output_kind == "equipment":
            try:
                item_level = recipe_item_level(character.level, recipe.grade)
            except ValueError:
                reason = CraftingErrorCode.CHARACTER_LEVEL
        required = recipe_materials(recipe, item_level or character.level)
        ingredients, bound = self._plan_ingredients(required, material_rows)
        if recipe.output_kind == "equipment":
            cost = recipe_crown_cost(recipe, item_level or character.level)
        else:
            cost = recipe_crown_cost(recipe, item_level or character.level)
        if recipe.output_kind == "enchantment" and not recipe.creation_enabled:
            reason = CraftingErrorCode.REQUIRES_EQUIPMENT
        elif active_row is None:
            reason = CraftingErrorCode.PROFESSION_INACTIVE
        elif active_row.level < recipe.required_level:
            reason = CraftingErrorCode.PROFESSION_LEVEL
        elif reason is None and any(item.owned < item.required for item in ingredients):
            reason = CraftingErrorCode.MATERIALS
        elif reason is None and character.crowns < cost:
            reason = CraftingErrorCode.CROWNS
        elif reason is None and location not in SAFE_CRAFTING_LOCATIONS:
            reason = CraftingErrorCode.WRONG_LOCATION
        elif reason is None and foreground:
            reason = CraftingErrorCode.FOREGROUND
        elif reason is None and character.delivery_blocked:
            reason = CraftingErrorCode.DELIVERY_BLOCKED
        return RecipeView(
            recipe,
            active_row.level if active_row is not None else None,
            item_level,
            cost,
            ingredients,
            True,
            reason is None,
            reason,
            bound if recipe.output_kind in {"equipment", "rune"} else False,
        )

    async def _recipe_view_for_session(
        self,
        session,
        character,
        recipe,
        active_row,
        material_rows,
        location,
        foreground,
    ) -> RecipeView:
        view = self._recipe_view(character, recipe, active_row, material_rows, location, foreground)
        delivery = await self._delivery_destination(session, character, recipe, view.result_bound)
        if (
            view.reason is None
            and recipe.output_kind in {"equipment", "consumable", "rune"}
            and delivery != "Inventário"
        ):
            view = replace(
                view,
                available=False,
                reason=CraftingErrorCode.INVENTORY_FULL,
            )
        return replace(view, delivery=delivery)

    async def _delivery_destination(self, session, character, recipe, result_bound: bool) -> str:
        if recipe.output_kind not in {"equipment", "consumable", "rune"}:
            return "Indisponível em C1"
        if recipe.output_kind == "consumable":
            stack = await session.scalar(
                select(ConsumableStack).where(
                    ConsumableStack.character_id == character.id,
                    ConsumableStack.consumable_id == recipe.output_id,
                )
            )
            if stack is not None and stack.quantity < 99:
                return "Inventário"
            if stack is None and await self._inventory_slots(session, character.id) < (
                INVENTORY_CAPACITY
            ):
                return "Inventário"
        elif recipe.output_kind == "rune":
            stack = await session.scalar(
                select(RuneStack).where(
                    RuneStack.character_id == character.id,
                    RuneStack.family == recipe.output_family,
                    RuneStack.rarity == recipe.rarity,
                    RuneStack.grade == recipe.grade,
                    RuneStack.bound.is_(result_bound),
                )
            )
            if stack is not None:
                return "Inventário"
            if await self._inventory_slots(session, character.id) < INVENTORY_CAPACITY:
                return "Inventário"
        elif await self._inventory_slots(session, character.id) < INVENTORY_CAPACITY:
            return "Inventário"

        pending_count = int(
            await session.scalar(
                select(func.count(PendingItem.id)).where(PendingItem.character_id == character.id)
            )
            or 0
        )
        return "Pending" if pending_count < PENDING_CAPACITY else "BlockedDelivery"

    @staticmethod
    def _plan_ingredients(required, material_rows) -> tuple[tuple[IngredientPreview, ...], bool]:
        by_material = {}
        for row in material_rows:
            if row.quantity > 0:
                by_material.setdefault(row.material_id, []).append(row)
        previews = []
        result_bound = False
        for requirement in required:
            rows = sorted(
                by_material.get(requirement.material_id, ()),
                key=lambda row: (row.bound, str(row.id)),
            )
            owned = sum(row.quantity for row in rows)
            unbound_owned = sum(row.quantity for row in rows if not row.bound)
            remaining = requirement.quantity
            consumed = []
            for row in rows:
                if remaining <= 0:
                    break
                quantity = min(remaining, row.quantity)
                consumed.append((str(row.id), quantity, bool(row.bound)))
                if requirement.transmits_bind and row.bound:
                    result_bound = True
                remaining -= quantity
            previews.append(
                IngredientPreview(
                    requirement.material_id,
                    MATERIAL_NAMES.get(requirement.material_id, requirement.material_id),
                    requirement.quantity,
                    owned,
                    unbound_owned,
                    tuple(consumed),
                )
            )
        return tuple(previews), result_bound

    @staticmethod
    def _require_available(view: RecipeView, known: bool) -> None:
        if not known:
            raise CraftingRejected(CraftingErrorCode.RECIPE_NOT_KNOWN)
        if view.available:
            return
        raise CraftingRejected(view.reason or CraftingErrorCode.STALE_PREVIEW)

    @staticmethod
    def _fingerprint(
        character, recipe, profession_rows, location, material_rows, ingredients, known
    ) -> str:
        relevant_ids = {entry.material_id for entry in ingredients}
        payload = {
            "character_id": str(character.id),
            "level": character.level,
            "crowns": int(character.crowns),
            "delivery_blocked": bool(character.delivery_blocked),
            "location": location,
            "recipe_id": recipe.recipe_id,
            "known": known,
            # Delivery is intentionally excluded: a preview is created only with
            # valid Inventory capacity, while a later capacity race is recovered
            # through Pending/BlockedDelivery after confirmation.
            "professions": [
                (row.slot, row.profession_id, row.level, row.pxp)
                for row in sorted(profession_rows, key=lambda item: item.slot)
            ],
            "materials": [
                (str(row.id), row.material_id, row.quantity, bool(row.bound))
                for row in sorted(
                    material_rows, key=lambda item: (item.material_id, item.bound, str(item.id))
                )
                if row.material_id in relevant_ids and row.quantity > 0
            ],
            "ingredients": [
                (item.material_id, item.required, item.consumed_stacks) for item in ingredients
            ],
        }
        return sha256(dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    async def _consume_materials(session, material_rows, ingredients) -> None:
        rows_by_id = {str(row.id): row for row in material_rows}
        for ingredient in ingredients:
            remaining = ingredient.required
            for stack_id, quantity, bound in ingredient.consumed_stacks:
                row = rows_by_id.get(stack_id)
                if row is None or row.material_id != ingredient.material_id or row.bound != bound:
                    raise CraftingRejected(CraftingErrorCode.STALE_PREVIEW)
                if row.quantity < quantity:
                    raise CraftingRejected(CraftingErrorCode.STALE_PREVIEW)
                row.quantity -= quantity
                remaining -= quantity
                if row.quantity == 0:
                    await session.delete(row)
            if remaining:
                raise CraftingRejected(CraftingErrorCode.MATERIALS)

    async def _materialize_and_deliver(self, session, character, recipe, receipt, view):
        output_payload: dict
        if recipe.output_kind == "equipment":
            output_payload = materialize_equipment(
                receipt.seed,
                recipe.rarity or "Comum",
                view.item_level or character.level,
                forced_name=recipe.output_name,
                forced_slot=recipe.output_slot,
                bound=view.result_bound,
                weapon_type_id=weapon_type_id_for_recipe(recipe.recipe_id),
            )
            item_id, item_payload = equipment_instance_payload(output_payload)
            source_key = f"{receipt.source_key}:equipment"
            delivery = await self._deliver_equipment(
                session,
                character,
                source_key,
                item_id,
                item_payload,
            )
            result = {"equipment_item_id": str(item_id), "equipment": item_payload}
        elif recipe.output_kind == "consumable":
            output_payload = {"consumable_id": recipe.output_id, "quantity": 1}
            delivery = await self._deliver_consumable(
                session,
                character,
                f"{receipt.source_key}:consumable",
                recipe.output_id or "",
                1,
            )
            result = output_payload
        elif recipe.output_kind == "rune":
            family = recipe.output_family
            if family is None or recipe.rarity is None:
                raise CraftingRejected(CraftingErrorCode.UNKNOWN_RECIPE)
            output_payload = {
                "family": family,
                "rarity": recipe.rarity,
                "grade": recipe.grade,
                "potency": rune_potency(family, recipe.rarity, recipe.grade),
                "bound": view.result_bound,
            }
            delivery = await self._deliver_rune(
                session, character, f"{receipt.source_key}:rune", output_payload
            )
            result = {"rune": output_payload}
        else:
            raise CraftingRejected(CraftingErrorCode.REQUIRES_EQUIPMENT)

        return {**result, "delivery": delivery}

    async def _deliver_equipment(self, session, character, source_key, item_id, payload) -> str:
        if await self._delivery_exists(session, character.id, source_key):
            return "pending_or_inventory"
        if await self._inventory_slots(session, character.id) < INVENTORY_CAPACITY:
            session.add(
                EquipmentItem(
                    id=item_id,
                    character_id=character.id,
                    source_key=source_key,
                    item_name=payload["item_name"],
                    rarity=payload["rarity"],
                    slot=payload["slot"],
                    item_level=payload["item_level"],
                    bound=bool(payload.get("bound", False)),
                    payload=payload,
                )
            )
            return "Inventário"
        return await self._store_pending(
            session, character, source_key, "equipment", payload, 1
        )

    async def _deliver_consumable(self, session, character, source_key, item_id, quantity) -> str:
        if await self._delivery_exists(session, character.id, source_key):
            return "Pending"
        stack = await session.scalar(
            select(ConsumableStack)
            .where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == item_id,
            )
            .with_for_update()
        )
        if stack is not None and stack.quantity + quantity <= 99:
            stack.quantity += quantity
            return "Inventário"
        if (
            stack is None
            and await self._inventory_slots(session, character.id) < INVENTORY_CAPACITY
        ):
            session.add(
                ConsumableStack(character_id=character.id, consumable_id=item_id, quantity=quantity)
            )
            return "Inventário"
        return await self._store_pending(
            session,
            character,
            source_key,
            "consumable",
            {"consumable_id": item_id},
            quantity,
        )

    async def _deliver_rune(self, session, character, source_key, payload) -> str:
        if await self._delivery_exists(session, character.id, source_key):
            return "Pending"
        stack = await session.scalar(
            select(RuneStack)
            .where(
                RuneStack.character_id == character.id,
                RuneStack.family == payload["family"],
                RuneStack.rarity == payload["rarity"],
                RuneStack.grade == payload["grade"],
                RuneStack.bound.is_(payload["bound"]),
            )
            .with_for_update()
        )
        if stack is not None:
            stack.quantity += 1
            return "Inventário"
        if await self._inventory_slots(session, character.id) < INVENTORY_CAPACITY:
            session.add(
                RuneStack(
                    character_id=character.id,
                    family=payload["family"],
                    rarity=payload["rarity"],
                    grade=payload["grade"],
                    potency=payload["potency"],
                    quantity=1,
                    bound=payload["bound"],
                )
            )
            return "Inventário"
        return await self._store_pending(
            session, character, source_key, "rune", payload, 1
        )

    async def _store_pending(self, session, character, source_key, kind, payload, quantity):
        count = int(
            await session.scalar(
                select(func.count(PendingItem.id)).where(PendingItem.character_id == character.id)
            )
            or 0
        )
        if count < PENDING_CAPACITY:
            session.add(
                PendingItem(
                    character_id=character.id,
                    source_key=source_key,
                    kind=kind,
                    payload=payload,
                    quantity=quantity,
                )
            )
            return "Pending"
        session.add(
            BlockedDelivery(
                character_id=character.id,
                source_key=source_key,
                kind=kind,
                payload=payload,
                quantity=quantity,
                status="pending",
            )
        )
        character.delivery_blocked = True
        return "BlockedDelivery"

    async def _delivery_exists(self, session, character_id, source_key) -> bool:
        for model in (EquipmentItem, PendingItem, BlockedDelivery):
            if (
                await session.scalar(
                    select(model.id).where(
                        model.source_key == source_key,
                        *(
                            (model.character_id == character_id,)
                            if hasattr(model, "character_id")
                            else ()
                        ),
                    )
                )
                is not None
            ):
                return True
        return False

    @staticmethod
    async def _inventory_slots(session, character_id):
        counts = []
        for model in (EquipmentItem, ConsumableStack, MaterialStack, RuneStack):
            statement = select(func.count(model.id)).where(model.character_id == character_id)
            if model is not EquipmentItem:
                statement = statement.where(model.quantity > 0)
            counts.append(int(await session.scalar(statement) or 0))
        return sum(counts)

    async def _lock_character(self, session, actor):
        character_id = await session.scalar(
            select(Character.id).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )
        if character_id is None:
            return None
        try:
            character = await lock_for_combat_configuration_mutation(session, character_id)
        except CombatConfigurationLocked as exc:
            raise CraftingRejected(CraftingErrorCode.FOREGROUND) from exc
        if character is not None:
            await self._require_no_dungeon(session, character.id)
        return character

    async def _require_no_dungeon(self, session, character_id):
        if await self._dungeon_foreground(session, character_id):
            raise CraftingRejected(CraftingErrorCode.FOREGROUND)

    @staticmethod
    async def _dungeon_foreground(session, character_id):
        return (
            await session.scalar(
                select(DungeonRun.id)
                .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
                .where(
                    DungeonRunMember.character_id == character_id,
                    DungeonRunMember.status == "active",
                    DungeonRun.status == "active",
                )
                .limit(1)
            )
            is not None
        )

    @classmethod
    async def _has_foreground(cls, session, character_id):
        return await find_combat_configuration_blocker(
            session, character_id
        ) is not None or await cls._dungeon_foreground(session, character_id)

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    @staticmethod
    async def _profession_rows(session, character_id, *, lock=False):
        statement = (
            select(CharacterProfession)
            .where(CharacterProfession.character_id == character_id)
            .order_by(CharacterProfession.slot)
        )
        if lock:
            statement = statement.with_for_update()
        return list((await session.scalars(statement)).all())

    @staticmethod
    async def _material_rows(session, character_id, *, lock=False):
        statement = (
            select(MaterialStack)
            .where(MaterialStack.character_id == character_id, MaterialStack.quantity > 0)
            .order_by(MaterialStack.material_id, MaterialStack.bound, MaterialStack.id)
        )
        if lock:
            statement = statement.with_for_update()
        return list((await session.scalars(statement)).all())

    @staticmethod
    async def _location(session, character_id, *, lock=False):
        statement = select(WorldState).where(WorldState.character_id == character_id)
        if lock:
            statement = statement.with_for_update()
        world = await session.scalar(statement)
        return world.location if world is not None else None

    @staticmethod
    async def _known_special_ids(session, character_id):
        return set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(Unlock.character_id == character_id)
                )
            ).all()
        )

    @staticmethod
    async def _recipe_known(session, character_id, recipe, *, lock=False):
        if recipe.unlock_id is None:
            return True
        statement = select(Unlock.id).where(
            Unlock.character_id == character_id,
            Unlock.unlock_id == recipe.unlock_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement) is not None
