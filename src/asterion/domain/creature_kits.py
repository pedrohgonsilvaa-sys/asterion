"""Kits for Event and Provação creatures (briefing de conteúdo, 2026-11).

The authored content names a creature, a profile and three actions in words. No
number is new here: every action below repeats one that a creature already in the
game uses (``road.py``), picked by profile:

- strike:  Golpe da Última Trilha (1.00, no cooldown);
- mark:    Marca do Rastro (0.90, mark 0.10 for 2 turns, cooldown 3);
- poison:  Picada Tóxica da Aranha de Cinza (0.80, poison, cooldown 2);
- bleed:   Dilacerar do Carniçal de Fuligem (0.90, bleed, cooldown 2);
- charge:  Arrancada do Carniçal de Fuligem (1.25, cooldown 3);
- guard:   Guarda do Poente (barrier 0.90 for 2 turns, cooldown 3);
- heavy:   Queda da Travessia (1.65) or Queda do Poente (1.70), telegraphed, cooldown 4.

The balancing pass decides later whether any of them needs adjusting.
"""

from __future__ import annotations

from decimal import Decimal

from asterion.domain.road import Creature

D = Decimal

# Content profile (Portuguese) -> engine archetype.
PROFILE_ARCHETYPE = {
    "Bruto": "brute",
    "Equilibrado": "balanced",
    "Ágil": "predator",
    "Blindado": "armored",
    "Controlador": "controller",
}


def build_creature(
    creature_id: str,
    name: str,
    category: str,
    profile: str,
    level: int,
    labels: tuple[str, str, str],
) -> Creature:
    """A creature whose three actions are called ``labels`` (strike, special, heavy)."""
    if category not in {"elite", "boss"}:
        raise ValueError("Event and Provação creatures are Elite or Chefe.")
    archetype = PROFILE_ARCHETYPE[profile]
    strike_name, special_name, heavy_name = labels
    strike = ("strike", strike_name, D("1.00"), 0, D(0), 0)
    heavy_power = D("1.65") if category == "boss" else D("1.70")
    heavy = ("heavy", heavy_name, heavy_power, 0, D(0), 0, None, 0, True, 4)
    if archetype == "balanced":
        special = (
            "special", special_name, D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "agility",
        )
        ai = ("special", "strike", "strike", "heavy")
        priority = ("special", "heavy")
    elif archetype == "controller":
        special = ("special", special_name, D("0.80"), 0, D(0), 0, "poison", 1, False, 2)
        ai = ("special", "strike", "special", "heavy")
        priority = ("special", "heavy")
    elif archetype == "armored":
        special = (
            "special", special_name, D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.90"),
            2, True,
        )
        ai = ("strike", "special", "strike", "heavy")
        priority = ("special", "heavy")
    elif archetype == "brute":
        special = ("special", special_name, D("0.90"), 0, D(0), 0, "bleed", 1, False, 2)
        heavy = ("heavy", heavy_name, D("1.25"), 0, D(0), 0, None, 0, False, 3)
        ai = ("special", "strike", "heavy", "strike")
        priority = ()
    else:  # predator (Ágil)
        special = ("special", special_name, D("0.90"), 0, D(0), 0, "bleed", 1, False, 2)
        ai = ("strike", "special", "strike", "heavy")
        priority = ("heavy",)
    return Creature(
        creature_id,
        name,
        category,
        archetype,
        level,
        level,
        0,
        ai,
        (strike, special, heavy),
        ai_priority=priority,
    )
