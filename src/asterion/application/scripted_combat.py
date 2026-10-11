"""Small persistence helpers for mission fights using the shared combat engine."""
# ruff: noqa: E501

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.progression import consolidate_character_level
from asterion.domain.combat import act, combat_consumable_options, use_combat_consumable
from asterion.domain.consumables import (
    ENCOUNTER_CONSUMABLE_LIMITS,
    ConsumableFamily,
)
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.road import RULESET, create_creature_combat
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import ConsumableStack


async def materialize(session, character, content_id, creature, enemy_level, *, ai=None, flavor="", opening_log=""):
    """Create one fixed-identity mission encounter; callers own its Quest progress."""
    from dataclasses import replace

    configuration = await load_equipment_configuration(session, character)
    active_art_configuration = await load_active_art_configuration(session, character)
    reconcile_character_hp(character, configuration)
    actor = replace(creature, ai=ai) if ai is not None else creature
    state = create_creature_combat(
        uuid4(),
        character.name,
        character.character_class,
        character.race,
        character.hp,
        actor,
        enemy_level,
        None,
        player_level=character.level,
        equipment_configuration=configuration,
        ruleset_version=RULESET,
        flavor=flavor,
        opening_log=opening_log,
        active_art_ids=active_art_configuration.art_ids,
    )
    state.configuration_snapshot = (state.configuration_snapshot or {}) | (
        active_art_configuration.to_data()
    )
    activity, _, _ = await CombatRepository(session).create(character, content_id, state)
    return activity


async def normalize_character_hp(session, character):
    """Reconcile equipped HP and level progress at a scripted-combat boundary."""
    configuration = await load_equipment_configuration(session, character)
    reconcile_character_hp(character, configuration)
    await consolidate_character_level(session, character, configuration)
    reconcile_character_hp(character, configuration)


async def current_combat(session, activity):
    """Decode the persisted snapshot for an activity, if it has a combat record."""
    if activity is None:
        return None, None, None
    encounter, record = await CombatRepository(session).combat(activity)
    return decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version), encounter, record


async def apply_action(
    session,
    character,
    activity,
    *,
    action=None,
    consumable_id=None,
    target_id=None,
    effect_id=None,
    category="common",
):
    """Persist one versioned combat intent and consume an item exactly once."""
    if activity is None or activity.status != "active" or (action is None) == (consumable_id is None):
        return None
    combat, _, record = await current_combat(session, activity)
    if consumable_id is None:
        updated = (
            act(combat, action)
            if target_id is None
            else act(combat, action, target_id=target_id)
        )
    else:
        stack = await session.scalar(
            select(ConsumableStack)
            .where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == consumable_id,
                ConsumableStack.quantity > 0,
            )
            .with_for_update()
        )
        if stack is None:
            return combat
        updated = use_combat_consumable(
            combat,
            consumable_id,
            target_id=target_id,
            effect_id=effect_id,
            budget_limit=ENCOUNTER_CONSUMABLE_LIMITS.get(category, 0),
        )
        if updated.version == combat.version:
            return combat
        stack.quantity -= 1
    if updated.version == combat.version:
        return combat
    activity.state_version = updated.version
    activity.last_valid_action_at = datetime.now(UTC)
    record.snapshot = encode(updated)
    character.hp = updated.fighters["player"].hp
    return updated


async def consumable_state(session, character, combat, category, *, actor_key=None):
    stacks = (
        await session.scalars(
            select(ConsumableStack)
            .where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.quantity > 0,
            )
            .order_by(ConsumableStack.consumable_id)
        )
    ).all()
    budget = ENCOUNTER_CONSUMABLE_LIMITS.get(category, 0)
    quantities = tuple((stack.consumable_id, stack.quantity) for stack in stacks)
    options = combat_consumable_options(
        combat,
        tuple(stack.consumable_id for stack in stacks),
        budget_limit=budget,
        actor_key=actor_key,
    )
    return options, quantities, budget


def derive_consumable_selection(current, *, screen, item_id=None, target_id=None, parent="items"):
    """Derive a combat consumable screen from the current authoritative options."""
    if screen == "combat":
        return current
    if screen == "items":
        return replace(current, consumable_screen="items") if current.consumable_options else current
    item = consumable_definition(item_id or "")
    options = tuple(option for option in current.consumable_options if option.item_id == item_id)
    if item is None or not options:
        return replace(
            current,
            consumable_screen=None,
            consumable_notice="⚠️ Consumível · Não está mais disponível.",
        )
    if screen == "choose_item":
        targets = tuple(dict.fromkeys(option.target_id for option in options))
        if item.family == ConsumableFamily.DISPELLER and len(targets) > 1:
            return replace(current, consumable_screen="targets", selected_consumable_id=item.id)
        target_id = targets[0] if item.family == ConsumableFamily.DISPELLER and targets else "player"
        selected = tuple(option for option in options if option.target_id == target_id)
        return _selection_after_target(current, item.id, target_id, selected, parent="items")
    if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
        selected = tuple(option for option in options if option.target_id == target_id)
        if not selected:
            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Dissipador · Sem Alvo Válido",
            )
        return _selection_after_target(current, item.id, target_id, selected, parent="targets")
    if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
        targets = tuple(dict.fromkeys(option.target_id for option in options))
        return replace(
            current,
            consumable_screen="targets" if len(targets) > 1 else "items",
            selected_consumable_id=item.id if len(targets) > 1 else None,
        )
    if screen == "effects" and target_id is not None:
        selected = tuple(
            option for option in options
            if option.target_id == target_id and option.effect_id is not None
        )
        if len(selected) == 1:
            return replace(current, ready_consumable_option=selected[0])
        return replace(
            current,
            consumable_screen="effects",
            selected_consumable_id=item.id,
            selected_target_id=target_id,
            selection_parent=parent,
        )
    return replace(
        current,
        consumable_screen="items",
        consumable_notice="⚠️ Consumível · Não está mais disponível.",
    )


def _selection_after_target(current, item_id, target_id, selected, *, parent):
    if len(selected) == 1:
        return replace(current, ready_consumable_option=selected[0])
    if not selected:
        return replace(
            current,
            consumable_screen="items",
            consumable_notice="⚠️ Consumível · Não está mais disponível.",
        )
    return replace(
        current,
        consumable_screen="effects",
        selected_consumable_id=item_id,
        selected_target_id=target_id,
        selection_parent=parent,
    )
