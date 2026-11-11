"""Evento Mundial of Crônica I: O Compasso (proposal v0.2 §0.3.8, §8, §11.5).

During the Crônica (Day 1 .. T) every normal Event slot (GDD §49.15) runs O Compasso, one
version per Region band, all at the same time (author decisions, 2026-11-09 and
2026-11-11). Until chapter 7 opens (D43) the slot is ``evt_cr01_ressonancia``; from then
on it is ``evt_cr01_ressonancia_plena``. The Event rules are the normal ones (GDD §21,
§49.15): shared HP, 3 phases, normal eligibility and economy.

Each Event phase is its own combat, so the phase gates of the kit are set on the built
combat. The kit is in ``SIMULAR``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal

from asterion.domain.chronicle import Calendar
from asterion.domain.chronicle_content import ALTOS, CONFINS, NARETH, OCASO, VALES, VARZEAS
from asterion.domain.chronicle_encounters import configure_encounter
from asterion.domain.combat import Combat
from asterion.domain.road import (
    CR01_O_COMPASSO,
    CR01_REPETIDOR,
    CreatureCombatantSpec,
    StatMultipliers,
)
from asterion.domain.world_events import (
    ENTRY_WINDOW,
    SCHEDULE_TIMES,
    SCHEDULE_WEEKDAYS,
    WorldEventDefinition,
    WorldEventPhase,
    latest_slot,
    next_slot,
)

D = Decimal

RESSONANCIA = "evt_cr01_ressonancia"
RESSONANCIA_PLENA = "evt_cr01_ressonancia_plena"
EVENT_SOURCE = "rep_cr01_evento"
PLENA_FROM_CHAPTER = 7  # "semanas 7–8": Plena from D43 (author decision, 2026-11-11).

# §11.5: one version per band, event level 10/20/30/40/50/60.
VERSIONS: tuple[tuple[str, int], ...] = (
    (OCASO, 10),
    (VALES, 20),
    (NARETH, 30),
    (VARZEAS, 40),
    (ALTOS, 50),
    (CONFINS, 60),
)

# Which Event each Evento Mundial objective accepts (§2).
OBJECTIVE_FAMILY: dict[str, str] = {
    "cap_04_obj_03": RESSONANCIA,
    "cap_07_obj_04": RESSONANCIA_PLENA,
    "cap_08_obj_03": RESSONANCIA_PLENA,
}

PHASE_KEYS = ("phase_i", "phase_ii", "phase_iii")
ADD_KEY = "add"
# Plena, Fase 2: Threat 0,30 per valid participant. Each participant fights an own
# instance, so it is 1 Repetidor with HP ×0,30 (author decision, 2026-11-11).
PLENA_ADD_HP_FACTOR = D("0.30")
_SPENT = "cr01.compasso.spent"

# Draft texts (the proposal gives the phase names and the morphology only).
_PHASE_FLAVORS = (
    "Primeira Batida · Uma coluna de matéria pulsa no meio do campo. A cada batida, o chão "
    "em volta afunda e volta.",
    "Compasso · O ritmo acelera. Formas menores se montam dos lados e se desfazem no mesmo tempo.",
    "Batida Final · O chão inteiro afunda e não volta. Tudo em volta bate no ritmo dele.",
)
_CONCLUSION = "A coluna se desfaz em pedaços de formas menores. O chão para de afundar."
_NAMES = {RESSONANCIA: "Ressonância", RESSONANCIA_PLENA: "Ressonância Plena"}
_VERSION_CODES = {RESSONANCIA: "cr01r", RESSONANCIA_PLENA: "cr01p"}


def _definition(family: str, index: int, region: str, level: int) -> WorldEventDefinition:
    version = f"{_VERSION_CODES[family]}{index}"
    return WorldEventDefinition(
        f"{family}.{index}",
        _NAMES[family],
        region,
        level,
        tuple(WorldEventPhase(CR01_O_COMPASSO, flavor) for flavor in _PHASE_FLAVORS),
        _CONCLUSION,
        attuned=True,  # Sintonização do Véu for veterans in lower versions (§11.5).
        family=family,
        version=version,
    )


DEFINITIONS: dict[str, tuple[WorldEventDefinition, ...]] = {
    family: tuple(
        _definition(family, index, region, level)
        for index, (region, level) in enumerate(VERSIONS, start=1)
    )
    for family in (RESSONANCIA, RESSONANCIA_PLENA)
}
ALL_DEFINITIONS: tuple[WorldEventDefinition, ...] = tuple(
    definition for versions in DEFINITIONS.values() for definition in versions
)


def family_for_slot(calendar: Calendar, slot: datetime) -> str | None:
    """The Crônica Event of a slot, or ``None`` outside Day 1 .. T."""
    if not calendar.starts_at <= slot < calendar.end_at:
        return None
    if slot >= calendar.chapter_opens_at(PLENA_FROM_CHAPTER):
        return RESSONANCIA_PLENA
    return RESSONANCIA


def definitions_for_slot(calendar: Calendar, slot: datetime) -> tuple[WorldEventDefinition, ...]:
    family = family_for_slot(calendar, slot)
    return DEFINITIONS[family] if family is not None else ()


def next_chronicle_slot(calendar: Calendar, now: datetime) -> datetime | None:
    """The next O Compasso slot after ``now``, before T."""
    slot = next_slot(max(now, calendar.starts_at - timedelta(seconds=1)))
    return slot if slot < calendar.end_at else None


@dataclass(frozen=True, slots=True)
class NextOccurrence:
    at: datetime
    live: bool  # entry is open now


def next_occurrence(calendar: Calendar, family: str, now: datetime) -> NextOccurrence | None:
    """The open slot of ``family`` (entry window) or the next one, before T."""
    current = latest_slot(now)
    if (
        current is not None
        and now < current + ENTRY_WINDOW
        and family_for_slot(calendar, current) == family
    ):
        return NextOccurrence(current, True)
    moment = now
    # 6 slots a week (3 days x 2 times); the Crônica lasts 8 weeks.
    for _ in range(len(SCHEDULE_WEEKDAYS) * len(SCHEDULE_TIMES) * 9):
        slot = next_slot(moment)
        if slot >= calendar.end_at:
            return None
        if family_for_slot(calendar, slot) == family:
            return NextOccurrence(slot, False)
        moment = slot
    return None


# ------------------------------------------------------------------- combat


def enemy_specs(
    definition: WorldEventDefinition, phase: int, base: CreatureCombatantSpec
) -> tuple[CreatureCombatantSpec, ...]:
    """The Chefe, plus the Plena Repetidor in Fase 2 (optional, no XP)."""
    if definition.family != RESSONANCIA_PLENA or phase != 2:
        return (base,)
    add = CreatureCombatantSpec(
        CR01_REPETIDOR,
        definition.reference_level,
        ADD_KEY,
        stat_multipliers=StatMultipliers(PLENA_ADD_HP_FACTOR, D(1), D(1), D(1)),
        required_for_victory=False,
    )
    return (base, add)


def configure_compasso(combat: Combat, phase: int, *, resonance: bool) -> Combat:
    """Phase gates of §11.5 on the combat of one Event phase.

    Fase 1: Batida and Contratempo. Fase 2: + Onda de Compasso and Batida Plena.
    Fase 3: Ressonância on entry, everything available. ``resonance`` is False when the
    participant already had a Fase 3 instance (once per participant, author decision,
    2026-11-11).
    """
    configure_encounter(combat)  # Contratempo DEF mark, Repetidor multi-hit.
    combat.phase_id = PHASE_KEYS[phase - 1]
    for key, action in list(combat.enemy_actions.items()):
        if key.endswith("onda_de_compasso") or key.endswith("batida_plena"):
            combat.enemy_actions[key] = replace(action, phase_ids=PHASE_KEYS[1:])
        elif key.endswith("ressonancia"):
            gate = (PHASE_KEYS[2],) if resonance else (_SPENT,)
            combat.enemy_actions[key] = replace(action, phase_ids=gate)
    return combat
