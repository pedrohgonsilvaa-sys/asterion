"""Enemy kits for Eventos Públicos and Provações do Juramento.

Source: ``ASTERION_EVENTOS_PUBLICOS_IMPLEMENTACAO_v1_1_0.md`` and
``ASTERION_PROVACOES_JURAMENTO_IMPLEMENTACAO_v1_1_0.md``. Each coefficient is the
midpoint of its GDD v1.6.0 §49.6 band, as those documents fix it. The kit is a
priority list, top to bottom, with the Simples action as fallback; single-target
actions hit the lowest current HP (``target_policy="lowest_hp"``).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from asterion.domain.road import Creature

D = Decimal

SIMPLE = "simple"
STRONG = "strong"
PREPARED = "prepared"
AOE = "aoe"
MULTI_HIT = "multi_hit"
DOT = "dot"
BARRIER = "barrier"

COEFFICIENTS = {
    SIMPLE: D("1.00"),
    STRONG: D("1.325"),
    PREPARED: D("1.70"),
    AOE: D("0.825"),
    DOT: D("0.85"),
    BARRIER: D("0.80"),
}
# Multi-hit: 130% total in two hits of 65%.
MULTI_HIT_HITS = 2
MULTI_HIT_EACH = D("0.65")
BARRIER_DURATION = 2

ATK, DEF, AGI, PER, HEALING = "attack", "defense", "agility", "per", "healing_received"
BURN, BLEED = "burn", "bleed"


@dataclass(frozen=True, slots=True)
class KitAction:
    key: str
    name: str
    kind: str
    cooldown: int | None = None
    # Debuff on the target: stat, magnitude (fraction, or p.p. for PER) and turns.
    stat: str | None = None
    magnitude: Decimal = D(0)
    duration: int = 0
    dot: str | None = None
    # "HP próprio ≤ X%".
    hp_at_most: Decimal | None = None
    # "2+ alvos válidos".
    group_only: bool = False
    # Skip targets that already have this action's debuff or DoT at the cap.
    conditional: bool = True

    def effect_id(self) -> str | None:
        if self.stat is None:
            return None
        return f"pve.{self.stat}_down_{int(self.magnitude * 100)}"


def debuff(stat: str, percent: int, duration: int = 2) -> dict:
    return {"stat": stat, "magnitude": D(percent) / D(100), "duration": duration}


def _tuple(action: KitAction) -> tuple:
    prepared = action.kind == PREPARED
    coefficient = MULTI_HIT_EACH if action.kind == MULTI_HIT else COEFFICIENTS[action.kind]
    barrier = action.kind == BARRIER
    return (
        action.key,
        action.name,
        D(0) if barrier else coefficient,
        0,
        action.magnitude,
        action.duration,
        action.dot,
        1 if action.dot else 0,
        prepared,
        action.cooldown,
        action.stat,
        D(0),
        coefficient if barrier else D(0),
        BARRIER_DURATION if barrier else 0,
        barrier,
        "self" if barrier else ("all_opponents" if action.kind == AOE else "opponent"),
        None,
        action.hp_at_most,
    )


def _extras(action: KitAction) -> tuple[tuple[str, object], ...]:
    extras: list[tuple[str, object]] = []
    effect_id = action.effect_id()
    if effect_id is not None:
        extras.append(("effect_id", effect_id))
        if action.conditional:
            extras.append(("skip_if_target_effect_active", effect_id))
    if action.dot is not None and action.conditional:
        extras.append(("skip_if_target_dot_at_cap", action.dot))
    if action.kind == MULTI_HIT:
        extras.append(("hit_count", MULTI_HIT_HITS))
    if action.group_only:
        extras.append(("min_living_opponents", 2))
    return tuple(extras)


def kit_creature(
    creature_id: str,
    name: str,
    category: str,
    archetype: str,
    actions: tuple[KitAction, ...],
) -> Creature:
    """Priority is the table order; the last action is the fallback and has no CD."""
    fallback = actions[-1]
    if fallback.cooldown is not None or fallback.kind == PREPARED:
        raise ValueError(f"{creature_id}: the fallback action must have no Recarga.")
    if len({action.key for action in actions}) != len(actions):
        raise ValueError(f"{creature_id}: action keys must be unique.")
    extras = tuple((action.key, _extras(action)) for action in actions if _extras(action))
    return Creature(
        creature_id,
        name,
        category,
        archetype,
        1,
        60,
        0,
        (fallback.key,),
        tuple(_tuple(action) for action in actions),
        ai_priority=tuple(action.key for action in actions[:-1]),
        action_extras=extras,
        target_policy="lowest_hp",
    )
