"""Reusable deterministic duel engine. Inputs and outputs are pure domain snapshots."""

from copy import deepcopy
from dataclasses import InitVar, dataclass, field, replace
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
class ActionEffectRemoval:
    """One explicit Purification/Dispel component of an active action.

    The component resolves after the action's ordinary damage/status/healing/
    barrier effects. Target and effect selection are validated before commit;
    the component itself never owns a separate action, RNG roll, or cooldown.
    """

    kind: str
    count: int = 1
    trigger: str = "action"
    scope: str = "per_action"
    selection_required: bool = True
    resolution_order: str = "after_primary"

    def __post_init__(self) -> None:
        if self.kind not in {"purification", "dispel"}:
            raise ValueError("Action effect removal must be Purification or Dispel.")
        if self.count < 1:
            raise ValueError("Action effect removal count must be positive.")
        if self.trigger not in {"action", "successful_direct_hit"}:
            raise ValueError("Action effect removal trigger is invalid.")
        if self.scope not in {"per_action", "per_target"}:
            raise ValueError("Action effect removal scope is invalid.")
        if self.resolution_order != "after_primary":
            raise ValueError("Action effect removal resolution order is invalid.")


_CLASS_RESOURCE_IDS = frozenset(
    {
        "retaliation",
        "aim",
        "trama",
        "omen_offensive",
        "omen_defensive",
        "luminar_state",
    }
)


@dataclass(frozen=True)
class ActionResourceUse:
    """Declarative snapshot requirement and consumption for an internal class resource.

    Class resources remain owned by their existing state machines. This metadata
    only states when an action needs a resource and when its committed use is
    paid; it does not turn the resource into a normal removable combat effect.
    """

    resource: str
    minimum: int = 1
    consume: int = 0
    consume_at: str = "never"
    target_selector: str = "actor"
    consumption_scope: str = "per_action"
    required: bool = False
    state_kind: str | None = None

    def __post_init__(self) -> None:
        if self.resource not in _CLASS_RESOURCE_IDS:
            raise ValueError("Action resource use references an unknown class resource.")
        if self.minimum < 1 or self.consume < 0:
            raise ValueError("Action resource quantities must be valid positive counts.")
        if self.consume > 0 and self.consume_at not in {"commit", "after_resolution"}:
            raise ValueError("Consumed action resources need a valid consumption phase.")
        if self.consume == 0 and self.consume_at != "never":
            raise ValueError("Non-consuming action resources must use the never phase.")
        if self.target_selector not in {"actor", "primary_target", "each_target"}:
            raise ValueError("Action resource target selector is invalid.")
        if self.consumption_scope not in {"per_action", "per_target"}:
            raise ValueError("Action resource consumption scope is invalid.")
        actor_resources = {"retaliation", "trama", "luminar_state"}
        if self.resource in actor_resources and self.target_selector != "actor":
            raise ValueError("This class resource belongs to the acting character.")
        if self.resource in {"aim", "omen_offensive", "omen_defensive"} and (
            self.target_selector == "actor"
        ):
            raise ValueError("This class resource is associated with a target.")
        if self.resource != "luminar_state" and self.state_kind is not None:
            raise ValueError("Only a Luminar state may declare its state kind.")
        if self.state_kind not in {None, "fulgor", "julgamento"}:
            raise ValueError("Luminar resource state kind is invalid.")
        if self.resource == "luminar_state" and self.state_kind is None:
            raise ValueError("Luminar resource use must identify Fulgor or Julgamento.")
        if self.resource != "aim" and max(self.minimum, self.consume) > 1:
            raise ValueError("This class resource has at most one consumable instance.")
        if self.consume_at == "after_resolution" and self.resource != "aim":
            raise ValueError("Only target-linked Mira may be consumed after resolution.")
        if (
            self.consume > 0
            and self.target_selector == "each_target"
            and self.consumption_scope != "per_target"
        ):
            raise ValueError(
                "AoE resource consumption must declare per-target scope explicitly."
            )


@dataclass(frozen=True)
class ActionCondition:
    """A condition read from the immutable beginning-of-action snapshot."""

    kind: str
    threshold: Decimal = ZERO
    resource: str | None = None
    minimum: int = 1
    state_kind: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {
            "actor_hp_fraction_below",
            "target_hp_fraction_at_most",
            "target_has_normal_negative_effect",
            "class_resource_at_least",
        }:
            raise ValueError("Action condition kind is unsupported.")
        if self.kind in {"actor_hp_fraction_below", "target_hp_fraction_at_most"}:
            if not ZERO <= self.threshold <= D(1):
                raise ValueError("Action HP condition threshold must be between zero and one.")
        if self.kind == "class_resource_at_least":
            if self.resource not in _CLASS_RESOURCE_IDS or self.minimum < 1:
                raise ValueError("Action class-resource condition is invalid.")
        elif self.resource is not None or self.state_kind is not None:
            raise ValueError("Only a class-resource condition accepts resource metadata.")
        if self.resource != "luminar_state" and self.state_kind is not None:
            raise ValueError("Only a Luminar condition may specify its state kind.")
        if self.state_kind not in {None, "fulgor", "julgamento"}:
            raise ValueError("Luminar condition state kind is invalid.")
        if self.resource == "luminar_state" and self.state_kind is None:
            raise ValueError("Luminar condition must identify Fulgor or Julgamento.")
        if self.resource is not None and self.resource != "aim" and self.minimum > 1:
            raise ValueError("This class resource has at most one instance.")


@dataclass(frozen=True)
class ActionConditionalModifier:
    """One typed modifier activated by a snapshot condition."""

    id: str
    condition: ActionCondition
    component: str
    magnitude: Decimal
    operation: str = "add"
    target_scope: str = "per_target"
    evaluation_scope: str = "per_target"

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.condition, ActionCondition):
            raise ValueError("Conditional action modifiers need an id and typed condition.")
        if self.component not in {
            "damage_power",
            "healing_power",
            "barrier_power",
            "final_damage_bonus",
            "precision_bonus",
            "crit_bonus",
        }:
            raise ValueError("Conditional action modifier component is unsupported.")
        if self.operation not in {"add", "multiply"}:
            raise ValueError("Conditional action modifier operation is unsupported.")
        if self.operation == "multiply" and self.component not in {
            "damage_power",
            "healing_power",
            "barrier_power",
        }:
            raise ValueError("Multiplication is only valid for power components.")
        if self.target_scope not in {"per_target", "primary_target"}:
            raise ValueError("Conditional action modifier target scope is invalid.")
        if self.evaluation_scope not in {"per_action", "per_target"}:
            raise ValueError("Conditional action modifier evaluation scope is invalid.")


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
    revive_fighter_keys: tuple[str, ...] = ()
    revive_hp_fraction: Decimal = D("0.50")
    requires_defeated_fighter_keys: tuple[str, ...] = ()
    self_barrier_hp_fraction: Decimal = ZERO
    actor_per_bonus: Decimal = ZERO
    actor_per_bonus_if_target_bleeding: Decimal = ZERO
    actor_per_bonus_if_target_hp_fraction_at_most: Decimal = ZERO
    actor_per_bonus_hp_fraction_threshold: Decimal = D("0.40")
    native_dot_stacks_if_target_poisoned: int = 0
    vampirism_fraction: Decimal = ZERO
    # Optional shared-engine encounter constraints. Empty values preserve the
    # legacy action contract used by existing combat content.
    phase_ids: tuple[str, ...] = ()
    skip_if_target_effect_active: str | None = None
    skip_if_target_dot_at_cap: str | None = None
    vampirism_cap_hp_fraction: Decimal | None = None
    skip_if_self_effect_active: str | None = None
    skip_if_any_self_effect_active: tuple[str, ...] = ()
    skip_if_actor_last_action: tuple[str, ...] = ()
    ai_priority_after: tuple[str, ...] = ()
    barrier_bound_effect_ids: tuple[str, ...] = ()
    effect_removal: ActionEffectRemoval | None = None
    resource_uses: tuple[ActionResourceUse, ...] = ()
    conditional_modifiers: tuple[ActionConditionalModifier, ...] = ()

    def __post_init__(self) -> None:
        if self.hit_count < 1:
            raise ValueError("An action must resolve at least one hit.")
        if self.chain_power_bonus < ZERO:
            raise ValueError("Action chain power bonus cannot be negative.")
        if not ZERO <= self.vampirism_fraction <= D(1):
            raise ValueError("Action vampirism must be between zero and one.")
        if (
            self.vampirism_cap_hp_fraction is not None
            and not ZERO <= self.vampirism_cap_hp_fraction <= D(1)
        ):
            raise ValueError("Action vampirism HP cap must be between zero and one.")
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
        if self.effect_removal is not None:
            if not isinstance(self.effect_removal, ActionEffectRemoval):
                raise ValueError("Action effect removal must use its typed component.")
            if (
                self.effect_removal.trigger == "successful_direct_hit"
                and self.coefficient <= ZERO
            ):
                raise ValueError("Direct-hit effect removal requires direct damage.")
        if any(not isinstance(use, ActionResourceUse) for use in self.resource_uses):
            raise ValueError("Action resources must use typed resource-use declarations.")
        if any(
            not isinstance(modifier, ActionConditionalModifier)
            for modifier in self.conditional_modifiers
        ):
            raise ValueError("Conditional action effects must use typed declarations.")
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
        if self.self_barrier_hp_fraction < ZERO or self.self_barrier_hp_fraction > D(1):
            raise ValueError("HP-based barrier fraction must be between zero and one.")
        if not ZERO < self.revive_hp_fraction <= D(1):
            raise ValueError("Revive HP fraction must be between zero and one.")


@dataclass
class BarrierLayer:
    """One independently expiring barrier source in FIFO absorption order."""

    applier_id: str | None
    effect_definition_id: str | None
    value: Decimal
    remaining: int
    applied_opportunity: int
    debuff_magnitude_reduction: Decimal = ZERO
    source_label: str = ""
    bound_effect_ids: tuple[str, ...] = ()
    legacy: bool = False

    def __post_init__(self) -> None:
        self.value = max(ZERO, D(self.value))
        self.debuff_magnitude_reduction = max(
            ZERO, D(self.debuff_magnitude_reduction)
        )
        self.remaining = int(self.remaining)
        self.applied_opportunity = int(self.applied_opportunity)
        self.bound_effect_ids = tuple(self.bound_effect_ids)
        if not self.legacy and (not self.applier_id or not self.effect_definition_id):
            raise ValueError("A barrier source requires an applier and effect definition.")

    @property
    def identity(self) -> tuple[str | None, str | None] | None:
        if self.legacy:
            return None
        return self.applier_id, self.effect_definition_id


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
    # InitVars preserve construction from callers and scalar snapshots. Runtime
    # access is provided by aggregate compatibility properties installed below.
    barrier: InitVar[Decimal] = D(0)
    barrier_remaining: InitVar[int] = 0
    barrier_applied_opportunity: InitVar[int] = 0
    barrier_source: InitVar[str] = ""
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
    encounter_hidden: bool = False
    defeat_on_zero: bool | None = None
    required_for_victory: bool | None = None
    protection_layers: int = 0
    protection_reduction_per_layer: Decimal = ZERO
    training_state_tags: tuple[str, ...] = ()
    tagged_direct_damage_reductions: dict[str, Decimal] = field(default_factory=dict)
    action_chains: dict[str, dict[str, str]] = field(default_factory=dict)
    barrier_debuff_magnitude_reduction: InitVar[Decimal] = ZERO
    selected_path: str | None = None
    talent_ids: tuple[str, ...] = ()
    path_state: dict[str, Any] = field(default_factory=dict)
    action_use_counts: dict[str, int] = field(default_factory=dict)
    barrier_layers: list[BarrierLayer] = field(default_factory=list)
    barrier_cap_fraction: Decimal | None = None

    def __post_init__(
        self,
        barrier: Decimal,
        barrier_remaining: int,
        barrier_applied_opportunity: int,
        barrier_source: str,
        barrier_debuff_magnitude_reduction: Decimal,
    ) -> None:
        # Old snapshots had one scalar barrier. Preserve it as an explicitly
        # anonymous legacy layer instead of inventing canonical source IDs.
        if not self.barrier_layers and D(barrier) > ZERO and barrier_remaining != 0:
            self.barrier_layers.append(
                BarrierLayer(
                    applier_id=None,
                    effect_definition_id=None,
                    value=D(barrier),
                    remaining=int(barrier_remaining),
                    applied_opportunity=int(barrier_applied_opportunity),
                    debuff_magnitude_reduction=D(barrier_debuff_magnitude_reduction),
                    source_label=barrier_source,
                    legacy=True,
                )
            )
        self._enforce_barrier_cap()

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
        if name in {"stats", "barrier_cap_fraction"}:
            data = object.__getattribute__(self, "__dict__")
            if data.get("barrier_layers") and data.get("barrier_cap_fraction") is not None:
                self._enforce_barrier_cap()

    def _active_barrier_layers(self) -> tuple[BarrierLayer, ...]:
        return tuple(
            layer
            for layer in self.barrier_layers
            if layer.value > ZERO and layer.remaining != 0
        )

    def _remove_barrier_linked_effects(self, removed: tuple[BarrierLayer, ...]) -> None:
        linked = {effect_id for layer in removed for effect_id in layer.bound_effect_ids}
        retained = {
            effect_id
            for layer in self._active_barrier_layers()
            for effect_id in layer.bound_effect_ids
        }
        expired = linked - retained
        if expired:
            self.effects = [effect for effect in self.effects if effect.id not in expired]

    def _enforce_barrier_cap(self) -> None:
        data = object.__getattribute__(self, "__dict__")
        cap_fraction = data.get("barrier_cap_fraction")
        stats = data.get("stats")
        layers = data.get("barrier_layers")
        if cap_fraction is None or stats is None or layers is None:
            return
        fraction = max(ZERO, D(cap_fraction))
        cap = (stats.hp * fraction).to_integral_value(rounding=ROUND_FLOOR)
        total = sum((layer.value for layer in self._active_barrier_layers()), ZERO)
        excess = max(ZERO, total - cap)
        if excess <= ZERO:
            return
        removed: list[BarrierLayer] = []
        # On an HP-cap reduction, trim newest layers first. Existing layers
        # retain their FIFO protection priority and their own durations.
        for index in range(len(layers) - 1, -1, -1):
            layer = layers[index]
            if layer.remaining == 0 or layer.value <= ZERO:
                continue
            cut = min(excess, layer.value)
            remainder = layer.value - cut
            excess -= cut
            if remainder <= ZERO:
                removed.append(layer)
                layers.pop(index)
            else:
                layers[index] = replace(layer, value=remainder)
            if excess <= ZERO:
                break
        if removed:
            self._remove_barrier_linked_effects(tuple(removed))

    @property
    def barriers(self) -> tuple[BarrierLayer, ...]:
        """Compatibility view for consumers that only ask whether a shield exists."""
        return self._active_barrier_layers()

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


def _fighter_barrier(fighter: Fighter) -> Decimal:
    return sum((layer.value for layer in fighter._active_barrier_layers()), ZERO)


def _legacy_layer_index(fighter: Fighter) -> int | None:
    return next(
        (index for index, layer in enumerate(fighter.barrier_layers) if layer.legacy),
        None,
    )


def _set_legacy_barrier_component(fighter: Fighter, **changes: Any) -> None:
    active_indexes = [
        current
        for current, layer in enumerate(fighter.barrier_layers)
        if layer.value > ZERO and layer.remaining != 0
    ]
    # Scalar callers address the compatibility view, which represents the
    # most recently applied active source.
    index = active_indexes[-1] if active_indexes else _legacy_layer_index(fighter)
    if index is None:
        meaningful = any(
            value not in (0, ZERO, "", None)
            for value in changes.values()
        )
        if not meaningful:
            return
        layer = BarrierLayer(
            applier_id=None,
            effect_definition_id=None,
            value=ZERO,
            remaining=0,
            applied_opportunity=0,
            legacy=True,
        )
        fighter.barrier_layers.append(replace(layer, **changes))
        return
    updated = replace(fighter.barrier_layers[index], **changes)
    if updated.value <= ZERO or updated.remaining == 0:
        removed = (fighter.barrier_layers.pop(index),)
        fighter._remove_barrier_linked_effects(removed)
        return
    fighter.barrier_layers[index] = updated


def _set_fighter_barrier(fighter: Fighter, amount: Decimal | int) -> None:
    value = max(ZERO, D(amount))
    removed = tuple(fighter.barrier_layers)
    fighter.barrier_layers.clear()
    if value > ZERO:
        fighter.barrier_layers.append(
            BarrierLayer(
                applier_id=None,
                effect_definition_id=None,
                value=value,
                remaining=0,
                applied_opportunity=fighter.opportunity,
                legacy=True,
            )
        )
    fighter._remove_barrier_linked_effects(removed)
    fighter._enforce_barrier_cap()


def _set_fighter_barrier_remaining(fighter: Fighter, remaining: int) -> None:
    _set_legacy_barrier_component(fighter, remaining=int(remaining))


def _set_fighter_barrier_applied_opportunity(fighter: Fighter, opportunity: int) -> None:
    _set_legacy_barrier_component(fighter, applied_opportunity=int(opportunity))


def _set_fighter_barrier_source(fighter: Fighter, source: str) -> None:
    _set_legacy_barrier_component(fighter, source_label=str(source))


def _set_fighter_barrier_debuff_reduction(fighter: Fighter, reduction: Decimal) -> None:
    _set_legacy_barrier_component(
        fighter, debuff_magnitude_reduction=max(ZERO, D(reduction))
    )


def _fighter_barrier_remaining(fighter: Fighter) -> int:
    layers = fighter._active_barrier_layers()
    if any(layer.remaining < 0 for layer in layers):
        return -1
    return max((layer.remaining for layer in layers), default=0)


def _fighter_barrier_applied_opportunity(fighter: Fighter) -> int:
    layers = fighter._active_barrier_layers()
    return layers[-1].applied_opportunity if layers else 0


def _fighter_barrier_source(fighter: Fighter) -> str:
    layers = fighter._active_barrier_layers()
    return layers[-1].source_label if layers else ""


def _fighter_barrier_debuff_reduction(fighter: Fighter) -> Decimal:
    # There is no stacking rule for distinct barrier-derived reductions;
    # retain the former scalar semantics by using the strongest active source.
    return max(
        (layer.debuff_magnitude_reduction for layer in fighter._active_barrier_layers()),
        default=ZERO,
    )


# InitVars keep the old Fighter(...) constructor while these descriptors expose
# aggregate compatibility views; barrier_layers is the only authoritative state.
Fighter.barrier = property(_fighter_barrier, _set_fighter_barrier)
Fighter.barrier_remaining = property(
    _fighter_barrier_remaining, _set_fighter_barrier_remaining
)
Fighter.barrier_applied_opportunity = property(
    _fighter_barrier_applied_opportunity, _set_fighter_barrier_applied_opportunity
)
Fighter.barrier_source = property(_fighter_barrier_source, _set_fighter_barrier_source)
Fighter.barrier_debuff_magnitude_reduction = property(
    _fighter_barrier_debuff_reduction, _set_fighter_barrier_debuff_reduction
)


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
    barrier_total_after: Decimal = D(0)
    barrier_duration: int = 0
    barrier_absorbed_sources: tuple[str, ...] = ()
    effect_removal_kind: str | None = None
    effect_removal_component: str | None = None
    effect_removal_result: str | None = None
    removed_effect_ids: tuple[str, ...] = ()
    effect_removal_kinds: tuple[str, ...] = ()
    remaining_effect_stacks: tuple[int, ...] = ()
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
    class_resource_changes: tuple[tuple[str, str, int, int], ...] = ()
    path_power_multiplier: Decimal = D(1)
    path_final_damage_bonus: Decimal = ZERO
    aim_stacks: int = 0
    path_per_bonus: Decimal = ZERO
    path_crit_bonus: Decimal = ZERO
    pressure_stacks: int = 0


@dataclass(frozen=True, slots=True)
class CombatStatAura:
    """A live source-counted modifier applied to selected combatants."""

    aura_id: str
    stat: str
    source_fighter_keys: tuple[str, ...]
    target_fighter_keys: tuple[str, ...]
    multiplier_per_source: Decimal


@dataclass(frozen=True, slots=True)
class CombatDamageAura:
    """A final-damage reduction supplied by a set of living combat entities."""

    aura_id: str
    source_fighter_keys: tuple[str, ...]
    target_fighter_keys: tuple[str, ...]
    reduction_per_source: Decimal
    reduction_mode: str = "per_source"
    barrier_received_per_source: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class CombatPhaseTrigger:
    """One-shot, HP-threshold event that activates or revives encounter objects."""

    trigger_id: str
    source_fighter_key: str
    hp_fraction_at_most: Decimal
    activate_fighter_keys: tuple[str, ...] = ()
    revive_fighter_keys: tuple[str, ...] = ()
    revive_hp_fraction: Decimal = D("0.50")
    phase_id: str | None = None
    resolution_id: str | None = None
    heal_source_per_active_fighter_fraction: Decimal = ZERO
    consume_active_fighter_keys: tuple[str, ...] = ()
    barrier_source_per_active_fighter_fraction: Decimal = ZERO
    ai_priority: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CombatConsumableOption:
    item_id: str
    target_id: str
    effect_id: str | None
    label: str


@dataclass(frozen=True, slots=True)
class CombatEffectRemovalOption:
    target_id: str
    effect_id: str
    label: str
    stacks: int
    remaining: int
    stackable: bool


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
    ai_cycles: dict[str, tuple[str, ...]] = field(default_factory=dict)
    ai_positions: dict[str, int] = field(default_factory=dict)
    ai_priorities: dict[str, tuple[str, ...]] = field(default_factory=dict)
    pressure_start_opportunity: int = 0
    pressure_cap: int = 0
    pressure_step: Decimal = D("0.03")
    pressure_stacks: int = 0
    stat_auras: tuple[CombatStatAura, ...] = ()
    player_actions_by_fighter: dict[str, dict[str, Action]] = field(default_factory=dict)
    player_configuration_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    party_mode: bool = False
    damage_auras: tuple[CombatDamageAura, ...] = ()
    phase_triggers: tuple[CombatPhaseTrigger, ...] = ()
    phase_triggered_ids: set[str] = field(default_factory=set)
    phase_id: str = "default"
    manual_sides: tuple[str, ...] = ()
    pvp_mode: bool = False

    def __post_init__(self) -> None:
        for fighter in self.fighters.values():
            fighter.barrier_cap_fraction = D("0.35") if self.pvp_mode else None

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


def _fighter_stat(state: Combat, fighter_key: str, stat_name: str) -> Decimal:
    value = state.fighters[fighter_key].stat(stat_name)
    for aura in state.stat_auras:
        if aura.stat != stat_name or fighter_key not in aura.target_fighter_keys:
            continue
        active_sources = sum(
            state.fighters[source_key].hp > 0
            for source_key in aura.source_fighter_keys
            if source_key in state.fighters
        )
        if active_sources:
            value *= D(1) + aura.multiplier_per_source * active_sources
    return value


def _fighter_defeat_on_zero(state: Combat, key: str) -> bool:
    value = state.fighters[key].defeat_on_zero
    if value is not None:
        return value
    if state.party_mode and _fighter_side(state, key) == "player":
        return False
    return key == "player"


def active_player_key(state: Combat) -> str | None:
    """Return the manually controlled fighter whose opportunity is open."""
    if not state.order:
        return None
    key = state.order[state.turn_index]
    is_player_turn = _is_player_turn_actor(state, key)
    if key in state.fighters and is_player_turn:
        return key
    return None


def _is_player_turn_actor(state: Combat, key: str) -> bool:
    """Identify sides whose turns are submitted by a player rather than AI."""
    if not state.party_mode:
        return key == "player"
    side = _fighter_side(state, key)
    if state.manual_sides:
        return side in state.manual_sides
    return side == "player"


def player_actions_for(state: Combat, fighter_key: str | None = None) -> dict[str, Action]:
    if fighter_key is None:
        fighter_key = active_player_key(state) or "player"
    return state.player_actions_by_fighter.get(fighter_key, state.player_actions)


def _resolve_phase_triggers(state: Combat) -> None:
    for trigger in state.phase_triggers:
        if trigger.trigger_id in state.phase_triggered_ids:
            continue
        source = state.fighters.get(trigger.source_fighter_key)
        if source is None or source.stats.hp <= ZERO:
            continue
        if source.hp > source.stats.hp * trigger.hp_fraction_at_most:
            continue
        if trigger.phase_id is not None:
            state.phase_id = trigger.phase_id
        if trigger.ai_priority:
            state.ai_priorities[trigger.source_fighter_key] = trigger.ai_priority
        for key in trigger.activate_fighter_keys:
            fighter = state.fighters.get(key)
            if fighter is not None and fighter.hp <= ZERO:
                fighter.hp = fighter.stats.hp
                fighter.encounter_hidden = False
        for key in trigger.revive_fighter_keys:
            fighter = state.fighters.get(key)
            if fighter is not None and fighter.hp <= ZERO:
                fighter.hp = fighter.stats.hp * trigger.revive_hp_fraction
        active_resolution_fighters = [
            state.fighters[key]
            for key in trigger.consume_active_fighter_keys
            if key in state.fighters and state.fighters[key].hp > ZERO
        ]
        if active_resolution_fighters and trigger.heal_source_per_active_fighter_fraction > ZERO:
            healing = (
                source.stats.hp
                * trigger.heal_source_per_active_fighter_fraction
                * len(active_resolution_fighters)
            )
            source.hp = min(source.stats.hp, source.hp + healing)
        if (
            active_resolution_fighters
            and trigger.barrier_source_per_active_fighter_fraction > ZERO
        ):
            barrier_value = (
                source.stats.hp
                * trigger.barrier_source_per_active_fighter_fraction
                * len(active_resolution_fighters)
            ).to_integral_value(rounding=ROUND_FLOOR)
            barrier_value = _apply_barrier(
                source,
                applier_id=source.id,
                effect_definition_id=trigger.trigger_id,
                value=barrier_value,
                duration=-1,
                applied_opportunity=source.opportunity,
                round_number=state.round,
            )
            if barrier_value > ZERO:
                state.mechanic_events.append(
                    CombatEvent(
                        len(state.mechanic_events),
                        state.round,
                        trigger.source_fighter_key,
                        f"phase:{trigger.trigger_id}:barrier",
                        target=source.id,
                        barrier_value=barrier_value,
                        barrier_total_after=source.barrier,
                        barrier_duration=-1,
                        barrier_applied_source=f"{source.id}:{trigger.trigger_id}",
                        actor_entity_id=source.id,
                        internal=True,
                    )
                )
        for fighter in active_resolution_fighters:
            fighter.hp = ZERO
            fighter.encounter_hidden = True
        state.phase_triggered_ids.add(trigger.trigger_id)
        state.mechanic_events.append(
            CombatEvent(
                len(state.mechanic_events),
                state.round,
                trigger.source_fighter_key,
                f"phase:{trigger.trigger_id}",
                target=source.id,
                actor_entity_id=source.id,
                internal=True,
            )
        )
        if trigger.resolution_id is not None:
            state.mechanic_events.append(
                CombatEvent(
                    len(state.mechanic_events),
                    state.round,
                    trigger.source_fighter_key,
                    f"phase:{trigger.resolution_id}",
                    target=source.id,
                    actor_entity_id=source.id,
                    internal=True,
                )
            )


def _damage_aura_reduction(state: Combat, target_key: str) -> Decimal:
    reduction = ZERO
    for aura in state.damage_auras:
        if target_key not in aura.target_fighter_keys:
            continue
        active_sources = sum(
            state.fighters[key].hp > ZERO
            for key in aura.source_fighter_keys
            if key in state.fighters
        )
        if aura.reduction_mode == "any_source":
            reduction += aura.reduction_per_source if active_sources else ZERO
        else:
            reduction += aura.reduction_per_source * active_sources
    return min(D(1), max(ZERO, reduction))


def _barrier_received_multiplier(state: Combat, target_key: str) -> Decimal:
    multiplier = D(1)
    for aura in state.damage_auras:
        if target_key not in aura.target_fighter_keys or aura.barrier_received_per_source <= ZERO:
            continue
        active_sources = sum(
            state.fighters[key].hp > ZERO
            for key in aura.source_fighter_keys
            if key in state.fighters
        )
        multiplier += aura.barrier_received_per_source * active_sources
    return multiplier


def _apply_barrier(
    target: Fighter,
    *,
    applier_id: str,
    effect_definition_id: str,
    value: Decimal | int,
    duration: int,
    applied_opportunity: int,
    round_number: int = 1,
    debuff_magnitude_reduction: Decimal = ZERO,
    bound_effect_ids: tuple[str, ...] = (),
    source_label: str | None = None,
) -> Decimal:
    """Apply or replace one source-keyed barrier and return the granted amount."""
    requested = max(ZERO, D(value))
    duration = int(duration)
    if target.hp <= ZERO or requested <= ZERO or duration == 0:
        return ZERO

    if target.barrier_cap_fraction is not None and round_number >= 20:
        exhaustion = max(D("0.35"), D(1) - D("0.10") * (round_number - 19))
        requested = (requested * exhaustion).to_integral_value(rounding=ROUND_FLOOR)
        if requested <= ZERO:
            return ZERO

    identity = (applier_id, effect_definition_id)
    existing_index = next(
        (
            index
            for index, layer in enumerate(target.barrier_layers)
            if not layer.legacy and layer.identity == identity
        ),
        None,
    )
    existing = (
        target.barrier_layers[existing_index]
        if existing_index is not None
        else None
    )
    other_total = sum(
        (
            layer.value
            for index, layer in enumerate(target._active_barrier_layers())
            if layer is not existing
        ),
        ZERO,
    )
    granted = requested
    if target.barrier_cap_fraction is not None:
        cap = (target.stats.hp * target.barrier_cap_fraction).to_integral_value(
            rounding=ROUND_FLOOR
        )
        granted = min(granted, max(ZERO, cap - other_total))

    if granted <= ZERO:
        removed = ()
        if existing_index is not None:
            removed = (target.barrier_layers.pop(existing_index),)
            target._remove_barrier_linked_effects(removed)
        return ZERO

    layer = BarrierLayer(
        applier_id=applier_id,
        effect_definition_id=effect_definition_id,
        value=granted,
        remaining=duration,
        applied_opportunity=applied_opportunity,
        debuff_magnitude_reduction=debuff_magnitude_reduction,
        source_label=source_label or f"{applier_id}:{effect_definition_id}",
        bound_effect_ids=bound_effect_ids,
    )
    if existing_index is None:
        target.barrier_layers.append(layer)
    else:
        # Same-source refresh replaces its amount and duration in place; this
        # preserves deterministic FIFO priority without renewing other sources.
        previous = target.barrier_layers[existing_index]
        target.barrier_layers[existing_index] = layer
        target._remove_barrier_linked_effects((previous,))
    target._enforce_barrier_cap()
    return layer.value


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
            or action.self_barrier_hp_fraction > ZERO
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
        if requested_target is not None:
            requested_key = _resolve_fighter_key(state, requested_target)
            if requested_key not in candidates:
                return ()
        return tuple(candidates)

    requested_key = _resolve_fighter_key(state, requested_target)
    if requested_key is not None:
        return (requested_key,) if requested_key in candidates else ()
    if requested_target is not None:
        return ()
    if len(candidates) == 1:
        return (candidates[0],)
    if _fighter_side(state, actor_key) == "enemy":
        player_candidates = tuple(
            key for key in candidates if _fighter_side(state, key) == "player"
        )
        if len(player_candidates) == 1:
            return player_candidates
    return ()


def action_target_ids(
    state: Combat, action_id: str, *, actor_key: str = "player"
) -> tuple[str, ...]:
    """Return deterministic, alive target entity IDs selectable for one action."""
    actions = (
        player_actions_for(state, actor_key)
        if _is_player_turn_actor(state, actor_key)
        else state.enemy_actions
    )
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


_CLASS_MECHANIC_STATE_KEYS = (
    "luminar_state",
    "trama_state",
    "omen_offensive",
    "omen_defensive",
    "guard_prepared_barrier",
    "guard_integrity_debuff",
    "trama_next_per",
    "aim_next_per",
    "aim_current_target_id",
    "errante_sangue_frio_crit",
)
_CLASS_MECHANIC_COMBAT_FLAGS = (
    "vigilia_retaliation_triggered",
    "trama_expiry_renewed",
    "omen_flexible_used",
    "luminar_cycle_used",
    "aim_acquisition_used",
)


def _clear_class_mechanics_for_death(state: Combat, fighter_key: str) -> None:
    dead = state.fighters.get(fighter_key)
    if dead is None:
        return
    _clear_retaliation(dead)
    for key in _CLASS_MECHANIC_STATE_KEYS:
        dead.path_state.pop(key, None)
    dead.path_state.pop("aim_from", None)
    dead.effects = [effect for effect in dead.effects if not _is_class_mechanic_effect(effect)]

    for fighter in state.fighters.values():
        aim_from = fighter.path_state.get("aim_from")
        if isinstance(aim_from, dict):
            aim_from.pop(dead.id, None)
            if not aim_from:
                fighter.path_state.pop("aim_from", None)
        for key in ("omen_offensive", "omen_defensive"):
            omens = fighter.path_state.get(key)
            if isinstance(omens, dict):
                omens.pop(dead.id, None)


def _clear_class_mechanics_at_combat_end(state: Combat) -> None:
    for fighter in state.fighters.values():
        _clear_retaliation(fighter)
        for key in (*_CLASS_MECHANIC_STATE_KEYS, *_CLASS_MECHANIC_COMBAT_FLAGS, "aim_from"):
            fighter.path_state.pop(key, None)
        fighter.effects = [
            effect for effect in fighter.effects if not _is_class_mechanic_effect(effect)
        ]


def _is_class_mechanic_effect(effect: Effect) -> bool:
    return effect.id.startswith("class_mechanic.") or effect.id == (
        "talent.sentinela.ritmo_de_guarda.agility"
    )


def _finish_combat(state: Combat, result: str) -> None:
    state.result = result
    _clear_prepared_action(state)
    _clear_class_mechanics_at_combat_end(state)


def _refresh_result(state: Combat) -> None:
    if state.party_mode:
        if not any(
            _fighter_side(state, key) == "player"
            and fighter.hp > ZERO
            and fighter.takes_turn
            for key, fighter in state.fighters.items()
        ):
            _finish_combat(state, "defeat")
            return
    if any(
        fighter.hp <= 0 and _fighter_defeat_on_zero(state, key)
        for key, fighter in state.fighters.items()
    ):
        _finish_combat(state, "defeat")
        return
    required_enemies = [
        key
        for key, fighter in state.fighters.items()
        if _fighter_side(state, key) == "enemy"
        and _fighter_required_for_victory(state, key)
    ]
    if required_enemies and all(state.fighters[key].hp <= 0 for key in required_enemies):
        _finish_combat(state, "victory")


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


def allowed_actions(state: Combat, fighter_key: str | None = None) -> tuple[str, ...]:
    active_key = active_player_key(state)
    fighter_key = fighter_key or active_key
    if state.result or active_key is None or fighter_key != active_key:
        return ()
    player = state.fighters[fighter_key]
    actions = player_actions_for(state, fighter_key)
    allowed = [
        key for key in actions if player.cooldowns.get(key, 0) <= player.opportunity
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
            and target.barrier_remaining != 0
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
    if item.family == ConsumableFamily.PURIFICATION:
        return tuple(
            (option.effect_id, option.label)
            for option in _effect_removal_options_for_target(
                state, "purification", target_id
            )
        )
    if item.family == ConsumableFamily.ANTIDOTE:
        return tuple(
            (option.effect_id, option.label)
            for option in _dot_removal_options_for_target(state, target_id)
        )
    if item.family == ConsumableFamily.DISPELLER and target_id != "player":
        return tuple(
            (option.effect_id, option.label)
            for option in _effect_removal_options_for_target(state, "dispel", target_id)
        )
    return ()


def _dot_is_removable(dot: DotState) -> bool:
    return bool(
        dot.stacks > 0
        and dot.remaining > 0
        and dot.removable
        and not dot.unremovable
        and not dot.protected
        and not dot.fixed_mechanic
        and not dot.boss_protected
    )


def _dot_removal_options_for_target(
    state: Combat, target_id: str
) -> tuple[CombatEffectRemovalOption, ...]:
    options = []
    for index, dot in enumerate(state.dot_states.get(target_id, ())):
        if not _dot_is_removable(dot):
            continue
        options.append(
            CombatEffectRemovalOption(
                target_id,
                _dot_token(dot, index),
                f"dot:{dot.kind}",
                dot.stacks,
                dot.remaining,
                True,
            )
        )
    return tuple(options)


def _effect_removal_options_for_target(
    state: Combat, component: str, target_id: str
) -> tuple[CombatEffectRemovalOption, ...]:
    target = state.fighters.get(target_id)
    if target is None:
        return ()
    options: list[CombatEffectRemovalOption] = []
    if component == "purification":
        options.extend(_dot_removal_options_for_target(state, target_id))
    for index, effect in enumerate(target.effects):
        eligible = (
            purifiable(effect)
            if component == "purification"
            else dissipatable(effect)
            if component == "dispel"
            else False
        )
        if eligible:
            options.append(
                CombatEffectRemovalOption(
                    target_id,
                    _effect_token(effect, index),
                    f"effect:{effect.id}",
                    effect.stacks,
                    effect.remaining,
                    effect.stackable,
                )
            )
    return tuple(options)


def action_effect_removal_options(
    state: Combat,
    action_id: str,
    *,
    target_id: str | None = None,
    actor_key: str | None = None,
) -> tuple[CombatEffectRemovalOption, ...]:
    """Expose only currently valid, stable effect selections for an Action."""
    actor_key = actor_key or active_player_key(state)
    if actor_key is None:
        return ()
    action = player_actions_for(state, actor_key).get(action_id)
    if action is None or action.effect_removal is None:
        return ()
    targets = _resolve_action_targets(state, actor_key, action, target_id)
    actor_side = _fighter_side(state, actor_key)
    options = []
    for target_key in targets:
        target_side = _fighter_side(state, target_key)
        if action.effect_removal.kind == "purification" and target_side != actor_side:
            continue
        if action.effect_removal.kind == "dispel" and target_side == actor_side:
            continue
        options.extend(
            _effect_removal_options_for_target(
                state, action.effect_removal.kind, target_key
            )
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
    state: Combat,
    item_ids: tuple[str, ...] | list[str],
    *,
    budget_limit: int,
    actor_key: str | None = None,
) -> tuple[CombatConsumableOption, ...]:
    """Project stock-backed, currently valid actions for a combat screen."""
    actor_key = actor_key or active_player_key(state) or "player"
    actor = state.fighters.get(actor_key)
    if actor is None:
        return ()
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
                state, item_id, target_id=actor_key, budget_limit=budget_limit,
                actor_key=actor_key,
            ):
                options.append(CombatConsumableOption(item_id, actor_key, None, item.name))
        elif item.family in {ConsumableFamily.PURIFICATION, ConsumableFamily.ANTIDOTE}:
            for effect_id, selection in consumable_effect_options(
                state, item_id, target_id=actor_key
            ):
                if combat_consumable_usable(
                    state,
                    item_id,
                    target_id=actor_key,
                    effect_id=effect_id,
                    budget_limit=budget_limit,
                    actor_key=actor_key,
                ):
                    options.append(
                        CombatConsumableOption(
                            item_id,
                            actor_key,
                            effect_id,
                            f"{item.name} · {_effect_display_name(state, actor_key, selection)}",
                        )
                    )
        elif item.family == ConsumableFamily.DISPELLER:
            for target_id, target in state.fighters.items():
                if (
                    _fighter_side(state, target_id) == _fighter_side(state, actor_key)
                    or target_id == actor_key
                    or target.hp <= 0
                ):
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
                        actor_key=actor_key,
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


def _deal_damage(
    target: Fighter,
    amount: Decimal | int,
    *,
    absorbed_sources: list[str] | None = None,
) -> tuple[Decimal, Decimal]:
    incoming = max(D(0), D(amount))
    absorbed = D(0)
    remaining = incoming
    layers: list[BarrierLayer] = []
    depleted: list[BarrierLayer] = []
    # FIFO by source application order is deterministic; refreshes replace in
    # place. No canonical source-order rule exists, so this is a stable engine
    # policy that preserves the legacy single-layer behavior.
    for layer in target.barrier_layers:
        if layer.value <= ZERO or layer.remaining == 0:
            depleted.append(layer)
            continue
        if remaining <= ZERO:
            layers.append(layer)
            continue
        consumed = min(layer.value, remaining)
        if consumed > ZERO and absorbed_sources is not None and layer.source_label:
            if layer.source_label not in absorbed_sources:
                absorbed_sources.append(layer.source_label)
        remaining -= consumed
        absorbed += consumed
        layer_remaining = layer.value - consumed
        if layer_remaining > ZERO:
            layers.append(replace(layer, value=layer_remaining))
        else:
            depleted.append(layer)
    target.barrier_layers[:] = layers
    target._remove_barrier_linked_effects(tuple(depleted))
    hp_damage = min(max(D(0), target.hp), remaining)
    target.hp = max(D(0), target.hp - hp_damage)
    return hp_damage, absorbed


def _remove_barrier_bound_effects(
    state: Combat,
    fighter: Fighter,
    source: BarrierLayer | str,
) -> None:
    if isinstance(source, BarrierLayer):
        linked = set(source.bound_effect_ids)
        action_id = source.effect_definition_id
        if action_id is None and source.source_label:
            action_id = source.source_label.rsplit(":", 1)[-1]
    else:
        if not source:
            return
        linked = set()
        action_id = source.rsplit(":", 1)[-1]
    action = state.enemy_actions.get(action_id or "") or state.player_actions.get(
        action_id or ""
    )
    if action is not None:
        linked.update(action.barrier_bound_effect_ids)
    retained = {
        effect_id
        for layer in fighter._active_barrier_layers()
        for effect_id in layer.bound_effect_ids
    }
    linked -= retained
    if linked:
        fighter.effects = [effect for effect in fighter.effects if effect.id not in linked]


def _advance_barrier_sources(fighter: Fighter) -> tuple[BarrierLayer, ...]:
    active: list[BarrierLayer] = []
    expired: list[BarrierLayer] = []
    for layer in fighter.barrier_layers:
        if layer.value <= ZERO or layer.remaining == 0:
            expired.append(layer)
        elif layer.remaining > 0 and fighter.opportunity > layer.applied_opportunity:
            remaining = layer.remaining - 1
            if remaining == 0:
                expired.append(layer)
            else:
                active.append(replace(layer, remaining=remaining))
        else:
            active.append(layer)
    fighter.barrier_layers[:] = active
    fighter._remove_barrier_linked_effects(tuple(expired))
    return tuple(expired)


def _deal_combat_damage(
    state: Combat,
    target_key: str,
    amount: Decimal | int,
    *,
    source_key: str | None = None,
    absorbed_sources: list[str] | None = None,
) -> tuple[Decimal, Decimal]:
    target = state.fighters[target_key]
    hp_before = target.hp
    layers_before = tuple(target.barrier_layers)
    actual_damage, barrier_absorbed = _deal_damage(
        target, amount, absorbed_sources=absorbed_sources
    )
    remaining_identities = {
        (layer.legacy, layer.applier_id, layer.effect_definition_id, layer.source_label)
        for layer in target.barrier_layers
    }
    for layer in layers_before:
        identity = (
            layer.legacy,
            layer.applier_id,
            layer.effect_definition_id,
            layer.source_label,
        )
        if identity not in remaining_identities:
            _remove_barrier_bound_effects(state, target, layer)
    threshold = target.stats.hp * D("0.50")
    if hp_before > threshold and target.hp <= threshold:
        _grant_vigilia_retaliation(state, target_key, source_key)
    if hp_before > ZERO and target.hp <= ZERO:
        _clear_class_mechanics_for_death(state, target_key)
    return actual_damage, barrier_absorbed


def _begin_turn(state: Combat) -> None:
    if state.result or not state.order:
        return
    actor_key = state.order[state.turn_index]
    actor = state.fighters[actor_key]
    actor.opportunity += 1
    actor.defending = False
    guard_integrity = actor.path_state.get("guard_integrity_debuff")
    if (
        isinstance(guard_integrity, dict)
        and actor.opportunity >= int(guard_integrity.get("expires_opportunity", 0))
    ):
        actor.path_state.pop("guard_integrity_debuff", None)
    for fighter_key, fighter in state.fighters.items():
        if fighter.hp > ZERO and fighter.hp <= fighter.stats.hp * D("0.50"):
            _grant_vigilia_retaliation(state, fighter_key)
    if _is_player_turn_actor(state, actor_key) and state.prepared_action is not None:
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


def _has_talent(actor: Fighter, slug: str) -> bool:
    return f"talent.{actor.character_class}.{slug}" in actor.talent_ids


def _apply_class_mechanic_buff(
    actor: Fighter,
    *,
    mechanic: str,
    stat: str,
    magnitude: Decimal,
    duration: int = 1,
    effect_id: str | None = None,
) -> None:
    resolved_effect_id = effect_id or f"class_mechanic.{mechanic}.{stat}"
    existing = next(
        (effect for effect in actor.effects if effect.id == resolved_effect_id), None
    )
    if existing is None:
        actor.effects.append(
            Effect(
                resolved_effect_id,
                stat,
                magnitude,
                duration,
                actor.opportunity,
                kind="buff",
            )
        )
        return
    existing.magnitude = magnitude
    existing.remaining = duration
    existing.applied_opportunity = actor.opportunity


def _retaliation_duration(actor: Fighter) -> int:
    talent_bonus = 1 if _has_talent(actor, "retaliacao_persistente") else 0
    return max(1, 1 + max(0, actor.retaliation_duration_bonus, talent_bonus))


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
    if target.character_class != "sentinela" or target.hp <= ZERO:
        return
    duration = _retaliation_duration(target)
    if _retaliation_active(target):
        target.retaliation_charges = 1
        target.retaliation_remaining = duration
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
    if _has_talent(target, "ritmo_de_guarda"):
        _apply_class_mechanic_buff(
            target,
            mechanic="sentinela.ritmo_de_guarda",
            stat="agility",
            magnitude=D("0.05"),
            effect_id="talent.sentinela.ritmo_de_guarda.agility",
        )
    if source_type == "defender" and target.selected_path == "bastiao":
        source = "path.bastiao.fortaleza"
        if not (
            any(
                not layer.legacy
                and layer.identity == (target.id, source)
                for layer in target._active_barrier_layers()
            )
        ):
            value = (target.stats.hp * D("0.04") * D("1.10")).to_integral_value(
                rounding=ROUND_FLOOR
            )
            if value > ZERO:
                value = _apply_barrier(
                    target,
                    applier_id=target.id,
                    effect_definition_id=source,
                    value=value,
                    duration=1,
                    applied_opportunity=target.opportunity,
                    round_number=state.round,
                    source_label=source,
                )
                if value > ZERO:
                    state.mechanic_events.append(
                        CombatEvent(
                            len(state.mechanic_events),
                            state.round,
                            target_key,
                            "path.bastiao.fortaleza",
                            target.id,
                            actor_entity_id=target.id,
                            barrier_value=value,
                            barrier_total_after=target.barrier,
                            barrier_duration=1,
                            barrier_applied_source=f"{target.id}:{source}",
                            path_triggers=("bastiao.fortaleza",),
                            internal=True,
                        )
                    )


def _grant_defender_retaliation(
    state: Combat,
    *,
    target_key: str,
    source_actor: Fighter,
    source_event_id: str,
) -> None:
    target = state.fighters[target_key]
    if target.hp <= ZERO or target.character_class != "sentinela":
        return
    _grant_retaliation(
        state,
        target_key=target_key,
        source_actor=source_actor,
        source_event_id=source_event_id,
    )
    if _has_talent(target, "guarda_preparada"):
        target.path_state["guard_prepared_barrier"] = {
            "remaining": 2,
            "applied_opportunity": target.opportunity,
        }
    if _has_talent(target, "guarda_integra"):
        target.path_state["guard_integrity_debuff"] = {
            "expires_opportunity": target.opportunity + 1,
        }


def _grant_vigilia_retaliation(
    state: Combat,
    target_key: str,
    source_key: str | None = None,
) -> None:
    target = state.fighters[target_key]
    if (
        target.hp <= ZERO
        or target.character_class != "sentinela"
        or target.hp > target.stats.hp * D("0.50")
        or not _has_talent(target, "vigilia")
        or target.path_state.get("vigilia_retaliation_triggered")
    ):
        return
    target.path_state["vigilia_retaliation_triggered"] = True
    source = state.fighters.get(source_key or "", target)
    _grant_retaliation(
        state,
        target_key=target_key,
        source_actor=source,
        source_event_id=f"{state.id.hex}:{state.version}:{len(state.events)}:vigilia",
        source_type="vigilia",
    )


def _consume_retaliation(
    state: Combat,
    actor_key: str,
    actor: Fighter,
    action_id: str,
    action: Action,
    target_keys: tuple[str, ...],
) -> dict[str, str | bool | int]:
    targets_enemy = any(
        _fighter_side(state, target_key) != _fighter_side(state, actor_key)
        for target_key in target_keys
    )
    eligible = targets_enemy and (
        action_id == "attack"
        or (_is_art_action(action_id, action) and action.coefficient > ZERO)
    )
    if (
        actor.character_class != "sentinela"
        or not _retaliation_active(actor)
        or not eligible
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
    if _has_talent(actor, "contrapeso"):
        _apply_class_mechanic_buff(
            actor,
            mechanic="sentinela.contrapeso",
            stat="defense",
            magnitude=D("0.04"),
        )
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
        aura_reduction = (
            _damage_aura_reduction(state, actor_key) if actor_key is not None else ZERO
        )
        if aura_reduction > ZERO and damage > 0:
            damage = int(
                (D(damage) * (D(1) - aura_reduction)).to_integral_value(
                    rounding=ROUND_FLOOR
                )
            )
        barrier_absorbed_sources: list[str] = []
        actual_damage, barrier_absorbed = _deal_combat_damage(
            state,
            actor_key,
            damage,
            source_key=source_key,
            absorbed_sources=barrier_absorbed_sources,
        )
        if actual_damage > ZERO:
            _resolve_phase_triggers(state)
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
                barrier_total_after=actor.barrier,
                barrier_absorbed_sources=tuple(barrier_absorbed_sources),
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
    sangue_frio = actor.path_state.get("errante_sangue_frio_crit")
    expires_opportunity = (
        sangue_frio.get("expires_opportunity")
        if isinstance(sangue_frio, dict)
        else None
    )
    if (
        isinstance(expires_opportunity, int)
        and not isinstance(expires_opportunity, bool)
        and actor.opportunity > expires_opportunity
    ):
        actor.path_state.pop("errante_sangue_frio_crit", None)
    expired_barriers = _advance_barrier_sources(actor)
    for layer in expired_barriers:
        _remove_barrier_bound_effects(state, actor, layer)
        state.mechanic_events.append(
            CombatEvent(
                len(state.mechanic_events),
                state.round,
                layer.applier_id or layer.source_label,
                "barrier.expired",
                actor.id,
                barrier_value=layer.value,
                barrier_total_after=actor.barrier,
                barrier_applied_source=layer.source_label,
                internal=True,
            )
        )
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
    if (
        action.self_barrier_coefficient > ZERO
        or action.self_barrier_hp_fraction > ZERO
        or action.target_barrier_coefficient > ZERO
    ):
        return "barrier"
    return ""


def _is_art_action(action_id: str, action: Action) -> bool:
    return action_id == "art" or action.id.startswith(("class_art.", "path_art."))


def _has_valid_negative_effect(state: Combat, target: Fighter) -> bool:
    return any(
        effect.kind == "debuff"
        and not effect.fixed_mechanic
        and effect.remaining > 0
        and effect.stacks > 0
        for effect in target.effects
    ) or any(
        not dot.fixed_mechanic
        and dot.remaining > 0
        and dot.stacks > 0
        for dot in state.dot_states.get(target.id, ())
    )


def _has_valid_defense_reduction(target: Fighter) -> bool:
    """Whether the action-start target snapshot contains a live −DEF debuff."""
    return any(
        effect.kind == "debuff"
        and not effect.fixed_mechanic
        and effect.stat == "defense"
        and effect.magnitude > ZERO
        and effect.remaining > 0
        and effect.stacks > 0
        for effect in target.effects
    )


def _aim_entry(target: Fighter, source: Fighter) -> dict | None:
    entries = target.path_state.get("aim_from", {})
    if not isinstance(entries, dict):
        return None
    entry = entries.get(source.id)
    if (
        source.hp <= ZERO
        or target.hp <= ZERO
        or not isinstance(entry, dict)
        or int(entry.get("remaining", 0)) <= 0
    ):
        return None
    return entry


def _remove_aim_entry(target: Fighter, source_id: str) -> None:
    entries = target.path_state.get("aim_from")
    if not isinstance(entries, dict):
        return
    entries.pop(source_id, None)
    if not entries:
        target.path_state.pop("aim_from", None)


def _consume_aim_stacks(target: Fighter, source: Fighter, count: int) -> int:
    entry = _aim_entry(target, source)
    if entry is None or count <= 0:
        return 0
    consumed = min(int(entry.get("stacks", 0)), count)
    entry["stacks"] = max(0, int(entry.get("stacks", 0)) - consumed)
    if entry["stacks"] == 0:
        _remove_aim_entry(target, source.id)
    return consumed


def _grant_aim(
    state: Combat,
    source_key: str,
    target_key: str,
    *,
    trigger: str,
) -> int:
    source = state.fighters[source_key]
    target = state.fighters[target_key]
    if (
        source.hp <= ZERO
        or target.hp <= ZERO
        or source.character_class != "vigia"
        or _fighter_side(state, source_key) == _fighter_side(state, target_key)
    ):
        return 0
    specialization = source.selected_path if source.character_class == "vigia" else None
    maximum = 4 if specialization == "atirador" else 2 if specialization == "rastreador" else 3
    current_entry = _aim_entry(target, source)
    if specialization == "rastreador":
        current_targets = [
            fighter
            for fighter in state.fighters.values()
            if _aim_entry(fighter, source) is not None
        ]
        if current_entry is None and len(current_targets) >= 3:
            return 0
    entries = target.path_state.setdefault("aim_from", {})
    stacks = min(maximum, int(current_entry.get("stacks", 0)) + 1) if current_entry else 1
    entries[source.id] = {
        "stacks": stacks,
        "remaining": 3 if _has_talent(source, "mira_estavel") else 2,
        "applied_opportunity": source.opportunity,
        "trigger": trigger,
    }
    return stacks


def _switch_aim_target(
    state: Combat, source_key: str, primary_target_id: str | None
) -> None:
    source = state.fighters[source_key]
    if (
        source.character_class != "vigia"
        or source.selected_path == "rastreador"
        or primary_target_id is None
    ):
        return
    previous_target_id = source.path_state.get("aim_current_target_id")
    for other in state.fighters.values():
        if other.id == primary_target_id:
            continue
        entry = _aim_entry(other, source)
        if entry is None:
            _remove_aim_entry(other, source.id)
            continue
        if (
            _has_talent(source, "visao_persistente")
            and other.id == previous_target_id
        ):
            other.path_state.setdefault("aim_from", {})[source.id] = {
                "stacks": 1,
                "remaining": 1,
                "applied_opportunity": source.opportunity,
                "trigger": "visao_persistente",
            }
        else:
            _remove_aim_entry(other, source.id)
    source.path_state["aim_current_target_id"] = primary_target_id


def _tick_path_resources(state: Combat, actor_key: str) -> None:
    actor = state.fighters[actor_key]
    state_data = actor.path_state
    for key in (
        "luminar_state",
        "trama_state",
        "guard_prepared_barrier",
        "trama_next_per",
        "aim_next_per",
        "manifestation_state",
        "devastador_charge",
    ):
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
            renewal_talent = {
                "luminar_state": "ciclo_luminoso",
                "trama_state": "fio_persistente",
            }.get(key)
            renewal_flag = {
                "luminar_state": "luminar_cycle_used",
                "trama_state": "trama_expiry_renewed",
            }.get(key)
            if (
                renewal_talent
                and renewal_flag
                and _has_talent(actor, renewal_talent)
                and not state_data.get(renewal_flag)
            ):
                state_data[renewal_flag] = True
                entry["remaining"] = 1
                entry["applied_opportunity"] = actor.opportunity
            else:
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
                target = next(
                    (fighter for fighter in state.fighters.values() if fighter.id == target_id),
                    None,
                )
                if (
                    target is not None
                    and _has_talent(actor, "pressagio_flexivel")
                    and not state_data.get("omen_flexible_used")
                ):
                    state_data["omen_flexible_used"] = True
                    entry["remaining"] = 1
                    entry["applied_opportunity"] = actor.opportunity
                else:
                    entries.pop(target_id, None)
    for target in state.fighters.values():
        incoming = target.path_state.get("aim_from")
        if not isinstance(incoming, dict):
            continue
        entry = incoming.get(actor.id)
        if not isinstance(entry, dict):
            continue
        if actor.hp <= ZERO or target.hp <= ZERO:
            incoming.pop(actor.id, None)
            continue
        applied = int(entry.get("applied_opportunity", actor.opportunity))
        if actor.opportunity > applied:
            entry["remaining"] = max(0, int(entry.get("remaining", 0)) - 1)
            entry["applied_opportunity"] = actor.opportunity
        if int(entry.get("remaining", 0)) <= 0:
            incoming.pop(actor.id, None)
        if not incoming:
            target.path_state.pop("aim_from", None)


def _new_omen(actor: Fighter, kind: str, target: Fighter) -> None:
    if target.hp <= ZERO:
        return
    key = "omen_offensive" if kind == "offensive" else "omen_defensive"
    actor.path_state.setdefault(key, {})[target.id] = {
        "remaining": 3 if _has_talent(actor, "sinal_persistente") else 2,
        "applied_opportunity": actor.opportunity,
    }


def _is_named_art(action_id: str, action: Action, slug: str) -> bool:
    return any(
        value.casefold().endswith(slug)
        for value in (action_id, action.id)
        if value
    )


def _primary_target_key(
    state: Combat,
    actor_id: str,
    action: Action,
    target_keys: tuple[str, ...],
    requested_target: str | None,
) -> str | None:
    if action.target_mode in {"all_opponents", "all_allies"}:
        requested_key = _resolve_fighter_key(state, requested_target)
        return requested_key if requested_key in target_keys else None
    return target_keys[0] if target_keys else actor_id if action.target_mode == "self" else None


def _action_has_barrier(action: Action) -> bool:
    return bool(
        action.self_barrier_coefficient > ZERO
        or action.self_barrier_hp_fraction > ZERO
        or action.target_barrier_coefficient > ZERO
    )


def _action_has_support(action: Action) -> bool:
    return action.heal_coefficient > ZERO or _action_has_barrier(action)


def _class_resource_count(
    state: Combat,
    actor_key: str,
    target_key: str | None,
    resource: str,
    *,
    state_kind: str | None = None,
    action_id: str = "",
    action: Action | None = None,
) -> int:
    """Read one class machine without converting it into a removable Effect."""
    actor = state.fighters[actor_key]
    if resource == "retaliation":
        return int(actor.retaliation_charges > 0 and actor.retaliation_remaining > 0)
    if resource == "trama":
        entry = actor.path_state.get("trama_state")
        eligible_art = bool(
            action is not None
            and _is_art_action(action_id, action)
            and (action.coefficient > ZERO or _action_has_support(action))
            and isinstance(entry, dict)
            and entry.get("origin_art") != action.id
        )
        return int(
            actor.character_class == "tecelao"
            and eligible_art
            and int(entry.get("remaining", 0)) > 0
        )
    if resource == "luminar_state":
        entry = actor.path_state.get("luminar_state")
        return int(
            actor.character_class == "luminar"
            and isinstance(entry, dict)
            and int(entry.get("remaining", 0)) > 0
            and (state_kind is None or entry.get("kind") == state_kind)
        )
    if target_key is None:
        return 0
    target = state.fighters[target_key]
    if resource == "aim":
        entry = _aim_entry(target, actor) if actor.character_class == "vigia" else None
        return int(entry.get("stacks", 0)) if entry is not None else 0
    if resource in {"omen_offensive", "omen_defensive"}:
        eligible_action = bool(
            action is not None
            and _is_art_action(action_id, action)
            and (
                resource == "omen_offensive"
                and action.coefficient > ZERO
                and _fighter_side(state, actor_key) != _fighter_side(state, target_key)
                or resource == "omen_defensive"
                and _action_has_support(action)
                and _fighter_side(state, actor_key) == _fighter_side(state, target_key)
            )
        )
        if not eligible_action:
            return 0
        entries = actor.path_state.get(resource, {})
        entry = entries.get(target.id) if isinstance(entries, dict) else None
        return int(
            actor.character_class == "oraculo"
            and isinstance(entry, dict)
            and int(entry.get("remaining", 0)) > 0
        )
    return 0


def _resource_selector_targets(
    state: Combat,
    actor_key: str,
    target_keys: tuple[str, ...],
    primary_target_key: str | None,
    selector: str,
) -> tuple[str, ...]:
    if selector == "actor":
        return (actor_key,)
    if selector == "primary_target":
        return (primary_target_key,) if primary_target_key is not None else ()
    return target_keys


def _snapshot_action_resource_uses(
    state: Combat,
    actor_key: str,
    action_id: str,
    action: Action,
    target_keys: tuple[str, ...],
    requested_target_id: str | None,
) -> tuple[dict, ...] | None:
    if not action.resource_uses:
        return ()
    primary_target_key = _primary_target_key(
        state, actor_key, action, target_keys, requested_target_id
    )
    plans: list[dict] = []
    for index, use in enumerate(action.resource_uses):
        selected_keys = _resource_selector_targets(
            state,
            actor_key,
            target_keys,
            primary_target_key,
            use.target_selector,
        )
        if not selected_keys:
            if use.required:
                return None
            continue
        snapshots = tuple(
            (
                key,
                state.fighters[key].id,
                _class_resource_count(
                    state,
                    actor_key,
                    key if key != actor_key else None,
                    use.resource,
                    state_kind=use.state_kind,
                    action_id=action_id,
                    action=action,
                ),
            )
            for key in selected_keys
        )
        if use.resource == "retaliation" and use.consume and use.consume_at == "commit":
            eligible_retaliation_action = bool(
                action_id == "attack"
                or _is_art_action(action_id, action) and action.coefficient > ZERO
            ) and any(
                _fighter_side(state, actor_key) != _fighter_side(state, target_key)
                for target_key in target_keys
            )
            if not eligible_retaliation_action:
                if use.required:
                    return None
                continue
        threshold = max(use.minimum, use.consume)
        eligible = tuple(row for row in snapshots if row[2] >= threshold)
        if use.required and len(eligible) != len(snapshots):
            return None
        if use.consume and eligible:
            if use.consumption_scope == "per_action":
                eligible = eligible[:1]
            plans.append(
                {
                    "index": index,
                    "use": use,
                    "targets": eligible,
                    "action_id": action_id,
                }
            )
    return tuple(plans)


def _action_condition_matches(
    state: Combat,
    actor_key: str,
    target_key: str | None,
    condition: ActionCondition,
    *,
    action_id: str,
    action: Action,
) -> bool:
    actor = state.fighters[actor_key]
    if condition.kind == "actor_hp_fraction_below":
        return actor.stats.hp > ZERO and actor.hp < actor.stats.hp * condition.threshold
    if condition.kind == "target_hp_fraction_at_most":
        if target_key is None:
            return False
        target = state.fighters[target_key]
        return target.stats.hp > ZERO and target.hp <= target.stats.hp * condition.threshold
    if condition.kind == "target_has_normal_negative_effect":
        return target_key is not None and _has_valid_negative_effect(
            state, state.fighters[target_key]
        )
    if condition.kind == "class_resource_at_least" and condition.resource is not None:
        count = _class_resource_count(
            state,
            actor_key,
            target_key,
            condition.resource,
            state_kind=condition.state_kind,
            action_id=action_id,
            action=action,
        )
        return count >= condition.minimum
    return False


def _apply_declared_conditional_modifiers(
    state: Combat,
    actor_key: str,
    action_id: str,
    action: Action,
    target_keys: tuple[str, ...],
    primary_target_key: str | None,
    context: dict,
) -> None:
    condition_snapshot = context.get("condition_snapshot", {})
    for modifier_index, modifier in enumerate(action.conditional_modifiers):
        selected_keys = (
            (primary_target_key,)
            if modifier.target_scope == "primary_target"
            and primary_target_key is not None
            else target_keys
            if modifier.target_scope == "per_target"
            else ()
        )
        for target_key in selected_keys:
            target = state.fighters[target_key]
            entry = context["by_target"].get(target.id)
            condition_target_key = (
                primary_target_key
                if modifier.evaluation_scope == "per_action"
                else target_key
            )
            condition_target_id = (
                state.fighters[condition_target_key].id
                if condition_target_key is not None
                else "__action__"
            )
            if entry is None or not condition_snapshot.get(
                (modifier_index, condition_target_id), False
            ):
                continue
            component = modifier.component
            if component in {"damage_power", "healing_power", "barrier_power"}:
                if modifier.operation == "multiply":
                    entry[component] *= D(1) + modifier.magnitude
                else:
                    entry[component] += modifier.magnitude
            elif component == "final_damage_bonus":
                entry[component] += modifier.magnitude
            elif component == "precision_bonus":
                entry["per_bonus"] += modifier.magnitude
            elif component == "crit_bonus":
                entry[component] += modifier.magnitude
            entry["triggers"].append(modifier.id)


def _guard_integrity_can_reduce(target: Fighter, effect: ActionEffect | Effect) -> bool:
    token = target.path_state.get("guard_integrity_debuff")
    return bool(
        target.character_class == "sentinela"
        and isinstance(token, dict)
        and target.opportunity < int(token.get("expires_opportunity", 0))
        and effect.kind == "debuff"
        and effect.magnitude > ZERO
        and (hasattr(target.stats, effect.stat) or effect.stat == "healing_received")
        and getattr(effect, "removable", True)
        and not getattr(effect, "unremovable", False)
        and not getattr(effect, "protected", False)
        and not getattr(effect, "fixed_mechanic", False)
        and not getattr(effect, "hard_cc", False)
    )


def _trama_component_bonus(actor: Fighter, component: str) -> Decimal:
    if actor.selected_path == "conjurador":
        return D("0.15") if component == "damage" else D("0.06")
    if actor.selected_path == "runico":
        return D("0.06") if component == "damage" else D("0.15")
    return D("0.10")


def _prepare_path_action(
    state: Combat,
    actor_id: str,
    action_id: str,
    action: Action,
    target_keys: tuple[str, ...],
    requested_target: str | None = None,
    resource_uses: tuple[dict, ...] = (),
) -> dict:
    actor = state.fighters[actor_id]
    is_art = _is_art_action(action_id, action)
    direct = action.coefficient > ZERO
    support = _action_has_support(action)
    primary_key = _primary_target_key(
        state, actor_id, action, target_keys, requested_target
    )
    primary_target = state.fighters.get(primary_key) if primary_key else None
    condition_snapshot: dict[tuple[int, str], bool] = {}
    for modifier_index, modifier in enumerate(action.conditional_modifiers):
        condition_targets = (
            (primary_key,)
            if modifier.evaluation_scope == "per_action"
            else target_keys
        )
        if not condition_targets and modifier.evaluation_scope == "per_action":
            condition_snapshot[(modifier_index, "__action__")] = (
                _action_condition_matches(
                    state,
                    actor_id,
                    None,
                    modifier.condition,
                    action_id=action_id,
                    action=action,
                )
            )
        for condition_target_key in condition_targets:
            if condition_target_key is None:
                continue
            condition_target = state.fighters[condition_target_key]
            condition_snapshot[(modifier_index, condition_target.id)] = (
                _action_condition_matches(
                    state,
                    actor_id,
                    condition_target_key,
                    modifier.condition,
                    action_id=action_id,
                    action=action,
                )
            )
    context = {
        "by_target": {},
        "target_ids": {state.fighters[key].id for key in target_keys},
        "primary_target_id": primary_target.id if primary_target else None,
        "primary_target_key": primary_key,
        "luminar_consumed": False,
        "trama_consumed": False,
        "class_resources_committed": False,
        "omen_consumptions": [],
        "generated_triggers": [],
        "oportunism_triggered": False,
        "resource_uses": resource_uses,
        "condition_snapshot": condition_snapshot,
        "resource_changes": [],
        "automatic_resource_changes": [],
        "target_keys": target_keys,
        "action_instance_id": "",
        "next_direct_crit_bonus": ZERO,
        "next_direct_crit_effect_ids": (),
        "next_direct_crit_consumed": False,
        "next_direct_crit_committed": False,
        "errante_negative_effect_applied": False,
    }

    if direct:
        prepared_bonus = ZERO
        prepared_effect_ids: list[str] = []
        if (
            actor.next_direct_crit_expires_opportunity is not None
            and actor.opportunity <= actor.next_direct_crit_expires_opportunity
        ):
            prepared_bonus += actor.next_direct_crit_bonus
            if actor.next_direct_crit_effect_id:
                prepared_effect_ids.append(actor.next_direct_crit_effect_id)
        sangue_frio = actor.path_state.get("errante_sangue_frio_crit")
        expires_opportunity = (
            sangue_frio.get("expires_opportunity")
            if isinstance(sangue_frio, dict)
            else None
        )
        if (
            actor.character_class == "errante"
            and _has_talent(actor, "sangue_frio")
            and isinstance(expires_opportunity, int)
            and not isinstance(expires_opportunity, bool)
            and actor.opportunity <= expires_opportunity
        ):
            prepared_bonus += D(5)
            prepared_effect_ids.append("errante.sangue_frio.crit")
            context["sangue_frio_source_action_instance_id"] = str(
                sangue_frio.get("source_action_instance_id", "")
            )
            context["sangue_frio_applied_opportunity"] = sangue_frio.get(
                "applied_opportunity"
            )
        context["next_direct_crit_bonus"] = prepared_bonus
        context["next_direct_crit_effect_ids"] = tuple(sorted(set(prepared_effect_ids)))
        context["next_direct_crit_consumed"] = bool(prepared_effect_ids)

    for target_key in target_keys:
        target = state.fighters[target_key]
        aim = _aim_entry(target, actor) if actor.character_class == "vigia" else None
        stacks = int(aim.get("stacks", 0)) if aim is not None else 0
        entry = {
            "damage_power": D(1),
            "healing_power": D(1),
            "barrier_power": D(1),
            # AoE primary results use action-start target state. Keep source-
            # counted auras and DEF stable if an earlier target is defeated.
            "pre_event_defense": _fighter_stat(state, target_key, "defense"),
            "pre_event_damage_aura_reduction": _damage_aura_reduction(
                state, target_key
            ),
            "final_damage_bonus": D(0),
            "per_bonus": D(3) * stacks if actor.selected_path == "atirador" else ZERO,
            "crit_bonus": D(6) if actor.selected_path == "atirador" and stacks >= 4 else ZERO,
            "aim_stacks": stacks,
            "triggers": [],
            "oportunism": (
                actor.character_class == "errante"
                and direct
                and _fighter_side(state, actor_id) != _fighter_side(state, target_key)
                and _has_valid_negative_effect(state, target)
            ),
        }
        if (
            actor.character_class == "sentinela"
            and direct
            and _has_talent(actor, "pressao_de_fissuras")
            and _has_valid_defense_reduction(target)
        ):
            # §49.5 grants a direct-damage power increase against the target's
            # action-start −DEF state. It belongs in the damage component power
            # stage, before the shared DEF/PER/Crit/mitigation calculation.
            entry["damage_power"] *= D("1.03")
            entry["triggers"].append("sentinela.pressao_de_fissuras")
        if entry["oportunism"]:
            entry["final_damage_bonus"] += (
                D("0.10") if _has_talent(actor, "oportunismo_ampliado") else D("0.08")
            )
            entry["triggers"].append("oportunismo")
            context["oportunism_triggered"] = True
            if _has_talent(actor, "brecha_exposta"):
                entry["per_bonus"] += D(4)
        if actor.character_class == "vigia":
            if stacks >= 2 and _has_talent(actor, "alvo_exposto"):
                entry["final_damage_bonus"] += D("0.03")
                entry["triggers"].append("vigia.alvo_exposto")
            if stacks >= 3 and _has_talent(actor, "ponto_fraco"):
                entry["crit_bonus"] += D(2)
                entry["triggers"].append("vigia.ponto_fraco")
        if direct:
            for key, slug in (("trama_next_per", "tecelao"), ("aim_next_per", "vigia")):
                next_bonus = actor.path_state.get(key)
                if (
                    actor.character_class == slug
                    and isinstance(next_bonus, dict)
                    and int(next_bonus.get("remaining", 0)) > 0
                ):
                    entry["per_bonus"] += D(next_bonus.get("magnitude", 3))
                    entry["triggers"].append(f"{slug}.proximo_dano_consumido")

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
            if direct and _fighter_side(state, actor_id) != _fighter_side(state, target_key):
                omen = actor.path_state.get("omen_offensive", {}).get(target.id)
                if isinstance(omen, dict) and int(omen.get("remaining", 0)) > 0:
                    entry["damage_power"] *= (
                        D("1.16")
                        if actor.selected_path == "agoureiro"
                        else D("1.12")
                    )
                    if _has_talent(actor, "profecia_dolorosa"):
                        entry["damage_power"] *= D("1.02")
                    if _has_talent(actor, "pressagio_cortante"):
                        entry["per_bonus"] += D(2)
                    if _has_talent(actor, "sinais_convergentes"):
                        entry["crit_bonus"] += D(2)
                    entry["triggers"].append("pressagio.ofensivo_consumido")
                    context["omen_consumptions"].append(("offensive", target.id))
            if support and _fighter_side(state, actor_id) == _fighter_side(state, target_key):
                omen = actor.path_state.get("omen_defensive", {}).get(target.id)
                if isinstance(omen, dict) and int(omen.get("remaining", 0)) > 0:
                    multiplier = D("1.12")
                    if _has_talent(actor, "sinais_convergentes"):
                        multiplier *= D("1.03")
                    entry["healing_power"] *= multiplier
                    entry["barrier_power"] *= multiplier
                    entry["triggers"].append("pressagio.defensivo_consumido")
                    context["omen_consumptions"].append(("defensive", target.id))

        if actor.character_class == "luminar" and is_art and support:
            if (
                action.heal_coefficient > ZERO
                and target.stats.hp > ZERO
                and target.hp <= target.stats.hp * D("0.40")
                and _has_talent(actor, "cura_prudente")
            ):
                entry["healing_power"] *= D("1.05")
                entry["triggers"].append("luminar.cura_prudente")
            if _action_has_barrier(action) and _has_talent(actor, "egide_densa"):
                entry["barrier_power"] *= D("1.04")
                entry["triggers"].append("luminar.egide_densa")

        guard_barrier = actor.path_state.get("guard_prepared_barrier")
        if support and _action_has_barrier(action) and isinstance(guard_barrier, dict):
            if int(guard_barrier.get("remaining", 0)) > 0:
                entry["barrier_power"] *= D("1.06")
                entry["triggers"].append("sentinela.guarda_preparada")
                context["guard_prepared_consumed"] = True

        context["by_target"][target.id] = entry

    if actor.character_class == "luminar" and is_art:
        state_entry = actor.path_state.get("luminar_state")
        expected_kind = (
            "fulgor"
            if support and not direct
            else "julgamento"
            if direct and not support
            else None
        )
        if (
            isinstance(state_entry, dict)
            and expected_kind is not None
            and state_entry.get("kind") == expected_kind
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
            if expected_kind == "fulgor" and _has_talent(actor, "contraluz_perfeita"):
                multiplier += D("0.02")
            for entry in context["by_target"].values():
                if expected_kind == "julgamento":
                    entry["damage_power"] *= multiplier
                    if _has_talent(actor, "julgamento_preciso"):
                        entry["crit_bonus"] += D(2)
                    if _has_talent(actor, "veredito_ardente"):
                        entry["damage_power"] *= D("1.02")
                    if _has_talent(actor, "contraluz_perfeita"):
                        entry["per_bonus"] += D(2)
                else:
                    entry["healing_power"] *= multiplier
                    entry["barrier_power"] *= multiplier
                entry["triggers"].append(f"luminar.{expected_kind}_consumido")
            context["luminar_consumed"] = True
            context["luminar_consumed_kind"] = expected_kind

    trama_state = actor.path_state.get("trama_state")
    trial_chain = (
        action.prepares_chain == "trama_encadeada"
        or action.consumes_chain == "trama_encadeada"
    )
    if (
        actor.character_class == "tecelao"
        and is_art
        and (direct or support)
        and not trial_chain
        and isinstance(trama_state, dict)
        and int(trama_state.get("remaining", 0)) > 0
        and trama_state.get("origin_art") != action.id
    ):
        context["trama_consumed"] = True
        context["trama_consumed_origin"] = str(trama_state.get("origin_art", ""))
        for entry in context["by_target"].values():
            if direct:
                bonus = _trama_component_bonus(actor, "damage")
                if _has_talent(actor, "trama_agressiva"):
                    bonus += D("0.02")
                if _has_talent(actor, "sobrecarga_controlada"):
                    target_id = next(
                        target_id
                        for target_id, target_context in context["by_target"].items()
                        if target_context is entry
                    )
                    target = next(
                        fighter
                        for fighter in state.fighters.values()
                        if fighter.id == target_id
                    )
                    if target.stats.hp > ZERO and target.hp <= target.stats.hp * D("0.40"):
                        bonus += D("0.04")
                entry["damage_power"] *= D(1) + bonus
                if _has_talent(actor, "trama_precisa"):
                    entry["crit_bonus"] += D(2)
                entry["triggers"].append("tecelao.trama_dano_consumida")
            if action.heal_coefficient > ZERO:
                bonus = _trama_component_bonus(actor, "healing")
                if _has_talent(actor, "trama_precisa"):
                    bonus += D("0.02")
                entry["healing_power"] *= D(1) + bonus
                entry["triggers"].append("tecelao.trama_cura_consumida")
            if _action_has_barrier(action):
                bonus = _trama_component_bonus(actor, "barrier")
                if _has_talent(actor, "trama_precisa"):
                    bonus += D("0.02")
                entry["barrier_power"] *= D(1) + bonus
                entry["triggers"].append("tecelao.trama_barreira_consumida")

    if actor.character_class == "tecelao" and direct and not context["trama_consumed"]:
        trama_next_per = actor.path_state.get("trama_next_per")
        if isinstance(trama_next_per, dict) and int(trama_next_per.get("remaining", 0)) > 0:
            context["trama_next_per_consumed"] = True
    if actor.character_class == "vigia" and direct:
        aim_next_per = actor.path_state.get("aim_next_per")
        if isinstance(aim_next_per, dict) and int(aim_next_per.get("remaining", 0)) > 0:
            context["aim_next_per_consumed"] = True

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
    _apply_declared_conditional_modifiers(
        state,
        actor_id,
        action_id,
        action,
        target_keys,
        primary_key,
        context,
    )
    return context


def _commit_path_action(
    state: Combat,
    actor_id: str,
    action_id: str,
    action: Action,
    context: dict,
) -> None:
    if context.get("class_resources_committed"):
        return
    actor = state.fighters[actor_id]
    if (
        action.coefficient > ZERO
        and context.get("next_direct_crit_consumed")
        and not context.get("next_direct_crit_committed")
    ):
        if (
            actor.next_direct_crit_expires_opportunity is not None
            and actor.opportunity <= actor.next_direct_crit_expires_opportunity
            and actor.next_direct_crit_effect_id
            in context.get("next_direct_crit_effect_ids", ())
        ):
            actor.next_direct_crit_bonus = ZERO
            actor.next_direct_crit_expires_opportunity = None
            actor.next_direct_crit_effect_id = ""
        expected_source = str(context.get("sangue_frio_source_action_instance_id", ""))
        sangue_frio = actor.path_state.get("errante_sangue_frio_crit")
        if (
            "errante.sangue_frio.crit"
            in context.get("next_direct_crit_effect_ids", ())
            and isinstance(sangue_frio, dict)
            and str(sangue_frio.get("source_action_instance_id", "")) == expected_source
            and sangue_frio.get("applied_opportunity")
            == context.get("sangue_frio_applied_opportunity")
        ):
            actor.path_state.pop("errante_sangue_frio_crit", None)
            context.setdefault("automatic_resource_changes", []).append(
                ("errante_sangue_frio_crit", actor.id, 1, 0)
            )
        context["next_direct_crit_committed"] = True
    for plan in context.get("resource_uses", ()):
        use = plan["use"]
        if use.consume_at != "commit":
            continue
        if use.resource == "trama" and not context.get("trama_consumed"):
            trama = actor.path_state.get("trama_state")
            if isinstance(trama, dict) and int(trama.get("remaining", 0)) > 0:
                context["trama_consumed"] = True
                context["trama_consumed_origin"] = str(trama.get("origin_art", ""))
        elif use.resource == "luminar_state" and not context.get("luminar_consumed"):
            luminar = actor.path_state.get("luminar_state")
            if (
                isinstance(luminar, dict)
                and int(luminar.get("remaining", 0)) > 0
                and (use.state_kind is None or luminar.get("kind") == use.state_kind)
            ):
                context["luminar_consumed"] = True
                context["luminar_consumed_kind"] = str(luminar.get("kind", ""))
        elif use.resource in {"omen_offensive", "omen_defensive"}:
            kind = "offensive" if use.resource == "omen_offensive" else "defensive"
            for _key, target_id, _available in plan["targets"]:
                consumption = (kind, target_id)
                if consumption not in context["omen_consumptions"]:
                    context["omen_consumptions"].append(consumption)
        elif use.resource == "aim":
            for target_key, _target_id, _available in plan["targets"]:
                _consume_aim_stacks(
                    state.fighters[target_key], actor, use.consume
                )
    aim_primary_target = (
        context.get("primary_target_id") if action.coefficient > ZERO else None
    )
    _switch_aim_target(state, actor_id, aim_primary_target)
    if context.get("devastador_consumed"):
        actor.path_state.pop("devastador_charge", None)
    if context.get("guard_prepared_consumed"):
        actor.path_state.pop("guard_prepared_barrier", None)
    if context.get("trama_consumed"):
        trama = actor.path_state.pop("trama_state", None)
        if isinstance(trama, dict):
            context["automatic_resource_changes"].append(
                ("trama", actor.id, 1, 0)
            )
        if _has_talent(actor, "alternancia_fluida"):
            _apply_class_mechanic_buff(
                actor,
                mechanic="tecelao.alternancia_fluida",
                stat="agility",
                magnitude=D("0.05"),
            )
    if context.get("luminar_consumed"):
        luminar = actor.path_state.pop("luminar_state", None)
        if isinstance(luminar, dict):
            context["automatic_resource_changes"].append(
                ("luminar_state", actor.id, 1, 0)
            )
        if _has_talent(actor, "alternancia_radiante"):
            _apply_class_mechanic_buff(
                actor,
                mechanic="luminar.alternancia_radiante",
                stat="agility",
                magnitude=D("0.04"),
            )
    consumed_omen = False
    for kind, target_id in context.get("omen_consumptions", ()):
        key = "omen_offensive" if kind == "offensive" else "omen_defensive"
        omen = actor.path_state.get(key, {}).get(target_id)
        if isinstance(omen, dict) and int(omen.get("remaining", 0)) > 0:
            actor.path_state[key].pop(target_id, None)
            context["automatic_resource_changes"].append(
                (key, target_id, 1, 0)
            )
            if not actor.path_state[key]:
                actor.path_state.pop(key, None)
            consumed_omen = True
    if consumed_omen and _has_talent(actor, "sequencia_profetica"):
        _apply_class_mechanic_buff(
            actor,
            mechanic="oraculo.sequencia_profetica",
            stat="agility",
            magnitude=D("0.03"),
        )
    if context.get("trama_next_per_consumed"):
        actor.path_state.pop("trama_next_per", None)
    if context.get("aim_next_per_consumed"):
        actor.path_state.pop("aim_next_per", None)
    context["class_resources_committed"] = True


def _record_class_path_trigger(
    state: Combat,
    context: dict,
    trigger: str,
    target_id: str | None = None,
) -> None:
    actor_id = context.get("actor_entity_id")
    action_instance_id = context.get("action_instance_id")
    indices = [
        index
        for index, event in enumerate(state.events)
        if event.actor_entity_id == actor_id
        and event.action_instance_id == action_instance_id
        and (target_id is None or event.target == target_id)
    ]
    if not indices:
        return
    index = indices[0]
    event = state.events[index]
    if trigger not in event.path_triggers:
        state.events[index] = replace(event, path_triggers=event.path_triggers + (trigger,))


def _finalize_path_action(
    state: Combat,
    actor_id: str,
    action_id: str,
    action: Action,
    context: dict,
) -> str | None:
    actor = state.fighters[actor_id]
    if context.get("path_action_finalized"):
        return None
    context["path_action_finalized"] = True
    resource_changes: list[tuple[str, str, int, int]] = []
    for plan in context.get("resource_uses", ()):
        use = plan["use"]
        for target_key, target_id, _available in plan["targets"]:
            if use.consume_at == "after_resolution":
                _consume_aim_stacks(state.fighters[target_key], actor, use.consume)
            remaining = _class_resource_count(
                state,
                actor_id,
                target_key if target_key != actor_id else None,
                use.resource,
                state_kind=use.state_kind,
                action_id=action_id,
                action=action,
            )
            resource_changes.append((use.resource, target_id, use.consume, remaining))
    seen_resource_targets = {(row[0], row[1]) for row in resource_changes}
    for row in context.get("automatic_resource_changes", ()):
        if (row[0], row[1]) not in seen_resource_targets:
            resource_changes.append(row)
            seen_resource_targets.add((row[0], row[1]))
    if resource_changes:
        context["resource_changes"] = resource_changes
        actor_entity_id = context.get("actor_entity_id", actor.id)
        action_instance_id = context.get("action_instance_id", "")
        indices = [
            index
            for index, event in enumerate(state.events)
            if event.actor_entity_id == actor_entity_id
            and event.action_instance_id == action_instance_id
            and event.action == action_id
        ]
        if indices:
            first = indices[0]
            event = state.events[first]
            state.events[first] = replace(
                event,
                class_resource_changes=tuple(resource_changes),
            )
    if state.result:
        return None
    generated: list[tuple[str, str | None]] = []
    if (
        actor.character_class == "errante"
        and actor.hp > ZERO
        and context.get("errante_negative_effect_applied")
        and _has_talent(actor, "passos_da_sombra")
    ):
        _apply_class_mechanic_buff(
            actor,
            mechanic="errante.passos_da_sombra",
            stat="agility",
            magnitude=D("0.05"),
            duration=1,
        )
        generated.append(("errante.passos_da_sombra", None))
    for kind in ("offensive", "defensive"):
        target_id = context.get(f"omen_{kind}_applied_target_id")
        if (
            actor.character_class == "oraculo"
            and _is_art_action(action_id, action)
            and target_id
        ):
            target = next(
                (fighter for fighter in state.fighters.values() if fighter.id == target_id),
                None,
            )
            if target is not None and target.hp > ZERO:
                _new_omen(actor, kind, target)
                generated.append((f"oraculo.pressagio_{kind}_criado", target.id))
                target_key = next(
                    (key for key, fighter in state.fighters.items() if fighter.id == target.id),
                    None,
                )
                if (
                    kind == "offensive"
                    and target_key is not None
                    and _fighter_side(state, target_key) != _fighter_side(state, actor_id)
                    and _has_talent(actor, "leitura_dos_sinais")
                ):
                    _apply_class_mechanic_buff(
                        actor,
                        mechanic="oraculo.leitura_dos_sinais",
                        stat="agility",
                        magnitude=D("0.05"),
                    )
                    generated.append(("oraculo.leitura_dos_sinais", None))

    is_art = _is_art_action(action_id, action)
    direct = action.coefficient > ZERO
    support = _action_has_support(action)
    if actor.character_class == "luminar" and is_art and not context.get("luminar_consumed"):
        kind = (
            "fulgor"
            if direct and not support
            else "julgamento"
            if support and not direct
            else None
        )
        if kind:
            actor.path_state["luminar_state"] = {
                "kind": kind,
                "remaining": 3 if _has_talent(actor, "contraluz_persistente") else 2,
                "applied_opportunity": actor.opportunity,
            }
            generated.append((f"luminar.{kind}_gerado", None))
    if (
        actor.character_class == "tecelao"
        and is_art
        and not context.get("trama_consumed")
        and not (
            action.prepares_chain == "trama_encadeada"
            or action.consumes_chain == "trama_encadeada"
        )
        and not (
            isinstance(actor.path_state.get("trama_state"), dict)
            and int(actor.path_state["trama_state"].get("remaining", 0)) > 0
        )
    ):
        origin_art = action.id if action.id.startswith(("class_art.", "path_art.")) else action_id
        actor.path_state["trama_state"] = {
            "origin_art": origin_art,
            "remaining": 3 if _has_talent(actor, "trama_duradoura") else 2,
            "applied_opportunity": actor.opportunity,
        }
        generated.append(("tecelao.trama_gerada", None))
    if context.get("oportunism_triggered") and _has_talent(actor, "ritmo_predatorio"):
        _apply_class_mechanic_buff(
            actor,
            mechanic="errante.ritmo_predatorio",
            stat="agility",
            magnitude=D("0.05"),
        )
        generated.append(("errante.ritmo_predatorio", None))
    if context.get("rastreador_agility_applied") and _has_talent(actor, "leitura_de_movimento"):
        _apply_class_mechanic_buff(
            actor,
            mechanic="vigia.leitura_de_movimento",
            stat="agility",
            magnitude=D("0.05"),
        )
        generated.append(("vigia.leitura_de_movimento", None))
    aim_max_hit_target_id = context.get("aim_max_hit_target_id")
    if aim_max_hit_target_id and _has_talent(actor, "cacada_metodica"):
        actor.path_state["aim_next_per"] = {
            "magnitude": 3,
            "remaining": 2,
            "applied_opportunity": actor.opportunity,
        }
        generated.append(("vigia.cacada_metodica", None))
    if context.get("trama_consumed") and _has_talent(actor, "eco_de_alternancia"):
        actor.path_state["trama_next_per"] = {
            "magnitude": 3,
            "remaining": 2,
            "applied_opportunity": actor.opportunity,
        }
        generated.append(("tecelao.eco_de_alternancia", None))
    if (
        context.get("luminar_consumed_kind") == "fulgor"
        and _has_talent(actor, "fluxo_restaurador")
    ):
        events = [
            event
            for event in state.events
            if event.actor_entity_id == actor.id
            and event.action_instance_id == context.get("action_instance_id")
            and event.effective_healing > ZERO
        ]
        if events:
            target = next(
                (fighter for fighter in state.fighters.values() if fighter.id == events[0].target),
                None,
            )
            if target is not None:
                _apply_class_mechanic_buff(
                    target,
                    mechanic="luminar.fluxo_restaurador",
                    stat="defense",
                    magnitude=D("0.04"),
                )
                generated.append(("luminar.fluxo_restaurador", target.id))

    context["actor_entity_id"] = actor.id
    for trigger, target_id in generated:
        _record_class_path_trigger(state, context, trigger, target_id)
    return None


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
    for target_key, target in state.fighters.items():
        hp_loss = sum(
            (
                D(event.effective_damage)
                for event in state.events[event_start:]
                if event.actor == actor_key
                and event.target == target.id
                and event.action == action_id
                and not event.action.startswith("dot:")
            ),
            ZERO,
        )
        if hp_loss <= ZERO:
            continue
        if (
            target.selected_path == "devastador"
            and hp_loss >= target.stats.hp * D("0.08")
        ):
            target.path_state["devastador_charge"] = {
                "expires_opportunity": target.opportunity + 2,
                "source_action": action_id,
            }
        if (
            target.character_class == "sentinela"
            and target.hp > ZERO
            and _fighter_side(state, actor_key) != _fighter_side(state, target_key)
            and _has_talent(target, "firme_sob_impacto")
            and hp_loss >= target.stats.hp * D("0.08")
        ):
            _apply_class_mechanic_buff(
                target,
                mechanic="sentinela.firme_sob_impacto",
                stat="defense",
                magnitude=D("0.05"),
                duration=1,
            )

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
        if _fighter_side(state, actor_id) == "player"
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
            _deal_combat_damage(state, actor_id, recoil, source_key=actor_id)
    if actor.hp == 0:
        _refresh_result(state)
        return True

    actions = (
        player_actions_for(state, actor_id)
        if _is_player_turn_actor(state, actor_id)
        else state.enemy_actions
    )
    action = actions.get(action_id)
    if action is None:
        return False
    if action.requires_defeated_fighter_keys and not any(
        key in state.fighters and state.fighters[key].hp <= ZERO
        for key in action.requires_defeated_fighter_keys
    ):
        return False
    target_keys = _resolve_action_targets(state, actor_id, action, target_id)
    if not target_keys:
        return False
    if _path_resolution is None:
        resource_uses = _snapshot_action_resource_uses(
            state, actor_id, action_id, action, target_keys, target_id
        )
        if resource_uses is None:
            return False
        _path_resolution = _prepare_path_action(
            state,
            actor_id,
            action_id,
            action,
            target_keys,
            target_id,
            resource_uses,
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
                        _grant_defender_retaliation(
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
        not _is_player_turn_actor(state, actor_id)
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
    _path_resolution["actor_entity_id"] = actor.id
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
            and (
                action.self_barrier_coefficient > ZERO
                or action.self_barrier_hp_fraction > ZERO
                or action.target_barrier_coefficient > ZERO
            )
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

    if action.self_barrier_coefficient > ZERO or action.self_barrier_hp_fraction > ZERO:
        _commit_path_action(state, actor_id, action_id, action, _path_resolution)
        self_context = _path_target_context(_path_resolution, actor)
        path_barrier_multiplier = D(self_context.get("barrier_power", D(1)))
        if actor.selected_path == "bastiao":
            path_barrier_multiplier *= D("1.10")
        if action.self_barrier_hp_fraction > ZERO:
            value = (
                actor.stats.hp
                * action.self_barrier_hp_fraction
                * barrier_power_multiplier
                * path_barrier_multiplier
                * _barrier_received_multiplier(state, actor_id)
            ).to_integral_value(rounding=ROUND_FLOOR)
        else:
            barrier_coefficient = (
                action.self_barrier_coefficient
                * barrier_power_multiplier
                * path_barrier_multiplier
                * _barrier_received_multiplier(state, actor_id)
            )
            value = (actor.stat("attack") * barrier_coefficient).to_integral_value(
                rounding=ROUND_FLOOR
            )
        value = _apply_barrier(
            actor,
            applier_id=actor.id,
            effect_definition_id=action.id,
            value=max(ZERO, value),
            duration=(
                action.self_barrier_duration
                if action.self_barrier_duration < 0
                else max(0, action.self_barrier_duration)
            ),
            applied_opportunity=actor.opportunity,
            round_number=state.round,
            debuff_magnitude_reduction=action.self_barrier_debuff_magnitude_reduction,
            bound_effect_ids=action.barrier_bound_effect_ids,
        )
        barrier_source = f"{actor.id}:{action.id}" if value > ZERO else ""
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
                barrier_value=value,
                barrier_total_after=actor.barrier,
                barrier_duration=(
                    action.self_barrier_duration
                    if value > ZERO
                    else 0
                ),
                actor_entity_id=actor.id,
                response_to_prepared_action_instance_id=(
                    response_to_prepared_action_instance_id
                ),
                barrier_applied_source=barrier_source,
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
        if (
            value > ZERO
            and actor.character_class == "oraculo"
            and _is_art_action(action_id, action)
        ):
            _path_resolution["omen_defensive_applied_target_id"] = actor.id
        if _hit_index is None:
            _finalize_path_action(state, actor_id, action_id, action, _path_resolution)
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
    active_actor_effect_ids.update(
        _path_resolution.get("next_direct_crit_effect_ids", ())
    )
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
    _commit_path_action(state, actor_id, action_id, action, _path_resolution)
    retaliation_context = _path_resolution.get("retaliation_context")
    if not isinstance(retaliation_context, dict):
        retaliation_context = _consume_retaliation(
            state, actor_id, actor, action_id, action, target_keys
        )
        _path_resolution["retaliation_context"] = retaliation_context
    retaliation_used = bool(retaliation_context.get("used"))
    retaliation_source_type = str(retaliation_context.get("source_type", ""))
    retaliation_source_actor_id = str(retaliation_context.get("source_actor_id", ""))
    if retaliation_used:
        _path_resolution["automatic_resource_changes"].append(
            (
                "retaliation",
                actor.id,
                1,
                int(actor.retaliation_charges),
            )
        )
    retaliation_valid = retaliation_used and retaliation_source_type == "defender"

    current_ruleset = state.ruleset == CURRENT_COMBAT_RULESET
    direct_eligible = action.coefficient > ZERO
    prepared_resolution = state.resolving_prepared
    resolved_hit_index = _hit_index or 1
    resolved_hit_count = _hit_count if _hit_index is not None else action.hit_count
    action_event_indices: list[int] = []
    total_vamp_damage = D(0)
    defer_aoe_phase_triggers = (
        action.target_mode == "all_opponents" and action.hit_count == 1
    )
    aoe_phase_trigger_pending = False

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
            if target.barrier > ZERO and target.barrier_remaining != 0
            else ""
        )
        applied_barrier_source = ""
        applied_barrier_duration = 0

        dodged = False
        if current_ruleset and direct_eligible:
            streak = state.evasion_streaks.get(target.id, 0)
            if streak >= 2:
                state.evasion_streaks[target.id] = 0
            else:
                evasion_points = target.stat("evasion")
                if state.pvp_mode:
                    evasion_points = min(D(25), evasion_points)
                evasion_chance = chance_from_percentage_points(evasion_points)
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
            dodge_path_triggers = tuple(target_path.get("triggers", ()))
            if (
                target.character_class == "errante"
                and _has_talent(target, "sangue_frio")
            ):
                target.path_state["errante_sangue_frio_crit"] = {
                    "applied_opportunity": target.opportunity,
                    "expires_opportunity": target.opportunity + 2,
                    "source_action_instance_id": action_instance_id,
                }
                dodge_path_triggers += ("errante.sangue_frio_preparado",)
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
                    path_triggers=dodge_path_triggers,
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
            next_direct_bonus = D(
                _path_resolution.get("next_direct_crit_bonus", ZERO)
            )
            crit_points = (
                actor.stat("crit")
                + target_debuff_bonus
                + next_direct_bonus
                + D(target_path.get("crit_bonus", ZERO))
            )
            if state.pvp_mode:
                crit_points = min(D(40), crit_points)
            crit_chance = (
                chance_from_percentage_points(crit_points)
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
        ) + action.actor_per_bonus + (
            action.actor_per_bonus_if_target_bleeding
            if any(
                dot.kind == "bleed" and dot.stacks > 0 and dot.remaining > 0
                for dot in state.dot_states.get(target.id, ())
            )
            else ZERO
        ) + (
            action.actor_per_bonus_if_target_hp_fraction_at_most
            if target.stats.hp > ZERO
            and target.hp <= target.stats.hp * action.actor_per_bonus_hp_fraction_threshold
            else ZERO
        ) + D(target_path.get("per_bonus", ZERO)) + (
            D(4)
            if retaliation_used
            and actor.character_class == "sentinela"
            and _has_talent(actor, "ponta_revidada")
            else ZERO
        )
        damage = (
            direct_damage(
                actor.stat("attack"),
                damage_coefficient,
                D(
                    target_path.get(
                        "pre_event_defense",
                        _fighter_stat(state, target_key, "defense"),
                    )
                ),
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
            + D(
                target_path.get(
                    "pre_event_damage_aura_reduction",
                    _damage_aura_reduction(state, target_key),
                )
            )
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
        pressure_stacks = (
            state.pressure_stacks
            if _fighter_side(state, actor_id) == "enemy"
            else 0
        )
        if direct_eligible and pressure_stacks > 0:
            damage = int(
                (
                    D(damage)
                    * (D(1) + state.pressure_step * pressure_stacks)
                ).to_integral_value(rounding=ROUND_FLOOR)
            )
        damage_without_defender = damage
        if target.defending and direct_eligible:
            damage_without_defender = direct_damage(
                actor.stat("attack"),
                damage_coefficient,
                D(
                    target_path.get(
                        "pre_event_defense",
                        _fighter_stat(state, target_key, "defense"),
                    )
                ),
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
            if pressure_stacks > 0:
                damage_without_defender = int(
                    (
                        D(damage_without_defender)
                        * (D(1) + state.pressure_step * pressure_stacks)
                    ).to_integral_value(rounding=ROUND_FLOOR)
                )
        defender_prevented_damage = (
            max(0, damage_without_defender - damage)
            if target.defending and direct_eligible
            else 0
        )

        barrier_absorbed_sources: list[str] = []
        actual_damage, barrier_absorbed = _deal_combat_damage(
            state,
            target_key,
            damage,
            source_key=actor_id,
            absorbed_sources=barrier_absorbed_sources,
        )
        if actual_damage > 0:
            if defer_aoe_phase_triggers:
                aoe_phase_trigger_pending = True
            else:
                _resolve_phase_triggers(state)
        if (
            direct_eligible
            and damage > 0
            and actor.character_class == "vigia"
            and _fighter_side(state, actor_id) != _fighter_side(state, target_key)
        ):
            generated = _path_resolution.setdefault("aim_generated_targets", set())
            snapshot_stacks = int(target_path.get("aim_stacks", 0))
            maximum = (
                4
                if actor.selected_path == "atirador"
                else 2
                if actor.selected_path == "rastreador"
                else 3
            )
            if (
                snapshot_stacks >= maximum
                and _has_talent(actor, "cacada_metodica")
                and not _path_resolution.get("aim_max_hit_target_id")
            ):
                _path_resolution["aim_max_hit_target_id"] = target.id

            is_rastros_area = (
                actor.selected_path == "rastreador"
                and _is_named_art(action_id, action, "chuva_de_rastros")
            )
            primary_target_id = _path_resolution.get("primary_target_id")
            can_generate_base = target.id == primary_target_id or is_rastros_area
            stacks = 0
            if target.id not in generated and can_generate_base:
                stacks = _grant_aim(
                    state,
                    actor_id,
                    target_key,
                    trigger="chuva_de_rastros" if is_rastros_area else "direct",
                )

            used_acquisition = actor.path_state.setdefault("aim_acquisition_used", {})
            voleio_secondary = (
                action.target_mode == "all_opponents"
                and _is_named_art(action_id, action, "voleio")
                and target.id != primary_target_id
            )
            if (
                target.id not in generated
                and snapshot_stacks == 0
                and _has_talent(actor, "aquisicao_rapida")
                and isinstance(used_acquisition, dict)
                and not used_acquisition.get(target.id)
                and not voleio_secondary
            ):
                extra_stacks = _grant_aim(
                    state,
                    actor_id,
                    target_key,
                    trigger="aquisicao_rapida",
                )
                if extra_stacks:
                    used_acquisition[target.id] = True
                    stacks = extra_stacks

            if (
                target.id not in generated
                and can_generate_base
                and actor.selected_path == "atirador"
                and _is_named_art(action_id, action, "fixar_alvo")
            ):
                extra_stacks = _grant_aim(
                    state,
                    actor_id,
                    target_key,
                    trigger="fixar_alvo",
                )
                stacks = extra_stacks or stacks

            if stacks:
                generated.add(target.id)
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
            attack_debuff_effect = Effect(
                id=applied_effect_id,
                stat=action.effect_stat or "attack",
                magnitude=action.attack_debuff,
                remaining=(
                    min(3, action.duration + 1)
                    if actor.selected_path == "sabotador" and action.duration in {1, 2}
                    else action.duration
                ),
                applied_opportunity=target.opportunity,
            )
            guard_integrity_applied = _guard_integrity_can_reduce(
                target, attack_debuff_effect
            )
            if guard_integrity_applied:
                attack_debuff_effect.magnitude *= D("0.90")
            status_applied = apply_effect(
                state,
                target,
                attack_debuff_effect,
                application_event=effect_application_event_id,
            )
            if status_applied and guard_integrity_applied:
                target.path_state.pop("guard_integrity_debuff", None)
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
            guard_effect_index = next(
                (
                    index
                    for index, effect in enumerate(action.target_effects)
                    if _guard_integrity_can_reduce(target, effect)
                ),
                None,
            )
            target_effects = tuple(
                Effect(
                    id=effect.id,
                    stat=effect.stat,
                    magnitude=(
                        effect.magnitude * D("0.90")
                        if index == guard_effect_index
                        else effect.magnitude
                    ),
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
                for index, effect in enumerate(action.target_effects)
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
                if guard_effect_index is not None:
                    guarded_id = action.target_effects[guard_effect_index].id
                    guarded_effect_applied = any(
                        effect.application_event == application_id
                        and effect.id == guarded_id
                        for effect in target.effects
                    )
                    if guarded_effect_applied:
                        target.path_state.pop("guard_integrity_debuff", None)

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
            if native_kind == "poison" and any(
                dot.kind == "poison" and dot.stacks > 0 and dot.remaining > 0
                for dot in state.dot_states.get(target.id, ())
            ):
                native_stacks += action.native_dot_stacks_if_target_poisoned
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

        if actor.character_class == "errante":
            applied_event_ids = {
                event_id
                for event_id in (
                    effect_application_event_id,
                    target_effects_application_id,
                )
                if event_id
            }
            applied_normal_debuff = any(
                effect.application_event in applied_event_ids
                and effect.kind == "debuff"
                and effect.remaining > 0
                and effect.stacks > 0
                and not effect.fixed_mechanic
                for effect in target.effects
            )
            if dot_application_event_id or applied_normal_debuff:
                _path_resolution["errante_negative_effect_applied"] = True

        agility_debuff_applied = False
        if actor.character_class == "vigia":
            agility_debuff_applied = any(
                effect.application_event == target_effects_application_id
                and effect.stat == "agility"
                and effect.kind == "debuff"
                and effect.remaining > 0
                and not effect.fixed_mechanic
                for effect in target.effects
            ) or bool(
                applied_effect is not None
                and applied_effect.stat == "agility"
                and applied_effect.kind == "debuff"
                and not applied_effect.fixed_mechanic
            )
            if agility_debuff_applied:
                _path_resolution["rastreador_agility_applied"] = True
        if actor.character_class == "vigia" and actor.selected_path == "rastreador":
            if dot_application_event_id or agility_debuff_applied:
                generated = _path_resolution.setdefault("aim_generated_targets", set())
                if target.id not in generated:
                    stacks = _grant_aim(
                        state,
                        actor_id,
                        target_key,
                        trigger="status",
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
                * _barrier_received_multiplier(state, target_key)
            ).to_integral_value(rounding=ROUND_FLOOR)
            target_barrier = max(ZERO, target_barrier)
            if target_barrier > ZERO:
                target_barrier = _apply_barrier(
                    target,
                    applier_id=actor.id,
                    effect_definition_id=action.id,
                    value=target_barrier,
                    duration=max(0, action.target_barrier_duration),
                    applied_opportunity=target.opportunity,
                    round_number=state.round,
                    debuff_magnitude_reduction=(
                    action.target_barrier_debuff_magnitude_reduction
                    ),
                    bound_effect_ids=action.barrier_bound_effect_ids,
                )
                if target_barrier > ZERO:
                    applied_barrier_source = f"{actor.id}:{action.id}"
                    applied_barrier_duration = max(0, action.target_barrier_duration)

        if actor.character_class == "oraculo" and _is_art_action(action_id, action):
            applied_target_effects = [
                effect
                for effect in target.effects
                if effect.remaining > 0
                and not effect.fixed_mechanic
                and (
                    effect.application_event == effect_application_event_id
                    or effect.application_event == target_effects_application_id
                )
            ]
            if target.id == _path_resolution.get("primary_target_id"):
                if (
                    _fighter_side(state, actor_id) != _fighter_side(state, target_key)
                    and (dot_application_event_id or any(
                    effect.kind == "debuff" for effect in applied_target_effects
                    ))
                ):
                    _path_resolution["omen_offensive_applied_target_id"] = target.id
                if (
                    _fighter_side(state, actor_id) == _fighter_side(state, target_key)
                    and (
                        target_barrier > ZERO
                        or any(effect.kind == "buff" for effect in applied_target_effects)
                    )
                ):
                    _path_resolution["omen_defensive_applied_target_id"] = target.id

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
                barrier_total_after=target.barrier,
                barrier_duration=applied_barrier_duration,
                barrier_absorbed_sources=tuple(barrier_absorbed_sources),
                blocked=blocked,
                actor_entity_id=actor.id,
                calculated_damage=damage,
                effective_damage=int(actual_damage),
                target_defending=target_defending,
                defender_mitigation_applied=defender_prevented_damage > 0,
                defender_prevented_damage=defender_prevented_damage,
                target_barrier_source=target_barrier_source,
                barrier_applied_source=applied_barrier_source,
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
                    pressure_stacks=pressure_stacks,
                )
        )
        action_event_indices.append(action_event_sequence)

        if (
            current_ruleset
            and defender_prevented_damage > 0
            and target.character_class == "sentinela"
            and _grant_action_retaliation
        ):
            _grant_defender_retaliation(
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
            and not effect.fixed_mechanic
        ]
        if applied_actor_buffs:
            _path_resolution["omen_defensive_applied_target_id"] = actor.id
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

    # Content vampirism is applied from eligible direct HP damage for this action.
    action_vamp_healed = D(0)
    if (
        _fighter_side(state, actor_id) == "enemy"
        and action.vampirism_fraction > ZERO
        and total_vamp_damage > ZERO
    ):
        action_vamp_cap = (
            actor.stats.hp * action.vampirism_cap_hp_fraction
            if action.vampirism_cap_hp_fraction is not None
            else actor.stats.hp - actor.hp
        )
        action_vamp_healed = min(
            (total_vamp_damage * action.vampirism_fraction).to_integral_value(
                rounding=ROUND_FLOOR
            ),
            actor.stats.hp - actor.hp,
            action_vamp_cap,
        )
        action_vamp_healed = max(ZERO, action_vamp_healed)
        actor.hp += action_vamp_healed
        if action_vamp_healed > ZERO and action_event_indices:
            event_index = next(
                (
                    index
                    for index in action_event_indices
                    if state.events[index].effective_damage > 0
                ),
                action_event_indices[0],
            )
            state.events[event_index] = replace(
                state.events[event_index],
                healed=state.events[event_index].healed + action_vamp_healed,
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

    # Resolve encounter phases only after every simultaneous AoE result and
    # action-level vampirism have completed against the frozen target snapshot.
    if aoe_phase_trigger_pending:
        _resolve_phase_triggers(state)

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
    if _hit_index is None or _hit_index == _hit_count:
        _retaliation_action_resolved(state, actor_id, actor, retaliation_context)
    if action.revive_fighter_keys and _hit_index in {None, 1}:
        defeated = sorted(
            (
                key
                for key in action.revive_fighter_keys
                if key in state.fighters and state.fighters[key].hp <= ZERO
            ),
            key=lambda key: (state.fighters[key].id, key),
        )
        if defeated:
            revived_key = defeated[0]
            revived = state.fighters[revived_key]
            revived.hp = revived.stats.hp * action.revive_hp_fraction
            state.mechanic_events.append(
                CombatEvent(
                    len(state.mechanic_events),
                    state.round,
                    actor_id,
                    f"revive:{revived_key}",
                    target=revived.id,
                    actor_entity_id=actor.id,
                    internal=True,
                )
            )
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
    if state.pressure_start_opportunity and state.pressure_cap:
        enemy = state.fighters[actor_key]
        state.pressure_stacks = min(
            state.pressure_cap,
            max(0, enemy.opportunity - state.pressure_start_opportunity + 1),
        )
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

    def current_target_key() -> str | None:
        candidates = [
            key
            for key, fighter in state.fighters.items()
            if fighter.hp > ZERO and _fighter_side(state, key) != _fighter_side(state, actor_key)
        ]
        candidates.sort(key=lambda key: (state.fighters[key].id, key))
        if state.ai_target_cycle:
            requested = state.ai_target_cycle[
                state.ai_target_position % len(state.ai_target_cycle)
            ]
            requested_key = _resolve_fighter_key(state, requested)
            if requested_key in candidates:
                return requested_key
        player_candidates = [key for key in candidates if _fighter_side(state, key) == "player"]
        if player_candidates:
            return player_candidates[0]
        return candidates[0] if candidates else None

    def target_condition_blocks(action: Action) -> bool:
        target_key = current_target_key()
        if target_key is None:
            return False
        target = state.fighters[target_key]
        if action.skip_if_target_effect_active and any(
            effect.id == action.skip_if_target_effect_active and effect.remaining > 0
            for effect in target.effects
        ):
            return True
        if action.skip_if_target_dot_at_cap:
            cap = _DOT_STACK_CAPS.get(action.skip_if_target_dot_at_cap, 3)
            if any(
                dot.kind == action.skip_if_target_dot_at_cap
                and dot.remaining > 0
                and dot.stacks >= cap
                for dot in state.dot_states.get(target.id, ())
            ):
                return True
        return False

    def ready(action_id: str) -> bool:
        action = state.enemy_actions.get(action_id)
        if action is None or enemy.cooldowns.get(action_id, 0) > enemy.opportunity:
            return False
        if action.phase_ids and state.phase_id not in action.phase_ids:
            return False
        if enemy.last_action in action.skip_if_actor_last_action:
            return False
        if (
            action.max_uses_per_combat is not None
            and enemy.action_use_counts.get(action_id, 0) >= action.max_uses_per_combat
        ):
            return False
        if action.skip_if_self_effect_active and any(
            effect.id == action.skip_if_self_effect_active and effect.remaining > 0
            for effect in enemy.effects
        ):
            return False
        if action.skip_if_any_self_effect_active and any(
            effect.id in action.skip_if_any_self_effect_active and effect.remaining > 0
            for effect in enemy.effects
        ):
            return False
        if action.requires_defeated_fighter_keys and not any(
            key in state.fighters and state.fighters[key].hp <= ZERO
            for key in action.requires_defeated_fighter_keys
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
        if target_condition_blocks(action):
            return False
        return not (
            action.skip_if_barrier_active
            and enemy.barrier > ZERO
            and enemy.barrier_remaining != 0
        )

    priority = state.ai_priorities.get(actor_key, state.ai_priority)
    if priority:
        for action in priority:
            if ready(action):
                return action
    # Alfa Cinéreo uses content priority rather than a positional cycle.
    cycle = state.ai_cycles.get(actor_key, state.ai_cycle)
    if {"rend", "leap", "bite"}.issubset(cycle):
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
    if not cycle:
        return "hold"
    position = state.ai_positions.get(actor_key, 0)
    for _ in range(len(cycle)):
        action = cycle[position]
        position = (position + 1) % len(cycle)
        state.ai_positions[actor_key] = position
        if actor_key == 'enemy':
            state.ai_position = position
        if ready(action):
            return action
    return "hold"


def _advance_to_player(state: Combat) -> None:
    while (
        not state.result
        and state.order
        and not _is_player_turn_actor(state, state.order[state.turn_index])
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
            if committed and action and action.ai_priority_after:
                state.ai_priorities[actor_key] = action.ai_priority_after
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


def consumable_available(state: Combat, actor_key: str | None = None) -> bool:
    actor_key = actor_key or active_player_key(state) or "player"
    if state.result or not state.order or state.order[state.turn_index] != actor_key:
        return False
    player = state.fighters.get(actor_key)
    if player is None or not _is_player_turn_actor(state, actor_key):
        return False
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
    barrier_source: str = "",
    barrier_duration: int = 0,
    actor_key: str = "player",
) -> Combat:
    healed = D(0) if healed is None else healed
    player = state.fighters[actor_key]
    player.last_action = action
    # CD2: unavailable on the next opportunity and available on the following one.
    player.cooldowns[CONSUMABLE_COOLDOWN_KEY] = player.opportunity + 2
    state.events.append(
        CombatEvent(
            len(state.events),
            state.round,
            actor_key,
            action,
            target,
            healed=healed,
            effect_id=effect_id,
            effect_removal_kind=effect_removal_kind,
            barrier_absorbed=barrier_absorbed,
            barrier_value=barrier_value,
            barrier_total_after=player.barrier,
            barrier_duration=barrier_duration,
            barrier_applied_source=barrier_source,
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


def use_heal_consumable(state: Combat, *, actor_key: str | None = None) -> Combat:
    """Apply the official 22% HP-Max heal as a normal player action."""
    actor_key = actor_key or active_player_key(state) or "player"
    if not consumable_available(state, actor_key):
        return state
    with localcontext() as ctx:
        ctx.prec = PRECISION
        updated = deepcopy(state)
        player = updated.fighters[actor_key]
        healed = effective_heal_amount(updated, actor_key)
        if healed <= 0:
            return state
        player.hp += healed
        return _finish_consumable_turn(
            updated, "consumable:heal", healed, actor_key=actor_key
        )


def use_purification_consumable(
    state: Combat, *, dot_index: int | None = None, effect_index: int | None = None,
    actor_key: str | None = None,
) -> Combat:
    """Remove one oldest DoT stack or one removable non-stack debuff."""
    actor_key = actor_key or active_player_key(state) or "player"
    if not consumable_available(state, actor_key) or (dot_index is None) == (effect_index is None):
        return state
    with localcontext() as ctx:
        ctx.prec = PRECISION
        updated = deepcopy(state)
        player = updated.fighters[actor_key]
        if dot_index is not None:
            dots = updated.dot_states.get(actor_key, [])
            if not 0 <= dot_index < len(dots):
                return state
            selection_id = _dot_token(dots[dot_index], dot_index)
        else:
            if not 0 <= effect_index < len(player.effects):
                return state
            selection_id = _effect_token(player.effects[effect_index], effect_index)
        if _remove_selected_effect_component(
            updated, actor_key, selection_id, "purification"
        ) is None:
            return state
        return _finish_consumable_turn(
            updated, "consumable:purify", actor_key=actor_key
        )


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


def _remove_selected_effect_component(
    state: Combat,
    target_id: str,
    selection_id: str,
    component: str,
) -> tuple[str, str] | None:
    """Remove exactly one eligible unit, preserving the remaining stack state."""
    if component == "purification":
        dots = state.dot_states.get(target_id, [])
        for index, dot in enumerate(dots):
            if _dot_token(dot, index) != selection_id or not _dot_is_removable(dot):
                continue
            snapshots = list(dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks)
            if not snapshots:
                return None
            snapshots.pop(0)
            if snapshots:
                dot.stack_snapshots = snapshots
                dot.snapshot_attack = snapshots[0]
                dot.stacks = len(snapshots)
            else:
                dots.pop(index)
                if not dots:
                    state.dot_states.pop(target_id, None)
            return f"dot:{dot.kind}", "stack"

    target = state.fighters.get(target_id)
    if target is None:
        return None
    for index, effect in enumerate(target.effects):
        if _effect_token(effect, index) != selection_id:
            continue
        eligible = (
            purifiable(effect)
            if component == "purification"
            else dissipatable(effect)
            if component == "dispel"
            else False
        )
        if not eligible:
            return None
        removal_kind = "stack" if effect.stackable else "effect"
        effect_id = _remove_selected_effect(target, selection_id, one_stack=True)
        return (effect_id, removal_kind) if effect_id else None
    return None


def _remaining_effect_stack_count(
    state: Combat, target_id: str, selection_id: str
) -> int:
    for index, dot in enumerate(state.dot_states.get(target_id, ())):
        if _dot_token(dot, index) == selection_id:
            return max(0, dot.stacks)
    target = state.fighters.get(target_id)
    if target is not None:
        for index, effect in enumerate(target.effects):
            if _effect_token(effect, index) == selection_id:
                return max(0, effect.stacks)
    return 0


def combat_consumable_usable(
    state: Combat,
    item_id: str,
    *,
    target_id: str | None = None,
    effect_id: str | None = None,
    budget_limit: int | None = None,
    actor_key: str | None = None,
) -> bool:
    actor_key = actor_key or active_player_key(state) or "player"
    item = definition(item_id)
    actor = state.fighters.get(actor_key)
    if (
        item is None
        or item.use_context is not UseContext.COMBAT_PVE
        or not state.external_consumables_allowed
        or state.tutorial_stage != "normal"
        or not consumable_available(state, actor_key)
        or actor is None
        or not _is_player_turn_actor(state, actor_key)
        or actor.hp <= 0
        or (budget_limit is not None and state.consumable_uses >= budget_limit)
    ):
        return False
    if item.family == ConsumableFamily.HEALING:
        return (
            effective_heal_amount(state, actor_key) > 0
            and effect_id is None
            and target_id in {None, actor_key}
        )
    if item.family in {
        ConsumableFamily.PURIFICATION,
        ConsumableFamily.ANTIDOTE,
        ConsumableFamily.DISPELLER,
    }:
        if item.family == ConsumableFamily.DISPELLER:
            if (
                target_id is None
                or _fighter_side(state, target_id) == _fighter_side(state, actor_key)
                or target_id == actor_key
            ):
                return False
            target = state.fighters.get(target_id)
            if target is None or target.hp <= 0:
                return False
        else:
            target_id = actor_key
            target = actor
        choices = {option_id for option_id, _ in consumable_effect_options(
            state, item_id, target_id=target_id
        )}
        return bool(choices) and effect_id in choices
    if item.family in {ConsumableFamily.PROTECTION, ConsumableFamily.WARDING}:
        return effect_id is None and target_id in {None, actor_key}
    return False


def use_combat_consumable(
    state: Combat,
    item_id: str,
    *,
    target_id: str | None = None,
    effect_id: str | None = None,
    budget_limit: int | None = None,
    actor_key: str | None = None,
) -> Combat:
    """Apply a valid PvE Consumable as one normal, versioned combat action."""
    actor_key = actor_key or active_player_key(state) or "player"
    if not combat_consumable_usable(
        state,
        item_id,
        target_id=target_id,
        effect_id=effect_id,
        budget_limit=budget_limit,
        actor_key=actor_key,
    ):
        return state
    item = definition(item_id)
    assert item is not None
    updated = deepcopy(state)
    player = updated.fighters[actor_key]
    resolved_target = target_id or actor_key
    healed = D(0)
    effect_name = ""
    effect_removal_kind = None
    barrier_value = D(0)
    barrier_source = ""
    barrier_duration = 0

    if item.family == ConsumableFamily.HEALING:
        healed = effective_heal_amount(updated, actor_key)
        if healed <= 0:
            return state
        player.hp += healed
    elif item.family == ConsumableFamily.PURIFICATION:
        assert effect_id is not None
        removed = _remove_selected_effect_component(
            updated, actor_key, effect_id, "purification"
        )
        if removed is None:
            return state
        effect_name, _removal_kind = removed
    elif item.family == ConsumableFamily.ANTIDOTE:
        assert effect_id is not None
        effect_name = _remove_selected_dot(updated, actor_key, effect_id, all_stacks=True) or ""
        if not effect_name:
            return state
    elif item.family == ConsumableFamily.PROTECTION:
        barrier_multiplier = D("1.10") if player.selected_path == "bastiao" else D(1)
        barrier_value = (player.stats.hp * D("0.12") * barrier_multiplier).to_integral_value(
            rounding=ROUND_FLOOR
        )
        if barrier_value <= 0:
            return state
        barrier_value = _apply_barrier(
            player,
            applier_id=player.id,
            effect_definition_id="consumable.protecao",
            value=barrier_value,
            duration=2,
            applied_opportunity=player.opportunity,
            round_number=state.round,
        )
        if barrier_value <= ZERO:
            return state
        barrier_source = f"{player.id}:consumable.protecao"
        barrier_duration = 2
    elif item.family == ConsumableFamily.DISPELLER:
        assert effect_id is not None
        removed = _remove_selected_effect_component(
            updated, resolved_target, effect_id, "dispel"
        )
        if removed is None:
            return state
        effect_name, effect_removal_kind = removed
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
        barrier_source=barrier_source,
        barrier_duration=barrier_duration,
        actor_key=actor_key,
    )


def _action_has_primary_component(action: Action) -> bool:
    return bool(
        action.coefficient > ZERO
        or action.attack_debuff
        or action.native_dot_stacks
        or action.heal_coefficient > ZERO
        or action.self_barrier_coefficient > ZERO
        or action.self_barrier_hp_fraction > ZERO
        or action.target_barrier_coefficient > ZERO
        or action.target_effects
        or action.self_effects
        or action.self_effect_stat
        or action.revive_fighter_keys
        or action.next_direct_crit_bonus > ZERO
        or action.prepares_chain
        or action.self_state_tags_after is not None
        or action.manifestation_kind
    )


def _prepare_action_effect_removal(
    state: Combat,
    action: Action,
    target_keys: tuple[str, ...],
    *,
    actor_key: str,
    effect_id: str | None,
    effect_selections: tuple[tuple[str, str], ...],
) -> tuple[bool, tuple[tuple[str, str], ...]]:
    spec = action.effect_removal
    if spec is None:
        return (effect_id is None and not effect_selections, ())

    if actor_key not in state.fighters:
        return False, ()
    actor_side = _fighter_side(state, actor_key)
    eligible_targets = tuple(
        key
        for key in target_keys
        if (
            _fighter_side(state, key) == actor_side
            if spec.kind == "purification"
            else _fighter_side(state, key) != actor_side
        )
    )
    options_by_target = {
        key: _effect_removal_options_for_target(state, spec.kind, key)
        for key in eligible_targets
    }
    candidates = tuple(
        (key, option.effect_id)
        for key in eligible_targets
        for option in options_by_target[key]
    )

    if effect_id is not None and effect_selections:
        return False, ()
    selected: list[tuple[str, str]] = []
    if effect_id is not None:
        matches = tuple(pair for pair in candidates if pair[1] == effect_id)
        if len(matches) != 1:
            return False, ()
        selected.extend(matches)
    elif effect_selections:
        selected.extend((str(key), str(selection)) for key, selection in effect_selections)
        if any(pair not in candidates for pair in selected):
            return False, ()
    elif candidates:
        if spec.selection_required:
            return False, ()
        else:
            remaining = spec.count
            for key in eligible_targets:
                for option in options_by_target[key]:
                    if remaining <= 0:
                        break
                    units = min(remaining, option.stacks if option.stackable else 1)
                    selected.extend((key, option.effect_id) for _ in range(units))
                    remaining -= units
                if spec.scope == "per_action" and remaining <= 0:
                    break
                if spec.scope == "per_target":
                    remaining = spec.count

    selection_counts: dict[tuple[str, str], int] = {}
    option_by_selection = {
        (key, option.effect_id): option
        for key, options in options_by_target.items()
        for option in options
    }
    for selection in selected:
        selection_counts[selection] = selection_counts.get(selection, 0) + 1
        option = option_by_selection.get(selection)
        if option is None:
            return False, ()
        capacity = option.stacks if option.stackable else 1
        if selection_counts[selection] > capacity:
            return False, ()

    if spec.scope == "per_action" and len(selected) > spec.count:
        return False, ()
    if spec.scope == "per_target":
        selected_counts: dict[str, int] = {}
        for key, _ in selected:
            selected_counts[key] = selected_counts.get(key, 0) + 1
        if any(count > spec.count for count in selected_counts.values()):
            return False, ()
        if spec.selection_required and selected:
            if any(
                options_by_target[key]
                and selected_counts.get(key, 0) == 0
                for key in eligible_targets
            ):
                return False, ()

    if not selected and not _action_has_primary_component(action):
        return False, ()
    return True, tuple(selected)


def _resolve_action_effect_removal(
    state: Combat,
    actor_key: str,
    action_id: str,
    action: Action,
    plan: tuple[tuple[str, str], ...],
    target_keys: tuple[str, ...],
    *,
    event_start: int,
) -> None:
    spec = action.effect_removal
    if spec is None:
        return
    selected_by_target: dict[str, list[str]] = {}
    for target_key, selection_id in plan:
        selected_by_target.setdefault(target_key, []).append(selection_id)
    actor = state.fighters[actor_key]
    allowed_targets = {
        key
        for key in target_keys
        if (
            _fighter_side(state, key) == _fighter_side(state, actor_key)
            if spec.kind == "purification"
            else _fighter_side(state, key) != _fighter_side(state, actor_key)
        )
    }
    if spec.scope == "per_action":
        component_targets = (
            set(selected_by_target)
            if selected_by_target
            else set(tuple(key for key in target_keys if key in allowed_targets)[:1])
        )
    else:
        component_targets = allowed_targets
    for target_key in target_keys:
        if target_key not in component_targets:
            continue
        matching = [
            index
            for index in range(event_start, len(state.events))
            if state.events[index].actor_entity_id == actor.id
            and state.events[index].action == action_id
            and state.events[index].target == state.fighters[target_key].id
        ]
        if not matching:
            continue
        event_index = matching[-1]
        target_events = [state.events[index] for index in matching]
        if spec.trigger == "successful_direct_hit" and not any(
            not event.dodged for event in target_events
        ):
            state.events[event_index] = replace(
                state.events[event_index],
                effect_removal_component=spec.kind,
                effect_removal_result="missed",
            )
            continue
        selections = selected_by_target.get(target_key, [])
        removed = []
        for selection_id in selections:
            result = _remove_selected_effect_component(
                state, target_key, selection_id, spec.kind
            )
            if result is not None:
                removed.append(
                    (
                        result[0],
                        result[1],
                        _remaining_effect_stack_count(state, target_key, selection_id),
                    )
                )
        if removed:
            effect_ids = tuple(result[0] for result in removed)
            removal_kinds = tuple(result[1] for result in removed)
            remaining_stacks = tuple(result[2] for result in removed)
            result_label = "removed"
        else:
            effect_ids = ()
            removal_kinds = ()
            remaining_stacks = ()
            result_label = "no_eligible_effect"
        state.events[event_index] = replace(
            state.events[event_index],
            effect_removal_component=spec.kind,
            effect_removal_result=result_label,
            removed_effect_ids=effect_ids,
            effect_removal_kinds=removal_kinds,
            remaining_effect_stacks=remaining_stacks,
            effect_removal_kind=removal_kinds[0] if removal_kinds else None,
        )


def act(
    state: Combat,
    action: str,
    *,
    target_id: str | None = None,
    actor_key: str | None = None,
    effect_id: str | None = None,
    effect_selections: tuple[tuple[str, str], ...] = (),
) -> Combat:
    """Resolve one player action; invalid action/target intentions are a no-op."""
    actor_key = actor_key or active_player_key(state)
    if actor_key is None:
        return state
    if (
        not state.party_mode
        and len(action) == 2
        and action[0] == "a"
        and action[1] in "123"
        and isinstance(state.configuration_snapshot, dict)
    ):
        slot = int(action[1])
        for entry in state.configuration_snapshot.get("active_arts", ()):
            if isinstance(entry, dict) and entry.get("slot") == slot:
                action = str(entry.get("art_id", action))
                break
    if action not in allowed_actions(state, actor_key):
        return state
    actions = player_actions_for(state, actor_key)
    action_definition = actions.get(action)
    effect_removal_plan: tuple[tuple[str, str], ...] = ()
    target_keys: tuple[str, ...] = ()
    if action_definition is not None:
        target_keys = _resolve_action_targets(state, actor_key, action_definition, target_id)
        if not target_keys:
            return state
        valid_removal, effect_removal_plan = _prepare_action_effect_removal(
            state,
            action_definition,
            target_keys,
            actor_key=actor_key,
            effect_id=effect_id,
            effect_selections=effect_selections,
        )
        if not valid_removal:
            return state
    elif effect_id is not None or effect_selections:
        return state
    with localcontext() as ctx:
        ctx.prec = PRECISION
        updated = deepcopy(state)
        if updated.tutorial and updated.tutorial_stage != "normal":
            updated.pending_response = updated.tutorial.responses.get(action)
        event_start = len(updated.events)
        committed = _perform(updated, actor_key, action, target_id=target_id)
        if not committed:
            return state
        if action_definition is not None and action_definition.effect_removal is not None:
            _resolve_action_effect_removal(
                updated,
                actor_key,
                action,
                action_definition,
                effect_removal_plan,
                target_keys,
                event_start=event_start,
            )
        _record_devastador_charge(updated, actor_key, event_start, action)
        updated.used_attack |= action == "attack"
        updated.used_defend |= action == "defend"
        updated.used_art |= action == "art"
        if not updated.result:
            _end_turn(updated)
            _advance_to_player(updated)
        updated.version += 1
        return updated
