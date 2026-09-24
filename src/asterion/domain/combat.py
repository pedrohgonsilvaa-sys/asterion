"""Reusable deterministic duel engine. Inputs and outputs are pure domain snapshots."""

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal, localcontext
from uuid import UUID

from asterion.domain.combat_math import (
    PRECISION,
    CombatRng,
    Stats,
    direct_damage,
    dot_damage,
    stable_priority,
)
from asterion.domain.consumables import ConsumableFamily, UseContext, definition

D = Decimal
ZERO = D(0)


@dataclass
class Effect:
    id: str
    stat: str
    magnitude: Decimal
    remaining: int
    applied_opportunity: int
    kind: str = "debuff"
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
class Action:
    id: str
    name: str
    coefficient: Decimal
    blocked_opportunities: int = 0
    attack_debuff: Decimal = D(0)
    duration: int = 0


@dataclass
class Fighter:
    id: str
    name: str
    level: int
    stats: Stats
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

    def stat(self, name: str) -> Decimal:
        value = getattr(self.stats, name)
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
    prepared_action: str | None = None
    prepared_source: str | None = None
    prepared_target: str | None = None
    resolving_prepared: bool = False
    response_window_seen: bool = False
    variant: str | None = None
    dot_states: dict[str, list[DotState]] = field(default_factory=dict)
    effect_sequence: int = 0
    application_sequence: int = 0
    blocked_application_events: list[str] = field(default_factory=list)
    consumable_uses: int = 0

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


def initiative(state: Combat) -> tuple[str, ...]:
    return tuple(
        sorted(
            state.fighters,
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
    if item is None or target_id not in state.fighters:
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
    else:
        target.barrier = D(0)
        target.barrier_remaining = 0
        target.barrier_source = ""
    hp_damage = min(max(D(0), target.hp), incoming - absorbed)
    target.hp = max(D(0), target.hp - hp_damage)
    return hp_damage, absorbed


def _begin_turn(state: Combat) -> None:
    actor = state.fighters[state.order[state.turn_index]]
    actor.opportunity += 1
    actor.defending = False
    if actor.id == "player" and state.prepared_action is not None:
        state.response_window_seen = True


def _end_turn(state: Combat) -> None:
    actor = state.fighters[state.order[state.turn_index]]
    for dot in state.dot_states.get(actor.id, []):
        coefficient = (
            D("0.12")
            if dot.kind == "poison"
            else D("0.15")
            if dot.kind == "burn"
            else D("0.10")
        )
        snapshots = dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks
        source = state.fighters.get(dot.source)
        attacker_level = source.level if source is not None else actor.level
        damage = dot_damage(
            snapshots,
            coefficient,
            actor.stat("defense"),
            attacker_level,
        )
        _deal_damage(actor, damage)
        dot.remaining -= 1
    state.dot_states[actor.id] = [
        dot for dot in state.dot_states.get(actor.id, []) if dot.remaining > 0
    ]
    if actor.hp == 0 and not state.result:
        state.result = "defeat" if actor.id == "player" else "victory"
    for effect in actor.effects:
        if actor.opportunity > effect.applied_opportunity:
            effect.remaining -= 1
    actor.effects = [effect for effect in actor.effects if effect.remaining > 0]
    if actor.opportunity > actor.barrier_applied_opportunity and actor.barrier_remaining > 0:
        actor.barrier_remaining -= 1
        if actor.barrier_remaining == 0:
            actor.barrier = D(0)
            actor.barrier_source = ""
    if actor.opportunity > actor.ward_applied_opportunity and actor.ward_remaining > 0:
        actor.ward_remaining -= 1
        if actor.ward_remaining == 0:
            actor.ward_charges = 0
    state.turn_index += 1
    if state.turn_index == len(state.order):
        state.round += 1
        state.order = initiative(state)
        state.turn_index = 0
    _begin_turn(state)


def _perform(state: Combat, actor_id: str, action_id: str) -> None:
    actor = state.fighters[actor_id]
    target = state.fighters["enemy" if actor_id == "player" else "player"]
    if action_id == "hold":
        actor.last_action = "hold"
        state.events.append(CombatEvent(len(state.events), state.round, actor_id, action_id))
        return
    if action_id == "defend":
        actor.defending = True
        actor.last_action = action_id
        state.events.append(CombatEvent(len(state.events), state.round, actor_id, action_id))
        return
    if actor_id == "player" or actor_id == "enemy":
        for dot in state.dot_states.get(actor.id, []):
            if dot.kind == "bleed":
                snapshots = dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks
                recoil = (
                    sum(snapshots, D(0)) * D("0.03")
                ).to_integral_value(rounding=ROUND_FLOOR)
                _deal_damage(actor, recoil)
        if actor.hp == 0:
            state.result = "defeat" if actor_id == "player" else "victory"
            return
    actions = state.player_actions if actor_id == "player" else state.enemy_actions
    action = actions[action_id]
    if actor_id == "enemy" and action_id == "leap" and not state.resolving_prepared:
        state.prepared_action = action_id
        state.prepared_source = actor_id
        state.prepared_target = target.id
        state.response_window_seen = False
        actor.last_action = f"prepare:{action_id}"
        actor.cooldowns[action_id] = actor.opportunity + action.blocked_opportunities + 1
        state.events.append(
            CombatEvent(len(state.events), state.round, actor_id, f"prepare:{action_id}")
        )
        return
    rng = CombatRng(state.id, state.rng_cursor)
    critical = rng.chance(D("0.05"), f"critical:{actor_id}:{action_id}")
    state.rng_cursor = rng.cursor
    mitigation = D(0)
    if target.defending:
        mitigation = D("0.52") if target.race == "cinereo" else D("0.45")
    damage = direct_damage(
        actor.stat("attack"),
        action.coefficient,
        target.stat("defense"),
        actor.level,
        critical=critical,
        mitigation=mitigation,
    )
    actual_damage, barrier_absorbed = _deal_damage(target, damage)
    healed = D(0)
    if actor.race == "hemario" and actor.hp <= actor.stats.hp * D("0.40"):
        healed = min(
            actual_damage * D("0.12"), actor.stats.hp * D("0.03"), actor.stats.hp - actor.hp
        ).to_integral_value(rounding=ROUND_FLOOR)
        healed = max(D(0), healed)
        actor.hp += healed
    ward_blocked: list[str] = []
    status_applied = False
    if action.attack_debuff and target.hp > 0:
        had_ward = target.ward_charges > 0 and target.ward_remaining > 0
        status_applied = apply_effect(
            state,
            target,
            Effect(
                id=action.id,
                stat="attack",
                magnitude=action.attack_debuff,
                remaining=action.duration,
                applied_opportunity=target.opportunity,
            ),
            application_event=(
                f"{state.id.hex}:{state.version}:{len(state.events)}:effect:{action.id}"
            ),
        )
        if had_ward and not status_applied and target.ward_charges == 0:
            ward_blocked.append(action.id)
    # Variant riders are attached only to real direct offensive hits.  Native
    # bleed from Investida Rasgante occupies the same per-action slot.
    if actor_id == "enemy" and damage > 0 and target.hp > 0:
        rider = (
            "bleed" if state.variant == "hemorrhagic"
            else "poison" if state.variant == "venomous" else None
        )
        native = "bleed" if action_id == "rend" else None
        chosen = native or rider
        if chosen:
            snapshot = actor.stat("attack")
            had_ward = target.ward_charges > 0 and target.ward_remaining > 0
            applied = apply_dot_stacks(
                state,
                target,
                kind=chosen,
                snapshots=[snapshot],
                source=actor.id,
                duration=3 if chosen == "poison" else 2,
                application_event=(
                    f"{state.id.hex}:{state.version}:{len(state.events)}:dot:{chosen}"
                ),
            )
            if had_ward and not applied and target.ward_charges == 0:
                ward_blocked.append(chosen)
    actor.last_action = action_id
    if action.blocked_opportunities:
        actor.cooldowns[action_id] = actor.opportunity + action.blocked_opportunities + 1
    state.events.append(
        CombatEvent(
            len(state.events),
            state.round,
            actor_id,
            action_id,
            target.id,
            damage,
            critical,
            healed,
            action.id if status_applied else "",
            barrier_absorbed=barrier_absorbed,
        )
    )
    for effect_id in ward_blocked:
        state.events.append(
            CombatEvent(
                len(state.events),
                state.round,
                target.id,
                "resguardo:block",
                target.id,
                effect_id=effect_id,
            )
        )
    if target.hp == 0:
        state.result = "victory" if actor_id == "player" else "defeat"
    state.resolving_prepared = False


def _enemy_action(state: Combat) -> str:
    if state.pending_response is not None:
        action = state.pending_response
        state.pending_response = None
        return action
    if state.prepared_action is not None and state.response_window_seen:
        action = state.prepared_action
        state.prepared_action = None
        state.resolving_prepared = True
        state.response_window_seen = False
        return action
    if state.prepared_action is not None:
        return "hold"
    enemy = state.fighters["enemy"]
    # Alfa Cinéreo uses content priority rather than a positional cycle.
    if {"rend", "leap", "bite"}.issubset(state.enemy_actions):
        bleed_count = next(
            (dot.stacks for dot in state.dot_states.get("player", []) if dot.kind == "bleed"),
            0,
        )
        if enemy.cooldowns.get("rend", 0) <= enemy.opportunity and bleed_count == 0:
            return "rend"
        if enemy.cooldowns.get("leap", 0) <= enemy.opportunity:
            return "leap"
        if enemy.cooldowns.get("rend", 0) <= enemy.opportunity and bleed_count < 3:
            return "rend"
        return "bite"
    for _ in range(len(state.ai_cycle)):
        action = state.ai_cycle[state.ai_position]
        state.ai_position = (state.ai_position + 1) % len(state.ai_cycle)
        if enemy.cooldowns.get(action, 0) <= enemy.opportunity:
            return action
    return state.ai_cycle[state.ai_position]


def _advance_to_player(state: Combat) -> None:
    while not state.result and state.order[state.turn_index] != "player":
        _perform(state, "enemy", _enemy_action(state))
        if not state.result:
            _end_turn(state)


def start_combat(state: Combat) -> Combat:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        state = deepcopy(state)
        state.order = initiative(state)
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
            for dot in state.dot_states.get(target_id, ())
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
        barrier_value = (player.stats.hp * D("0.12")).to_integral_value(
            rounding=ROUND_FLOOR
        )
        if barrier_value <= 0:
            return state
        player.barrier = barrier_value
        player.barrier_remaining = 2
        player.barrier_applied_opportunity = player.opportunity
        player.barrier_source = "player:consumable.protecao"
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
        barrier_value=barrier_value,
    )


def act(state: Combat, action: str) -> Combat:
    """Invalid intentions are a no-op; application also checks ownership/version."""
    if action not in allowed_actions(state):
        return state
    with localcontext() as ctx:
        ctx.prec = PRECISION
        state = deepcopy(state)
        if state.tutorial and state.tutorial_stage != "normal":
            state.pending_response = state.tutorial.responses.get(action)
        _perform(state, "player", action)
        state.used_attack |= action == "attack"
        state.used_defend |= action == "defend"
        state.used_art |= action == "art"
        if not state.result:
            _end_turn(state)
            _advance_to_player(state)
        state.version += 1
        return state
