"""Pure interpretation of the stat-bearing state persisted on equipped items."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from asterion.domain.equipment import EquipmentSlot, assignment_for_item_slot, parse_equipment_slot

D = Decimal
ZERO = D(0)

ATTRIBUTE_NAMES = {
    "HP": "hp",
    "ATQ": "attack",
    "DEF": "defense",
    "AGI": "agility",
    "PER": "per",
    "CRIT": "crit",
    "Esquiva": "evasion",
    "Bloqueio": "block",
}
CORE_ATTRIBUTES = frozenset({"HP", "ATQ", "DEF", "AGI"})
CORE_POOLS = {
    EquipmentSlot.PRINCIPAL: frozenset({"ATQ"}),
    EquipmentSlot.SECUNDARIA: frozenset({"ATQ", "DEF"}),
    EquipmentSlot.CABECA: frozenset({"HP", "DEF"}),
    EquipmentSlot.TORSO: frozenset({"HP", "DEF"}),
    EquipmentSlot.MAOS: frozenset({"ATQ", "DEF"}),
    EquipmentSlot.PES: frozenset({"HP", "AGI"}),
    EquipmentSlot.ACESSORIO: frozenset({"HP", "ATQ", "AGI"}),
    EquipmentSlot.ARTEFATO: frozenset({"HP", "ATQ", "DEF", "AGI"}),
}
SECONDARY_POOLS = {
    EquipmentSlot.PRINCIPAL: frozenset({"ATQ", "AGI", "PER", "CRIT"}),
    EquipmentSlot.SECUNDARIA: frozenset({"ATQ", "DEF", "PER", "CRIT", "Bloqueio"}),
    EquipmentSlot.CABECA: frozenset({"HP", "DEF", "PER", "CRIT"}),
    EquipmentSlot.TORSO: frozenset({"HP", "DEF", "Bloqueio"}),
    EquipmentSlot.MAOS: frozenset({"ATQ", "AGI", "PER", "CRIT"}),
    EquipmentSlot.PES: frozenset({"HP", "DEF", "AGI", "Esquiva"}),
    EquipmentSlot.ACESSORIO: frozenset({"HP", "ATQ", "AGI", "PER", "CRIT", "Esquiva"}),
    EquipmentSlot.ARTEFATO: frozenset({"HP", "ATQ", "DEF", "PER", "CRIT", "Bloqueio"}),
}
RARITY_SECONDARY_COUNTS = {
    "Comum": 0,
    "Raro": 1,
    "Épico": 2,
    "Lendário": 3,
    "Mítico": 4,
}
ENHANCEMENT_MULTIPLIERS = (
    D("1.00"), D("1.02"), D("1.04"), D("1.06"), D("1.08"), D("1.10"),
    D("1.125"), D("1.15"), D("1.175"), D("1.20"), D("1.25"),
)


class EquipmentConfigurationError(ValueError):
    """Persisted equipped-item state cannot safely enter combat stat resolution."""


@dataclass(frozen=True, slots=True)
class EquipmentStatContribution:
    """Flat equipment bonus; CRIT defaults to zero because base CRIT is separate."""

    hp: Decimal = ZERO
    attack: Decimal = ZERO
    defense: Decimal = ZERO
    agility: Decimal = ZERO
    per: Decimal = ZERO
    crit: Decimal = ZERO
    evasion: Decimal = ZERO
    block: Decimal = ZERO

    def values(self) -> tuple[Decimal, ...]:
        return (
            self.hp,
            self.attack,
            self.defense,
            self.agility,
            self.per,
            self.crit,
            self.evasion,
            self.block,
        )

    def __add__(self, other: EquipmentStatContribution) -> EquipmentStatContribution:
        return EquipmentStatContribution(
            *(left + right for left, right in zip(self.values(), other.values(), strict=True))
        )


@dataclass(frozen=True, slots=True)
class EquippedItemSnapshot:
    """A validated, SQLAlchemy-independent copy of one equipped item instance."""

    item_instance_id: str
    slot: str
    item_slot: str
    item_level: int
    rarity: str
    enhancement: int
    core: tuple[tuple[str, Decimal], ...]
    secondaries: tuple[tuple[str, Decimal], ...]
    rune: None = None
    enchantment: None = None

    def to_data(self) -> dict[str, Any]:
        return {
            "item_instance_id": self.item_instance_id,
            "slot": self.slot,
            "item_slot": self.item_slot,
            "item_level": self.item_level,
            "rarity": self.rarity,
            "enhancement": self.enhancement,
            "core": {key: str(value) for key, value in self.core},
            "secondaries": [
                {"attribute": key, "value": str(value)} for key, value in self.secondaries
            ],
            "rune": self.rune,
            "enchantment": self.enchantment,
        }


@dataclass(frozen=True, slots=True)
class EquipmentConfigurationSnapshot:
    """The equipment and configuration version frozen for an activity."""

    combat_configuration_version: int
    items: tuple[EquippedItemSnapshot, ...] = ()
    selected_path: str | None = None
    talent_choices: tuple[tuple[int, str], ...] = ()

    def contribution(self) -> EquipmentStatContribution:
        slots: set[EquipmentSlot] = set()
        ids: set[str] = set()
        has_two_handed = False
        result = EquipmentStatContribution()
        for item in self.items:
            slot = parse_equipment_slot(item.slot)
            assignment = assignment_for_item_slot(item.item_slot)
            if slot is None or assignment is None or assignment.slot != slot:
                raise EquipmentConfigurationError("Equipped item slot is inconsistent.")
            if slot in slots or item.item_instance_id in ids:
                raise EquipmentConfigurationError("Duplicate equipped slot or item.")
            if assignment.two_handed:
                has_two_handed = True
            slots.add(slot)
            ids.add(item.item_instance_id)
            result = result + equipment_stat_contribution(item)
        if has_two_handed and EquipmentSlot.SECUNDARIA in slots:
            raise EquipmentConfigurationError("A two-handed item blocks the secondary slot.")
        if not 0 <= self.combat_configuration_version:
            raise EquipmentConfigurationError("Invalid combat configuration version.")
        return result

    def to_data(self, ruleset_version: str) -> dict[str, Any]:
        return {
            "combat_configuration_version": self.combat_configuration_version,
            "ruleset_version": ruleset_version,
            "equipment": [item.to_data() for item in self.items],
            "selected_path": self.selected_path,
            "talents": [
                {"point_slot": slot, "talent_id": talent_id}
                for slot, talent_id in self.talent_choices
            ],
        }


def item_snapshot_from_persisted(
    *,
    item_instance_id: str,
    equipped_slot: str,
    item_slot: str,
    item_level: int,
    rarity: str,
    payload: Mapping[str, Any],
) -> EquippedItemSnapshot:
    """Validate and freeze materialized item values without deriving any rolls."""
    if not item_instance_id:
        raise EquipmentConfigurationError("Missing item instance identity.")
    parsed_slot = parse_equipment_slot(equipped_slot)
    assignment = assignment_for_item_slot(item_slot)
    payload = dict(payload)
    payload_slot = payload.get("slot")
    payload_assignment = (
        assignment_for_item_slot(str(payload_slot)) if payload_slot is not None else None
    )
    if (
        parsed_slot is None
        or assignment is None
        or assignment.slot != parsed_slot
        or payload_assignment != assignment
    ):
        raise EquipmentConfigurationError("Item slot does not match its equipped slot.")
    payload_id = payload.get("item_instance_id")
    if payload_id is not None and str(payload_id) != item_instance_id:
        raise EquipmentConfigurationError("Item payload identity does not match its row.")
    if isinstance(item_level, bool) or not isinstance(item_level, int) or not 1 <= item_level <= 60:
        raise EquipmentConfigurationError("Invalid item level.")
    if rarity not in RARITY_SECONDARY_COUNTS:
        raise EquipmentConfigurationError("Unknown equipment rarity.")
    enhancement = payload.get("enhancement")
    if (
        isinstance(enhancement, bool)
        or not isinstance(enhancement, int)
        or not 0 <= enhancement <= 10
    ):
        raise EquipmentConfigurationError("Invalid equipment enhancement.")

    raw_core = payload.get("core")
    raw_secondaries = payload.get("secondaries")
    if not isinstance(raw_core, Mapping) or not raw_core:
        raise EquipmentConfigurationError("Missing or invalid materialized equipment core.")
    if not isinstance(raw_secondaries, (list, tuple)):
        raise EquipmentConfigurationError("Missing or invalid equipment secondaries.")
    core: list[tuple[str, Decimal]] = []
    for name, value in raw_core.items():
        if name not in CORE_ATTRIBUTES:
            raise EquipmentConfigurationError(f"Invalid core attribute: {name}.")
        core.append((name, _decimal_value(value, allow_zero=True)))
    secondaries: list[tuple[str, Decimal]] = []
    seen: set[str] = set()
    for secondary in raw_secondaries:
        if not isinstance(secondary, Mapping):
            raise EquipmentConfigurationError("Invalid equipment secondary.")
        name = secondary.get("attribute")
        if name not in ATTRIBUTE_NAMES or name in seen:
            raise EquipmentConfigurationError("Unknown or duplicate secondary attribute.")
        seen.add(name)
        secondaries.append((name, _decimal_value(secondary.get("value"), allow_zero=False)))
    pool_slot = assignment.slot
    if any(name not in CORE_POOLS[pool_slot] for name, _ in core):
        raise EquipmentConfigurationError("Core attribute is not eligible for this equipment slot.")
    if any(name not in SECONDARY_POOLS[pool_slot] for name, _ in secondaries):
        raise EquipmentConfigurationError("Secondary is not eligible for this equipment slot.")
    if payload.get("rune") is not None or payload.get("enchantment") is not None:
        raise EquipmentConfigurationError("Installed runes and enchantments are unsupported.")
    return EquippedItemSnapshot(
        item_instance_id=item_instance_id,
        slot=parsed_slot.value,
        item_slot=item_slot,
        item_level=item_level,
        rarity=rarity,
        enhancement=enhancement,
        core=tuple(sorted(core)),
        secondaries=tuple(secondaries),
    )


def equipment_stat_contribution(item: EquippedItemSnapshot) -> EquipmentStatContribution:
    """Compose persisted core, secondaries, then total enhancement multiplier."""
    values = {name: ZERO for name in ATTRIBUTE_NAMES}
    for name, value in item.core:
        values[name] += value
    for name, value in item.secondaries:
        values[name] += value
    multiplier = ENHANCEMENT_MULTIPLIERS[item.enhancement]
    return EquipmentStatContribution(
        *(values[name] * multiplier for name in ATTRIBUTE_NAMES)
    )


def equipment_configuration_from_data(data: Mapping[str, Any]) -> EquipmentConfigurationSnapshot:
    """Decode a frozen equipment payload used by a Ronda or combat snapshot."""
    version = data.get("combat_configuration_version", 0)
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise EquipmentConfigurationError("Invalid combat configuration version.")
    raw_items = data.get("equipment", [])
    if not isinstance(raw_items, (list, tuple)):
        raise EquipmentConfigurationError("Invalid equipment snapshot.")
    items: list[EquippedItemSnapshot] = []
    for raw in raw_items:
        if not isinstance(raw, Mapping):
            raise EquipmentConfigurationError("Invalid equipped item snapshot.")
        normalized_payload = {
            "slot": raw.get("item_slot"),
            "enhancement": raw.get("enhancement"),
            "core": raw.get("core"),
            "secondaries": raw.get("secondaries"),
            "rune": raw.get("rune"),
            "enchantment": raw.get("enchantment"),
            "item_instance_id": raw.get("item_instance_id"),
        }
        items.append(
            item_snapshot_from_persisted(
                item_instance_id=str(raw.get("item_instance_id", "")),
                equipped_slot=str(raw.get("slot", "")),
                item_slot=str(raw.get("item_slot", "")),
                item_level=raw.get("item_level"),
                rarity=str(raw.get("rarity", "")),
                payload=normalized_payload,
            )
        )
    selected_path = data.get("selected_path")
    if selected_path is not None and not isinstance(selected_path, str):
        raise EquipmentConfigurationError("Invalid selected Path snapshot.")
    raw_talents = data.get("talents", [])
    if not isinstance(raw_talents, (list, tuple)):
        raise EquipmentConfigurationError("Invalid Talent configuration snapshot.")
    talent_choices = []
    seen_slots: set[int] = set()
    seen_talents: set[str] = set()
    for raw in raw_talents:
        if not isinstance(raw, Mapping):
            raise EquipmentConfigurationError("Invalid Talent choice snapshot.")
        slot = raw.get("point_slot")
        talent_id = raw.get("talent_id")
        if (
            isinstance(slot, bool)
            or not isinstance(slot, int)
            or not 1 <= slot <= 12
            or not isinstance(talent_id, str)
            or not talent_id
            or slot in seen_slots
            or talent_id in seen_talents
        ):
            raise EquipmentConfigurationError("Invalid or duplicate Talent choice snapshot.")
        seen_slots.add(slot)
        seen_talents.add(talent_id)
        talent_choices.append((slot, talent_id))
    result = EquipmentConfigurationSnapshot(
        version,
        tuple(items),
        selected_path,
        tuple(sorted(talent_choices)),
    )
    result.contribution()  # validate duplicates and 2H/off-hand invariants
    return result


def _decimal_value(value: Any, *, allow_zero: bool) -> Decimal:
    if isinstance(value, (float, bool)) or value is None:
        raise EquipmentConfigurationError("Equipment stats must be exact numeric values.")
    if not isinstance(value, (int, str, Decimal)):
        raise EquipmentConfigurationError("Equipment stats must be exact numeric values.")
    try:
        result = D(value)
    except (InvalidOperation, ValueError) as exc:
        raise EquipmentConfigurationError("Invalid equipment stat value.") from exc
    if not result.is_finite() or result < ZERO or (not allow_zero and result == ZERO):
        raise EquipmentConfigurationError("Equipment stat value is out of range.")
    return result
