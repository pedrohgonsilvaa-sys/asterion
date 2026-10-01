"""Reusable deterministic duel engine. Inputs and outputs are pure domain snapshots."""

from copy import deepcopy
from dataclasses import dataclass, field, replace
from decimal import ROUND_FLOOR, Decimal, localcontext
from typing import Any
from uuid import UUID

from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    PRECISION,
    CombatRng,
    CombatStats,
    chance_from_percentage_points,
    combine_active_mitigation,
    direct_damage,
    dot_damage,
    stable_priority,
)
from asterion.domain.consumables import ConsumableFamily, UseContext, definition

D = Decimal
ZERO = D(0)
PERCENT_POINT_STATS = frozenset({"per", "crit", "evasion", "block"})


@dataclass
class Effect:
    id: str
    stat: str
    magnitude: Decimal
    remaining: int
    applied_opportunity: int
    kind: str = "debuff"
    stat_modifier_mode: str = "multiplicative"
    removable: bool = True
    duration_eligible: bool = True
    protected: bool = False
    unremovable: bool = False
    fixed_mechanic: bool = False
    boss_protected: bool = False
    dissipatable: bool | None = None
    resguardo_eligible: bool | None = None
    hard_cc: bool = False
    stackable: bool = False
    stacks: int = 1
    stack_cap: int = 3
    stack_orders: list[int] = field(default_factory=list)
    application_event: str = ""
    instance_id: str = ""


@dataclass
class DotState:
    kind: str
    stacks: int
    remaining: int
    snapshot_attack: Decimal
    source: str
    stack_snapshots: list[Decimal] = field(default_factory=list)
    removable: bool = True
    protected: bool = False
    unremovable: bool = False
    fixed_mechanic: bool = False
    boss_protected: bool = False
    resguardo_eligible: bool | None = None
    application_event: str = ""
    instance_id: str = ""
    stack_cap: int = 3


@dataclass(frozen=True)
class ActionEffect:
    """Additional deterministic effect applied by a single committed action."""

    id: str
    stat: str
    magnitude: Decimal
    duration: int
    kind: str = "buff"
    stat_modifier_mode: str = "multiplicative"
    removable: bool = True
    unremovable: bool = False
    fixed_mechanic: bool = False
    hard_cc: bool = False


@dataclass(frozen=True)
class Action:
    id: str
    name: str
    coefficient: Decimal
    blocked_opportunities: int = 0
    attack_debuff: Decimal = D(0)
    duration: int = 0
    native_dot_kind: str | None = None
    native_dot_stacks: int = 0
    prepared: bool | None = None
    # Explicit canonical cooldowns coexist with the legacy blocked-opportunity
    # encoding so existing combat snapshots keep their exact timing.
    cooldown: int | None = None
    effect_stat: str | None = None
    per_bonus_if_target_poisoned: Decimal = D(0)
    self_barrier_coefficient: Decimal = D(0)
    self_barrier_duration: int = 0
    skip_if_barrier_active: bool = False
    effect_id: str | None = None
    self_effect_stat: str | None = None
    self_effect_magnitude: Decimal = ZERO
    self_effect_duration: int = 0
    self_effect_id: str | None = None
    self_effect_kind: str = "debuff"
    self_effect_modifier_mode: str = "multiplicative"
    target_mode: str = "opponent"
    heal_coefficient: Decimal = ZERO
    target_barrier_coefficient: Decimal = ZERO
    target_barrier_duration: int = 0
    next_direct_crit_bonus: Decimal = ZERO
    next_direct_crit_duration: int = 0
    next_direct_crit_effect_id: str | None = None
    crit_bonus_if_target_debuffed: Decimal = ZERO
    hit_count: int = 1
    self_effects: tuple[ActionEffect, ...] = ()
    self_state_tags_after: tuple[str, ...] | None = None
    effect_trigger_scope: str = "per_target"
    prepares_chain: str | None = None
    consumes_chain: str | None = None
    chain_power_bonus: Decimal = ZERO
    chain_power_bonus_damage: Decimal | None = None
    chain_power_bonus_healing: Decimal | None = None
    chain_power_bonus_barrier: Decimal | None = None
    prepares_chain_duration: int = 2
    self_barrier_debuff_magnitude_reduction: Decimal = ZERO
    target_barrier_debuff_magnitude_reduction: Decimal = ZERO
    target_effects: tuple[ActionEffect, ...] = ()
    manifestation_kind: str | None = None
    enemy_hp_fraction_below: Decimal | None = None
    enemy_hp_fraction_at_most: Decimal | None = None
    max_uses_per_combat: int | None = None

    def __post_init__(self) -> None:
        if self.hit_count < 1:
            raise ValueError("An action must resolve at least one hit.")
        if self.chain_power_bonus < ZERO:
            raise ValueError("Action chain power bonus cannot be negative.")
        if any(
            bonus is not None and bonus < ZERO
            for bonus in (
                self.chain_power_bonus_damage,
                self.chain_power_bonus_healing,
                self.chain_power_bonus_barrier,
            )
        ):
            raise ValueError("Action component chain power bonus cannot be negative.")
        if self.prepares_chain and self.prepares_chain_duration < 1:
            raise ValueError("Prepared action chains require a positive duration.")
        if self.effect_trigger_scope not in {"per_action", "per_hit", "per_target"}:
            raise ValueError("Action effect trigger scope is invalid.")
        if (
            self.enemy_hp_fraction_below is not None
            and not ZERO <= self.enemy_hp_fraction_below <= D(1)
        ):
            raise ValueError("Enemy HP phase threshold must be between zero and one.")
        if (
            self.enemy_hp_fraction_at_most is not None
            and not ZERO <= self.enemy_hp_fraction_at_most <= D(1)
        ):
            raise ValueError("Enemy HP phase threshold must be between zero and one.")
        if self.max_uses_per_combat is not None and self.max_uses_per_combat < 1:
            raise ValueError("Combat action use limit must be positive.")


@dataclass
class Fighter:
    id: str
    name: str
    level: int
    stats: CombatStats
    hp: Decimal
    race: str = ""
    character_class: str = ""
    opportunity: int = 0
    defending: bool = False
    last_action: str | None = None
    cooldowns: dict[str, int] = field(default_factory=dict)
    effects: list[Effect] = field(default_factory=list)
    barrier: Decimal = D(0)
    barrier_remaining: int = 0
    barrier_applied_opportunity: int = 0
    barrier_source: str = ""
    ward_remaining: int = 0
    ward_charges: int = 0
    ward_applied_opportunity: int = 0
    damage_taken_modifiers: dict[str, Decimal] = field(default_factory=dict)
    next_direct_crit_bonus: Decimal = ZERO
    next_direct_crit_expires_opportunity: int | None = None
    next_direct_crit_effect_id: str = ""
    retaliation_charges: int = 0
    retaliation_remaining: int = 0
    retaliation_applied_opportunity: int = 0
    retaliation_activation_id: str = ""
    retaliation_source_type: str = ""
    retaliation_source_event_id: str = ""
    retaliation_source_actor_id: str = ""
    retaliation_duration_bonus: int = 0
    side: str = ""
    takes_turn: bool = True
    defeat_on_zero: bool | None = None
    required_for_victory: bool | None = None
    protection_layers: int = 0
    protection_reduction_per_layer: Decimal = ZERO
    training_state_tags: tuple[str, ...] = ()
    tagged_direct_damage_reductions: dict[str, Decimal] = field(default_factory=dict)
    action_chains: dict[str, dict[str, str]] = field(default_factory=dict)
    barrier_debuff_magnitude_reduction: Decimal = ZERO
    selected_path: str | None = None
    talent_ids: tuple[str, ...] = ()
    path_state: dict[str, Any] = field(default_factory=dict)
    action_use_counts: dict[str, int] = field(default_factory=dict)

    def stat(self, name: str) -> Decimal:
        value = getattr(self.stats, name)
        # These attributes use percentage points; the existing Effect magnitude
        # contract is multiplicative and must not be applied to them implicitly.
        if name in PERCENT_POINT_STATS:
            for effect in self.effects:
                if effect.stat == name and effect.stat_modifier_mode == "percentage_points":
                    direction = -1 if effect.kind == "debuff" else 1
                    value += effect.magnitude * max(0, effect.stacks) * direction
            return value
        for effect in self.effects:
            if effect.stat == name:
                modifier = (
                    D(1) - effect.magnitude
                    if effect.kind == "debuff"
                    else D(1) + effect.magnitude
                )
                value *= modifier ** max(0, effect.stacks)
        return value


@dataclass(frozen=True)
class Tutorial:
    responses: dict[str, str]
    required_basics: tuple[str, ...] = ("attack", "defend")
    required_art: str = "art"


@dataclass(frozen=True)
class CombatEvent:
    sequence: int
    round: int
    actor: str
    action: str
    target: str = ""
    damage: int = 0
    critical: bool = False
    healed: Decimal = D(0)
    effect_id: str = ""
    barrier_absorbed: Decimal = D(0)
    barrier_value: Decimal = D(0)
    effect_removal_kind: str | None = None
    dodged: bool = False
    blocked: bool = False
    actor_entity_id: str = ""
    actor_effect_id: str = ""
    calculated_damage: int = 0
    effective_damage: int = 0
    target_defending: bool = False
    defender_mitigation_applied: bool = False
    target_barrier_source: str = ""
    prepared_resolution: bool = False
    target_effect_ids: tuple[str, ...] = ()
    defender_prevented_damage: int = 0
    retaliation_valid: bool = False
    retaliation_used: bool = False
    retaliation_event: str = ""
    retaliation_activation_id: str = ""
    retaliation_source_type: str = ""
    retaliation_source_event_id: str = ""
    retaliation_source_actor_id: str = ""
    retaliation_remaining: int = 0
    internal: bool = False
    action_instance_id: str = ""
    actor_effect_ids: tuple[str, ...] = ()
    prepared_action_instance_id: str = ""
    response_to_prepared_action_instance_id: str = ""
    dot_kind: str = ""
    dot_application_event_id: str = ""
    dot_source_id: str = ""
    hit_index: int = 1
    hit_count: int = 1
    protection_layers_before: int = 0
    protection_layers_after: int = 0
    target_state_tags: tuple[str, ...] = ()
    target_effect_application_event_ids: tuple[str, ...] = ()
    effect_application_event_id: str = ""
    chain_state_before: str = ""
    chain_state_after: str = ""
    chain_prepared_by_action_id: str = ""
    chain_consumed: bool = False
    chain_empowered: bool = False
    empowered_by_action_instance_id: str = ""
    chain_prepared_by_action_instance_id: str = ""
    chain_consumed_by_action_instance_id: str = ""
    chain_window_before: int = 0
    chain_window_after: int = 0
    power_component: str = ""
    power_multiplier: Decimal = D(1)
    damage_power_multiplier: Decimal = D(1)
    healing_power_multiplier: Decimal = D(1)
    barrier_power_multiplier: Decimal = D(1)
    trigger_scope: str = "per_action"
    barrier_applied_source: str = ""
    applied_effect_stat: str = ""
    applied_effect_magnitude: Decimal = ZERO
    applied_effect_duration: int = 0
    applied_effect_kind: str = ""
    applied_effect_removable: bool = False
    actor_effect_facts: tuple[tuple[str, str, Decimal, int, str], ...] = ()
    actor_applied_effect_stat: str = ""
    actor_applied_effect_magnitude: Decimal = ZERO
    actor_applied_effect_duration: int = 0
    actor_applied_effect_kind: str = ""
    base_healing: Decimal = ZERO
    calculated_healing: Decimal = ZERO
    effective_healing: Decimal = ZERO
    healing_received_multiplier: Decimal = D(1)
    overheal: Decimal = ZERO
    target_hp_after: Decimal | None = None
    fighter_hp_after: tuple[tuple[str, Decimal], ...] = ()
    path_triggers: tuple[str, ...] = ()
    path_power_multiplier: Decimal = D(1)
    path_final_damage_bonus: Decimal = ZERO
    aim_stacks: int = 0
    path_per_bonus: Decimal = ZERO
    path_crit_bonus: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class CombatConsumableOption:
    item_id: str
    target_id: str
    effect_id: str | None
    label: str


@dataclass
class Combat:
    id: UUID
    ruleset: str
    fighters: dict[str, Fighter]
    player_actions: dict[str, Action]
    enemy_actions: dict[str, Action]
    ai_cycle: tuple[str, ...]
    tutorial: Tutorial | None = None
    flavor: str = ""
    opening_log: str = ""
    version: int = 0
    round: int = 1
    order: tuple[str, ...] = ()
    turn_index: int = 0
    used_attack: bool = False
    used_defend: bool = False
    used_art: bool = False
    pending_response: str | None = None
    ai_position: int = 0
    rng_cursor: int = 0
    result: str | None = None
    events: list[CombatEvent] = field(default_factory=list)
    mechanic_events: list[CombatEvent] = field(default_factory=list)
    prepared_action: str | None = None
    prepared_source: str | None = None
    prepared_target: str | None = None
    prepared_action_instance_id: str | None = None
    resolving_prepared: bool = False
    response_window_seen: bool = False
    variant: str | None = None
    dot_states: dict[str, list[DotState]] = field(default_factory=dict)
    effect_sequence: int = 0
    application_sequence: int = 0
    blocked_application_events: list[str] = field(default_factory=list)
    consumable_uses: int = 0
    evasion_streaks: dict[str, int] = field(default_factory=dict)
    configuration_snapshot: dict | None = None
    ai_priority: tuple[str, ...] = ()
    external_consumables_allowed: bool = True
    ai_target_cycle: tuple[str, ...] = ()
    ai_target_position: int = 0

    @property
    def tutorial_stage(self) -> str:
        if self.tutorial is None or self.used_art:
            return "normal"
        if self.used_attack and self.used_defend:
            return "art"
        if self.used_attack:
            return "defend"
        if self.used_defend:
            return "attack"
        return "basics"


TARGET_MODES = frozenset({"opponent", "ally", "self", "all_opponents", "all_allies"})


def _fighter_side(state: Combat, key: str) -> str:
    fighter = state.fighters[key]
    return fighter.side or ("player" if key == "player" else "enemy")


def _fighter_defeat_on_zero(state: Combat, key: str) -> bool:
    value = state.fighters[key].defeat_on_zero
    return key == "player" if value is None else value


def _fighter_required_for_victory(state: Combat, key: str) -> bool:
    value = state.fighters[key].required_for_victory
    return _fighter_side(state, key) == "enemy" if value is None else value


def _resolve_fighter_key(state: Combat, target_id: str | None) -> str | None:
    if target_id is None:
        return None
    if target_id in state.fighters:
        return target_id
    matches = [key for key, fighter in state.fighters.items() if fighter.id == target_id]
    return matches[0] if len(matches) == 1 else None


def _action_is_pure_self(action: Action) -> bool:
    return bool(
        action.coefficient <= ZERO
        and action.attack_debuff <= ZERO
        and action.native_dot_stacks <= 0
        and action.heal_coefficient <= ZERO
        and action.target_barrier_coefficient <= ZERO
        and (
            action.self_barrier_coefficient > ZERO
            or (
                action.self_effect_id
                and action.self_effect_stat
                and action.self_effect_magnitude > ZERO
                and action.self_effect_duration > 0
            )
            or bool(action.self_effects)
        )
    )


def _resolve_action_targets(
    state: Combat,
    actor_key: str,
    action: Action,
    requested_target: str | None = None,
) -> tuple[str, ...]:
    if actor_key not in state.fighters or state.fighters[actor_key].hp <= 0:
        return ()
    if action.target_mode not in TARGET_MODES:
        return ()
    if _action_is_pure_self(action) or action.target_mode == "self":
        return (actor_key,)

    actor_side = _fighter_side(state, actor_key)
    wants_allies = action.target_mode in {"ally", "all_allies"}
    candidates = [
        key
        for key, fighter in state.fighters.items()
        if fighter.hp > 0
        and ((_fighter_side(state, key) == actor_side) == wants_allies)
    ]
    candidates.sort(key=lambda key: (state.fighters[key].id, key))
    if action.target_mode in {"all_opponents", "all_allies"}:
        return tuple(candidates)

    requested_key = _resolve_fighter_key(state, requested_target)
    if requested_key is not None:
        return (requested_key,) if requested_key in candidates else ()
    if len(candidates) == 1:
        return (candidates[0],)
    if actor_key != "player" and "player" in candidates:
        return ("player",)
    return ()


def action_target_ids(
    state: Combat, action_id: str, *, actor_key: str = "player"
) -> tuple[str, ...]:
    """Return deterministic, alive target entity IDs selectable for one action."""
    actions = state.player_actions if actor_key == "player" else state.enemy_actions
    action = actions.get(action_id)
    if action is None:
        return ()
    if (
        action.target_mode in {"all_opponents", "all_allies", "self"}
        or _action_is_pure_self(action)
    ):
        keys = _resolve_action_targets(state, actor_key, action)
    else:
        actor_side = _fighter_side(state, actor_key)
        wants_allies = action.target_mode == "ally"
        keys = tuple(
            sorted(
                (
                    key
                    for key, fighter in state.fighters.items()
                    if fighter.hp > 0
                    and ((_fighter_side(state, key) == actor_side) == wants_allies)
                ),
                key=lambda key: (state.fighters[key].id, key),
            )
        )
    return tuple(state.fighters[key].id for key in keys)


def _refresh_result(state: Combat) -> None:
    if any(
        fighter.hp <= 0 and _fighter_defeat_on_zero(state, key)
        for key, fighter in state.fighters.items()
    ):
        state.result = "defeat"
        _clear_prepared_action(state)
        return
    required_enemies = [
        key
        for key, fighter in state.fighters.items()
        if _fighter_side(state, key) == "enemy"
        and _fighter_required_for_victory(state, key)
    ]
    if required_enemies and all(state.fighters[key].hp <= 0 for key in required_enemies):
        state.result = "victory"
        _clear_prepared_action(state)


def initiative(state: Combat) -> tuple[str, ...]:
    return tuple(
        sorted(
            (
                key
                for key, fighter in state.fighters.items()
                if fighter.hp > 0 and fighter.takes_turn
            ),
            key=lambda key: (
                -state.fighters[key].stat("agility"),
                -stable_priority(state.id, key),
            ),
        )
    )


def allowed_actions(state: Combat) -> tuple[str, ...]:
    if state.result or not state.order or state.order[state.turn_index] != "player":
        return ()
    player = state.fighters["player"]
    allowed = [
        key for key in state.player_actions if player.cooldowns.get(key, 0) <= player.opportunity
    ]
    if player.last_action != "defend":
        allowed.append("defend")
    mask = {
        "basics": ("attack", "defend"),
        "attack": ("attack",),
        "defend": ("defend",),
        "art": ("art",),
    }.get(state.tutorial_stage)
    return tuple(action for action in allowed if mask is None or action in mask)


_RESGUARDO_DEFAULT_STATS = frozenset(
    {
        "attack",
        "defense",
        "agility",
        "perception",
        "precision",
        "accuracy",
        "crit",
        "critical",
        "block",
        "evasion",
        "healing_received",
        "action_restriction",
    }
)
_DOT_STACK_CAPS = {"poison": 3, "bleed": 3, "burn": 2}
_DOT_DURATIONS = {"poison": 3, "bleed": 2, "burn": 2}


def dissipatable(effect: Effect) -> bool:
    return bool(
        effect.kind == "buff"
        and effect.removable
        and effect.remaining > 0
        and effect.stacks > 0
        and not effect.unremovable
        and not effect.protected
        and not effect.fixed_mechanic
        and not effect.boss_protected
        and effect.dissipatable is not False
    )


def purifiable(effect: Effect) -> bool:
    return bool(
        effect.kind == "debuff"
        and effect.removable
        and effect.remaining > 0
        and effect.stacks > 0
        and not effect.unremovable
        and not effect.protected
        and not effect.fixed_mechanic
        and not effect.boss_protected
    )


def resguardo_eligible(effect: Effect) -> bool:
    if (
        effect.kind != "debuff"
        or not effect.removable
        or effect.unremovable
        or effect.protected
        or effect.fixed_mechanic
        or effect.boss_protected
        or effect.hard_cc
    ):
        return False
    if effect.resguardo_eligible is not None:
        return effect.resguardo_eligible
    return effect.stat in _RESGUARDO_DEFAULT_STATS


def _next_instance_id(state: Combat, prefix: str) -> tuple[str, int]:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    existing = {
        effect.instance_id or f"e{index + 1:x}"
        for fighter in state.fighters.values()
        for index, effect in enumerate(fighter.effects)
    }
    existing.update(
        dot.instance_id or f"d{index + 1:x}"
        for dots in state.dot_states.values()
        for index, dot in enumerate(dots)
    )
    while True:
        state.effect_sequence += 1
        value = state.effect_sequence
        parts = []
        while value:
            value, remainder = divmod(value, 36)
            parts.append(digits[remainder])
        encoded = "".join(reversed(parts)) or "0"
        candidate = f"{prefix}{encoded}"
        if candidate not in existing:
            return candidate, state.effect_sequence


def _next_application_event(state: Combat) -> str:
    state.application_sequence += 1
    return f"{state.id.hex}:application:{state.application_sequence:x}"


def _consume_ward(target: Fighter) -> None:
    target.ward_charges = 0
    target.ward_remaining = 0


def _matching_effect_index(effects: list[Effect], candidate: Effect) -> int | None:
    return next(
        (
            index
            for index, current in enumerate(effects)
            if current.id == candidate.id
            and current.kind == candidate.kind
            and current.stat == candidate.stat
        ),
        None,
    )


def _effect_application_would_apply(existing: Effect | None, candidate: Effect) -> bool:
    if existing is None:
        return True
    if candidate.stackable != existing.stackable or candidate.magnitude > existing.magnitude:
        return True
    if candidate.magnitude < existing.magnitude:
        return False
    if candidate.stackable:
        cap = max(1, candidate.stack_cap)
        return min(candidate.stacks, max(0, cap - existing.stacks)) > 0
    return True


def _simulate_effect_application(effects: list[Effect], candidate: Effect) -> None:
    index = _matching_effect_index(effects, candidate)
    if index is None:
        effects.append(deepcopy(candidate))
        return
    existing = effects[index]
    if candidate.stackable != existing.stackable or candidate.magnitude > existing.magnitude:
        effects[index] = deepcopy(candidate)
    elif candidate.magnitude == existing.magnitude and candidate.stackable:
        existing.stacks += min(
            candidate.stacks,
            max(0, max(1, candidate.stack_cap) - existing.stacks),
        )


def _apply_effect_duration(state: Combat, target: Fighter, effect: Effect) -> None:
    if target.race == "velado" and effect.duration_eligible and effect.remaining >= 2:
        rng = CombatRng(state.id, state.rng_cursor)
        if rng.chance(D("0.25"), f"racial-duration:{target.id}:{effect.id}"):
            effect.remaining += 1 if effect.kind == "buff" else -1
        state.rng_cursor = rng.cursor


def _prepare_effect_identity(state: Combat, target: Fighter, effect: Effect) -> None:
    order_values = sorted(effect.stack_orders[: max(0, effect.stacks)])
    while len(order_values) < max(0, effect.stacks):
        _instance_id, order = _next_instance_id(state, "e")
        order_values.append(order)
    effect.stack_orders = order_values
    if not effect.instance_id or any(
        current.instance_id == effect.instance_id for current in target.effects
    ):
        effect.instance_id, _ = _next_instance_id(state, "e")


def apply_effect_batch(
    state: Combat,
    target: Fighter,
    effects: list[Effect] | tuple[Effect, ...],
    *,
    application_event: str | None = None,
    immunity_passed: bool = True,
    resistance_passed: bool = True,
) -> bool:
    """Resolve one status application after immunity and resistance checks.

    Effects in one batch share an application event. Resguardo therefore blocks
    every eligible stack in that application while consuming one charge.
    """
    if not effects or not immunity_passed or not resistance_passed:
        return False
    event_id = application_event or _next_application_event(state)
    if event_id in state.blocked_application_events:
        return False

    pending = [
        deepcopy(effect)
        for effect in effects
        if effect.remaining > 0 and effect.stacks > 0
    ]
    if not pending:
        return False
    # Alvorano's reduction resolves before the success check and Resguardo.
    for effect in pending:
        if target.race == "alvorano" and effect.kind == "debuff" and effect.removable:
            effect.magnitude *= D("0.88")
        barrier_reduction = target.barrier_debuff_magnitude_reduction
        numeric_stat = hasattr(target.stats, effect.stat) or effect.stat == "healing_received"
        if (
            barrier_reduction > ZERO
            and target.barrier > ZERO
            and target.barrier_remaining > 0
            and effect.kind == "debuff"
            and effect.removable
            and not effect.fixed_mechanic
            and not effect.hard_cc
            and numeric_stat
        ):
            effect.magnitude *= max(ZERO, D(1) - barrier_reduction)

    simulated_effects = deepcopy(target.effects)
    would_apply: list[bool] = []
    for effect in pending:
        index = _matching_effect_index(simulated_effects, effect)
        existing = simulated_effects[index] if index is not None else None
        accepted = _effect_application_would_apply(existing, effect)
        would_apply.append(accepted)
        if accepted:
            _simulate_effect_application(simulated_effects, effect)

    if (
        target.ward_charges > 0
        and target.ward_remaining > 0
        and any(
            accepted and resguardo_eligible(effect)
            for accepted, effect in zip(would_apply, pending, strict=True)
        )
    ):
        _consume_ward(target)
        state.blocked_application_events.append(event_id)
        return False

    applied_any = False
    for accepted, effect in zip(would_apply, pending, strict=True):
        if not accepted:
            continue
        if effect.stackable:
            effect.stack_cap = max(1, effect.stack_cap)
            effect.stacks = min(effect.stacks, effect.stack_cap)
        effect.applied_opportunity = target.opportunity
        effect.application_event = event_id
        existing_index = _matching_effect_index(target.effects, effect)
        if existing_index is None:
            _apply_effect_duration(state, target, effect)
            _prepare_effect_identity(state, target, effect)
            target.effects.append(effect)
            applied_any = True
            continue

        existing = target.effects[existing_index]
        if effect.stackable != existing.stackable or effect.magnitude > existing.magnitude:
            _apply_effect_duration(state, target, effect)
            _prepare_effect_identity(state, target, effect)
            target.effects[existing_index] = effect
            applied_any = True
            continue
        if effect.magnitude < existing.magnitude:
            continue
        if effect.stackable:
            cap = max(1, effect.stack_cap)
            accepted = min(effect.stacks, max(0, cap - existing.stacks))
            if accepted <= 0:
                continue
            _apply_effect_duration(state, target, effect)
            existing.stack_cap = cap
            existing_orders = sorted(existing.stack_orders[: existing.stacks])
            while len(existing_orders) < existing.stacks:
                _instance_id, order = _next_instance_id(state, "e")
                existing_orders.append(order)
            incoming_orders = sorted(effect.stack_orders[: effect.stacks])
            while len(incoming_orders) < effect.stacks:
                _instance_id, order = _next_instance_id(state, "e")
                incoming_orders.append(order)
            if not existing.instance_id:
                existing.instance_id, _ = _next_instance_id(state, "e")
            existing.stacks += accepted
            existing.stack_orders = sorted(
                existing_orders + incoming_orders[:accepted]
            )
        else:
            _apply_effect_duration(state, target, effect)
            if not existing.instance_id:
                existing.instance_id, _ = _next_instance_id(state, "e")
        existing.remaining = max(existing.remaining, effect.remaining)
        existing.applied_opportunity = target.opportunity
        existing.application_event = event_id
        applied_any = True
    return applied_any


def apply_effect(
    state: Combat,
    target: Fighter,
    effect: Effect,
    *,
    application_event: str | None = None,
    immunity_passed: bool = True,
    resistance_passed: bool = True,
) -> bool:
    """Apply one effect through the same protection/interception pipeline."""
    return apply_effect_batch(
        state,
        target,
        (effect,),
        application_event=application_event,
        immunity_passed=immunity_passed,
        resistance_passed=resistance_passed,
    )


def _dot_is_resguardo_eligible(dot: DotState) -> bool:
    if (
        not dot.removable
        or dot.unremovable
        or dot.protected
        or dot.fixed_mechanic
        or dot.boss_protected
    ):
        return False
    return dot.resguardo_eligible is not False


def apply_dot_stacks(
    state: Combat,
    target: Fighter,
    *,
    kind: str,
    snapshots: list[Decimal] | tuple[Decimal, ...],
    source: str,
    duration: int,
    application_event: str,
    immunity_passed: bool = True,
    resistance_passed: bool = True,
    removable: bool = True,
    protected: bool = False,
    unremovable: bool = False,
    fixed_mechanic: bool = False,
    boss_protected: bool = False,
    resguardo_eligible: bool | None = None,
    stack_cap: int | None = None,
) -> bool:
    """Add one DoT application, respecting Resguardo before stack mutation."""
    if not snapshots or duration <= 0 or not immunity_passed or not resistance_passed:
        return False
    dots = state.dot_states.get(target.id, [])
    current = next((dot for dot in dots if dot.kind == kind), None)
    cap = max(1, stack_cap or _DOT_STACK_CAPS.get(kind, 3))
    candidate = DotState(
        kind,
        0,
        duration,
        snapshots[0],
        source,
        [],
        removable,
        protected,
        unremovable,
        fixed_mechanic,
        boss_protected,
        resguardo_eligible,
        stack_cap=cap,
    )
    if application_event in state.blocked_application_events:
        return False
    if (
        target.ward_charges > 0
        and target.ward_remaining > 0
        and _dot_is_resguardo_eligible(candidate)
    ):
        _consume_ward(target)
        state.blocked_application_events.append(application_event)
        return False

    if current is None:
        current = candidate
        current.instance_id, _ = _next_instance_id(state, "d")
        current.application_event = application_event
        if target.id not in state.dot_states:
            state.dot_states[target.id] = dots
        dots.append(current)
    existing_snapshots = current.stack_snapshots or [
        current.snapshot_attack
    ] * current.stacks
    merged = list(existing_snapshots)
    for snapshot in snapshots:
        while len(merged) >= cap:
            merged.pop(0)
        merged.append(snapshot)
    current.stack_snapshots = merged
    current.snapshot_attack = merged[0]
    current.stacks = len(merged)
    current.remaining = duration
    current.source = source
    current.removable = removable
    current.protected = protected
    current.unremovable = unremovable
    current.fixed_mechanic = fixed_mechanic
    current.boss_protected = boss_protected
    current.resguardo_eligible = resguardo_eligible
    current.application_event = application_event
    current.stack_cap = cap
    return True


def consumable_effect_options(
    state: Combat, item_id: str, *, target_id: str = "player"
) -> tuple[tuple[str, str], ...]:
    """Return stable IDs for currently selectable effects, not display indexes."""
    item = definition(item_id)
    if (
        item is None
        or not state.external_consumables_allowed
        or target_id not in state.fighters
    ):
        return ()
    target = state.fighters[target_id]
    options: list[tuple[str, str]] = []
    if item.family in {ConsumableFamily.PURIFICATION, ConsumableFamily.ANTIDOTE}:
        for index, dot in enumerate(state.dot_states.get(target_id, [])):
            if (
                dot.stacks > 0
                and dot.remaining > 0
                and dot.removable
                and not dot.unremovable
                and not dot.protected
                and not dot.fixed_mechanic
                and not dot.boss_protected
            ):
                options.append((dot.instance_id or f"d{index + 1:x}", f"dot:{dot.kind}"))
        if item.family == ConsumableFamily.PURIFICATION:
            for index, effect in enumerate(target.effects):
                if purifiable(effect):
                    options.append(
                        (effect.instance_id or f"e{index + 1:x}", f"effect:{effect.id}")
                    )
    elif item.family == ConsumableFamily.DISPELLER and target_id != "player":
        for index, effect in enumerate(target.effects):
            if dissipatable(effect):
                options.append(
                    (effect.instance_id or f"e{index + 1:x}", f"effect:{effect.id}")
                )
    return tuple(options)


def _effect_display_name(state: Combat, target_id: str, selection: str) -> str:
    if selection.startswith("dot:"):
        return {
            "dot:poison": "Veneno",
            "dot:bleed": "Sangramento",
            "dot:burn": "Queimadura",
        }.get(selection, "Dano ao Longo do Tempo")
    effect_id = selection.removeprefix("effect:")
    actions = state.enemy_actions if target_id != "player" else state.player_actions
    action = actions.get(effect_id)
    if action is not None:
        return action.name
    return "Efeito Negativo" if target_id == "player" else "Efeito Positivo"


def combat_consumable_options(
    state: Combat, item_ids: tuple[str, ...] | list[str], *, budget_limit: int
) -> tuple[CombatConsumableOption, ...]:
    """Project stock-backed, currently valid actions for a combat screen."""
    if not state.external_consumables_allowed:
        return ()
    options: list[CombatConsumableOption] = []
    for item_id in sorted(set(item_ids)):
        item = definition(item_id)
        if item is None or item.use_context is not UseContext.COMBAT_PVE:
            continue
        if item.family in {
            ConsumableFamily.HEALING,
            ConsumableFamily.PROTECTION,
            ConsumableFamily.WARDING,
        }:
            if combat_consumable_usable(
                state, item_id, target_id="player", budget_limit=budget_limit
            ):
                options.append(CombatConsumableOption(item_id, "player", None, item.name))
        elif item.family in {ConsumableFamily.PURIFICATION, ConsumableFamily.ANTIDOTE}:
            for effect_id, selection in consumable_effect_options(
                state, item_id, target_id="player"
            ):
                if combat_consumable_usable(
                    state,
                    item_id,
                    target_id="player",
                    effect_id=effect_id,
                    budget_limit=budget_limit,
                ):
                    options.append(
                        CombatConsumableOption(
                            item_id,
                            "player",
                            effect_id,
                            f"{item.name} · {_effect_display_name(state, 'player', selection)}",
                        )
                    )
        elif item.family == ConsumableFamily.DISPELLER:
            for target_id, target in state.fighters.items():
                if target_id == "player" or target.hp <= 0:
                    continue
                for effect_id, selection in consumable_effect_options(
                    state, item_id, target_id=target_id
                ):
                    if combat_consumable_usable(
                        state,
                        item_id,
                        target_id=target_id,
                        effect_id=effect_id,
                        budget_limit=budget_limit,
                    ):
                        options.append(
                            CombatConsumableOption(
                                item_id,
                                target_id,
                                effect_id,
                                f"{item.name} · {target.name} · "
                                f"{_effect_display_name(state, target_id, selection)}",
                            )
                        )
    return tuple(options)


def _deal_damage(target: Fighter, amount: Decimal | int) -> tuple[Decimal, Decimal]:
    incoming = max(D(0), D(amount))
    absorbed = D(0)
    if target.barrier_remaining > 0 and target.barrier > 0:
        absorbed = min(target.barrier, incoming)
        target.barrier -= absorbed
        if target.barrier <= 0:
            target.barrier = D(0)
            target.barrier_remaining = 0
            target.barrier_source = ""
            target.barrier_debuff_magnitude_reduction = ZERO
    else:
        target.barrier = D(0)
        target.barrier_remaining = 0
        target.barrier_source = ""
        target.barrier_debuff_magnitude_reduction = ZERO
    hp_damage = min(max(D(0), target.hp), incoming - absorbed)
    target.hp = max(D(0), target.hp - hp_damage)
    return hp_damage, absorbed


def _begin_turn(state: Combat) -> None:
    if state.result or not state.order:
        return
    actor_key = state.order[state.turn_index]
    actor = state.fighters[actor_key]
    actor.opportunity += 1
    actor.defending = False
    if actor_key == "player" and state.prepared_action is not None:
        state.response_window_seen = True


def _clear_prepared_action(state: Combat) -> None:
    state.prepared_action = None
    state.prepared_source = None
    state.prepared_target = None
    state.prepared_action_instance_id = None
    state.resolving_prepared = False
    state.response_window_seen = False


def _cooldown_deadline(actor: Fighter, action: Action) -> int:
    if action.cooldown is not None:
        return actor.opportunity + action.cooldown
    return actor.opportunity + action.blocked_opportunities + 1


def _retaliation_duration(actor: Fighter) -> int:
    return max(1, 1 + max(0, actor.retaliation_duration_bonus))


def _retaliation_active(actor: Fighter) -> bool:
    return actor.retaliation_charges > 0 and actor.retaliation_remaining > 0


def _clear_retaliation(actor: Fighter) -> None:
    actor.retaliation_charges = 0
    actor.retaliation_remaining = 0
    actor.retaliation_applied_opportunity = 0
    actor.retaliation_activation_id = ""
    actor.retaliation_source_type = ""
    actor.retaliation_source_event_id = ""
    actor.retaliation_source_actor_id = ""


def _retaliation_event(
    state: Combat,
    *,
    actor_key: str,
    target_id: str,
    kind: str,
    activation_id: str,
    source_type: str,
    source_event_id: str,
    source_actor_id: str,
    remaining: int,
) -> None:
    state.mechanic_events.append(
        CombatEvent(
            len(state.mechanic_events),
            state.round,
            actor_key,
            f"retaliation:{kind}",
            target_id,
            actor_entity_id=state.fighters[actor_key].id,
            retaliation_event=kind,
            retaliation_activation_id=activation_id,
            retaliation_source_type=source_type,
            retaliation_source_event_id=source_event_id,
            retaliation_source_actor_id=source_actor_id,
            retaliation_remaining=remaining,
            internal=True,
        )
    )


def _grant_retaliation(
    state: Combat,
    *,
    target_key: str,
    source_actor: Fighter,
    source_event_id: str,
    source_type: str = "defender",
) -> None:
    target = state.fighters[target_key]
    if target.character_class != "sentinela":
        return
    duration = _retaliation_duration(target)
    if _retaliation_active(target):
        target.retaliation_remaining = max(target.retaliation_remaining, duration)
        target.retaliation_applied_opportunity = target.opportunity
        target.retaliation_source_type = source_type
        target.retaliation_source_event_id = source_event_id
        target.retaliation_source_actor_id = source_actor.id
        kind = "refreshed"
    else:
        target.retaliation_charges = 1
        target.retaliation_remaining = duration
        target.retaliation_applied_opportunity = target.opportunity
        target.retaliation_activation_id = (
            f"{state.id.hex}:retaliation:{state.version}:{len(state.events)}:{target.id}"
        )
        target.retaliation_source_type = source_type
        target.retaliation_source_event_id = source_event_id
        target.retaliation_source_actor_id = source_actor.id
        kind = "granted"
    _retaliation_event(
        state,
        actor_key=target_key,
        target_id=target.id,
        kind=kind,
        activation_id=target.retaliation_activation_id,
        source_type=target.retaliation_source_type,
        source_event_id=target.retaliation_source_event_id,
        source_actor_id=target.retaliation_source_actor_id,
        remaining=target.retaliation_remaining,
    )
    if "talent.sentinela.ritmo_de_guarda" in target.talent_ids:
        effect_id = "talent.sentinela.ritmo_de_guarda.agility"
        existing = next((effect for effect in target.effects if effect.id == effect_id), None)
        if existing is None:
            target.effects.append(
                Effect(
                    effect_id,
                    "agility",
                    D("0.05"),
                    1,
                    target.opportunity,
                    kind="buff",
                )
            )
        else:
            existing.magnitude = D("0.05")
            existing.remaining = 1
            existing.applied_opportunity = target.opportunity
    if target.selected_path == "bastiao":
        source = "path.bastiao.fortaleza"
        if not (
            target.barrier > ZERO
            and target.barrier_remaining > 0
            and target.barrier_source == source
        ):
            value = (target.stats.hp * D("0.04") * D("1.10")).to_integral_value(
                rounding=ROUND_FLOOR
            )
            if value > ZERO:
                target.barrier = value
                target.barrier_remaining = 1
                target.barrier_applied_opportunity = target.opportunity
                target.barrier_source = source
                target.barrier_debuff_magnitude_reduction = ZERO
                state.mechanic_events.append(
                    CombatEvent(
                        len(state.mechanic_events),
                        state.round,
                        target_key,
                        "path.bastiao.fortaleza",
                        target.id,
                        actor_entity_id=target.id,
                        barrier_value=value,
                        barrier_applied_source=source,
                        path_triggers=("bastiao.fortaleza",),
                        internal=True,
                    )
                )


def _action_is_offensive(action: Action) -> bool:
    return bool(
        action.coefficient > ZERO
        or action.attack_debuff > ZERO
        or action.native_dot_stacks > 0
    )


def _consume_retaliation(
    state: Combat, actor_key: str, actor: Fighter, action: Action
) -> dict[str, str | bool | int]:
    if (
        actor.character_class != "sentinela"
        or not _retaliation_active(actor)
        or not _action_is_offensive(action)
    ):
        return {"used": False}
    context: dict[str, str | bool | int] = {
        "used": True,
        "activation_id": actor.retaliation_activation_id,
        "source_type": actor.retaliation_source_type,
        "source_event_id": actor.retaliation_source_event_id,
        "source_actor_id": actor.retaliation_source_actor_id,
    }
    _retaliation_event(
        state,
        actor_key=actor_key,
        target_id=actor.id,
        kind="consumed",
        activation_id=actor.retaliation_activation_id,
        source_type=actor.retaliation_source_type,
        source_event_id=actor.retaliation_source_event_id,
        source_actor_id=actor.retaliation_source_actor_id,
        remaining=0,
    )
    _clear_retaliation(actor)
    return context


def _retaliation_action_resolved(
    state: Combat, actor_key: str, actor: Fighter, context: dict[str, str | bool | int]
) -> None:
    if not context.get("used"):
        return
    _retaliation_event(
        state,
        actor_key=actor_key,
        target_id=actor.id,
        kind="action_resolved",
        activation_id=str(context.get("activation_id", "")),
        source_type=str(context.get("source_type", "")),
        source_event_id=str(context.get("source_event_id", "")),
        source_actor_id=str(context.get("source_actor_id", "")),
        remaining=0,
    )


def _advance_turn_cursor(state: Combat) -> None:
    if state.result:
        return
    while True:
        state.turn_index += 1
        if state.turn_index >= len(state.order):
            state.round += 1
            state.order = initiative(state)
            state.turn_index = 0
            if not state.order:
                return
        actor = state.fighters[state.order[state.turn_index]]
        if actor.hp > 0 and actor.takes_turn:
            break
    _begin_turn(state)


def _end_turn(state: Combat) -> None:
    if not state.order:
        return
    actor_key = state.order[state.turn_index]
    actor = state.fighters[actor_key]
    for dot in state.dot_states.get(actor.id, []):
        coefficient = (
            D("0.12")
            if dot.kind == "poison"
            else D("0.15")
            if dot.kind == "burn"
            else D("0.10")
        )
        snapshots = dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks
        source_key = _resolve_fighter_key(state, dot.source)
        source = state.fighters.get(source_key) if source_key is not None else None
        attacker_level = source.level if source is not None else actor.level
        damage = dot_damage(
            snapshots,
            coefficient,
            actor.stat("defense"),
            attacker_level,
            penetration=(
                source.stat("per")
                if source is not None and state.ruleset == CURRENT_COMBAT_RULESET
                else ZERO
            ),
        )
        modifier = actor.damage_taken_modifiers.get(dot.kind, D(1))
        if modifier != D(1) and damage > 0:
            damage = max(
                1,
                int(
                    (D(damage) * modifier).to_integral_value(
                        rounding=ROUND_FLOOR
                    )
                ),
            )
        actual_damage, barrier_absorbed = _deal_damage(actor, damage)
        source_actor = source.id if source is not None else dot.source
        state.mechanic_events.append(
            CombatEvent(
                len(state.mechanic_events),
                state.round,
                source_key or source_actor,
                f"dot:{dot.kind}:tick",
                actor.id,
                int(actual_damage),
                actor_entity_id=source_actor,
                calculated_damage=int(damage),
                effective_damage=int(actual_damage),
                barrier_absorbed=barrier_absorbed,
                internal=True,
                dot_kind=dot.kind,
                dot_application_event_id=dot.application_event,
                dot_source_id=dot.source,
            )
        )
        dot.remaining -= 1
    state.dot_states[actor.id] = [
        dot for dot in state.dot_states.get(actor.id, []) if dot.remaining > 0
    ]
    _refresh_result(state)
    for effect in actor.effects:
        if actor.opportunity > effect.applied_opportunity:
            effect.remaining -= 1
    actor.effects = [effect for effect in actor.effects if effect.remaining > 0]
    if (
        actor.next_direct_crit_expires_opportunity is not None
        and actor.opportunity > actor.next_direct_crit_expires_opportunity
    ):
        actor.next_direct_crit_bonus = ZERO
        actor.next_direct_crit_expires_opportunity = None
        actor.next_direct_crit_effect_id = ""
    if actor.opportunity > actor.barrier_applied_opportunity and actor.barrier_remaining > 0:
        actor.barrier_remaining -= 1
        if actor.barrier_remaining == 0:
            actor.barrier = D(0)
            actor.barrier_source = ""
            actor.barrier_debuff_magnitude_reduction = ZERO
    if actor.opportunity > actor.ward_applied_opportunity and actor.ward_remaining > 0:
        actor.ward_remaining -= 1
        if actor.ward_remaining == 0:
            actor.ward_charges = 0
    if (
        _retaliation_active(actor)
        and actor.opportunity > actor.retaliation_applied_opportunity
    ):
        actor.retaliation_remaining -= 1
        if actor.retaliation_remaining <= 0:
            activation_id = actor.retaliation_activation_id
            source_type = actor.retaliation_source_type
            source_event_id = actor.retaliation_source_event_id
            source_actor_id = actor.retaliation_source_actor_id
            _clear_retaliation(actor)
            _retaliation_event(
                state,
                actor_key=actor_key,
                target_id=actor.id,
                kind="expired",
                activation_id=activation_id,
                source_type=source_type,
                source_event_id=source_event_id,
                source_actor_id=source_actor_id,
                remaining=0,
            )
    for chain_key, chain in tuple(sorted(actor.action_chains.items())):
        applied_opportunity = int(chain.get("applied_opportunity", actor.opportunity))
        if actor.opportunity <= applied_opportunity:
            continue
        window_before = int(chain.get("remaining", chain.get("duration", 2)))
        window_after = max(0, window_before - 1)
        if window_after > 0:
            chain["remaining"] = window_after
            continue
        actor.action_chains.pop(chain_key, None)
        state.events.append(
            CombatEvent(
                len(state.events),
                state.round,
                actor_key,
                "chain:expired",
                actor.id,
                actor_entity_id=actor.id,
                action_instance_id=str(chain.get("action_instance_id", "")),
                chain_state_before="ready",
                chain_state_after="expired",
                chain_prepared_by_action_id=str(chain.get("prepared_by_action_id", "")),
                chain_prepared_by_action_instance_id=str(
                    chain.get("action_instance_id", "")
                ),
                chain_window_before=window_before,
                chain_window_after=0,
                internal=True,
            )
        )
    _tick_path_resources(state, actor_key)
    if not state.result:
        _advance_turn_cursor(state)


def _chain_bonus(action: Action, component: str) -> Decimal:
    component_bonus = getattr(action, f"chain_power_bonus_{component}", None)
    return action.chain_power_bonus if component_bonus is None else component_bonus


def _path_chain_bonus(actor: Fighter, action: Action, component: str) -> Decimal:
    if actor.character_class == "tecelao" and actor.selected_path == "conjurador":
        return D("0.15") if component == "damage" else D("0.06")
    if actor.character_class == "tecelao" and actor.selected_path == "runico":
        return D("0.06") if component == "damage" else D("0.15")
    return _chain_bonus(action, component)


def _path_target_context(path_resolution: dict, target: Fighter) -> dict:
    return path_resolution.get("by_target", {}).get(target.id, {})


def _action_power_component(action: Action) -> str:
    if action.coefficient > ZERO:
        return "damage"
    if action.heal_coefficient > ZERO:
        return "healing"
    if action.self_barrier_coefficient > ZERO or action.target_barrier_coefficient > ZERO:
        return "barrier"
    return ""


def _is_art_action(action_id: str, action: Action) -> bool:
    return action_id == "art" or action.id.startswith(("class_art.", "path_art."))


def _has_valid_negative_effect(state: Combat, target: Fighter) -> bool:
    return any(
        effect.kind == "debuff"
        and effect.removable
        and not effect.unremovable
        and not effect.protected
        and not effect.fixed_mechanic
        and not effect.boss_protected
        and effect.remaining > 0
        and effect.stacks > 0
        for effect in target.effects
    ) or any(
        dot.removable
        and not dot.unremovable
        and not dot.protected
        and not dot.fixed_mechanic
        and not dot.boss_protected
        and dot.remaining > 0
        and dot.stacks > 0
        for dot in state.dot_states.get(target.id, ())
    )


def _aim_entry(target: Fighter, source: Fighter) -> dict | None:
    entries = target.path_state.setdefault("aim_from", {})
    entry = entries.get(source.id)
    if not isinstance(entry, dict) or int(entry.get("remaining", 0)) <= 0:
        return None
    return entry


def _grant_aim(
    state: Combat,
    source_key: str,
    target_key: str,
    *,
    trigger: str,
    action_targets: set[str] | None = None,
) -> int:
    source = state.fighters[source_key]
    target = state.fighters[target_key]
    specialization = source.selected_path if source.character_class == "vigia" else None
    maximum = 4 if specialization == "atirador" else 2 if specialization == "rastreador" else 3
    target_id = target.id
    if specialization != "rastreador":
        # Baseline Mira follows one offensive target; Atirador retains only the
        # selected target as well. Stable fighter order makes AoE deterministic.
        retained_ids = action_targets or {target_id}
        for other in state.fighters.values():
            if other.id not in retained_ids:
                other.path_state.setdefault("aim_from", {}).pop(source.id, None)
    else:
        current_targets = [
            fighter
            for fighter in state.fighters.values()
            if (entry := _aim_entry(fighter, source)) is not None
        ]
        if _aim_entry(target, source) is None and len(current_targets) >= 3:
            return 0
    entries = target.path_state.setdefault("aim_from", {})
    entry = entries.get(source.id)
    stacks = min(maximum, int(entry.get("stacks", 0)) + 1) if isinstance(entry, dict) else 1
    entries[source.id] = {
        "stacks": stacks,
        "remaining": 2,
        "applied_opportunity": target.opportunity,
        "trigger": trigger,
    }
    return stacks


def _tick_path_resources(state: Combat, actor_key: str) -> None:
    actor = state.fighters[actor_key]
    state_data = actor.path_state
    for key in ("luminar_state", "manifestation_state", "devastador_charge"):
        entry = state_data.get(key)
        if not isinstance(entry, dict):
            continue
        if key == "devastador_charge":
            if actor.opportunity > int(entry.get("expires_opportunity", -1)):
                state_data.pop(key, None)
            continue
        applied = int(entry.get("applied_opportunity", actor.opportunity))
        if actor.opportunity <= applied:
            continue
        remaining = max(0, int(entry.get("remaining", 0)) - 1)
        if remaining <= 0:
            state_data.pop(key, None)
        else:
            entry["remaining"] = remaining
    for key in ("omen_offensive", "omen_defensive"):
        entries = state_data.get(key)
        if not isinstance(entries, dict):
            continue
        for target_id, entry in tuple(entries.items()):
            if not isinstance(entry, dict):
                entries.pop(target_id, None)
                continue
            applied = int(entry.get("applied_opportunity", actor.opportunity))
            if actor.opportunity > applied:
                entry["remaining"] = max(0, int(entry.get("remaining", 0)) - 1)
            if int(entry.get("remaining", 0)) <= 0:
                entries.pop(target_id, None)
    incoming = actor.path_state.get("aim_from", {})
    if isinstance(incoming, dict):
        for source_id, entry in tuple(incoming.items()):
            if not isinstance(entry, dict):
                incoming.pop(source_id, None)
                continue
            applied = int(entry.get("applied_opportunity", actor.opportunity))
            if actor.opportunity > applied:
                entry["remaining"] = max(0, int(entry.get("remaining", 0)) - 1)
            if int(entry.get("remaining", 0)) <= 0:
                incoming.pop(source_id, None)


def _new_omen(actor: Fighter, kind: str, target: Fighter) -> None:
    key = "omen_offensive" if kind == "offensive" else "omen_defensive"
    actor.path_state.setdefault(key, {})[target.id] = {
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }


def _prepare_path_action(
    state: Combat,
    actor_id: str,
    action_id: str,
    action: Action,
    target_keys: tuple[str, ...],
) -> dict:
    actor = state.fighters[actor_id]
    is_art = _is_art_action(action_id, action)
    direct = action.coefficient > ZERO
    support = action.heal_coefficient > ZERO or (
        action.self_barrier_coefficient > ZERO
        or action.target_barrier_coefficient > ZERO
    )
    context = {
        "by_target": {},
        "target_ids": {state.fighters[key].id for key in target_keys},
        "luminar_consumed": False,
        "luminar_generated": None,
        "action_instance_id": "",
    }
    if actor.character_class == "vigia" and direct and actor.selected_path != "rastreador":
        target_ids = {state.fighters[key].id for key in target_keys}
        for other in state.fighters.values():
            if other.id not in target_ids:
                other.path_state.setdefault("aim_from", {}).pop(actor.id, None)
    for target_key in target_keys:
        target = state.fighters[target_key]
        aim = _aim_entry(target, actor) if actor.character_class == "vigia" else None
        stacks = int(aim.get("stacks", 0)) if aim is not None else 0
        entry = {
            "damage_power": D(1),
            "healing_power": D(1),
            "barrier_power": D(1),
            "final_damage_bonus": D(0),
            "per_bonus": D(3) * stacks if actor.selected_path == "atirador" else ZERO,
            "crit_bonus": D(6) if actor.selected_path == "atirador" and stacks >= 4 else ZERO,
            "aim_stacks": stacks,
            "triggers": [],
            "oportunism": (
                actor.character_class == "errante"
                and direct
                and _has_valid_negative_effect(state, target)
            ),
        }
        if entry["oportunism"]:
            entry["final_damage_bonus"] += D("0.08")
            entry["triggers"].append("oportunismo")
        if (
            actor.selected_path == "devastador"
            and is_art
            and direct
            and isinstance(actor.path_state.get("devastador_charge"), dict)
            and actor.opportunity
            <= int(actor.path_state["devastador_charge"].get("expires_opportunity", -1))
        ):
            entry["final_damage_bonus"] += D("0.12")
            entry["triggers"].append("devastador.impacto_consumido")
            context["devastador_consumed"] = True

        if actor.character_class == "oraculo" and is_art:
            if direct:
                omen = actor.path_state.setdefault("omen_offensive", {}).pop(target.id, None)
                if omen is not None and int(omen.get("remaining", 0)) > 0:
                    entry["damage_power"] *= (
                        D("1.16")
                        if actor.selected_path == "agoureiro"
                        else D("1.12")
                    )
                    entry["triggers"].append("pressagio.ofensivo_consumido")
            if support:
                omen = actor.path_state.setdefault("omen_defensive", {}).pop(target.id, None)
                if omen is not None and int(omen.get("remaining", 0)) > 0:
                    entry["healing_power"] *= D("1.12")
                    entry["barrier_power"] *= D("1.12")
                    entry["triggers"].append("pressagio.defensivo_consumido")
        context["by_target"][target.id] = entry

    if context.get("devastador_consumed"):
        actor.path_state.pop("devastador_charge", None)

    if actor.character_class == "luminar" and is_art:
        state_entry = actor.path_state.get("luminar_state")
        expected_kind = "fulgor" if support and not direct else "julgamento" if direct else None
        if isinstance(state_entry, dict) and expected_kind is not None:
            if (
                state_entry.get("kind") == expected_kind
                and int(state_entry.get("remaining", 0)) > 0
            ):
                percent = (
                    D("0.15")
                    if actor.selected_path == "guardiao" and expected_kind == "fulgor"
                    else D("0.06")
                    if actor.selected_path == "guardiao" and expected_kind == "julgamento"
                    else D("0.06")
                    if actor.selected_path == "inquisidor" and expected_kind == "fulgor"
                    else D("0.15")
                    if actor.selected_path == "inquisidor" and expected_kind == "julgamento"
                    else D("0.10")
                )
                multiplier = D(1) + percent
                for entry in context["by_target"].values():
                    if expected_kind == "julgamento":
                        entry["damage_power"] *= multiplier
                    else:
                        entry["healing_power"] *= multiplier
                        entry["barrier_power"] *= multiplier
                    entry["triggers"].append(f"luminar.{expected_kind}_consumido")
                actor.path_state.pop("luminar_state", None)
                context["luminar_consumed"] = True

    if (
        actor.selected_path == "invocador"
        and action.manifestation_kind
        and action.manifestation_kind != "triade_encarnada"
    ):
        previous = actor.path_state.get("manifestation_state")
        if (
            isinstance(previous, dict)
            and int(previous.get("remaining", 0)) > 0
            and actor.opportunity <= int(previous.get("expires_opportunity", -1))
            and previous.get("kind") != action.manifestation_kind
        ):
            for entry in context["by_target"].values():
                component = _action_power_component(action)
                if component:
                    entry[f"{component}_power"] *= D("1.12")
                    entry["triggers"].append("invocador.triade")
        actor.path_state["manifestation_state"] = {
            "kind": action.manifestation_kind,
            "remaining": 2,
            "applied_opportunity": actor.opportunity,
            "expires_opportunity": actor.opportunity + 2,
        }
    return context


def _finalize_path_action(
    state: Combat,
    actor_id: str,
    action_id: str,
    action: Action,
    context: dict,
) -> str | None:
    actor = state.fighters[actor_id]
    if actor.character_class != "luminar" or not _is_art_action(action_id, action):
        return None
    if context.get("luminar_consumed"):
        return None
    if action.coefficient > ZERO:
        kind = "fulgor"
    elif (
        action.heal_coefficient > ZERO
        or action.self_barrier_coefficient > ZERO
        or action.target_barrier_coefficient > ZERO
    ):
        kind = "julgamento"
    else:
        return None
    actor.path_state["luminar_state"] = {
        "kind": kind,
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    return f"luminar.{kind}_gerado"


def _path_effect_duration(actor: Fighter, effect: ActionEffect, duration: int) -> int:
    if (
        actor.selected_path == "sabotador"
        and effect.kind == "debuff"
        and effect.removable
        and not effect.unremovable
        and not effect.fixed_mechanic
        and not effect.hard_cc
        and duration in {1, 2}
    ):
        return min(3, duration + 1)
    return duration


def _record_devastador_charge(
    state: Combat, actor_key: str, event_start: int, action_id: str
) -> None:
    player = state.fighters.get("player")
    if player is None or player.selected_path != "devastador":
        return
    hp_loss = sum(
        (
            D(event.effective_damage)
            for event in state.events[event_start:]
            if event.actor == actor_key
            and event.target == player.id
            and event.action == action_id
            and not event.action.startswith("dot:")
        ),
        ZERO,
    )
    if hp_loss >= player.stats.hp * D("0.08") and hp_loss > ZERO:
        player.path_state["devastador_charge"] = {
            "expires_opportunity": player.opportunity + 2,
            "source_action": action_id,
        }

def _perform(
    state: Combat,
    actor_id: str,
    action_id: str,
    *,
    target_id: str | None = None,
    _hit_index: int | None = None,
    _hit_count: int = 1,
    _action_instance_id: str = "",
    _grant_action_retaliation: bool = True,
    _chain_resolution: dict[str, object] | None = None,
    _path_resolution: dict | None = None,
) -> bool:
    actor = state.fighters[actor_id]
    response_to_prepared_action_instance_id = (
        state.prepared_action_instance_id
        if actor_id == "player"
        and state.prepared_action is not None
        and state.response_window_seen
        and state.prepared_target == actor.id
        else ""
    )
    if action_id == "hold":
        actor.last_action = "hold"
        state.events.append(
            CombatEvent(
                len(state.events),
                state.round,
                actor_id,
                action_id,
                actor_entity_id=actor.id,
            )
        )
        return True
    if action_id == "defend":
        actor.defending = True
        actor.last_action = action_id
        state.events.append(
            CombatEvent(
                len(state.events),
                state.round,
                actor_id,
                action_id,
                actor_entity_id=actor.id,
                response_to_prepared_action_instance_id=(
                    response_to_prepared_action_instance_id
                ),
            )
        )
        return True

    # Bleed recoil belongs to the acting entity and resolves before its action.
    for dot in state.dot_states.get(actor.id, []) if _hit_index in {None, 1} else ():
        if dot.kind == "bleed":
            snapshots = dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks
            recoil = (sum(snapshots, D(0)) * D("0.03")).to_integral_value(
                rounding=ROUND_FLOOR
            )
            _deal_damage(actor, recoil)
    if actor.hp == 0:
        _refresh_result(state)
        return True

    actions = state.player_actions if actor_id == "player" else state.enemy_actions
    action = actions.get(action_id)
    if action is None:
        return False
    target_keys = _resolve_action_targets(state, actor_id, action, target_id)
    if not target_keys:
        return False
    if _path_resolution is None:
        _path_resolution = _prepare_path_action(
            state, actor_id, action_id, action, target_keys
        )

    if action.hit_count > 1 and _hit_index is None:
        common_instance_id = (
            f"{state.id.hex}:{state.version}:{len(state.events)}:{actor.id}:{action_id}"
        )
        actions[action_id] = replace(action, hit_count=1)
        _path_resolution["action_instance_id"] = common_instance_id
        committed = False
        chain_resolution = _chain_resolution
        try:
            for hit_index in range(1, action.hit_count + 1):
                if state.result or not _resolve_action_targets(
                    state, actor_id, action, target_id
                ):
                    break
                event_start = len(state.events)
                if not _perform(
                    state,
                    actor_id,
                    action_id,
                    target_id=target_id,
                    _hit_index=hit_index,
                    _hit_count=action.hit_count,
                    _action_instance_id=common_instance_id,
                    _grant_action_retaliation=False,
                    _chain_resolution=chain_resolution,
                    _path_resolution=_path_resolution,
                ):
                    break
                committed = True
                for index in range(event_start, len(state.events)):
                    event = state.events[index]
                    if (
                        event.actor == actor_id
                        and event.actor_entity_id == actor.id
                        and event.action == action_id
                        and event.target
                    ):
                        state.events[index] = replace(
                            event,
                            action_instance_id=common_instance_id,
                            hit_index=hit_index,
                            hit_count=action.hit_count,
                        )
                if chain_resolution is None:
                    action_event = next(
                        (
                            event
                            for event in state.events[event_start:]
                            if event.actor_entity_id == actor.id
                            and event.action == action_id
                            and event.action_instance_id == common_instance_id
                        ),
                        None,
                    )
                    if action_event is not None:
                        chain_resolution = {
                            "chain_state_before": action_event.chain_state_before,
                            "chain_state_after": action_event.chain_state_after,
                            "chain_prepared_by_action_id": (
                                action_event.chain_prepared_by_action_id
                            ),
                            "chain_prepared_by_action_instance_id": (
                                action_event.chain_prepared_by_action_instance_id
                            ),
                            "chain_consumed_by_action_instance_id": (
                                action_event.chain_consumed_by_action_instance_id
                            ),
                            "chain_consumed": action_event.chain_consumed,
                            "chain_empowered": action_event.chain_empowered,
                            "empowered_by_action_instance_id": (
                                action_event.empowered_by_action_instance_id
                            ),
                            "chain_window_before": action_event.chain_window_before,
                            "chain_window_after": action_event.chain_window_after,
                            "power_component": action_event.power_component,
                            "power_multiplier": action_event.power_multiplier,
                            "damage_power_multiplier": (
                                action_event.damage_power_multiplier
                            ),
                            "healing_power_multiplier": (
                                action_event.healing_power_multiplier
                            ),
                            "barrier_power_multiplier": (
                                action_event.barrier_power_multiplier
                            ),
                        }
            if committed and state.ruleset == CURRENT_COMBAT_RULESET:
                first_by_target: dict[str, int] = {}
                for index, event in enumerate(state.events):
                    if (
                        event.action == action_id
                        and event.action_instance_id == common_instance_id
                        and event.defender_prevented_damage > 0
                        and event.target
                        and event.target not in first_by_target
                    ):
                        first_by_target[event.target] = index
                for target_entity_id, index in first_by_target.items():
                    target_key = _resolve_fighter_key(state, target_entity_id)
                    if target_key is not None:
                        _grant_retaliation(
                            state,
                            target_key=target_key,
                            source_actor=actor,
                            source_event_id=f"{state.id.hex}:{state.events[index].sequence}",
                        )
            if committed:
                generated_path_trigger = _finalize_path_action(
                    state, actor_id, action_id, action, _path_resolution
                )
                if generated_path_trigger:
                    for index, event in enumerate(state.events):
                        if (
                            event.actor_entity_id == actor.id
                            and event.action == action_id
                            and event.action_instance_id == common_instance_id
                        ):
                            state.events[index] = replace(
                                event,
                                path_triggers=event.path_triggers
                                + (generated_path_trigger,),
                            )
        finally:
            actions[action_id] = action
        if committed:
            actor.action_use_counts[action_id] = actor.action_use_counts.get(action_id, 0) + 1
        return committed

    prepared = action.prepared is True or (
        action.prepared is None and action_id == "leap"
    )
    if (
        _fighter_side(state, actor_id) == "enemy"
        and prepared
        and not state.resolving_prepared
    ):
        state.prepared_action = action_id
        state.prepared_source = actor_id
        state.prepared_target = state.fighters[target_keys[0]].id
        state.prepared_action_instance_id = (
            f"{state.id.hex}:{state.version}:{len(state.events)}:{actor.id}:{action_id}:prepared"
        )
        state.response_window_seen = False
        actor.last_action = f"prepare:{action_id}"
        actor.cooldowns[action_id] = _cooldown_deadline(actor, action)
        actor.action_use_counts[action_id] = actor.action_use_counts.get(action_id, 0) + 1
        state.events.append(
            CombatEvent(
                len(state.events),
                state.round,
                actor_id,
                f"prepare:{action_id}",
                actor_entity_id=actor.id,
                action_instance_id=state.prepared_action_instance_id,
                prepared_action_instance_id=state.prepared_action_instance_id,
            )
        )
        return True

    action_instance_id = _action_instance_id or (
        f"{state.id.hex}:{state.version}:{len(state.events)}:{actor.id}:{action_id}"
    )
    _path_resolution["action_instance_id"] = action_instance_id
    chain_key = action.consumes_chain or action.prepares_chain
    if _chain_resolution is None:
        chain_state = actor.action_chains.get(chain_key, {}) if chain_key else {}
        chain_window_before = int(
            chain_state.get("remaining", chain_state.get("duration", 2))
        ) if chain_state else 0
        if chain_state and chain_window_before <= 0 and chain_key:
            actor.action_chains.pop(chain_key, None)
            chain_state = {}
            chain_window_before = 0
        chain_state_before = "ready" if chain_state and chain_window_before > 0 else "none"
        chain_prepared_by_action_id = str(chain_state.get("prepared_by_action_id", ""))
        chain_prepared_by_action_instance_id = str(
            chain_state.get("action_instance_id", "")
        )
        chain_consumed = bool(
            action.consumes_chain
            and chain_state
            and chain_window_before > 0
            and chain_prepared_by_action_id != action_id
        )
        if chain_consumed and action.consumes_chain:
            actor.action_chains.pop(action.consumes_chain, None)
        damage_power_multiplier = (
            D(1) + _path_chain_bonus(actor, action, "damage")
            if chain_consumed and action.coefficient > ZERO
            else D(1)
        )
        healing_power_multiplier = (
            D(1) + _path_chain_bonus(actor, action, "healing")
            if chain_consumed and action.heal_coefficient > ZERO
            else D(1)
        )
        barrier_power_multiplier = (
            D(1) + _path_chain_bonus(actor, action, "barrier")
            if chain_consumed
            and (action.self_barrier_coefficient > ZERO or action.target_barrier_coefficient > ZERO)
            else D(1)
        )
        chain_empowered = chain_consumed and any(
            multiplier > D(1)
            for multiplier in (
                damage_power_multiplier,
                healing_power_multiplier,
                barrier_power_multiplier,
            )
        )
        chain_state_after = (
            "consumed"
            if chain_consumed
            else "ready"
            if chain_state_before == "ready" or action.prepares_chain
            else "none"
        )
        chain_window_after = (
            0
            if chain_consumed
            else chain_window_before
            if chain_state_before == "ready"
            else action.prepares_chain_duration
            if action.prepares_chain
            else 0
        )
        if not chain_prepared_by_action_id and action.prepares_chain:
            chain_prepared_by_action_id = action_id
            chain_prepared_by_action_instance_id = action_instance_id
        empowered_by_action_instance_id = (
            chain_prepared_by_action_instance_id if chain_consumed else ""
        )
        chain_consumed_by_action_instance_id = action_instance_id if chain_consumed else ""
    else:
        chain_state = actor.action_chains.get(chain_key, {}) if chain_key else {}
        chain_state_before = str(_chain_resolution["chain_state_before"])
        chain_state_after = str(_chain_resolution["chain_state_after"])
        chain_prepared_by_action_id = str(
            _chain_resolution["chain_prepared_by_action_id"]
        )
        chain_prepared_by_action_instance_id = str(
            _chain_resolution["chain_prepared_by_action_instance_id"]
        )
        chain_consumed_by_action_instance_id = str(
            _chain_resolution["chain_consumed_by_action_instance_id"]
        )
        chain_consumed = bool(_chain_resolution["chain_consumed"])
        chain_empowered = bool(_chain_resolution["chain_empowered"])
        empowered_by_action_instance_id = str(
            _chain_resolution["empowered_by_action_instance_id"]
        )
        chain_window_before = int(_chain_resolution["chain_window_before"])
        chain_window_after = int(_chain_resolution["chain_window_after"])
        damage_power_multiplier = D(
            _chain_resolution["damage_power_multiplier"]
        )
        healing_power_multiplier = D(
            _chain_resolution["healing_power_multiplier"]
        )
        barrier_power_multiplier = D(
            _chain_resolution["barrier_power_multiplier"]
        )
    power_component = _action_power_component(action)
    power_multiplier = {
        "damage": damage_power_multiplier,
        "healing": healing_power_multiplier,
        "barrier": barrier_power_multiplier,
    }.get(power_component, D(1))

    if action.self_barrier_coefficient > ZERO:
        self_context = _path_target_context(_path_resolution, actor)
        path_barrier_multiplier = D(self_context.get("barrier_power", D(1)))
        if actor.selected_path == "bastiao":
            path_barrier_multiplier *= D("1.10")
        barrier_coefficient = (
            action.self_barrier_coefficient
            * barrier_power_multiplier
            * path_barrier_multiplier
        )
        value = (actor.stat("attack") * barrier_coefficient).to_integral_value(
            rounding=ROUND_FLOOR
        )
        actor.barrier = max(ZERO, value)
        actor.barrier_remaining = max(0, action.self_barrier_duration)
        actor.barrier_applied_opportunity = actor.opportunity
        actor.barrier_source = f"{actor_id}:{action.id}"
        actor.barrier_debuff_magnitude_reduction = (
            action.self_barrier_debuff_magnitude_reduction
        )
        actor.last_action = action_id
        if _hit_index is None:
            actor.action_use_counts[action_id] = actor.action_use_counts.get(action_id, 0) + 1
        if (action.cooldown or action.blocked_opportunities) and not state.resolving_prepared:
            actor.cooldowns[action_id] = _cooldown_deadline(actor, action)
        state.events.append(
            CombatEvent(
                len(state.events),
                state.round,
                actor_id,
                action_id,
                actor.id,
                barrier_value=actor.barrier,
                actor_entity_id=actor.id,
                response_to_prepared_action_instance_id=(
                    response_to_prepared_action_instance_id
                ),
                barrier_applied_source=actor.barrier_source,
                action_instance_id=action_instance_id,
                chain_state_before=chain_state_before,
                chain_state_after=chain_state_after,
                chain_prepared_by_action_id=chain_prepared_by_action_id,
                chain_consumed=chain_consumed,
                chain_empowered=chain_empowered,
                empowered_by_action_instance_id=empowered_by_action_instance_id,
                chain_prepared_by_action_instance_id=(
                    chain_prepared_by_action_instance_id
                ),
                chain_consumed_by_action_instance_id=(
                    chain_consumed_by_action_instance_id
                ),
                chain_window_before=chain_window_before,
                chain_window_after=chain_window_after,
                power_component=power_component,
                power_multiplier=power_multiplier,
                damage_power_multiplier=damage_power_multiplier,
                healing_power_multiplier=healing_power_multiplier,
                barrier_power_multiplier=barrier_power_multiplier * path_barrier_multiplier,
                path_triggers=tuple(self_context.get("triggers", ())),
                path_power_multiplier=path_barrier_multiplier,
                aim_stacks=int(self_context.get("aim_stacks", 0)),
            )
        )
        if action.prepares_chain and not chain_state and _hit_index in {None, 1}:
            if not chain_state:
                actor.action_chains[action.prepares_chain] = {
                    "prepared_by_action_id": action_id,
                    "action_instance_id": action_instance_id,
                    "duration": action.prepares_chain_duration,
                    "remaining": action.prepares_chain_duration,
                    "applied_opportunity": actor.opportunity,
                }
        generated_path_trigger = (
            _finalize_path_action(state, actor_id, action_id, action, _path_resolution)
            if _hit_index is None
            else None
        )
        if generated_path_trigger:
            state.events[-1] = replace(
                state.events[-1],
                path_triggers=state.events[-1].path_triggers + (generated_path_trigger,),
            )
        if (
            actor.barrier > ZERO
            and actor.character_class == "oraculo"
            and _is_art_action(action_id, action)
        ):
            _new_omen(actor, "defensive", actor)
            state.events[-1] = replace(
                state.events[-1],
                path_triggers=state.events[-1].path_triggers
                + ("oraculo.pressagio_defensivo_criado",),
            )
        state.resolving_prepared = False
        return True

    # Action-level resources are committed once, after action/target validation and
    # before any per-target hit outcome. This keeps AoE from consuming them per target.
    damage_coefficient = action.coefficient * damage_power_multiplier
    prepared_action_instance_id = (
        state.prepared_action_instance_id if state.resolving_prepared else ""
    )
    active_actor_effect_ids = {
        effect.id for effect in actor.effects if effect.remaining > 0
    }
    if (
        actor.next_direct_crit_effect_id
        and actor.next_direct_crit_expires_opportunity is not None
        and actor.opportunity <= actor.next_direct_crit_expires_opportunity
    ):
        active_actor_effect_ids.add(actor.next_direct_crit_effect_id)
    actor_effect_ids = tuple(sorted(active_actor_effect_ids))
    actor_effect_facts = tuple(
        sorted(
            (
                effect.id,
                effect.stat,
                effect.magnitude,
                effect.remaining,
                effect.kind,
            )
            for effect in actor.effects
            if effect.remaining > 0
        )
    )
    retaliation_context = _consume_retaliation(state, actor_id, actor, action)
    retaliation_used = bool(retaliation_context.get("used"))
    retaliation_source_type = str(retaliation_context.get("source_type", ""))
    retaliation_source_actor_id = str(retaliation_context.get("source_actor_id", ""))
    retaliation_valid = retaliation_used and retaliation_source_type == "defender"

    current_ruleset = state.ruleset == CURRENT_COMBAT_RULESET
    direct_eligible = action.coefficient > ZERO
    prepared_resolution = state.resolving_prepared
    resolved_hit_index = _hit_index or 1
    resolved_hit_count = _hit_count if _hit_index is not None else action.hit_count
    action_event_indices: list[int] = []
    total_vamp_damage = D(0)

    # The target set is frozen before the first primary result. Target ordering is
    # stable by entity id and never depends on database order.
    for target_index, target_key in enumerate(target_keys):
        target = state.fighters[target_key]
        target_path = _path_target_context(_path_resolution, target)
        target_damage_power = damage_power_multiplier * D(
            target_path.get("damage_power", D(1))
        )
        target_healing_power = healing_power_multiplier * D(
            target_path.get("healing_power", D(1))
        )
        target_barrier_power = barrier_power_multiplier * D(
            target_path.get("barrier_power", D(1))
        )
        if actor.selected_path == "bastiao":
            target_barrier_power *= D("1.10")
        damage_coefficient = action.coefficient * target_damage_power
        effect_trigger_applies = (
            action.effect_trigger_scope == "per_hit"
            or (
                action.effect_trigger_scope == "per_target"
                and resolved_hit_index == 1
            )
            or (
                action.effect_trigger_scope == "per_action"
                and resolved_hit_index == 1
                and target_index == 0
            )
        )
        target_defending = target.defending
        target_effect_ids = tuple(
            sorted(effect.id for effect in target.effects if effect.remaining > 0)
        )
        target_effect_application_event_ids = tuple(
            sorted(
                effect.application_event
                for effect in target.effects
                if effect.remaining > 0 and effect.application_event
            )
        )
        target_state_tags = tuple(sorted(target.training_state_tags))
        protection_layers_before = target.protection_layers
        target_barrier_source = (
            target.barrier_source
            if target.barrier > ZERO and target.barrier_remaining > 0
            else ""
        )

        dodged = False
        if current_ruleset and direct_eligible:
            streak = state.evasion_streaks.get(target.id, 0)
            if streak >= 2:
                state.evasion_streaks[target.id] = 0
            else:
                evasion_chance = chance_from_percentage_points(target.stat("evasion"))
                if evasion_chance > ZERO:
                    rng = CombatRng(state.id, state.rng_cursor)
                    dodged = rng.chance(
                        evasion_chance,
                        (
                            f"evasion:{actor_id}:{action_id}:{target.id}:hit:{resolved_hit_index}"
                            if resolved_hit_count > 1
                            else f"evasion:{actor_id}:{action_id}:{target.id}"
                        ),
                    )
                    state.rng_cursor = rng.cursor
                if dodged:
                    state.evasion_streaks[target.id] = streak + 1
                else:
                    state.evasion_streaks[target.id] = 0

        if dodged:
            event_index = len(state.events)
            state.events.append(
                CombatEvent(
                    event_index,
                    state.round,
                    actor_id,
                    action_id,
                    target.id,
                    dodged=True,
                    actor_entity_id=actor.id,
                    target_defending=target_defending,
                    prepared_resolution=prepared_resolution,
                    target_effect_ids=target_effect_ids,
                    target_barrier_source=target_barrier_source,
                    retaliation_valid=retaliation_valid,
                    retaliation_used=retaliation_used,
                    retaliation_activation_id=str(
                        retaliation_context.get("activation_id", "")
                    ),
                    retaliation_source_type=retaliation_source_type,
                    retaliation_source_event_id=str(
                        retaliation_context.get("source_event_id", "")
                    ),
                    retaliation_source_actor_id=retaliation_source_actor_id,
                    action_instance_id=action_instance_id,
                    hit_index=resolved_hit_index,
                    hit_count=resolved_hit_count,
                    protection_layers_before=protection_layers_before,
                    protection_layers_after=target.protection_layers,
                    target_state_tags=target_state_tags,
                    target_effect_application_event_ids=target_effect_application_event_ids,
                    chain_state_before=chain_state_before,
                    chain_state_after=chain_state_after,
                    chain_prepared_by_action_id=chain_prepared_by_action_id,
                    chain_consumed=chain_consumed,
                    chain_empowered=chain_empowered,
                    empowered_by_action_instance_id=empowered_by_action_instance_id,
                    chain_prepared_by_action_instance_id=(
                        chain_prepared_by_action_instance_id
                    ),
                    chain_consumed_by_action_instance_id=(
                        chain_consumed_by_action_instance_id
                    ),
                    chain_window_before=chain_window_before,
                    chain_window_after=chain_window_after,
                    power_component=power_component,
                    power_multiplier=power_multiplier,
                    damage_power_multiplier=damage_power_multiplier,
                    healing_power_multiplier=healing_power_multiplier,
                    barrier_power_multiplier=barrier_power_multiplier,
                    path_triggers=tuple(target_path.get("triggers", ())),
                    path_power_multiplier=D(target_path.get("damage_power", D(1))),
                    path_final_damage_bonus=D(
                        target_path.get("final_damage_bonus", ZERO)
                    ),
                    aim_stacks=int(target_path.get("aim_stacks", 0)),
                    path_per_bonus=D(target_path.get("per_bonus", ZERO)),
                    path_crit_bonus=D(target_path.get("crit_bonus", ZERO)),
                )
            )
            action_event_indices.append(event_index)
            continue

        rng = CombatRng(state.id, state.rng_cursor)
        critical = False
        if direct_eligible:
            target_debuff_bonus = (
                action.crit_bonus_if_target_debuffed
                if any(
                    effect.kind == "debuff" and effect.remaining > 0
                    for effect in target.effects
                )
                else ZERO
            )
            next_direct_bonus = (
                actor.next_direct_crit_bonus
                if actor.next_direct_crit_expires_opportunity is not None
                and actor.opportunity <= actor.next_direct_crit_expires_opportunity
                else ZERO
            )
            crit_chance = (
                chance_from_percentage_points(
                actor.stat("crit")
                + target_debuff_bonus
                + next_direct_bonus
                + D(target_path.get("crit_bonus", ZERO))
                )
                if current_ruleset
                else D("0.05")
            )
            if crit_chance > ZERO:
                crit_purpose = (
                    (
                        f"critical:{actor_id}:{action_id}:{target.id}:hit:{resolved_hit_index}"
                        if resolved_hit_count > 1
                        else f"critical:{actor_id}:{action_id}:{target.id}"
                    )
                    if current_ruleset
                    else f"critical:{actor_id}:{action_id}"
                )
                critical = rng.chance(crit_chance, crit_purpose)

        defender_reduction = (
            D("0.52") if target.race == "cinereo" else D("0.45")
        ) if target.defending else ZERO
        blocked = False
        if current_ruleset and direct_eligible:
            block_chance = chance_from_percentage_points(target.stat("block"))
            if block_chance > ZERO:
                blocked = rng.chance(
                    block_chance,
                    (
                        f"block:{actor_id}:{action_id}:{target.id}:hit:{resolved_hit_index}"
                        if resolved_hit_count > 1
                        else f"block:{actor_id}:{action_id}:{target.id}"
                    ),
                )
        state.rng_cursor = rng.cursor

        mitigation_without_defender = (
            combine_active_mitigation(D("0.35")) if blocked else ZERO
        )
        mitigation_parts = []
        if target.defending:
            mitigation_parts.append(defender_reduction)
        if blocked:
            mitigation_parts.append(D("0.35"))
        mitigation = combine_active_mitigation(*mitigation_parts)
        penetration = (actor.stat("per") if current_ruleset else ZERO) + (
            action.per_bonus_if_target_poisoned
            if any(
                dot.kind == "poison" and dot.stacks > 0 and dot.remaining > 0
                for dot in state.dot_states.get(target.id, ())
            )
            else ZERO
        ) + D(target_path.get("per_bonus", ZERO))
        damage = (
            direct_damage(
                actor.stat("attack"),
                damage_coefficient,
                target.stat("defense"),
                actor.level,
                critical=critical,
                mitigation=mitigation,
                penetration=penetration,
            )
            if direct_eligible
            else 0
        )
        direct_final_reduction = min(
            D(1),
            target.protection_layers * target.protection_reduction_per_layer
            + sum(
                (
                    target.tagged_direct_damage_reductions.get(tag, ZERO)
                    for tag in target_state_tags
                ),
                ZERO,
            ),
        )
        if direct_eligible and direct_final_reduction > ZERO:
            damage = int(
                (D(damage) * (D(1) - direct_final_reduction)).to_integral_value(
                    rounding=ROUND_FLOOR
                )
            )
        path_final_damage_bonus = D(target_path.get("final_damage_bonus", ZERO))
        path_triggers = list(target_path.get("triggers", ()))
        if (
            actor.selected_path == "carrasco"
            and direct_eligible
            and target.hp <= target.stats.hp * D("0.40")
        ):
            path_final_damage_bonus += D("0.08")
            path_triggers.append("carrasco.sentenca")
        if direct_eligible and path_final_damage_bonus > ZERO:
            damage = int(
                (D(damage) * (D(1) + path_final_damage_bonus)).to_integral_value(
                    rounding=ROUND_FLOOR
                )
            )
        damage_without_defender = damage
        if target.defending and direct_eligible:
            damage_without_defender = direct_damage(
                actor.stat("attack"),
                damage_coefficient,
                target.stat("defense"),
                actor.level,
                critical=critical,
                mitigation=mitigation_without_defender,
                penetration=penetration,
            )
            if direct_final_reduction > ZERO:
                damage_without_defender = int(
                    (
                        D(damage_without_defender)
                        * (D(1) - direct_final_reduction)
                    ).to_integral_value(rounding=ROUND_FLOOR)
                )
            if path_final_damage_bonus > ZERO:
                damage_without_defender = int(
                    (
                        D(damage_without_defender)
                        * (D(1) + path_final_damage_bonus)
                    ).to_integral_value(rounding=ROUND_FLOOR)
                )
        defender_prevented_damage = (
            max(0, damage_without_defender - damage)
            if target.defending and direct_eligible
            else 0
        )

        actual_damage, barrier_absorbed = _deal_damage(target, damage)
        if direct_eligible and damage > 0 and actor.character_class == "vigia":
            generated = _path_resolution.setdefault("aim_generated_targets", set())
            if target.id not in generated:
                stacks = _grant_aim(
                    state,
                    actor_id,
                    target_key,
                    trigger="direct",
                    action_targets=_path_resolution.get("target_ids"),
                )
                generated.add(target.id)
                if stacks:
                    path_triggers.append("vigia.mira_gerada")
                    target_path["aim_stacks_after"] = stacks
        if direct_eligible and protection_layers_before > 0:
            target.protection_layers -= 1
        protection_layers_after = target.protection_layers
        total_vamp_damage += actual_damage
        ward_blocked: list[str] = []
        status_applied = False
        effect_application_event_id = ""
        applied_effect = None
        dot_application_event_id = ""
        dot_application_kind = ""
        target_effects_application_id = ""
        target_effects_applied = False
        if action.attack_debuff and target.hp > 0 and effect_trigger_applies:
            had_ward = target.ward_charges > 0 and target.ward_remaining > 0
            applied_effect_id = action.effect_id or action.id
            effect_application_event_id = (
                f"{state.id.hex}:{state.version}:{len(state.events)}:effect:"
                f"{applied_effect_id}:{target.id}"
            )
            status_applied = apply_effect(
                state,
                target,
                Effect(
                    id=applied_effect_id,
                    stat=action.effect_stat or "attack",
                    magnitude=action.attack_debuff,
                    remaining=(
                        min(3, action.duration + 1)
                        if actor.selected_path == "sabotador"
                        and action.duration in {1, 2}
                        else action.duration
                    ),
                    applied_opportunity=target.opportunity,
                ),
                application_event=effect_application_event_id,
            )
            if had_ward and not status_applied and target.ward_charges == 0:
                ward_blocked.append(action.id)
            if not status_applied:
                effect_application_event_id = ""
            else:
                applied_effect = next(
                    (
                        effect
                        for effect in target.effects
                        if effect.application_event == effect_application_event_id
                    ),
                    None,
                )

        if action.target_effects and target.hp > 0 and effect_trigger_applies:
            application_id = (
                f"{state.id.hex}:{state.version}:{len(state.events)}:target-effects:"
                f"{action.id}:{target.id}"
            )
            target_effects = tuple(
                Effect(
                    id=effect.id,
                    stat=effect.stat,
                    magnitude=effect.magnitude,
                    remaining=_path_effect_duration(
                        actor, effect, effect.duration
                    ),
                    applied_opportunity=target.opportunity,
                    kind=effect.kind,
                    stat_modifier_mode=effect.stat_modifier_mode,
                    removable=effect.removable,
                    unremovable=effect.unremovable,
                    fixed_mechanic=effect.fixed_mechanic,
                    hard_cc=effect.hard_cc,
                )
                for effect in action.target_effects
            )
            target_effects_applied = apply_effect_batch(
                state, target, target_effects, application_event=application_id
            )
            if target_effects_applied:
                target_effects_application_id = application_id
                status_applied = True
                effect_application_event_id = application_id
                applied_effect = next(
                    (
                        effect
                        for effect in target.effects
                        if effect.application_event == application_id
                    ),
                    None,
                )

        if damage > 0 and target.hp > 0:
            enemy_actor = _fighter_side(state, actor_id) == "enemy"
            rider = (
                "bleed"
                if state.variant == "hemorrhagic"
                else "poison"
                if state.variant == "venomous"
                else None
            ) if enemy_actor else None
            native_kind = action.native_dot_kind
            native_stacks = action.native_dot_stacks
            if (
                enemy_actor
                and native_kind is None
                and native_stacks == 0
                and action_id == "rend"
            ):
                native_kind, native_stacks = "bleed", 1
            chosen = native_kind or rider
            if chosen and effect_trigger_applies:
                snapshot = actor.stat("attack")
                had_ward = target.ward_charges > 0 and target.ward_remaining > 0
                candidate_application_event_id = (
                    f"{state.id.hex}:{state.version}:{len(state.events)}:dot:"
                    f"{chosen}:{target.id}"
                )
                applied = apply_dot_stacks(
                    state,
                    target,
                    kind=chosen,
                    snapshots=[snapshot] * (native_stacks if native_kind else 1),
                    source=actor.id,
                    duration=_DOT_DURATIONS[chosen],
                    application_event=candidate_application_event_id,
                )
                if applied:
                    dot_application_event_id = candidate_application_event_id
                    dot_application_kind = chosen
                if had_ward and not applied and target.ward_charges == 0:
                    ward_blocked.append(chosen)

        if actor.character_class == "vigia" and actor.selected_path == "rastreador":
            agility_debuff_applied = any(
                effect.application_event == target_effects_application_id
                and effect.stat == "agility"
                and effect.kind == "debuff"
                and effect.remaining > 0
                for effect in target.effects
            ) or bool(
                applied_effect is not None
                and applied_effect.stat == "agility"
                and applied_effect.kind == "debuff"
            )
            if dot_application_event_id or agility_debuff_applied:
                generated = _path_resolution.setdefault("aim_generated_targets", set())
                if target.id not in generated:
                    stacks = _grant_aim(
                        state,
                        actor_id,
                        target_key,
                        trigger="status",
                        action_targets=_path_resolution.get("target_ids"),
                    )
                    generated.add(target.id)
                    if stacks:
                        path_triggers.append("rastreador.mira_gerada")
                        target_path["aim_stacks_after"] = stacks

        target_healed = D(0)
        base_healing = D(0)
        calculated_healing = D(0)
        received_healing_multiplier = D(1)
        overheal = D(0)
        if (
            action.heal_coefficient > ZERO
            and target.hp > 0
            and effect_trigger_applies
        ):
            base_healing = (
                actor.stat("attack")
                * action.heal_coefficient
                * target_healing_power
            )
            received_healing_multiplier = healing_received_multiplier(state, target_key)
            calculated_healing = (
                base_healing * received_healing_multiplier
            ).to_integral_value(rounding=ROUND_FLOOR)
            target_healed = calculated_healing
            target_healed = min(
                max(ZERO, target_healed),
                max(ZERO, target.stats.hp - target.hp),
            )
            overheal = max(ZERO, calculated_healing - target_healed)
            target.hp += target_healed

        target_barrier = ZERO
        if (
            action.target_barrier_coefficient > ZERO
            and target.hp > 0
            and effect_trigger_applies
        ):
            target_barrier = (
                actor.stat("attack")
                * action.target_barrier_coefficient
                * target_barrier_power
            ).to_integral_value(rounding=ROUND_FLOOR)
            target_barrier = max(ZERO, target_barrier)
            if target_barrier > ZERO:
                target.barrier = target_barrier
                target.barrier_remaining = max(0, action.target_barrier_duration)
                target.barrier_applied_opportunity = target.opportunity
                target.barrier_source = f"{actor.id}:{action.id}"
                target.barrier_debuff_magnitude_reduction = (
                    action.target_barrier_debuff_magnitude_reduction
                )

        if actor.character_class == "oraculo" and _is_art_action(action_id, action):
            applied_target_effects = [
                effect
                for effect in target.effects
                if effect.remaining > 0
                and (
                    effect.application_event == effect_application_event_id
                    or effect.application_event == target_effects_application_id
                )
            ]
            if dot_application_event_id or any(
                effect.kind == "debuff" for effect in applied_target_effects
            ):
                _new_omen(actor, "offensive", target)
                path_triggers.append("oraculo.pressagio_ofensivo_criado")
            if target_barrier > ZERO or any(
                effect.kind == "buff" for effect in applied_target_effects
            ):
                _new_omen(actor, "defensive", target)
                path_triggers.append("oraculo.pressagio_defensivo_criado")

        action_event_sequence = len(state.events)
        state.events.append(
            CombatEvent(
                action_event_sequence,
                state.round,
                actor_id,
                action_id,
                target.id,
                damage,
                critical,
                target_healed,
                applied_effect.id if applied_effect is not None else "",
                barrier_absorbed=barrier_absorbed,
                barrier_value=target_barrier,
                blocked=blocked,
                actor_entity_id=actor.id,
                calculated_damage=damage,
                effective_damage=int(actual_damage),
                target_defending=target_defending,
                defender_mitigation_applied=defender_prevented_damage > 0,
                defender_prevented_damage=defender_prevented_damage,
                target_barrier_source=target_barrier_source,
                prepared_resolution=prepared_resolution,
                target_effect_ids=target_effect_ids,
                target_effect_application_event_ids=target_effect_application_event_ids,
                actor_effect_ids=actor_effect_ids,
                effect_application_event_id=effect_application_event_id,
                prepared_action_instance_id=prepared_action_instance_id,
                response_to_prepared_action_instance_id=response_to_prepared_action_instance_id,
                dot_kind=dot_application_kind,
                dot_application_event_id=dot_application_event_id,
                retaliation_valid=retaliation_valid,
                retaliation_used=retaliation_used,
                retaliation_activation_id=str(
                    retaliation_context.get("activation_id", "")
                ),
                retaliation_source_type=retaliation_source_type,
                retaliation_source_event_id=str(
                    retaliation_context.get("source_event_id", "")
                ),
                retaliation_source_actor_id=retaliation_source_actor_id,
                action_instance_id=action_instance_id,
                hit_index=resolved_hit_index,
                hit_count=resolved_hit_count,
                protection_layers_before=protection_layers_before,
                protection_layers_after=protection_layers_after,
                target_state_tags=target_state_tags,
                chain_state_before=chain_state_before,
                chain_state_after=chain_state_after,
                chain_prepared_by_action_id=chain_prepared_by_action_id,
                chain_consumed=chain_consumed,
                chain_empowered=chain_empowered,
                empowered_by_action_instance_id=empowered_by_action_instance_id,
                    chain_prepared_by_action_instance_id=(
                        chain_prepared_by_action_instance_id
                    ),
                    chain_consumed_by_action_instance_id=(
                        chain_consumed_by_action_instance_id
                    ),
                    chain_window_before=chain_window_before,
                    chain_window_after=chain_window_after,
                    power_component=power_component,
                    power_multiplier=power_multiplier,
                    damage_power_multiplier=damage_power_multiplier,
                    healing_power_multiplier=healing_power_multiplier,
                    barrier_power_multiplier=target_barrier_power,
                    path_triggers=tuple(path_triggers),
                    path_power_multiplier=(
                        D(target_path.get("damage_power", D(1)))
                        if power_component == "damage"
                        else D(target_path.get("healing_power", D(1)))
                        if power_component == "healing"
                        else D(target_path.get("barrier_power", D(1)))
                        * (D("1.10") if actor.selected_path == "bastiao" else D(1))
                        if power_component == "barrier"
                        else D(1)
                    ),
                    path_final_damage_bonus=path_final_damage_bonus,
                    aim_stacks=int(
                        target_path.get("aim_stacks_after", target_path.get("aim_stacks", 0))
                    ),
                path_per_bonus=D(target_path.get("per_bonus", ZERO)),
                path_crit_bonus=D(target_path.get("crit_bonus", ZERO)),
                trigger_scope=action.effect_trigger_scope,
                barrier_applied_source=(
                    f"{actor.id}:{action.id}" if target_barrier > ZERO else ""
                ),
                applied_effect_stat=applied_effect.stat if applied_effect else "",
                applied_effect_magnitude=(
                    applied_effect.magnitude if applied_effect else ZERO
                ),
                applied_effect_duration=applied_effect.remaining if applied_effect else 0,
                applied_effect_kind=applied_effect.kind if applied_effect else "",
                applied_effect_removable=(
                    applied_effect.removable if applied_effect else False
                ),
                actor_effect_facts=actor_effect_facts,
                base_healing=base_healing,
                calculated_healing=calculated_healing,
                effective_healing=target_healed,
                healing_received_multiplier=received_healing_multiplier,
                overheal=overheal,
                target_hp_after=target.hp,
                fighter_hp_after=tuple(
                    sorted((fighter.id, fighter.hp) for fighter in state.fighters.values())
                ),
            )
        )
        action_event_indices.append(action_event_sequence)

        if (
            current_ruleset
            and defender_prevented_damage > 0
            and target.character_class == "sentinela"
            and _grant_action_retaliation
        ):
            _grant_retaliation(
                state,
                target_key=target_key,
                source_actor=actor,
                source_event_id=f"{state.id.hex}:{action_event_sequence}",
            )

        for effect_id in ward_blocked:
            state.events.append(
                CombatEvent(
                    len(state.events),
                    state.round,
                    target_key,
                    "resguardo:block",
                    target.id,
                    effect_id=effect_id,
                    actor_entity_id=target.id,
                    action_instance_id=action_instance_id,
                )
            )

    applied_actor_effect_ids = (
        _apply_action_self_effect(state, actor, action)
        if _hit_index in {None, 1}
        else ()
    )
    if actor.character_class == "oraculo" and _is_art_action(action_id, action):
        applied_actor_buffs = [
            effect
            for effect in actor.effects
            if effect.id in applied_actor_effect_ids
            and effect.kind == "buff"
            and effect.remaining > 0
        ]
        if applied_actor_buffs:
            _new_omen(actor, "defensive", actor)
            if action_event_indices:
                first = action_event_indices[0]
                state.events[first] = replace(
                    state.events[first],
                    path_triggers=state.events[first].path_triggers
                    + ("oraculo.pressagio_defensivo_criado",),
                )
    if applied_actor_effect_ids and action_event_indices:
        first = action_event_indices[0]
        applied_actor_effect = next(
            (
                effect
                for effect in actor.effects
                if effect.id == applied_actor_effect_ids[0]
                and effect.remaining > 0
            ),
            None,
        )
        state.events[first] = replace(
            state.events[first],
            actor_effect_id=applied_actor_effect_ids[0],
            actor_effect_ids=tuple(
                sorted(set(state.events[first].actor_effect_ids) | set(applied_actor_effect_ids))
            ),
            actor_applied_effect_stat=(
                applied_actor_effect.stat if applied_actor_effect else ""
            ),
            actor_applied_effect_magnitude=(
                applied_actor_effect.magnitude if applied_actor_effect else ZERO
            ),
            actor_applied_effect_duration=(
                applied_actor_effect.remaining if applied_actor_effect else 0
            ),
            actor_applied_effect_kind=(
                applied_actor_effect.kind if applied_actor_effect else ""
            ),
        )

    # Hemário vampirism is per action, including AoE: aggregate eligible HP damage
    # and apply the existing 3% HP-Max cap once.
    vamp_healed = D(0)
    if (
        actor.race == "hemario"
        and actor.hp <= actor.stats.hp * D("0.40")
        and total_vamp_damage > ZERO
    ):
        vamp_healed = min(
            total_vamp_damage * D("0.12"),
            actor.stats.hp * D("0.03"),
            actor.stats.hp - actor.hp,
        ).to_integral_value(rounding=ROUND_FLOOR)
        vamp_healed = max(ZERO, vamp_healed)
        actor.hp += vamp_healed
        if vamp_healed > ZERO and action_event_indices:
            target_event = next(
                (
                    index
                    for index in action_event_indices
                    if state.events[index].effective_damage > 0
                ),
                action_event_indices[0],
            )
            state.events[target_event] = replace(
                state.events[target_event],
                healed=state.events[target_event].healed + vamp_healed,
            )

    if action.self_state_tags_after is not None:
        actor.training_state_tags = tuple(sorted(set(action.self_state_tags_after)))
    if action.prepares_chain and not chain_state and _hit_index in {None, 1}:
        actor.action_chains[action.prepares_chain] = {
            "prepared_by_action_id": action_id,
            "action_instance_id": action_instance_id,
            "duration": action.prepares_chain_duration,
            "remaining": action.prepares_chain_duration,
            "applied_opportunity": actor.opportunity,
        }
    actor.last_action = action_id
    if _hit_index is None and not prepared_resolution:
        actor.action_use_counts[action_id] = actor.action_use_counts.get(action_id, 0) + 1
    if (action.cooldown or action.blocked_opportunities) and not state.resolving_prepared:
        actor.cooldowns[action_id] = _cooldown_deadline(actor, action)
    if action.next_direct_crit_bonus > ZERO:
        actor.next_direct_crit_bonus = action.next_direct_crit_bonus
        actor.next_direct_crit_expires_opportunity = (
            actor.opportunity + max(1, action.next_direct_crit_duration)
        )
        actor.next_direct_crit_effect_id = action.next_direct_crit_effect_id or ""
    if direct_eligible and actor.next_direct_crit_expires_opportunity is not None:
        actor.next_direct_crit_bonus = ZERO
        actor.next_direct_crit_expires_opportunity = None
        actor.next_direct_crit_effect_id = ""
    _retaliation_action_resolved(state, actor_id, actor, retaliation_context)
    _refresh_result(state)
    if prepared_resolution:
        state.prepared_action_instance_id = None
    generated_path_trigger = (
        _finalize_path_action(state, actor_id, action_id, action, _path_resolution)
        if _hit_index is None
        else None
    )
    if generated_path_trigger:
        for index in action_event_indices:
            state.events[index] = replace(
                state.events[index],
                path_triggers=state.events[index].path_triggers
                + (generated_path_trigger,),
            )
    state.resolving_prepared = False
    return True

def _apply_action_self_effect(
    state: Combat, actor: Fighter, action: Action
) -> tuple[str, ...]:
    applied_ids: list[str] = []
    if (
        not action.self_effect_id
        or not action.self_effect_stat
        or action.self_effect_magnitude < ZERO
        or action.self_effect_duration <= 0
    ):
        pass
    else:
        if apply_effect(
            state,
            actor,
            Effect(
                id=action.self_effect_id,
                stat=action.self_effect_stat,
                magnitude=action.self_effect_magnitude,
                remaining=action.self_effect_duration,
                applied_opportunity=actor.opportunity,
                kind=action.self_effect_kind,
                stat_modifier_mode=action.self_effect_modifier_mode,
            ),
            application_event=(
                f"{state.id.hex}:{state.version}:{len(state.events)}:self-effect:"
                f"{action.self_effect_id}"
            ),
        ):
            applied_ids.append(action.self_effect_id)
    for effect in action.self_effects:
        if apply_effect(
            state,
            actor,
            Effect(
                id=effect.id,
                stat=effect.stat,
                magnitude=effect.magnitude,
                remaining=effect.duration,
                applied_opportunity=actor.opportunity,
                kind=effect.kind,
                stat_modifier_mode=effect.stat_modifier_mode,
                removable=effect.removable,
                unremovable=effect.unremovable,
                fixed_mechanic=effect.fixed_mechanic,
                hard_cc=effect.hard_cc,
            ),
            application_event=(
                f"{state.id.hex}:{state.version}:{len(state.events)}:self-effect:{effect.id}"
            ),
        ):
            applied_ids.append(effect.id)
    return tuple(applied_ids)


def _enemy_action(state: Combat, actor_key: str = "enemy") -> str:
    if state.pending_response is not None:
        action = state.pending_response
        state.pending_response = None
        return action
    if (
        state.prepared_action is not None
        and state.prepared_source == actor_key
        and state.response_window_seen
    ):
        action = state.prepared_action
        state.prepared_action = None
        state.resolving_prepared = True
        state.response_window_seen = False
        return action
    if state.prepared_action is not None:
        return "hold"
    enemy = state.fighters[actor_key]

    def ready(action_id: str) -> bool:
        action = state.enemy_actions.get(action_id)
        if action is None or enemy.cooldowns.get(action_id, 0) > enemy.opportunity:
            return False
        if (
            action.max_uses_per_combat is not None
            and enemy.action_use_counts.get(action_id, 0) >= action.max_uses_per_combat
        ):
            return False
        if (
            action.enemy_hp_fraction_below is not None
            and enemy.hp >= enemy.stats.hp * action.enemy_hp_fraction_below
        ):
            return False
        if (
            action.enemy_hp_fraction_at_most is not None
            and enemy.hp > enemy.stats.hp * action.enemy_hp_fraction_at_most
        ):
            return False
        return not (
            action.skip_if_barrier_active
            and enemy.barrier > ZERO
            and enemy.barrier_remaining > 0
        )

    if state.ai_priority:
        for action in state.ai_priority:
            if ready(action):
                return action
    # Alfa Cinéreo uses content priority rather than a positional cycle.
    if {"rend", "leap", "bite"}.issubset(state.enemy_actions):
        player = state.fighters["player"]
        bleed_count = next(
            (
                dot.stacks
                for dot in state.dot_states.get(player.id, [])
                if dot.kind == "bleed"
            ),
            0,
        )
        if ready("rend") and bleed_count == 0:
            return "rend"
        if ready("leap"):
            return "leap"
        if ready("rend") and bleed_count < 3:
            return "rend"
        return "bite"
    if not state.ai_cycle:
        return "hold"
    for _ in range(len(state.ai_cycle)):
        action = state.ai_cycle[state.ai_position]
        state.ai_position = (state.ai_position + 1) % len(state.ai_cycle)
        if ready(action):
            return action
    return "hold"


def _advance_to_player(state: Combat) -> None:
    while (
        not state.result
        and state.order
        and state.order[state.turn_index] != "player"
    ):
        actor_key = state.order[state.turn_index]
        if _fighter_side(state, actor_key) == "enemy":
            action_id = _enemy_action(state, actor_key)
            action = state.enemy_actions.get(action_id)
            resolving_prepared = state.resolving_prepared
            prepared_declaration = bool(
                action
                and (action.prepared is True or (action.prepared is None and action_id == "leap"))
                and not resolving_prepared
            )
            target_id = None
            if action and action.target_mode == "opponent" and state.ai_target_cycle:
                if resolving_prepared:
                    target_id = state.prepared_target
                else:
                    requested = state.ai_target_cycle[
                        state.ai_target_position % len(state.ai_target_cycle)
                    ]
                    requested_key = _resolve_fighter_key(state, requested)
                    if requested_key is not None and state.fighters[requested_key].hp > ZERO:
                        target_id = requested
                    else:
                        candidates = sorted(
                            (
                                fighter.id
                                for key, fighter in state.fighters.items()
                                if fighter.hp > ZERO
                                and _fighter_side(state, key) != _fighter_side(state, actor_key)
                            )
                        )
                        target_id = candidates[0] if candidates else None
            event_start = len(state.events)
            committed = _perform(
                state, actor_key, action_id, target_id=target_id
            )
            if committed and not prepared_declaration:
                _record_devastador_charge(
                    state, actor_key, event_start, action_id
                )
            if (
                committed
                and action
                and action.target_mode == "opponent"
                and state.ai_target_cycle
                and not prepared_declaration
            ):
                state.ai_target_position = (
                    state.ai_target_position + 1
                ) % len(state.ai_target_cycle)
        else:
            _perform(state, actor_key, "hold")
        if state.result:
            break
        if state.fighters[actor_key].hp <= 0:
            _advance_turn_cursor(state)
        else:
            _end_turn(state)



def start_combat(state: Combat) -> Combat:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        state = deepcopy(state)
        _refresh_result(state)
        if state.result:
            state.order = ()
            state.turn_index = 0
            return state
        state.order = initiative(state)
        state.turn_index = 0
        _begin_turn(state)
        _advance_to_player(state)
        return state


CONSUMABLE_COOLDOWN_KEY = "consumable"


def consumable_available(state: Combat) -> bool:
    if state.result or not state.order or state.order[state.turn_index] != "player":
        return False
    player = state.fighters["player"]
    return player.cooldowns.get(CONSUMABLE_COOLDOWN_KEY, 0) <= player.opportunity


def _finish_consumable_turn(
    state: Combat,
    action: str,
    healed: Decimal | None = None,
    *,
    target: str = "player",
    effect_id: str = "",
    effect_removal_kind: str | None = None,
    barrier_value: Decimal = ZERO,
    barrier_absorbed: Decimal = ZERO,
) -> Combat:
    healed = D(0) if healed is None else healed
    player = state.fighters["player"]
    player.last_action = action
    # CD2: unavailable on the next opportunity and available on the following one.
    player.cooldowns[CONSUMABLE_COOLDOWN_KEY] = player.opportunity + 2
    state.events.append(
        CombatEvent(
            len(state.events),
            state.round,
            "player",
            action,
            target,
            healed=healed,
            effect_id=effect_id,
            effect_removal_kind=effect_removal_kind,
            barrier_absorbed=barrier_absorbed,
            barrier_value=barrier_value,
        )
    )
    state.consumable_uses += 1
    if not state.result:
        _end_turn(state)
        _advance_to_player(state)
    state.version += 1
    return state


def healing_received_multiplier(state: Combat, target_id: str = "player") -> Decimal:
    target = state.fighters[target_id]
    multiplier = D(1)
    for effect in target.effects:
        if effect.stat != "healing_received":
            continue
        multiplier *= (
            max(D(0), D(1) - effect.magnitude)
            if effect.kind == "debuff"
            else D(1) + effect.magnitude
        )

    burn_stacks = min(
        _DOT_STACK_CAPS["burn"],
        sum(
            max(0, dot.stacks)
            for dot in state.dot_states.get(target.id, ())
            if dot.kind == "burn" and dot.remaining > 0
        ),
    )
    if burn_stacks:
        multiplier *= max(D(0), D(1) - D("0.05") * burn_stacks)
    return multiplier


def effective_heal_amount(state: Combat, target_id: str = "player") -> Decimal:
    target = state.fighters[target_id]
    multiplier = healing_received_multiplier(state, target_id)
    amount = (target.stats.hp * D("0.22") * multiplier).to_integral_value(
        rounding=ROUND_FLOOR
    )
    return min(max(D(0), amount), max(D(0), target.stats.hp - target.hp))


def use_heal_consumable(state: Combat) -> Combat:
    """Apply the official 22% HP-Max heal as a normal player action."""
    if not consumable_available(state):
        return state
    with localcontext() as ctx:
        ctx.prec = PRECISION
        updated = deepcopy(state)
        player = updated.fighters["player"]
        healed = effective_heal_amount(updated)
        if healed <= 0:
            return state
        player.hp += healed
        return _finish_consumable_turn(updated, "consumable:heal", healed)


def use_purification_consumable(
    state: Combat, *, dot_index: int | None = None, effect_index: int | None = None
) -> Combat:
    """Remove one oldest DoT stack or one removable non-stack debuff."""
    if not consumable_available(state) or (dot_index is None) == (effect_index is None):
        return state
    with localcontext() as ctx:
        ctx.prec = PRECISION
        updated = deepcopy(state)
        player = updated.fighters["player"]
        if dot_index is not None:
            dots = updated.dot_states.get("player", [])
            if not 0 <= dot_index < len(dots):
                return state
            dot = dots[dot_index]
            if (
                not dot.removable
                or dot.unremovable
                or dot.protected
                or dot.fixed_mechanic
                or dot.boss_protected
                or dot.stacks <= 0
                or dot.remaining <= 0
            ):
                return state
            snapshots = list(dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks)
            if not snapshots:
                return state
            snapshots.pop(0)
            if snapshots:
                dot.stack_snapshots = snapshots
                dot.snapshot_attack = snapshots[0]
                dot.stacks = len(snapshots)
            else:
                dots.pop(dot_index)
        else:
            if not 0 <= effect_index < len(player.effects):
                return state
            effect = player.effects[effect_index]
            if not purifiable(effect):
                return state
            player.effects.pop(effect_index)
        return _finish_consumable_turn(updated, "consumable:purify")


def _effect_token(effect: Effect, index: int) -> str:
    return effect.instance_id or f"e{index + 1:x}"


def _dot_token(dot: DotState, index: int) -> str:
    return dot.instance_id or f"d{index + 1:x}"


def _remove_selected_dot(
    state: Combat, target_id: str, selection_id: str, *, all_stacks: bool
) -> str | None:
    dots = state.dot_states.get(target_id, [])
    for index, dot in enumerate(dots):
        if _dot_token(dot, index) != selection_id:
            continue
        snapshots = list(dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks)
        if not snapshots or dot.stacks <= 0 or dot.remaining <= 0:
            return None
        if all_stacks:
            dots.pop(index)
        else:
            snapshots.pop(0)
            if snapshots:
                dot.stack_snapshots = snapshots
                dot.snapshot_attack = snapshots[0]
                dot.stacks = len(snapshots)
            else:
                dots.pop(index)
        if not dots:
            state.dot_states.pop(target_id, None)
        return f"dot:{dot.kind}"
    return None


def _remove_selected_effect(
    target: Fighter, selection_id: str, *, one_stack: bool
) -> str | None:
    for index, effect in enumerate(target.effects):
        if _effect_token(effect, index) != selection_id:
            continue
        if one_stack and effect.stackable and effect.stacks > 1:
            if effect.stack_orders:
                effect.stack_orders.pop(0)
            effect.stacks -= 1
        else:
            target.effects.pop(index)
        return effect.id
    return None


def combat_consumable_usable(
    state: Combat,
    item_id: str,
    *,
    target_id: str | None = None,
    effect_id: str | None = None,
    budget_limit: int | None = None,
) -> bool:
    item = definition(item_id)
    if (
        item is None
        or item.use_context is not UseContext.COMBAT_PVE
        or not state.external_consumables_allowed
        or state.tutorial_stage != "normal"
        or not consumable_available(state)
        or state.fighters["player"].hp <= 0
        or (budget_limit is not None and state.consumable_uses >= budget_limit)
    ):
        return False
    player = state.fighters["player"]
    if item.family == ConsumableFamily.HEALING:
        return effective_heal_amount(state) > 0 and effect_id is None
    if item.family in {
        ConsumableFamily.PURIFICATION,
        ConsumableFamily.ANTIDOTE,
        ConsumableFamily.DISPELLER,
    }:
        if item.family == ConsumableFamily.DISPELLER:
            if target_id is None or target_id == "player":
                return False
            target = state.fighters.get(target_id)
            if target is None or target.hp <= 0:
                return False
        else:
            target_id = "player"
            target = player
        choices = {option_id for option_id, _ in consumable_effect_options(
            state, item_id, target_id=target_id
        )}
        return bool(choices) and effect_id in choices
    if item.family in {ConsumableFamily.PROTECTION, ConsumableFamily.WARDING}:
        return effect_id is None and target_id in {None, "player"}
    return False


def use_combat_consumable(
    state: Combat,
    item_id: str,
    *,
    target_id: str | None = None,
    effect_id: str | None = None,
    budget_limit: int | None = None,
) -> Combat:
    """Apply a valid PvE Consumable as one normal, versioned combat action."""
    if not combat_consumable_usable(
        state,
        item_id,
        target_id=target_id,
        effect_id=effect_id,
        budget_limit=budget_limit,
    ):
        return state
    item = definition(item_id)
    assert item is not None
    updated = deepcopy(state)
    player = updated.fighters["player"]
    resolved_target = target_id or "player"
    target = updated.fighters[resolved_target]
    healed = D(0)
    effect_name = ""
    effect_removal_kind = None
    barrier_value = D(0)

    if item.family == ConsumableFamily.HEALING:
        healed = effective_heal_amount(updated)
        if healed <= 0:
            return state
        player.hp += healed
    elif item.family == ConsumableFamily.PURIFICATION:
        assert effect_id is not None
        effect_name = _remove_selected_dot(
            updated, "player", effect_id, all_stacks=False
        ) or _remove_selected_effect(player, effect_id, one_stack=True) or ""
        if not effect_name:
            return state
    elif item.family == ConsumableFamily.ANTIDOTE:
        assert effect_id is not None
        effect_name = _remove_selected_dot(updated, "player", effect_id, all_stacks=True) or ""
        if not effect_name:
            return state
    elif item.family == ConsumableFamily.PROTECTION:
        barrier_multiplier = D("1.10") if player.selected_path == "bastiao" else D(1)
        barrier_value = (player.stats.hp * D("0.12") * barrier_multiplier).to_integral_value(
            rounding=ROUND_FLOOR
        )
        if barrier_value <= 0:
            return state
        player.barrier = barrier_value
        player.barrier_remaining = 2
        player.barrier_applied_opportunity = player.opportunity
        player.barrier_source = "player:consumable.protecao"
        player.barrier_debuff_magnitude_reduction = ZERO
    elif item.family == ConsumableFamily.DISPELLER:
        assert effect_id is not None
        selected = next(
            (
                effect
                for index, effect in enumerate(target.effects)
                if _effect_token(effect, index) == effect_id and dissipatable(effect)
            ),
            None,
        )
        if selected is None:
            return state
        effect_removal_kind = "stack" if selected.stackable else "effect"
        effect_name = _remove_selected_effect(target, effect_id, one_stack=True) or ""
        if not effect_name:
            return state
    elif item.family == ConsumableFamily.WARDING:
        player.ward_charges = 1
        player.ward_remaining = 2
        player.ward_applied_opportunity = player.opportunity
    else:
        return state

    return _finish_consumable_turn(
        updated,
        f"consumable:{item_id}",
        healed,
        target=resolved_target,
        effect_id=effect_name,
        effect_removal_kind=effect_removal_kind,
        barrier_value=barrier_value,
    )


def act(state: Combat, action: str, *, target_id: str | None = None) -> Combat:
    """Resolve one player action; invalid action/target intentions are a no-op."""
    if (
        len(action) == 2
        and action[0] == "a"
        and action[1] in "123"
        and isinstance(state.configuration_snapshot, dict)
    ):
        slot = int(action[1])
        for entry in state.configuration_snapshot.get("active_arts", ()):
            if isinstance(entry, dict) and entry.get("slot") == slot:
                action = str(entry.get("art_id", action))
                break
    if action not in allowed_actions(state):
        return state
    if action in state.player_actions:
        definition = state.player_actions[action]
        if not _resolve_action_targets(state, "player", definition, target_id):
            return state
    with localcontext() as ctx:
        ctx.prec = PRECISION
        updated = deepcopy(state)
        if updated.tutorial and updated.tutorial_stage != "normal":
            updated.pending_response = updated.tutorial.responses.get(action)
        committed = _perform(updated, "player", action, target_id=target_id)
        if not committed:
            return state
        updated.used_attack |= action == "attack"
        updated.used_defend |= action == "defend"
        updated.used_art |= action == "art"
        if not updated.result:
            _end_turn(updated)
            _advance_to_player(updated)
        updated.version += 1
        return updated
