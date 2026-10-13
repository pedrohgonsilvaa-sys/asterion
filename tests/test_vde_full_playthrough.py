"""Long regional campaign validation, opt-in because it includes a fresh TDO run."""

import os
from datetime import UTC
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

import asterion.application.road as road_application
import asterion.application.vigor as vigor_module
from asterion.application.active_arts import ActiveArtService
from asterion.application.crafting import CraftingService
from asterion.application.equipment import EquipmentService
from asterion.application.equipment_configuration import (
    build_equipment_configuration,
    load_equipment_configuration,
    resolve_character_combat_stats,
)
from asterion.application.equipment_modifications import EquipmentModificationService
from asterion.application.inventory import InventoryService
from asterion.application.p7 import (
    GARGANTA_BRAZIER,
    P7_ID,
    P7_REWARD_SOURCE,
    P7Service,
)
from asterion.application.road import (
    REFUGE,
    ROAD,
    VDE_BAIXIOS,
    VDE_BERCO,
    VDE_CLAUSTRO,
    VDE_GARGANTA,
    VDE_MATA,
    VDE_VIGILIA,
    RoadService,
)
from asterion.application.vde_missions import (
    P8_ID,
    P8_REWARD_SOURCE,
    P9_ID,
    P9_REWARD_SOURCE,
    P10_ID,
    P10_REWARD_SOURCE,
    P11_ID,
    P11_REWARD_SOURCE,
    P12_ID,
    P12_NUCLEUS_SOURCE,
    P12_REWARD_SOURCE,
    S7_ID,
    S7_REWARD_SOURCE,
    S8_ID,
    S8_REWARD_SOURCE,
    S9_ID,
    S9_REWARD_SOURCE,
    S10_ID,
    S10_REWARD_SOURCE,
    S11_ID,
    S11_REWARD_SOURCE,
    S12_ID,
    S12_REWARD_SOURCE,
    VDE_CAMPAIGN_UNLOCK,
    VDEMissionService,
)
from asterion.domain.arts import SENTINEL_ART_IDS
from asterion.domain.combat import action_target_ids, allowed_actions
from asterion.domain.equipment import assignment_for_item_slot, parse_equipment_slot
from asterion.domain.professions import RECIPE_DEFINITIONS
from asterion.domain.road import (
    EXPLORATION_PROFILES,
    LOCATION_LEVEL_BANDS,
    hunt_profile_for_location,
)
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Brazier,
    Character,
    CharacterActiveArtSlot,
    CharacterEquipmentSlot,
    CharacterProfession,
    CharacterTalentChoice,
    CodexEntry,
    ConsumableStack,
    DungeonRun,
    EquipmentItem,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.tdo_playthrough import (
    choose_p6_policy_action,
    install_best_owned_runes,
)
from tests.test_tdo_full_playthrough import run_tdo_full_playthrough

pytestmark = pytest.mark.skipif(
    os.getenv("ASTERION_RUN_VDE_FULL_PLAYTHROUGH") != "1",
    reason="playthrough regional longo; habilite ASTERION_RUN_VDE_FULL_PLAYTHROUGH=1",
)


async def _free_p12_crafting_slot(inventory, modifications, actor):
    """Dismantle one clearly inferior, unmodified item through the public service."""
    root = await inventory.root(actor)
    if root is None or root.used_slots < root.capacity:
        return None
    rarity_rank = {"Comum": 1, "Raro": 2, "Épico": 3, "Mítico": 4}
    initial_slots = root.used_slots
    dismantled = []
    while root.used_slots >= root.capacity:
        equipment_view = await inventory.category(actor, "equipment")
        materials_view = await inventory.category(actor, "materials")
        if equipment_view is None or materials_view is None:
            break
        equipped_by_slot = {
            entry.slot: entry for entry in equipment_view.entries if entry.equipped
        }
        owned_materials = {(entry.key, entry.bound) for entry in materials_view.entries}
        candidates = []
        for entry in equipment_view.entries:
            if entry.equipped or entry.slot not in equipped_by_slot or entry.item_level is None:
                continue
            current = equipped_by_slot[entry.slot]
            if current.item_level is None:
                continue
            if (
                rarity_rank.get(entry.rarity or "", 0)
                > rarity_rank.get(current.rarity or "", 0)
                or entry.item_level >= current.item_level
            ):
                continue
            payload = entry.payload or {}
            if (
                payload.get("favorite")
                or payload.get("locked")
                or payload.get("runes")
                or payload.get("rune")
                or payload.get("enchantment")
                or int(payload.get("enhancement", 0)) > 0
            ):
                continue
            candidates.append(entry)

        candidates.sort(
            key=lambda entry: (
                rarity_rank.get(entry.rarity or "", 0),
                entry.item_level or 0,
                entry.title,
                entry.key,
            )
        )
        made_progress = False
        for entry in candidates:
            preview = await modifications.dismantle_preview(actor, UUID(entry.key))
            if preview is None or not preview.available:
                continue
            if preview.details.get("needs_mythic_confirmation"):
                continue
            outputs = tuple(preview.details.get("materials", ()))
            # Only dismantle when every output merges into an already-owned stack,
            # so the normal public action is guaranteed to free an Inventory slot.
            if not outputs or any(
                (output["material_id"], bool(output["bound"])) not in owned_materials
                for output in outputs
            ):
                continue
            await modifications.dismantle(
                actor,
                UUID(entry.key),
                expected_item_version=preview.item_version,
                expected_configuration_version=preview.combat_configuration_version,
            )
            after = await inventory.root(actor)
            if after is not None and after.used_slots < root.used_slots:
                dismantled.append(
                    {
                        "item": entry.title,
                        "rarity": entry.rarity,
                        "slot": entry.slot,
                        "item_level": entry.item_level,
                        "materials": outputs,
                    }
                )
                root = after
                made_progress = True
                break
        if not made_progress:
            break
    if not dismantled:
        return None
    return {
        "items": tuple(dismantled),
        "slots_freed": initial_slots - root.used_slots,
        "has_room": root.used_slots < root.capacity,
    }


async def _craft_vde_p12_preparation(
    sessions,
    crafting,
    actor,
    *,
    equipment_only=False,
    skip_recipe_ids=(),
):
    """Prepare only through public Grade II recipes and equipment services."""
    inventory = InventoryService(sessions, "ocaso")
    modifications = EquipmentModificationService(sessions, "ocaso")
    dismantled = []
    unavailable_consumables = []

    async def available_recipe(recipe_id):
        recipe = await crafting.recipe(actor, recipe_id)
        if recipe is not None and not recipe.available and recipe.reason == "inventory_full":
            freed = await _free_p12_crafting_slot(inventory, modifications, actor)
            if freed is not None:
                dismantled.append(freed)
                recipe = await crafting.recipe(actor, recipe_id)
        return recipe

    crafted_consumables = []
    if not equipment_only:
        for recipe_id, limit in (
            ("recipe.vde.alchemist.heal.vde.ii", 4),
            ("recipe.vde.alchemist.antidote.vde.ii", 1),
            ("recipe.vde.alchemist.protection.vde.ii", 1),
            ("recipe.vde.alchemist.purification.vde.ii", 1),
        ):
            for _ in range(limit):
                recipe = await available_recipe(recipe_id)
                if recipe is None or not recipe.available:
                    unavailable_consumables.append(
                        (recipe_id, None if recipe is None else recipe.reason)
                    )
                    break
                preview = await crafting.preview(actor, recipe_id)
                assert preview is not None
                committed = await crafting.commit(actor, preview.receipt_id)
                assert committed is not None and committed.status == "committed"
                crafted_consumables.append(recipe_id)

    rarity_rank = {"Comum": 1, "Raro": 2, "Épico": 3}
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        main_item = await session.scalar(
            select(EquipmentItem)
            .join(
                CharacterEquipmentSlot,
                CharacterEquipmentSlot.equipment_item_id == EquipmentItem.id,
            )
            .where(
                CharacterEquipmentSlot.character_id == character.id,
                CharacterEquipmentSlot.slot == "Principal",
            )
        )
    main_recipe_slot = (
        "2H" if main_item is not None and main_item.slot == "2H" else "Principal"
    )
    hand_slots = (
        ("2H",)
        if main_recipe_slot == "2H"
        else ("Principal", "Secundária")
    )
    target_slots = (*hand_slots, "Cabeça", "Torso", "Mãos", "Pés")
    skipped = set(skip_recipe_ids)
    equipment_recipes = tuple(
        definition
        for definition in RECIPE_DEFINITIONS
        if definition.recipe_id.startswith("recipe.vde.")
        and definition.output_kind == "equipment"
        and definition.output_slot in target_slots
        and definition.unlock_id is None
    )
    crafted_equipment = []
    unavailable = []
    for slot in target_slots:
        candidates = sorted(
            (recipe for recipe in equipment_recipes if recipe.output_slot == slot),
            key=lambda recipe: (
                rarity_rank.get(recipe.rarity or "", 0),
                recipe.required_level,
                recipe.recipe_id,
            ),
            reverse=True,
        )
        for definition in candidates:
            if definition.recipe_id in skipped:
                continue
            recipe = await available_recipe(definition.recipe_id)
            if recipe is None:
                unavailable.append((definition.recipe_id, "unknown_or_locked"))
                continue
            if not recipe.available:
                unavailable.append((definition.recipe_id, recipe.reason))
                continue
            preview = await crafting.preview(actor, definition.recipe_id)
            assert preview is not None
            committed = await crafting.commit(actor, preview.receipt_id)
            assert committed is not None and committed.status == "committed"
            crafted_equipment.append(
                (definition.recipe_id, definition.rarity, definition.output_slot)
            )
            break
    # The first pass can raise Blacksmith while making legitimate Common
    # equipment. Recheck higher rarities afterward instead of leaving a
    # newly unlocked public recipe unused merely because it was unavailable
    # earlier in the same preparation visit.
    upgraded_equipment = []
    for slot in target_slots:
        if any(
            crafted_slot == slot and rarity in {"Raro", "Épico"}
            for _, rarity, crafted_slot in crafted_equipment
        ):
            continue
        candidates = sorted(
            (
                recipe
                for recipe in equipment_recipes
                if recipe.output_slot == slot and recipe.rarity in {"Raro", "Épico"}
            ),
            key=lambda recipe: (
                rarity_rank.get(recipe.rarity or "", 0),
                recipe.required_level,
                recipe.recipe_id,
            ),
            reverse=True,
        )
        for definition in candidates:
            if definition.recipe_id in skipped:
                continue
            recipe = await available_recipe(definition.recipe_id)
            if recipe is None or not recipe.available:
                if recipe is not None:
                    unavailable.append((definition.recipe_id, recipe.reason))
                continue
            preview = await crafting.preview(actor, definition.recipe_id)
            assert preview is not None
            committed = await crafting.commit(actor, preview.receipt_id)
            assert committed is not None and committed.status == "committed"
            upgraded_equipment.append(
                (definition.recipe_id, definition.rarity, definition.output_slot)
            )
            break
    return {
        "consumables": crafted_consumables,
        "unavailable_consumables": unavailable_consumables,
        "equipment": crafted_equipment,
        "higher_rarity_equipment": upgraded_equipment,
        "unavailable_equipment_recipes": unavailable,
        "dismantled_for_capacity": dismantled,
    }


async def _craft_vde_p12_retry_consumables(crafting, actor):
    """Restock only through recipes accepted by the public crafting service."""
    crafted = []
    unavailable = []
    for recipe_id, limit in (
        ("recipe.vde.alchemist.heal.vde.ii", 4),
        ("recipe.vde.alchemist.antidote.vde.ii", 1),
        ("recipe.vde.alchemist.protection.vde.ii", 1),
        ("recipe.vde.alchemist.purification.vde.ii", 1),
    ):
        for _ in range(limit):
            recipe = await crafting.recipe(actor, recipe_id)
            if recipe is None or not recipe.available:
                unavailable.append((recipe_id, None if recipe is None else recipe.reason))
                break
            preview = await crafting.preview(actor, recipe_id)
            assert preview is not None
            committed = await crafting.commit(actor, preview.receipt_id)
            assert committed is not None and committed.status == "committed"
            crafted.append(recipe_id)
    return {"crafted": crafted, "unavailable": unavailable}


async def _p12_preparation_snapshot(sessions, actor):
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        configuration = await load_equipment_configuration(session, character)
        stats = resolve_character_combat_stats(character, configuration)
        equipment_rows = (
            await session.execute(
                select(CharacterEquipmentSlot.slot, EquipmentItem)
                .join(
                    EquipmentItem,
                    EquipmentItem.id == CharacterEquipmentSlot.equipment_item_id,
                )
                .where(CharacterEquipmentSlot.character_id == character.id)
                .order_by(CharacterEquipmentSlot.slot)
            )
        ).all()
        arts = (
            await session.scalars(
                select(CharacterActiveArtSlot.art_id)
                .where(CharacterActiveArtSlot.character_id == character.id)
                .order_by(CharacterActiveArtSlot.slot)
            )
        ).all()
        talents = (
            await session.scalars(
                select(CharacterTalentChoice.talent_id)
                .where(CharacterTalentChoice.character_id == character.id)
                .order_by(CharacterTalentChoice.point_slot)
            )
        ).all()
        professions = (
            await session.execute(
                select(
                    CharacterProfession.profession_id,
                    CharacterProfession.level,
                    CharacterProfession.pxp,
                )
                .where(CharacterProfession.character_id == character.id)
                .order_by(CharacterProfession.slot)
            )
        ).all()
        consumables = (
            await session.execute(
                select(ConsumableStack.consumable_id, ConsumableStack.quantity)
                .where(
                    ConsumableStack.character_id == character.id,
                    ConsumableStack.quantity > 0,
                )
                .order_by(ConsumableStack.consumable_id)
            )
        ).all()
        equipment = tuple(
            {
                "slot": slot,
                "name": item.item_name,
                "rarity": item.rarity,
                "item_level": item.item_level,
                "runes": (item.payload or {}).get("runes") or (item.payload or {}).get("rune"),
                "enchantment": (item.payload or {}).get("enchantment"),
            }
            for slot, item in equipment_rows
        )
        return {
            "level": character.level,
            "hp": str(character.hp),
            "max_hp": str(stats.hp),
            "ATQ": str(stats.attack),
            "DEF": str(stats.defense),
            "AGI": str(stats.agility),
            "PER": str(stats.per),
            "CRIT": str(stats.crit),
            "Esquiva": str(stats.evasion),
            "Bloqueio": str(stats.block),
            "class": character.character_class,
            "path": character.selected_path,
            "talents": tuple(talents),
            "professions": tuple(professions),
            "arts": tuple(arts),
            "equipment": equipment,
            "consumables": tuple(consumables),
        }


async def _p12_modification_access(sessions, actor):
    """Record public rune/enchantment service availability at the safe hub."""
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        equipped = (
            await session.execute(
                select(CharacterEquipmentSlot.slot, EquipmentItem.id)
                .join(
                    EquipmentItem,
                    EquipmentItem.id == CharacterEquipmentSlot.equipment_item_id,
                )
                .where(CharacterEquipmentSlot.character_id == character.id)
                .order_by(CharacterEquipmentSlot.slot)
            )
        ).all()
    service = EquipmentModificationService(sessions, "ocaso")
    result = []
    for slot, item_id in equipped:
        rune_view = await service.runes(actor, item_id, "A")
        enchantment_view = await service.enchantments(actor, item_id)
        result.append(
            {
                "slot": slot,
                "runes": None
                if rune_view is None
                else {
                    "available": rune_view.available,
                    "reason": rune_view.reason,
                    "owned_candidates": len(rune_view.details.get("candidates", ())),
                    "current": rune_view.details.get("current"),
                },
                "enchantments": None
                if enchantment_view is None
                else {
                    "available": enchantment_view.available,
                    "reason": enchantment_view.reason,
                    "craftable_candidates": sum(
                        bool(candidate.get("craftable"))
                        for candidate in enchantment_view.details.get("candidates", ())
                    ),
                    "current": enchantment_view.details.get("current"),
                },
            }
        )
    return tuple(result)


async def _character(sessions, actor):
    async with sessions() as session:
        return await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )


async def _equip_best_available_combat_gear(sessions, actor):
    """Equip only owned, level-eligible items through the public equipment service."""
    service = EquipmentService(sessions, "ocaso")
    changed = []
    for _ in range(12):
        async with sessions.begin() as session:
            character = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor)
                .with_for_update()
            )
            assert character is not None
            owned = (
                await session.scalars(
                    select(EquipmentItem)
                    .where(EquipmentItem.character_id == character.id)
                    .order_by(EquipmentItem.id)
                )
            ).all()
            equipped_rows = (
                await session.execute(
                    select(CharacterEquipmentSlot.slot, EquipmentItem)
                    .join(
                        EquipmentItem,
                        EquipmentItem.id == CharacterEquipmentSlot.equipment_item_id,
                    )
                    .where(CharacterEquipmentSlot.character_id == character.id)
                )
            ).all()
            assignments = {parse_equipment_slot(slot): item for slot, item in equipped_rows}
            current = build_equipment_configuration(
                character,
                list(assignments.items()),
                version=character.combat_configuration_version,
                talent_choices=(
                    await load_equipment_configuration(
                        session, character, lock_rows=False
                    )
                ).talent_choices,
            )
            baseline_stats = resolve_character_combat_stats(character, current)
            version = character.combat_configuration_version
            equipped_ids = {item.id for item in assignments.values()}
            candidates = []
            for item in owned:
                if item.id in equipped_ids or item.item_level > character.level:
                    continue
                assignment = assignment_for_item_slot(item.slot)
                if assignment is None:
                    continue
                replaced = dict(assignments)
                if item.slot == "2H":
                    replaced.pop(parse_equipment_slot("Secundária"), None)
                replaced[assignment.slot] = item
                try:
                    candidate = build_equipment_configuration(
                        character,
                        list(replaced.items()),
                        version=version,
                        talent_choices=current.talent_choices,
                    )
                    candidate_stats = resolve_character_combat_stats(character, candidate)
                except ValueError:
                    continue
                delta = sum(
                    (
                        (new - old) / max(abs(old), Decimal(1))
                        for old, new in zip(
                            baseline_stats.values(), candidate_stats.values(), strict=True
                        )
                    ),
                    Decimal(0),
                )
                if delta > 0:
                    candidates.append((delta, str(item.id), assignment.slot, item))
            if not candidates:
                break
            candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)
            delta, _item_id, slot, item = candidates[0]
        result = await service.equip_item(
            actor,
            item.id,
            expected_configuration_version=version,
        )
        if result is None or not result.changed:
            break
        changed.append((slot.value, item.item_name, item.rarity, item.item_level, str(delta)))
    return changed


async def _complete_mission_combat(
    missions, driver, actor, quest_id, view, label, *, action_picker=None
):
    for retry in range(1, 6):
        fight = await missions.start_solo_combat(actor, quest_id, view.state_version)
        if fight is not None and fight.progress.get("awaiting_retry"):
            view = fight
            continue
        assert fight is not None and fight.activity_id is not None and fight.combat is not None, (
            f"{label}: encontro não materializado\n{driver.diagnostic()}"
        )
        async def mutate(current, action):
            if action.startswith("consumable:"):
                consumable_id = action.removeprefix("consumable:")
                option = next(
                    item
                    for item in current.consumable_options
                    if item.item_id == consumable_id
                )
                return await missions.action_combat(
                    actor,
                    current.activity_id,
                    current.combat.version,
                    consumable_id=consumable_id,
                    target_id=option.target_id,
                    effect_id=option.effect_id,
                )
            return await missions.action_combat(
                actor,
                current.activity_id,
                current.combat.version,
                action,
            )

        result = await driver.combat_to_result(
            fight,
            mutate,
            lambda: missions.resume_active(actor),
            label=f"{label} · tentativa {retry}",
            max_actions=500,
            action_picker=action_picker,
        )
        if result.kind == "combat_result":
            result = await missions.resume(actor, quest_id)
        if result is not None and not (result.progress or {}).get("awaiting_retry"):
            assert result.kind != "combat", (
                f"{label}: o encontro não avançou a missão: {result!r}\n{driver.diagnostic()}"
            )
            return result
        view = await missions.resume(actor, quest_id)
        assert view is not None and view.status == "active"
    raise AssertionError(f"{label}: cinco retries não concluíram o encontro\n{driver.diagnostic()}")


async def _move_to(road, actor, destination):
    """Travel through only the public route graph; never set WorldState directly."""
    current = await road.resume(actor)
    assert current is not None
    if current.location == destination:
        return current

    if destination == ROAD and current.location == REFUGE:
        result = await road.travel(actor, ROAD)
        assert result is not None and result.location == ROAD
        return result

    # Every Vales connection is bidirectional. Walk the unique main route in
    # small hops so this journey also exercises the actual route unlocks.
    vales = (VDE_GARGANTA, VDE_VIGILIA, VDE_MATA, VDE_BAIXIOS, VDE_CLAUSTRO, VDE_BERCO)
    if current.location in vales and destination in vales:
        start = vales.index(current.location)
        end = vales.index(destination)
        step = 1 if end > start else -1
        for index in range(start + step, end + step, step):
            result = await road.travel_route(actor, vales[index])
            assert result is not None and result.location == vales[index], (
                f"rota bloqueada {current.location!r} -> {vales[index]!r}: {result!r}"
            )
        return await road.resume(actor)
    raise AssertionError(f"não há rota pública para {current.location!r} -> {destination!r}")


async def _huntable_location(road, actor):
    for _ in range(8):
        view = await road.resume(actor)
        assert view is not None
        character = await _character(road.sessions, actor)
        assert character is not None
        current_band = LOCATION_LEVEL_BANDS.get(view.location, (0, 0))
        if view.hunt_enabled:
            higher_routes = tuple(
                destination
                for destination in view.route_destinations
                if LOCATION_LEVEL_BANDS.get(destination, (0, 0))[1] > current_band[1]
            )
            if character.level <= current_band[1] or not higher_routes:
                return view
        if view.location == REFUGE:
            moved = await road.travel(actor, ROAD)
            if moved is not None:
                continue
        candidates = view.route_destinations
        if view.hunt_enabled:
            candidates = tuple(
                destination
                for destination in candidates
                if LOCATION_LEVEL_BANDS.get(destination, (0, 0))[1] > current_band[1]
            )
        if candidates:
            candidates = sorted(
                candidates,
                key=lambda location: LOCATION_LEVEL_BANDS.get(location, (0, 0))[1],
                reverse=True,
            )
            for destination in candidates:
                moved = await road.travel_route(actor, destination)
                if moved is not None:
                    moved_view = await road.resume(actor)
                    if moved_view is not None and moved_view.hunt_enabled:
                        return moved_view
                    break
            else:
                raise AssertionError(f"nenhuma rota de Caçada acessível: {view!r}")
            continue
        # At the regional level cap, retain a valid local profile so the
        # level-21 exit gate can be tested without opening another region.
        if view.hunt_enabled:
            return view
        raise AssertionError(f"nenhum Local de Caçada legitimamente acessível: {view!r}")
    raise AssertionError("não foi possível alcançar um Local de Caçada elegível")


async def _hunt_to_level(road, driver, actor, target_level, counts):
    """Use public Manual Hunt and natural simulated Vigor for any level gate."""
    for attempt in range(1, 1201):
        character = await _character(road.sessions, actor)
        assert character is not None
        if character.level >= target_level:
            print(
                f"VDE_LEVEL_GATE Nv.{target_level} reached | "
                f"actual=Nv.{character.level} xp={character.xp} "
                f"hunts={counts['hunts']}",
                flush=True,
            )
            return
        await _huntable_location(road, actor)
        await driver.clock.wait_for_vigor(
            road.sessions,
            actor,
            2,
            f"Vales offline natural regeneration before hunt {counts['hunts'] + 1}",
        )
        queued = await road.start_hunt(actor)
        if queued is None or queued.kind != "hunt_queue" or queued.pvpve_queue_id is None:
            raise AssertionError(
                f"Caçada pública indisponível ao buscar Nv.{target_level}: {queued!r}"
            )
        counts["hunts"] += 1
        if counts["hunts"] % 25 == 0:
            character = await _character(road.sessions, actor)
            assert character is not None
            print(
                f"VDE_PROGRESS hunts={counts['hunts']} level={character.level} "
                f"xp={character.xp} target={target_level}",
                flush=True,
            )
        fight = await road.pvpve.continue_queue(actor, queued.pvpve_queue_id)
        if fight is not None and fight.kind == "hunt_defeat":
            counts["hunt_defeats"] = counts.get("hunt_defeats", 0) + 1
            await road.acknowledge_defeat(actor)
            continue
        if fight is None or fight.kind != "combat" or fight.combat is None:
            raise AssertionError(f"PvPvE sem rival não seguiu para PvE: {fight!r}")
        outcome = await driver.combat_to_result(
            fight,
            lambda current, action: road.action(
                actor,
                current.activity_id,
                current.combat.version,
                action,
            ),
            lambda: RoadService(road.sessions, "ocaso").resume(actor),
            label=f"Vales · Caçada de progressão {attempt}",
            max_actions=300,
        )
        if outcome.kind == "hunt_victory":
            await road.acknowledge_result(actor)
        elif outcome.kind == "hunt_defeat":
            await road.acknowledge_defeat(actor)
        else:
            raise AssertionError(f"resultado inesperado de Caçada: {outcome!r}")
    character = await _character(road.sessions, actor)
    raise AssertionError(
        f"Nv.{target_level} exigiu mais de 1200 Caçadas públicas; "
        f"estado={character!r}\n{driver.diagnostic()}"
    )


async def _explore_unique(road, driver, monkeypatch, actor, key):
    view = await road.resume(actor)
    assert view is not None and view.explore_enabled, (
        f"Desbravar indisponível para {key}: {view!r}"
    )
    hunt_profile = hunt_profile_for_location(view.location)
    assert hunt_profile is not None, f"Local sem perfil canônico: {view.location!r}"
    local_profile = EXPLORATION_PROFILES[hunt_profile.local_id]
    result_definition = next(item for item in local_profile.results if item.key == key)
    assert result_definition.unique

    # Deterministic test RNG selects a source-defined eligible result. The
    # actual RoadService still creates and settles the persisted attempt.
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *_args, **_kwargs: (
            result_definition.category,
            result_definition.result_id,
            result_definition.text,
        ),
    )
    driver.clock.advance(300, f"Desbravar cooldown · {key}")
    assert await road.prepare_explore(actor) is not None
    result = await road.explore(actor)
    assert result is not None and result.result_id == result_definition.result_id
    await road.acknowledge_result(actor, result.attempt_id)
    return result


async def _round_trip_snapshot(driver, label):
    await driver.snapshot(label)
    print(f"VDE_MILESTONE {label}", flush=True)


@pytest.mark.asyncio
async def test_vde_full_playthrough_from_fresh_tdo_exit(database, monkeypatch):
    """Run public TDO and Vales journeys from a fresh PostgreSQL schema."""
    import asterion.application.pvpve as pvpve_module
    import asterion.application.round as round_module
    actor, driver = await run_tdo_full_playthrough(database, monkeypatch)
    sessions = driver.sessions
    # The TDO journey ends at the Refuge. Replenish healing stock only when
    # the official recipe is available, using the normal preview/commit flow.
    # These items are then consumed only by the actual VDE encounters below.
    crafting = CraftingService(sessions, "ocaso")
    crafted_heals = 0
    for _ in range(4):
        recipe = await crafting.recipe(actor, "recipe.tdo.alchemist.heal")
        if recipe is None or not recipe.available:
            break
        preview = await crafting.preview(actor, "recipe.tdo.alchemist.heal")
        assert preview is not None
        crafted = await crafting.commit(actor, preview.receipt_id)
        assert crafted is not None and crafted.status == "committed"
        crafted_heals += 1
    print(f"VDE_ENTRY_LEGITIMATE_HEALS_CRAFTED={crafted_heals}", flush=True)
    counts = {"hunts": 0, "hunt_defeats": 0, "explores": 0}
    JourneyClock = driver.clock.datetime_type()
    monkeypatch.setattr(vigor_module, "utcnow", driver.clock.now)
    monkeypatch.setattr(road_application, "datetime", JourneyClock)
    monkeypatch.setattr(round_module, "datetime", JourneyClock)
    monkeypatch.setattr(pvpve_module, "_utcnow", lambda: driver.clock.now(UTC))

    initial = await _character(sessions, actor)
    assert initial is not None
    assert initial.level >= 10
    character_id = initial.id
    road = RoadService(sessions, "ocaso")
    p7_service = P7Service(sessions, "ocaso")
    missions = VDEMissionService(sessions, "ocaso")

    await _hunt_to_level(road, driver, actor, 11, counts)
    p7 = await p7_service.enter_vales(actor)
    assert p7 is not None and p7.status == "active" and p7.location == VDE_GARGANTA
    async with sessions() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None and world.location == VDE_GARGANTA
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "vde.location.garganta_dos_lacos",
            )
        ) is not None
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                    Brazier.brazier_id == GARGANTA_BRAZIER,
            )
        ) is not None
    for point in ("a", "b"):
        p7 = await p7_service.examine_road_point(actor, p7.state_version, point)
    p7 = await p7_service.inspect_recent_passage(actor, p7.state_version)
    p7_fight = await p7_service.start_solo_combat(actor, p7.state_version)
    assert p7_fight is not None and p7_fight.activity_id is not None
    for retry in range(1, 7):
        p7 = await driver.combat_to_result(
            p7_fight,
            lambda current, action: p7_service.action_combat(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: p7_service.resume(actor),
            label=f"Vales P7 · fauna roteirizada · tentativa {retry}",
            max_actions=250,
        )
        if p7.kind == "worked_stone":
            break
        assert p7.kind == "retry", f"P7 terminou em estado inesperado: {p7!r}"
        p7_fight = await p7_service.retry(actor, p7.state_version)
        assert p7_fight is not None and p7_fight.kind == "combat"
    assert p7.kind == "worked_stone" and p7.step == 5
    p7 = await p7_service.inspect_worked_stone(actor, p7.state_version)
    p7 = await p7_service.proceed_to_vigilia(actor, p7.state_version)
    p7 = await p7_service.activate_brazier(actor, p7.state_version)
    p7 = await p7_service.report_dara(actor, p7.state_version)
    assert p7.status == "completed"
    await _round_trip_snapshot(driver, "Vales · P7 concluída")
    counts["explores"] += 1
    await _move_to(road, actor, VDE_GARGANTA)
    await _explore_unique(road, driver, monkeypatch, actor, "marco_lacos")

    # S7 is optional but is exercised to prove the authored Vales side path.
    await _hunt_to_level(road, driver, actor, 12, counts)
    await _move_to(road, actor, VDE_GARGANTA)
    s7 = await missions.start(actor, S7_ID)
    assert s7 is not None and s7.status == "active"
    for point in ("a", "b", "c"):
        s7 = await missions.examine(actor, S7_ID, s7.state_version, point)
    s7 = await _complete_mission_combat(missions, driver, actor, S7_ID, s7, "Vales S7")
    assert s7.kind == "rope"
    s7 = await missions.advance(actor, S7_ID, s7.state_version, "rope")
    await _move_to(road, actor, VDE_VIGILIA)
    s7 = await missions.advance(actor, S7_ID, s7.state_version, "report")
    assert s7.status == "completed"

    await _hunt_to_level(road, driver, actor, 13, counts)
    await _move_to(road, actor, VDE_VIGILIA)
    p8 = await missions.start(actor, P8_ID)
    assert p8 is not None and p8.kind == "enter_mata"
    await _move_to(road, actor, VDE_MATA)
    p8 = await missions.enter_mata(actor, p8.state_version)
    for point in ("a", "b", "c"):
        p8 = await missions.examine(actor, P8_ID, p8.state_version, point)
    p8 = await _complete_mission_combat(missions, driver, actor, P8_ID, p8, "Vales P8")
    assert p8.kind == "compare"
    for action in ("compare", "masonry", "record"):
        p8 = await missions.advance(actor, P8_ID, p8.state_version, action)
    await _move_to(road, actor, VDE_VIGILIA)
    p8 = await missions.return_vigilia(actor, p8.state_version)
    assert p8.status == "completed"
    await _round_trip_snapshot(driver, "Vales · P8 concluída")
    await _move_to(road, actor, VDE_MATA)
    counts["explores"] += 1
    await _explore_unique(road, driver, monkeypatch, actor, "brazier_copas")
    counts["explores"] += 1
    await _explore_unique(road, driver, monkeypatch, actor, "fosso_raizes")

    await _hunt_to_level(road, driver, actor, 14, counts)
    await _move_to(road, actor, VDE_MATA)
    s8 = await missions.start(actor, S8_ID)
    assert s8 is not None and s8.status == "active"
    s8 = await missions.advance(actor, S8_ID, s8.state_version, "passage")
    for point in ("a", "b", "c"):
        s8 = await missions.examine(actor, S8_ID, s8.state_version, point)
    s8 = await _complete_mission_combat(missions, driver, actor, S8_ID, s8, "Vales S8")
    assert s8.kind == "hardware"
    for _ in range(2):
        s8 = await missions.advance(actor, S8_ID, s8.state_version, "hardware")
    s8 = await missions.advance(actor, S8_ID, s8.state_version, "route")
    await _move_to(road, actor, VDE_VIGILIA)
    s8 = await missions.advance(actor, S8_ID, s8.state_version, "report")
    assert s8.status == "completed"

    await _hunt_to_level(road, driver, actor, 15, counts)
    await _move_to(road, actor, VDE_MATA)
    p9 = await missions.start(actor, P9_ID)
    assert p9 is not None and p9.kind == "follow"
    p9 = await missions.advance(actor, P9_ID, p9.state_version, "follow")
    await _move_to(road, actor, VDE_BAIXIOS)
    p9 = await missions.enter_baixios(actor, p9.state_version)
    for point in ("a", "b", "c"):
        p9 = await missions.examine(actor, P9_ID, p9.state_version, point)
    p9 = await _complete_mission_combat(missions, driver, actor, P9_ID, p9, "Vales P9")
    assert p9.kind == "inscription"
    p9 = await missions.advance(actor, P9_ID, p9.state_version, "inscription")
    p9 = await missions.advance(actor, P9_ID, p9.state_version, "fragment")
    p9 = await missions.advance(actor, P9_ID, p9.state_version, "report")
    p9 = await missions.choose_p9_reward(actor, p9.state_version, "2")
    assert p9.status == "completed"
    await _round_trip_snapshot(driver, "Vales · P9 concluída e escolha registrada")
    counts["explores"] += 1
    await _explore_unique(road, driver, monkeypatch, actor, "galeria_afogada")

    s9 = await missions.start(actor, S9_ID)
    assert s9 is not None and s9.kind == "locate"
    s9 = await missions.advance(actor, S9_ID, s9.state_version, "locate")
    s9 = await _complete_mission_combat(missions, driver, actor, S9_ID, s9, "Vales S9")
    assert s9.kind == "fragments"
    s9 = await missions.advance(actor, S9_ID, s9.state_version, "fragments")
    s9 = await missions.advance(actor, S9_ID, s9.state_version, "sample")
    s9 = await missions.advance(actor, S9_ID, s9.state_version, "report")
    assert s9.status == "completed"

    await _hunt_to_level(road, driver, actor, 17, counts)
    await _move_to(road, actor, VDE_BAIXIOS)
    p10 = await missions.start(actor, P10_ID)
    assert p10 is not None and p10.kind == "follow"
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "follow")
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "passage")
    for point in ("a", "b"):
        p10 = await missions.examine(actor, P10_ID, p10.state_version, point)
    p10 = await _complete_mission_combat(missions, driver, actor, P10_ID, p10, "Vales P10")
    assert p10.kind == "structure"
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "structure")
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "sanctuary")
    await _move_to(road, actor, VDE_BAIXIOS)
    p10 = await missions.advance(actor, P10_ID, p10.state_version, "report")
    assert p10.status == "completed"
    await _round_trip_snapshot(driver, "Vales · P10 concluída")
    # The Claustro's Desbravar gate is level 18; P10 itself is reachable
    # at level 17, so progress through the public hunt service first.
    await _hunt_to_level(road, driver, actor, 18, counts)
    await _move_to(road, actor, VDE_CLAUSTRO)
    counts["explores"] += 1
    await _explore_unique(road, driver, monkeypatch, actor, "brazier_pedras_enlacadas")
    await _move_to(road, actor, VDE_BAIXIOS)

    s10 = await missions.start(actor, S10_ID)
    assert s10 is not None and s10.status == "active"
    for point in ("a", "b", "c"):
        s10 = await missions.examine(actor, S10_ID, s10.state_version, point)
    s10 = await missions.advance(actor, S10_ID, s10.state_version, "zone")
    s10 = await missions.advance(actor, S10_ID, s10.state_version, "bag")
    s10 = await missions.advance(actor, S10_ID, s10.state_version, "tracks")
    s10 = await _complete_mission_combat(missions, driver, actor, S10_ID, s10, "Vales S10")
    assert s10.kind == "survivor"
    s10 = await missions.advance(actor, S10_ID, s10.state_version, "survivor")
    await _move_to(road, actor, VDE_VIGILIA)
    s10 = await missions.advance(actor, S10_ID, s10.state_version, "report")
    assert s10.status == "completed"

    await _hunt_to_level(road, driver, actor, 18, counts)
    await _move_to(road, actor, VDE_CLAUSTRO)
    s11 = await missions.start(actor, S11_ID)
    assert s11 is not None and s11.kind == "patrols"
    for point in ("a", "b"):
        s11 = await missions.examine(actor, S11_ID, s11.state_version, point)
    s11 = await _complete_mission_combat(missions, driver, actor, S11_ID, s11, "Vales S11")
    assert s11.kind == "return_place"
    s11 = await missions.advance(actor, S11_ID, s11.state_version, "return_place")
    for _ in range(3):
        s11 = await missions.advance(actor, S11_ID, s11.state_version, "fragment")
    s11 = await missions.advance(actor, S11_ID, s11.state_version, "report")
    assert s11.status == "completed"

    await _hunt_to_level(road, driver, actor, 19, counts)
    p11 = await missions.start(actor, P11_ID)
    assert p11 is not None and p11.kind == "pressure_points"
    for point in ("a", "b", "c"):
        p11 = await missions.examine(actor, P11_ID, p11.state_version, point)
    p11 = await missions.advance(actor, P11_ID, p11.state_version, "roots")
    p11 = await _complete_mission_combat(missions, driver, actor, P11_ID, p11, "Vales P11")
    assert p11.kind == "chamber"
    for action in ("chamber", "traces", "convergence", "open_berco"):
        p11 = await missions.advance(actor, P11_ID, p11.state_version, action)
    assert p11.status == "completed"
    await _round_trip_snapshot(driver, "Vales · P11 concluída e Berço descoberto")

    await _hunt_to_level(road, driver, actor, 20, counts)
    s12 = await missions.start(actor, S12_ID)
    assert s12 is not None and s12.kind == "read_record"
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "read_record")
    await _move_to(road, actor, VDE_GARGANTA)
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "visit_garganta")
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "find_mark")
    await _move_to(road, actor, VDE_MATA)
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "visit_mata")
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "recover_object")
    await _move_to(road, actor, VDE_BAIXIOS)
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "visit_baixios")

    def s12_policy(view):
        combat = view.combat
        available = allowed_actions(combat)
        if combat.prepared_action is not None and "defend" in available:
            return "defend"
        player = combat.fighters["player"]
        if player.hp / player.stats.hp <= Decimal("0.60"):
            for item_id in ("consumable.heal.vde.ii", "consumable.heal"):
                if any(option.item_id == item_id for option in view.consumable_options):
                    return f"consumable:{item_id}"
        damaging_arts = [
            action
            for action in available
            if action.startswith(("class_art.", "path_art."))
            and combat.player_actions[action].coefficient > 0
        ]
        if damaging_arts:
            return max(
                damaging_arts,
                key=lambda action: combat.player_actions[action].coefficient,
            )
        return driver.combat_action(combat)

    s12 = await _complete_mission_combat(
        missions,
        driver,
        actor,
        S12_ID,
        s12,
        "Vales S12",
        action_picker=s12_policy,
    )
    assert s12.kind == "examine_site"
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "examine_site")
    await _move_to(road, actor, VDE_CLAUSTRO)
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "visit_claustro")
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "last_record")
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "report_iven")
    await _move_to(road, actor, VDE_VIGILIA)
    s12 = await missions.advance(actor, S12_ID, s12.state_version, "register_names")
    assert s12.status == "completed"
    await _round_trip_snapshot(driver, "Vales · S12 concluída antes de P12")

    # The character already reached Vigília through the public route graph.
    # Reconfirm that safe-hub crafting is available and use only recipes whose
    # live service previews accept the earned profession, level and inventory.
    hub = await _move_to(road, actor, VDE_VIGILIA)
    assert hub.location == VDE_VIGILIA
    initial_p12_crafting = await _craft_vde_p12_preparation(sessions, crafting, actor)
    p12_crafting_passes = [initial_p12_crafting]
    p12_equipment_changes = await _equip_best_available_combat_gear(sessions, actor)
    crafted_recipe_ids = {
        recipe_id
        for result in p12_crafting_passes
        for recipe_id, *_details in (
            *result["equipment"],
            *result["higher_rarity_equipment"],
        )
    }
    # Equipping a legitimate upgrade can free the displaced item slot. Make
    # two bounded follow-up visits through the same public recipe previews so
    # those newly available slots can be used for other actual upgrades. Each
    # recipe is crafted at most once; this is not profession-level grinding.
    for _ in range(2):
        followup = await _craft_vde_p12_preparation(
            sessions,
            crafting,
            actor,
            equipment_only=True,
            skip_recipe_ids=crafted_recipe_ids,
        )
        p12_crafting_passes.append(followup)
        new_recipe_ids = {
            recipe_id
            for recipe_id, *_details in (
                *followup["equipment"],
                *followup["higher_rarity_equipment"],
            )
        }
        if not new_recipe_ids:
            break
        crafted_recipe_ids.update(new_recipe_ids)
        p12_equipment_changes.extend(
            await _equip_best_available_combat_gear(sessions, actor)
        )
    p12_crafting = {
        "passes": tuple(p12_crafting_passes),
        "unique_recipes_crafted": tuple(sorted(crafted_recipe_ids)),
    }
    p12_runes = await install_best_owned_runes(sessions, actor, server_id="ocaso")
    p12_modification_access = await _p12_modification_access(sessions, actor)
    print(f"VDE_P12_LEGITIMATE_CRAFTING={p12_crafting!r}", flush=True)
    print(f"VDE_P12_OFFICIAL_EQUIPMENT_CHANGES={p12_equipment_changes!r}", flush=True)
    print(f"VDE_P12_OFFICIAL_RUNES_INSTALLED={p12_runes!r}", flush=True)
    print(f"VDE_P12_MODIFICATION_ACCESS={p12_modification_access!r}", flush=True)
    p12_preparation = await _p12_preparation_snapshot(sessions, actor)
    print(f"VDE_P12_PREPARATION={p12_preparation!r}", flush=True)

    p12 = await missions.resume(actor, P12_ID)
    assert p12 is not None and p12.status == "active" and p12.step == 1
    await _move_to(road, actor, VDE_BERCO)
    p12 = await missions.advance(actor, P12_ID, p12.state_version, "enter_berco")
    p12 = await missions.advance(actor, P12_ID, p12.state_version, "advance_network")
    for point in ("a", "b", "c"):
        p12 = await missions.examine(actor, P12_ID, p12.state_version, point)
    p12 = await missions.advance(actor, P12_ID, p12.state_version, "central_chamber")
    # Begin with loadout C, then compare it against legal Quebra-Postura
    # alternatives in the retry plan below. This changes only equipped Arts.
    active_arts = ActiveArtService(sessions, "ocaso")
    desired_p12_arts = (
        SENTINEL_ART_IDS["golpe_de_guarda"],
        SENTINEL_ART_IDS["muralha_breve"],
        SENTINEL_ART_IDS["impacto_resoluto"],
    )
    art_view = await active_arts.view(actor)
    assert art_view is not None
    initial_slots = {entry.slot: entry.art_id for entry in art_view.slots}
    initial_art_ids = set(initial_slots.values())
    for target_slot, art_id in enumerate(desired_p12_arts, start=1):
        source_slot = next(
            (entry.slot for entry in art_view.slots if entry.art_id == art_id), None
        )
        if source_slot is None or source_slot == target_slot:
            continue
        replacement = desired_p12_arts[source_slot - 1]
        if replacement not in initial_art_ids:
            # Free the slot with the Art destined for that slot before moving
            # an equipped Art into the target slot; duplicate slots are invalid.
            moved = await active_arts.equip_art(
                actor,
                source_slot,
                replacement,
                expected_configuration_version=art_view.combat_configuration_version,
            )
            assert moved is not None and moved.changed
            art_view = await active_arts.view(actor)
            assert art_view is not None
            initial_slots[source_slot] = replacement
            initial_art_ids.add(replacement)
            break
    for slot, art_id in enumerate(desired_p12_arts, start=1):
        art_view = await active_arts.view(actor)
        assert art_view is not None
        current_target = next(
            (entry.art_id for entry in art_view.slots if entry.slot == slot), None
        )
        if current_target != art_id:
            await active_arts.equip_art(
                actor,
                slot,
                art_id,
                expected_configuration_version=art_view.combat_configuration_version,
            )
    final_art_view = await active_arts.view(actor)
    assert final_art_view is not None
    configured_p12_arts = tuple(entry.art_id for entry in final_art_view.slots)
    assert configured_p12_arts == desired_p12_arts
    print(f"VDE_P12_OFFICIAL_ACTIVE_ARTS={configured_p12_arts!r}", flush=True)
    p12_preparation = await _p12_preparation_snapshot(sessions, actor)
    print(f"VDE_P12_FINAL_PREPARATION={p12_preparation!r}", flush=True)
    p12_attempt_metrics = {
        "actions": [],
        "consumables": [],
        "target_ids": [],
        "destroyed_connections": set(),
    }

    p12_loadouts = {
        "C": (
            SENTINEL_ART_IDS["golpe_de_guarda"],
            SENTINEL_ART_IDS["muralha_breve"],
            SENTINEL_ART_IDS["impacto_resoluto"],
        ),
        "A": (
            SENTINEL_ART_IDS["golpe_de_guarda"],
            SENTINEL_ART_IDS["quebra_postura"],
            SENTINEL_ART_IDS["impacto_resoluto"],
        ),
        "D": (
            SENTINEL_ART_IDS["golpe_de_guarda"],
            SENTINEL_ART_IDS["quebra_postura"],
            SENTINEL_ART_IDS["muralha_breve"],
        ),
    }
    p12_attempt_target_connections = False
    p12_attempt_policy = "devastador"

    async def configure_p12_arts(desired_p12_arts):
        # The retry schedule only swaps the one Art that differs between each
        # adjacent loadout, using the public configuration service.
        for slot, art_id in enumerate(desired_p12_arts, start=1):
            view = await active_arts.view(actor)
            assert view is not None
            current = next((entry.art_id for entry in view.slots if entry.slot == slot), None)
            if current == art_id:
                continue
            changed = await active_arts.equip_art(
                actor,
                slot,
                art_id,
                expected_configuration_version=view.combat_configuration_version,
            )
            assert changed is not None and changed.changed
        view = await active_arts.view(actor)
        assert view is not None
        configured = tuple(entry.art_id for entry in view.slots)
        assert configured == desired_p12_arts
        return configured

    def p12_action_target(current, action):
        combat = current.combat
        if combat is None:
            return None
        definition = combat.player_actions.get(action)
        if definition is not None and definition.target_mode == "all_opponents":
            return None
        targets = action_target_ids(combat, action)
        if p12_attempt_target_connections:
            active_connections = tuple(
                target_id
                for target_id in targets
                if target_id in {"connection_a", "connection_b", "connection_c"}
                and combat.fighters[target_id].hp > 0
            )
            if active_connections:
                # This diagnostic retry tests the value of clearing the
                # lowest-HP active Connection against boss focus.
                return min(active_connections, key=lambda key: combat.fighters[key].hp)
        if "enemy" in targets:
            return "enemy"
        return targets[0] if targets else None

    async def p12_mutate(current, action):
        combat = current.combat
        if action.startswith("consumable:"):
            consumable_id = action.removeprefix("consumable:")
            option = next(
                option
                for option in current.consumable_options
                if option.item_id == consumable_id
            )
            p12_attempt_metrics["consumables"].append(consumable_id)
            p12_attempt_metrics["actions"].append(action)
            updated = await missions.action_combat(
                actor,
                current.activity_id,
                combat.version,
                consumable_id=consumable_id,
                target_id=option.target_id,
                effect_id=option.effect_id,
            )
        else:
            targets = action_target_ids(combat, action)
            connection_targets = tuple(
                target_id
                for target_id in targets
                if target_id in {"connection_a", "connection_b", "connection_c"}
                and combat.fighters[target_id].hp > 0
            )
            action_definition = combat.player_actions.get(action)
            target_id = p12_action_target(current, action)
            assert target_id is None or target_id in targets, (action, target_id, targets)
            p12_attempt_metrics["actions"].append(action)
            if action_definition is not None and action_definition.target_mode == "all_opponents":
                p12_attempt_metrics["target_ids"].extend(connection_targets)
            elif target_id is not None and target_id in connection_targets:
                p12_attempt_metrics["target_ids"].append(target_id)
            updated = await missions.action_combat(
                actor,
                current.activity_id,
                combat.version,
                action,
                target_id=target_id,
            )
        next_combat = getattr(updated, "combat", None)
        if next_combat is not None:
            for key in ("connection_a", "connection_b", "connection_c"):
                before = combat.fighters.get(key)
                after = next_combat.fighters.get(key)
                if before is not None and after is not None and before.hp > 0 and after.hp <= 0:
                    p12_attempt_metrics["destroyed_connections"].add(key)
        return updated

    def p12_policy(view):
        combat = view.combat
        available = allowed_actions(combat)
        if combat.prepared_action == "estrangulamento_vale" and "defend" in available:
            return "defend"
        player = combat.fighters["player"]
        hp_fraction = player.hp / player.stats.hp
        item_ids = {option.item_id for option in view.consumable_options}
        healing_id = next(
            (
                item_id
                for item_id in ("consumable.heal.vde.ii", "consumable.heal")
                if item_id in item_ids
            ),
            None,
        )
        if healing_id is not None and hp_fraction <= Decimal("0.60"):
            return f"consumable:{healing_id}"

        # P12 allows three combat consumables. Previous public-run diagnostics
        # showed that spending those slots on cleansing left fewer 22%-HP heals
        # and made less boss progress; this policy reserves them for healing.

        connections_alive = any(
            (fighter := combat.fighters.get(key)) is not None and fighter.hp > 0
            for key in ("connection_a", "connection_b", "connection_c")
        )
        if connections_alive:
            # Connections are optional and each reduces final damage by 4%.
            # Use a legal AoE that also hits the boss if available. Otherwise
            # the retry plan separately compares legal single-target attacks
            # on active Connections with boss focus.
            aoe_arts = [
                action
                for action in available
                if action.startswith(("class_art.", "path_art."))
                and (definition := combat.player_actions.get(action)) is not None
                and definition.coefficient > 0
                and definition.target_mode == "all_opponents"
            ]
            if aoe_arts:
                return max(
                    aoe_arts,
                    key=lambda action: combat.player_actions[action].coefficient,
                )

        # Use Devastador's actual charge, Retaliação and DEF-break logic. The
        # Devastador policy only spends a turn on Muralha at critical HP and
        # allows safe ordinary hits to trigger Ímpeto Doloroso.
        return choose_p6_policy_action(
            combat,
            p12_attempt_policy,
            heal_count=0,
            budget_limit=view.consumable_budget_limit,
        )

    after_boss = None
    p12_attempt_diagnostics = []
    p12_retry_plan = (
        ("C", False, "devastador"),
        ("C", False, "devastador"),
        ("A", False, "devastador"),
        ("A", True, "devastador"),
        ("D", False, "devastador"),
        ("D", True, "devastador"),
        ("C", False, "sentinela_devastador"),
        ("C", False, "sentinela_devastador"),
    )
    for retry, (loadout_name, target_connections, combat_policy) in enumerate(
        p12_retry_plan, start=1
    ):
        configured_p12_arts = await configure_p12_arts(p12_loadouts[loadout_name])
        p12_attempt_target_connections = target_connections
        p12_attempt_policy = combat_policy
        attempt_preparation = await _p12_preparation_snapshot(sessions, actor)
        print(
            f"VDE_P12_RETRY_PLAN_{retry}={{'loadout': {loadout_name!r}, "
            f"'target_connections': {target_connections}, 'policy': {combat_policy!r}, "
            f"'arts': {configured_p12_arts!r}}}",
            flush=True,
        )
        p12_attempt_metrics = {
            "actions": [],
            "consumables": [],
            "target_ids": [],
            "destroyed_connections": set(),
        }
        fight = await missions.start_solo_combat(actor, P12_ID, p12.state_version)
        if fight is not None and fight.progress.get("awaiting_retry"):
            p12 = fight
            continue
        assert fight is not None and fight.kind == "combat" and fight.activity_id is not None
        starting_combat = fight.combat
        assert starting_combat is not None
        start_player = starting_combat.fighters["player"]
        start_boss = starting_combat.fighters["enemy"]
        after_boss = await driver.combat_to_result(
            fight,
            p12_mutate,
            lambda: missions.resume_active(actor),
            label=f"Vales P12 · Matriarca das Raízes · tentativa {retry}",
            max_actions=700,
            action_picker=p12_policy,
            action_target_picker=p12_action_target,
            trace_actions=True,
        )
        if after_boss.kind == "combat_result":
            after_boss = await missions.resume(actor, P12_ID)
        final_combat = getattr(after_boss, "combat", None) or driver.last_combat
        assert final_combat is not None
        final_player = final_combat.fighters["player"]
        final_boss = final_combat.fighters["enemy"]
        events = tuple(final_combat.events) + tuple(final_combat.mechanic_events)
        player_damage = sum(
            event.effective_damage
            for event in events
            if event.target == start_player.id and event.effective_damage > 0
        )
        boss_damage = sum(
            event.effective_damage
            for event in events
            if event.target == start_boss.id and event.effective_damage > 0
        )
        attempt_report = {
            "attempt": retry,
            "result": final_combat.result,
            "service_result_kind": after_boss.kind,
            "service_awaiting_retry": bool(
                (after_boss.progress or {}).get("awaiting_retry")
            ),
            "level": attempt_preparation["level"],
            "stats": {
                key: attempt_preparation[key] for key in ("hp", "max_hp", "ATQ", "DEF", "AGI")
            },
            "equipment": attempt_preparation["equipment"],
            "arts": configured_p12_arts,
            "loadout": loadout_name,
            "target_connections": target_connections,
            "policy": combat_policy,
            "path": p12_preparation["path"],
            "talents": p12_preparation["talents"],
            "player_hp_start": str(start_player.hp),
            "player_hp_max": str(start_player.stats.hp),
            "boss_hp_start": str(start_boss.hp),
            "consumables_start": tuple(fight.consumable_quantities),
            "consumables_used": tuple(p12_attempt_metrics["consumables"]),
            "connection_targets": tuple(p12_attempt_metrics["target_ids"]),
            "connections_destroyed": tuple(sorted(p12_attempt_metrics["destroyed_connections"])),
            "phase_reached": final_combat.phase_id or "I",
            "rounds": final_combat.round,
            "actions": len(p12_attempt_metrics["actions"]),
            "defend_actions": sum(
                action == "defend" for action in p12_attempt_metrics["actions"]
            ),
            "muralha_actions": sum(
                action == SENTINEL_ART_IDS["muralha_breve"]
                for action in p12_attempt_metrics["actions"]
            ),
            "devastador_charges_consumed": sum(
                "devastador.impacto_consumido" in event.path_triggers
                for event in events
            ),
            "boss_hp_remaining": str(final_boss.hp),
            "boss_hp_max": str(final_boss.stats.hp),
            "player_hp_remaining": str(final_player.hp),
            "damage_to_boss": str(boss_damage),
            "damage_received": str(player_damage),
            "defeat_cause": (
                "player_hp_zero"
                if final_combat.result == "defeat" and final_player.hp <= 0
                else "service_retry_without_terminal_snapshot"
                if (after_boss.progress or {}).get("awaiting_retry")
                and final_combat.result is None
                else None
            ),
        }
        p12_attempt_diagnostics.append(attempt_report)
        print(f"VDE_P12_ATTEMPT_DIAGNOSTIC={attempt_report!r}", flush=True)
        if after_boss is not None and after_boss.kind == "examine_center":
            break
        assert after_boss is not None and after_boss.progress.get("awaiting_retry"), (
            f"Matriarca encerrou em estado inesperado: {after_boss!r}"
        )
        p12 = after_boss
        if retry < len(p12_retry_plan):
            # Retry recovery restores HP through the campaign service. Travel
            # back to the safe hub and restock only what public crafting still
            # accepts from resources actually earned by this playthrough.
            await _move_to(road, actor, VDE_VIGILIA)
            restock = await _craft_vde_p12_retry_consumables(crafting, actor)
            print(f"VDE_P12_RETRY_RESTOCK_{retry}={restock!r}", flush=True)
            await _move_to(road, actor, VDE_BERCO)
            p12 = await missions.resume(actor, P12_ID)
            assert p12 is not None and p12.progress.get("awaiting_retry")
    assert after_boss is not None and after_boss.kind == "examine_center", (
        f"Matriarca não concluiu vitória persistida: {after_boss!r}; "
        f"diagnóstico por tentativa={p12_attempt_diagnostics!r}\n{driver.diagnostic()}"
    )
    p12 = await missions.advance(actor, P12_ID, after_boss.state_version, "examine_center")
    p12 = await missions.advance(actor, P12_ID, p12.state_version, "register")
    assert p12.status == "completed" and p12.kind == "choice"
    p12 = await missions.choose_p12_reward(actor, p12.state_version, "2")
    assert p12 is not None and p12.kind == "completed"
    await _round_trip_snapshot(driver, "Vales · P12 concluída com escolha individual")

    # S12 is optional and may canonically be completed on either side of P12.
    await _hunt_to_level(road, driver, actor, 21, counts)
    await _move_to(road, actor, VDE_CLAUSTRO)
    await missions.resume(actor, P12_ID)
    await driver.snapshot("Vales · Nv.21 e saída regional disponível")

    async with sessions() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and character.level >= 21
        final_level, final_xp = character.level, character.xp
        assert world is not None and world.region == "Vales dos Enforcados"
        assert world.location == VDE_CLAUSTRO
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == "region.nareth.available",
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == VDE_CAMPAIGN_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == "P13",
            )
        ) is None
        quest_ids = (
            P7_ID,
            S7_ID,
            P8_ID,
            S8_ID,
            P9_ID,
            S9_ID,
            P10_ID,
            S10_ID,
            S11_ID,
            P11_ID,
            S12_ID,
            P12_ID,
        )
        quests = list(
            (
                await session.scalars(
                    select(Quest).where(
                        Quest.character_id == character_id,
                        Quest.quest_id.in_(quest_ids),
                    )
                )
            ).all()
        )
        assert {quest.quest_id for quest in quests} == set(quest_ids)
        assert all(quest.status == "completed" for quest in quests)
        reward_sources = (
            P7_REWARD_SOURCE,
            S7_REWARD_SOURCE,
            P8_REWARD_SOURCE,
            S8_REWARD_SOURCE,
            P9_REWARD_SOURCE,
            S9_REWARD_SOURCE,
            P10_REWARD_SOURCE,
            S10_REWARD_SOURCE,
            S11_REWARD_SOURCE,
            P11_REWARD_SOURCE,
            S12_REWARD_SOURCE,
            P12_REWARD_SOURCE,
            P12_NUCLEUS_SOURCE,
        )
        for source_id in reward_sources:
            assert await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == source_id,
                )
            ) == 1, source_id
        p12_components = list(
            (
                await session.scalars(
                    select(RewardComponent)
                    .join(RewardEvent)
                    .where(
                        RewardEvent.character_id == character_id,
                        RewardEvent.source_id == P12_REWARD_SOURCE,
                    )
                )
            ).all()
        )
        assert {(row.kind, row.quantity, row.item_id) for row in p12_components} >= {
            ("xp", 32580, None),
            ("crowns", 800, None),
            ("material", 4, "material.vde.ferro_enredado"),
            ("material", 4, "material.vde.resina_enredada"),
        }
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "matriarca_raizes",
            )
        ) is not None
        for entry_id in (
            "codex.location.berco_da_matriarca",
            "codex.mystery.a_rede_sob_os_vales",
            "codex.mystery.pulsacao_sob_a_pedra",
        ):
            assert await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character_id,
                    CodexEntry.entry_id == entry_id,
                )
            ) is not None
        assert await session.scalar(
            select(DungeonRun.id).where(
                DungeonRun.character_id == character_id,
                DungeonRun.dungeon_family_id.in_(
                    ("dungeon.vde.fosso_raizes", "dungeon.vde.santuario_no_antigo")
                ),
            )
        ) is None

    marks = [mark.label for mark in driver.marks if "Vales" in mark.label]
    print(
        "VDE_PLAYTHROUGH_REPORT="
        f"{{'character': {initial.name!r}, 'level': {final_level}, "
        f"'xp': {final_xp}, 'hunts': {counts['hunts']}, "
        f"'explores': {counts['explores']}, "
        f"'simulated_seconds': {driver.clock.elapsed_seconds}, 'marks': {marks!r}}}",
        flush=True,
    )
