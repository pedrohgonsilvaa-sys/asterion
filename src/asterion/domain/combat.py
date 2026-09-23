"""Reusable deterministic duel engine. Inputs and outputs are pure domain snapshots."""

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal, localcontext
from uuid import UUID

from asterion.domain.combat_math import PRECISION, CombatRng, Stats, direct_damage, stable_priority

D = Decimal


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


@dataclass
class DotState:
    kind: str
    stacks: int
    remaining: int
    snapshot_attack: Decimal
    source: str
    stack_snapshots: list[Decimal] = field(default_factory=list)


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

    def stat(self, name: str) -> Decimal:
        value = getattr(self.stats, name)
        for effect in self.effects:
            if effect.stat == name:
                value *= (
                    D(1) - effect.magnitude if effect.kind == "debuff" else D(1) + effect.magnitude
                )
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


def apply_effect(state: Combat, target: Fighter, effect: Effect) -> None:
    """Target-owned duration: future opportunities only, never the applying turn."""
    effect = deepcopy(effect)
    rng = CombatRng(state.id, state.rng_cursor)
    if target.race == "velado" and effect.duration_eligible and effect.remaining >= 2:
        if rng.chance(D("0.25"), f"racial-duration:{target.id}:{effect.id}"):
            effect.remaining += 1 if effect.kind == "buff" else -1
    if target.race == "alvorano" and effect.kind == "debuff" and effect.removable:
        effect.magnitude *= D("0.88")
    state.rng_cursor = rng.cursor
    effect.applied_opportunity = target.opportunity
    target.effects.append(effect)


def _begin_turn(state: Combat) -> None:
    actor = state.fighters[state.order[state.turn_index]]
    actor.opportunity += 1
    actor.defending = False
    if actor.id == "player" and state.prepared_action is not None:
        state.response_window_seen = True


def _end_turn(state: Combat) -> None:
    actor = state.fighters[state.order[state.turn_index]]
    for dot in state.dot_states.get(actor.id, []):
        coefficient = D("0.12") if dot.kind == "poison" else D("0.10")
        snapshots = dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks
        damage = int(
            sum((snapshot * coefficient for snapshot in snapshots), D(0)).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        actor.hp = max(D(0), actor.hp - D(damage))
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
                recoil = (
                    dot.snapshot_attack * D("0.03") * dot.stacks
                ).to_integral_value(rounding=ROUND_FLOOR)
                actor.hp = max(D(0), actor.hp - recoil)
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
    actual_damage = min(target.hp, D(damage))
    target.hp -= actual_damage
    healed = D(0)
    if actor.race == "hemario" and actor.hp <= actor.stats.hp * D("0.40"):
        healed = min(
            actual_damage * D("0.12"), actor.stats.hp * D("0.03"), actor.stats.hp - actor.hp
        ).to_integral_value(rounding=ROUND_FLOOR)
        healed = max(D(0), healed)
        actor.hp += healed
    if action.attack_debuff and target.hp > 0:
        apply_effect(
            state,
            target,
            Effect(
                id=action.id,
                stat="attack",
                magnitude=action.attack_debuff,
                remaining=action.duration,
                applied_opportunity=target.opportunity,
            ),
        )
    # Variant riders are attached only to real direct offensive hits.  Native
    # bleed from Investida Rasgante occupies the same per-action slot.
    if actor_id == "enemy" and actual_damage > 0:
        rider = (
            "bleed" if state.variant == "hemorrhagic"
            else "poison" if state.variant == "venomous" else None
        )
        native = "bleed" if action_id == "rend" else None
        chosen = native or rider
        states = state.dot_states.setdefault(target.id, [])
        existing = next((dot for dot in states if dot.kind == chosen), None) if chosen else None
        if chosen:
            snapshot = actor.stat("attack")
            if existing is None:
                states.append(
                    DotState(
                        chosen,
                        1,
                        3 if chosen == "poison" else 2,
                        snapshot,
                        actor.id,
                        [snapshot],
                    )
                )
            else:
                snapshots = list(
                    existing.stack_snapshots
                    or [existing.snapshot_attack] * existing.stacks
                )
                if len(snapshots) >= 3:
                    snapshots.pop(0)
                snapshots.append(snapshot)
                existing.stack_snapshots = snapshots
                existing.snapshot_attack = snapshots[0]
                existing.stacks = len(snapshots)
                existing.remaining = 3 if chosen == "poison" else 2
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
            action.id if action.attack_debuff else "",
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


def _finish_consumable_turn(state: Combat, action: str, healed: Decimal = D(0)) -> Combat:
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
            "player",
            healed=healed,
        )
    )
    if not state.result:
        _end_turn(state)
        _advance_to_player(state)
    state.version += 1
    return state


def use_heal_consumable(state: Combat) -> Combat:
    """Apply the official 22% HP-Max heal as a normal player action."""
    if not consumable_available(state):
        return state
    with localcontext() as ctx:
        ctx.prec = PRECISION
        updated = deepcopy(state)
        player = updated.fighters["player"]
        multiplier = D(1)
        for effect in player.effects:
            if effect.kind == "debuff" and effect.removable and effect.stat == "healing_received":
                multiplier *= max(D(0), D(1) - effect.magnitude)
        amount = (player.stats.hp * D("0.22") * multiplier).to_integral_value(
            rounding=ROUND_FLOOR
        )
        healed = min(max(D(0), amount), player.stats.hp - player.hp)
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
            if effect.kind != "debuff" or not effect.removable:
                return state
            player.effects.pop(effect_index)
        return _finish_consumable_turn(updated, "consumable:purify")


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
