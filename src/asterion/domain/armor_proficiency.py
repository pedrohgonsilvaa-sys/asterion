"""Proficiências de Armadura (spec Classes de Armadura v1.0.0 §5).

Four independent, permanent equip authorizations. Veste is the free initial one and
is implicit for every character (no row, no seeding). Like the weapon Proficiência it
grants no attribute: the Esquiva/Bloqueio of the armor class comes from the equipped
piece, not from learning it.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from asterion.domain.regional_equipment import ARMOR_CLASSES

INITIAL_ARMOR_CLASS = "veste"

ARMOR_CLASS_LABELS = MappingProxyType(
    {"veste": "Veste", "leve": "Leve", "media": "Média", "pesada": "Pesada"}
)


@dataclass(frozen=True, slots=True)
class ArmorTerms:
    armor_class: str
    min_level: int
    cost_crowns: int


ARMOR_TERMS = MappingProxyType(
    {
        "veste": ArmorTerms("veste", 1, 0),
        "leve": ArmorTerms("leve", 10, 1_000),
        "media": ArmorTerms("media", 20, 4_000),
        "pesada": ArmorTerms("pesada", 30, 10_000),
    }
)


def parse_armor_class(value: str | None) -> str | None:
    return value if value in ARMOR_CLASSES else None
