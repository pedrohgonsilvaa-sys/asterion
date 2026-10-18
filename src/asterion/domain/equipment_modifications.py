"""Pure equipment modification rules shared by services and combat snapshots.

No inventory or currency is changed here. Values and rounding come from the
GDD 24–25 and 49, with regional component families from TDO and Vales.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from hashlib import sha256
from typing import Any

from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.equipment import assignment_for_item_slot

D = Decimal

SLOT_WEIGHTS = {
    "Principal": 18,
    "Secundária": 10,
    "Cabeça": 10,
    "Torso": 16,
    "Mãos": 10,
    "Pés": 10,
    "Acessório": 12,
    "Artefato": 14,
    "2H": 28,
}
ECONOMY_SW = {
    "Principal": 2,
    "Secundária": 1,
    "Cabeça": 1,
    "Torso": 2,
    "Mãos": 1,
    "Pés": 1,
    "Acessório": 2,
    "Artefato": 2,
    "2H": 3,
}
ENHANCEMENT_BASE = (30, 60, 100, 160, 240, 340)
ENHANCEMENT_RARITY_COST = {
    "Comum": D("1.00"),
    "Raro": D("1.05"),
    "Épico": D("1.15"),
    "Lendário": D("1.30"),
    "Mítico": D("1.60"),
}
ENHANCEMENT_STEP_FACTOR = (
    D("1.0"), D("1.1"), D("1.2"), D("1.4"), D("1.6"),
    D("1.9"), D("2.2"), D("2.6"), D("3.1"), D("3.7"),
)
ENHANCEMENT_FRAGMENTS_PER_SW = (1, 1, 1, 1, 2, 2, 3, 3, 4, 5)

COMPONENT_POOLS = {
    "Principal": frozenset({"ATQ", "AGI", "PER", "CRIT"}),
    "Secundária": frozenset({"ATQ", "DEF", "PER", "CRIT", "Bloqueio"}),
    "Cabeça": frozenset({"HP", "DEF", "PER", "CRIT"}),
    "Torso": frozenset({"HP", "DEF", "Bloqueio"}),
    "Mãos": frozenset({"ATQ", "DEF", "AGI", "PER", "CRIT"}),
    "Pés": frozenset({"HP", "DEF", "AGI", "Esquiva"}),
    "Acessório": frozenset({"HP", "ATQ", "AGI", "PER", "CRIT", "Esquiva"}),
    "Artefato": frozenset({"HP", "ATQ", "DEF", "PER", "CRIT", "Bloqueio"}),
}
RUNE_FAMILIES = {
    "Brasa": ("ATQ", "Runa da Brasa"),
    "Pedra": ("DEF", "Runa da Pedra"),
    "Caminhante": ("AGI", "Runa do Caminhante"),
    "Fresta": ("PER", "Runa da Fresta"),
    "Presságio": ("CRIT", "Runa do Presságio"),
    "Persistência": ("HP", "Runa da Persistência"),
    "Desvio": ("Esquiva", "Runa do Desvio"),
    "Guarda": ("Bloqueio", "Runa da Guarda"),
    "Espinho": ("ATQ", "Runa do Espinho"),
    "Casca": ("DEF", "Runa da Casca"),
    "Copas": ("AGI", "Runa das Copas"),
    "Nó": ("PER", "Runa do Nó"),
    "Caçada": ("CRIT", "Runa da Caçada"),
    "Seiva": ("HP", "Runa da Seiva"),
    "Névoa": ("Esquiva", "Runa da Névoa"),
    "Raízes": ("Bloqueio", "Runa das Raízes"),
    "Meridiano": ("ATQ", "Runa do Meridiano"),
    "Prumo": ("DEF", "Runa do Prumo"),
    "Horizonte": ("AGI", "Runa do Horizonte"),
    "Marco": ("PER", "Runa do Marco"),
    "Distância": ("CRIT", "Runa da Distância"),
    "Abrigo": ("HP", "Runa do Abrigo"),
    "Referência": ("Bloqueio", "Runa da Referência"),
    "Dique": ("ATQ", "Runa do Dique"),
    "Contenção": ("DEF", "Runa da Contenção"),
    "Junco": ("AGI", "Runa do Junco"),
    "Triagem": ("PER", "Runa da Triagem"),
    "Emergência": ("CRIT", "Runa da Emergência"),
    "Restituição": ("HP", "Runa da Restituição"),
    "Margem": ("Esquiva", "Runa da Margem"),
    "Válvula": ("Bloqueio", "Runa da Válvula"),
}
ENCHANTMENT_FAMILIES = {
    "Fio Cinéreo": "ATQ",
    "Pele de Pedra": "DEF",
    "Passo de Fuligem": "AGI",
    "Marca da Fresta": "PER",
    "Eco do Presságio": "CRIT",
    "Sopro Persistente": "HP",
    "Véu de Desvio": "Esquiva",
    "Selo de Guarda": "Bloqueio",
    "Eco do Vigia Partido": "PER",
    "Fio Enredado": "ATQ",
    "Pele de Casca": "DEF",
    "Passo das Copas": "AGI",
    "Marca do Nó": "PER",
    "Eco da Caçada": "CRIT",
    "Sopro de Seiva": "HP",
    "Véu da Mata": "Esquiva",
    "Selo das Raízes": "Bloqueio",
    "Seiva da Matriarca": "HP",
    "Fio do Meridiano": "ATQ",
    "Pele do Prumo": "DEF",
    "Passo do Horizonte": "AGI",
    "Marca de Referência": "PER",
    "Eco da Distância": "CRIT",
    "Sopro do Posto": "HP",
    "Véu do Desvio": "Esquiva",
    "Selo do Eixo": "Bloqueio",
    "Calibração do Arconte": "PER",
    "Fio do Dique": "ATQ",
    "Pele de Contenção": "DEF",
    "Passo de Junco": "AGI",
    "Marca de Triagem": "PER",
    "Eco de Emergência": "CRIT",
    "Sopro de Restituição": "HP",
    "Véu da Margem": "Esquiva",
    "Selo da Válvula": "Bloqueio",
    "Regulação da Matriz": "HP",
    "Continuidade do Colosso": "Bloqueio",
}
RUNE_GRADE_VI = {
    "HP": (D("0.60"), D("0.80"), D("1.00")),
    "ATQ": (D("0.60"), D("0.80"), D("1.00")),
    "DEF": (D("1.00"), D("1.40"), D("1.80")),
    "AGI": (D("1.00"), D("1.40"), D("1.80")),
    "PER": (D("0.50"), D("0.75"), D("1.00")),
    "CRIT": (D("0.50"), D("0.75"), D("1.00")),
    "Esquiva": (D("0.25"), D("0.50"), D("0.50")),
    "Bloqueio": (D("0.50"), D("0.75"), D("1.00")),
}
ENCHANTMENT_GRADE_VI = {
    "HP": (D("0.20"), D("0.35"), D("0.50")),
    "ATQ": (D("0.20"), D("0.35"), D("0.50")),
    "DEF": (D("0.40"), D("0.70"), D("1.00")),
    "AGI": (D("0.40"), D("0.70"), D("1.00")),
    "PER": (D("0.25"), D("0.50"), D("0.75")),
    "CRIT": (D("0.25"), D("0.50"), D("0.75")),
    "Esquiva": (D("0.25"), D("0.25"), D("0.50")),
    "Bloqueio": (D("0.25"), D("0.50"), D("0.75")),
}
RUNE_GRADE_I = {
    "HP": (D("0.35"), D("0.45"), D("0.55")),
    "ATQ": (D("0.35"), D("0.45"), D("0.55")),
    "DEF": (D("0.55"), D("0.80"), D("1.00")),
    "AGI": (D("0.55"), D("0.80"), D("1.00")),
    "PER": (D("0.25"), D("0.50"), D("0.50")),
    "CRIT": (D("0.25"), D("0.50"), D("0.50")),
    "Esquiva": (D("0.25"), D("0.25"), D("0.25")),
    "Bloqueio": (D("0.25"), D("0.50"), D("0.50")),
}
ENCHANTMENT_GRADE_I = {
    "HP": (D("0.10"), D("0.20"), D("0.30")),
    "ATQ": (D("0.10"), D("0.20"), D("0.30")),
    "DEF": (D("0.20"), D("0.40"), D("0.55")),
    "AGI": (D("0.20"), D("0.40"), D("0.55")),
    "PER": (D("0.25"), D("0.25"), D("0.50")),
    "CRIT": (D("0.25"), D("0.25"), D("0.50")),
    "Esquiva": (D("0.25"), D("0.25"), D("0.25")),
    "Bloqueio": (D("0.25"), D("0.25"), D("0.50")),
}
GRADE_Q = (D("0.556"), D("0.625"), D("0.703"), D("0.791"), D("0.889"), D("1.000"))
SECONDARY_POOLS = {
    "Principal": ("ATQ", "AGI", "PER", "CRIT"),
    "Secundária": ("ATQ", "DEF", "PER", "CRIT", "Bloqueio"),
    "Cabeça": ("HP", "DEF", "PER", "CRIT"),
    "Torso": ("HP", "DEF", "Bloqueio"),
    "Mãos": ("ATQ", "AGI", "PER", "CRIT"),
    "Pés": ("HP", "DEF", "AGI", "Esquiva"),
    "Acessório": ("HP", "ATQ", "AGI", "PER", "CRIT", "Esquiva"),
    "Artefato": ("HP", "ATQ", "DEF", "PER", "CRIT", "Bloqueio"),
}
SECONDARY_SCALE = {
    "HP": D("8.5"), "ATQ": D("1.35"), "DEF": D("2.30"), "AGI": D("3.00"),
    "PER": D("0.80"), "CRIT": D("0.67"), "Esquiva": D("0.33"),
    "Bloqueio": D("0.95"),
}
RARITY_MULT = {
    "Comum": D("1"), "Raro": D("1.07"), "Épico": D("1.15"),
    "Lendário": D("1.24"), "Mítico": D("1.45"),
}
POINT_ATTRIBUTES = frozenset({"PER", "CRIT", "Esquiva", "Bloqueio"})


class EquipmentModificationError(ValueError):
    """A proposed equipment modification contradicts the canonical rules."""


@dataclass(frozen=True, slots=True)
class DismantleQuantities:
    basics: int
    catalysts: int
    fragments: int


def equipment_grade(item_level: int) -> int:
    if isinstance(item_level, bool) or not isinstance(item_level, int) or not 1 <= item_level <= 60:
        raise EquipmentModificationError("Equipment level must be in 1–60.")
    return (item_level - 1) // 10 + 1


def _item_slot(item_slot: str) -> str:
    if item_slot in SLOT_WEIGHTS:
        return item_slot
    assignment = assignment_for_item_slot(item_slot)
    if assignment is None:
        raise EquipmentModificationError("Unknown equipment slot.")
    return assignment.slot.value


def economy_sw(item_slot: str) -> int:
    return ECONOMY_SW[_item_slot(item_slot)]


def enhancement_crown_cost(item_level: int, item_slot: str, rarity: str, target_level: int) -> int:
    grade = equipment_grade(item_level)
    slot = _item_slot(item_slot)
    if rarity not in ENHANCEMENT_RARITY_COST or not 1 <= target_level <= 10:
        raise EquipmentModificationError("Invalid enhancement target or rarity.")
    amount = (
        D(ENHANCEMENT_BASE[grade - 1])
        * D(SLOT_WEIGHTS[slot]) / D(10)
        * ENHANCEMENT_RARITY_COST[rarity]
        * ENHANCEMENT_STEP_FACTOR[target_level - 1]
    )
    return round_10(amount)


def enhancement_fragment_cost(item_slot: str, target_level: int) -> int:
    if not 1 <= target_level <= 10:
        raise EquipmentModificationError("Invalid enhancement target.")
    return ENHANCEMENT_FRAGMENTS_PER_SW[target_level - 1] * economy_sw(item_slot)


def component_effect_pool(item_slot: str, affinity: str = "A") -> frozenset[str]:
    slot = _item_slot(item_slot)
    if slot == "2H":
        if affinity not in {"A", "B"}:
            raise EquipmentModificationError("Unknown two-handed affinity.")
        slot = "Principal" if affinity == "A" else "Secundária"
    elif affinity != "A":
        raise EquipmentModificationError("Normal equipment has one component affinity.")
    return COMPONENT_POOLS[slot]


def rune_compatible(item_slot: str, family: str, affinity: str = "A") -> bool:
    if family not in RUNE_FAMILIES:
        return False
    return RUNE_FAMILIES[family][0] in component_effect_pool(item_slot, affinity)


def enchantment_compatible(item_slot: str, family: str) -> bool:
    if family not in ENCHANTMENT_FAMILIES:
        return False
    effect = ENCHANTMENT_FAMILIES[family]
    return effect in component_effect_pool(item_slot) or (
        _item_slot(item_slot) == "2H" and effect in component_effect_pool(item_slot, "B")
    )


def enchantment_multiplier(item_slot: str, effect: str) -> int:
    """A 2H enchantment doubles only effects compatible with both affinities."""
    if _item_slot(item_slot) != "2H":
        return 1
    both_affinities = component_effect_pool("2H", "A") & component_effect_pool("2H", "B")
    return 2 if effect in both_affinities else 1


def _scaled_potency(
    attribute: str, rarity: str, grade: int, *,
    rarity_names: tuple[str, ...], grade_i: Mapping[str, tuple[Decimal, ...]],
    grade_vi: Mapping[str, tuple[Decimal, ...]],
) -> str:
    if attribute not in grade_vi or rarity not in rarity_names or not 1 <= grade <= 6:
        raise EquipmentModificationError("Unknown component potency.")
    index = rarity_names.index(rarity)
    if grade == 1:
        amount = grade_i[attribute][index]
    elif grade == 6:
        amount = grade_vi[attribute][index]
    else:
        unit = D("0.25") if attribute in POINT_ATTRIBUTES else D("0.05")
        amount = grade_vi[attribute][index] * GRADE_Q[grade - 1]
        amount = max(unit, (amount / unit).quantize(D(1), rounding=ROUND_HALF_UP) * unit)
    suffix = " p.p." if attribute in POINT_ATTRIBUTES else "%"
    return f"{amount:.2f}{suffix}"


def rune_potency_for(family: str, rarity: str, grade: int) -> str:
    try:
        attribute = RUNE_FAMILIES[family][0]
    except KeyError as exc:
        raise EquipmentModificationError("Unknown Rune family.") from exc
    return _scaled_potency(
        attribute, rarity, grade,
        rarity_names=("Rara", "Épica", "Lendária"),
        grade_i=RUNE_GRADE_I, grade_vi=RUNE_GRADE_VI,
    )


def enchantment_potency_for(family: str, rarity: str, grade: int) -> str:
    try:
        attribute = ENCHANTMENT_FAMILIES[family]
    except KeyError as exc:
        raise EquipmentModificationError("Unknown Enchantment family.") from exc
    return _scaled_potency(
        attribute, rarity, grade,
        rarity_names=("Raro", "Épico", "Lendário"),
        grade_i=ENCHANTMENT_GRADE_I, grade_vi=ENCHANTMENT_GRADE_VI,
    )


def effective_enchantment_potency(
    item_slot: str, family: str, rarity: str, grade: int
) -> str:
    """Return the displayed effect, including the shared-affinity 2H bonus."""
    potency = enchantment_potency_for(family, rarity, grade)
    multiplier = enchantment_multiplier(item_slot, ENCHANTMENT_FAMILIES[family])
    suffix = " p.p." if ENCHANTMENT_FAMILIES[family] in POINT_ATTRIBUTES else "%"
    amount = D(potency.removesuffix(suffix)) * multiplier
    return f"{amount:.2f}{suffix}"


def parse_component_potency(value: str, attribute: str) -> Decimal:
    """Return fractional percent for core stats or percentage points for the rest."""
    if not isinstance(value, str):
        raise EquipmentModificationError("Component potency must be exact text.")
    suffix = " p.p." if attribute in POINT_ATTRIBUTES else "%"
    if not value.endswith(suffix):
        raise EquipmentModificationError("Component potency has the wrong unit.")
    try:
        amount = D(value[:-len(suffix)])
    except (ValueError, ArithmeticError) as exc:
        raise EquipmentModificationError("Invalid component potency.") from exc
    if not amount.is_finite() or amount <= 0:
        raise EquipmentModificationError("Invalid component potency.")
    return amount if attribute in POINT_ATTRIBUTES else amount / D(100)


def reroll_crown_cost(item_level: int, current_count: int) -> int:
    equipment_grade(item_level)
    if isinstance(current_count, bool) or not isinstance(current_count, int) or current_count < 0:
        raise EquipmentModificationError("Invalid reroll count.")
    factors = (D("0.50"), D("0.75"), D("1.00"), D("1.50"), D("2.00"))
    return round_10(D(crowns_per_level(item_level)) * factors[min(current_count, 4)])


def _secondary_names(secondaries: Sequence[Mapping[str, Any] | tuple[str, Any]]) -> tuple[str, ...]:
    names = tuple(
        str(value.get("attribute")) if isinstance(value, Mapping) else str(value[0])
        for value in secondaries
    )
    if len(set(names)) != len(names):
        raise EquipmentModificationError("Duplicate secondary attribute.")
    return names


def _stable_uniform_index(seed: str, size: int) -> int:
    """Map a deterministic hash stream uniformly into a finite candidate set."""
    if size < 1:
        raise EquipmentModificationError("Candidate set cannot be empty.")
    space = 1 << 256
    limit = space - (space % size)
    nonce = 0
    while True:
        digest = sha256(f"{seed}:{nonce}".encode()).digest()
        value = int.from_bytes(digest, "big")
        if value < limit:
            return value % size
        nonce += 1


def reroll_candidates(
    item_slot: str, secondaries: Sequence[Mapping[str, Any] | tuple[str, Any]], index: int,
) -> tuple[str, ...]:
    slot = "Principal" if _item_slot(item_slot) == "2H" else _item_slot(item_slot)
    names = _secondary_names(secondaries)
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(names):
        raise EquipmentModificationError("Invalid secondary index.")
    if any(name not in SECONDARY_POOLS[slot] for name in names):
        raise EquipmentModificationError("Secondary attribute does not fit the slot.")
    return tuple(name for name in SECONDARY_POOLS[slot] if name not in names)


def reroll_secondary(
    item_instance_id: str, item_slot: str, rarity: str, item_level: int,
    secondaries: Sequence[Mapping[str, Any] | tuple[str, Any]], index: int, target_count: int,
) -> dict[str, str]:
    """Select one legal identity and recompute its fixed share of item budget."""
    names = _secondary_names(secondaries)
    equipment_grade(item_level)
    if (
        not item_instance_id
        or rarity not in RARITY_MULT
        or len(names) == 0
        or isinstance(target_count, bool)
        or not isinstance(target_count, int)
        or target_count < 1
    ):
        raise EquipmentModificationError("Invalid reroll identity or item.")
    candidates = reroll_candidates(item_slot, secondaries, index)
    if not candidates:
        raise EquipmentModificationError("No legal secondary identity remains.")
    seed = f"{item_instance_id}:{target_count}:{index}"
    draw = _stable_uniform_index(seed, len(candidates))
    attribute = candidates[draw]
    slot = _item_slot(item_slot)
    with localcontext() as ctx:
        ctx.prec = 50
        g = D(4) ** (D(item_level - 60) / D(59))
        budget = D(SLOT_WEIGHTS[slot]) * (RARITY_MULT[rarity] - D(1)) / D(len(names))
        scale = g.sqrt() if attribute in POINT_ATTRIBUTES else g
        raw = budget * SECONDARY_SCALE[attribute] * scale
        if attribute in POINT_ATTRIBUTES:
            magnitude = max(
                D("0.25"),
                (raw / D("0.25")).quantize(D(1), rounding=ROUND_HALF_EVEN) * D("0.25"),
            )
        else:
            magnitude = raw.quantize(D(1), rounding=ROUND_HALF_UP)
    return {"attribute": attribute, "value": str(magnitude)}


def dismantle_quantities(item_slot: str, rarity: str) -> DismantleQuantities:
    sw = economy_sw(item_slot)
    if rarity == "Comum":
        return DismantleQuantities(sw, 0, 0)
    if rarity == "Raro":
        return DismantleQuantities(2 * sw, 0, sw)
    if rarity == "Épico":
        catalysts = int((D(sw) / D(2)).to_integral_value(rounding=ROUND_CEILING))
        return DismantleQuantities(3 * sw, catalysts, 2 * sw)
    if rarity == "Lendário":
        return DismantleQuantities(4 * sw, sw, 4 * sw)
    if rarity == "Mítico":
        return DismantleQuantities(6 * sw, 2 * sw, 8 * sw)
    raise EquipmentModificationError("Unknown equipment rarity.")
