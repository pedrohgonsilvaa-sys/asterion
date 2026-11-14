"""Pure interpretation of the stat-bearing state persisted on equipped items."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from asterion.domain.equipment import EquipmentSlot, assignment_for_item_slot, parse_equipment_slot
from asterion.domain.equipment_modifications import (
    ENCHANTMENT_FAMILIES,
    POINT_ATTRIBUTES,
    RUNE_FAMILIES,
    EquipmentModificationError,
    enchantment_compatible,
    enchantment_multiplier,
    enchantment_potency_for,
    equipment_grade,
    parse_component_potency,
    rune_compatible,
    rune_potency_for,
)
from asterion.domain.regional_equipment import (
    ARMOR_CLASS_BONUS,
    ARMOR_CLASSES,
    ARMOR_SLOTS,
    armor_class_of,
)
from asterion.domain.weapon_metadata import weapon_definition

D = Decimal
ZERO = D(0)
ZERO_STAGE = (ZERO,) * 8

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
# GDD v1.7.1 §49.8: Shield core is HP/DEF (not the Secondary weapon core).
SHIELD_CORE_POOL = frozenset({"HP", "DEF"})
SHIELD_WEAPON_FORM = "weapon.form.shield"
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
    rune_percent: tuple[Decimal, ...] = ZERO_STAGE
    rune_points: tuple[Decimal, ...] = ZERO_STAGE
    enchantment_percent: tuple[Decimal, ...] = ZERO_STAGE
    enchantment_points: tuple[Decimal, ...] = ZERO_STAGE

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
            *(left + right for left, right in zip(self.values(), other.values(), strict=True)),
            rune_percent=_add_stage(self.rune_percent, other.rune_percent),
            rune_points=_add_stage(self.rune_points, other.rune_points),
            enchantment_percent=_add_stage(self.enchantment_percent, other.enchantment_percent),
            enchantment_points=_add_stage(self.enchantment_points, other.enchantment_points),
        )


@dataclass(frozen=True, slots=True)
class InstalledComponent:
    family: str
    effect: str
    rarity: str
    grade: int
    potency: str
    bound: bool
    identifier: str | None = None
    name: str | None = None

    def to_data(self, *, enchantment: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "family": self.family,
            "effect": self.effect,
            "rarity": self.rarity,
            "grade": self.grade,
            "potency": self.potency,
            "bound": self.bound,
        }
        if enchantment:
            if self.identifier is not None:
                data["enchantment_id"] = self.identifier
            if self.name is not None:
                data["name"] = self.name
        return data


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
    rune: InstalledComponent | None = None
    enchantment: InstalledComponent | None = None
    runes: tuple[tuple[str, InstalledComponent], ...] = ()
    armor_class: str | None = None

    def to_data(self) -> dict[str, Any]:
        data = {
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
            "rune": self.rune.to_data() if self.rune is not None else None,
            "enchantment": (
                self.enchantment.to_data(enchantment=True)
                if self.enchantment is not None else None
            ),
            "armor_class": self.armor_class,
        }
        if self.item_slot == "2H":
            data["runes"] = {key: value.to_data() for key, value in self.runes}
        return data


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
    definition = weapon_definition(payload.get("weapon_type_id"))
    if definition is not None:
        expected_assignment = assignment_for_item_slot(definition.persisted_item_slot)
        if expected_assignment != assignment:
            raise EquipmentConfigurationError(
                "Canonical weapon metadata does not match its persisted item slot."
            )
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
        # Low-level items can legitimately round a secondary's budget to zero;
        # identity still occupies its rarity slot and is valid for rerolling.
        secondaries.append((name, _decimal_value(secondary.get("value"), allow_zero=True)))
    pool_slot = assignment.slot
    core_pool = (
        SHIELD_CORE_POOL
        if definition is not None and definition.weapon_form == SHIELD_WEAPON_FORM
        else CORE_POOLS[pool_slot]
    )
    if any(name not in core_pool for name, _ in core):
        raise EquipmentConfigurationError("Core attribute is not eligible for this equipment slot.")
    if any(name not in SECONDARY_POOLS[pool_slot] for name, _ in secondaries):
        raise EquipmentConfigurationError("Secondary is not eligible for this equipment slot.")
    rune = None
    runes: tuple[tuple[str, InstalledComponent], ...] = ()
    if item_slot == "2H":
        if payload.get("rune") is not None:
            raise EquipmentConfigurationError("A two-handed item uses rune affinities A and B.")
        raw_runes = payload.get("runes")
        if raw_runes is not None:
            if not isinstance(raw_runes, Mapping) or any(
                key not in {"A", "B"} for key in raw_runes
            ):
                raise EquipmentConfigurationError("Invalid two-handed Rune affinity state.")
            runes = tuple(
                (key, _installed_component(raw, item_slot, item_level, kind="rune", affinity=key))
                for key, raw in sorted(raw_runes.items()) if raw is not None
            )
    else:
        if payload.get("runes") not in (None, {}):
            raise EquipmentConfigurationError("Normal equipment has one Rune slot.")
        if payload.get("rune") is not None:
            rune = _installed_component(payload["rune"], item_slot, item_level, kind="rune")
    enchantment = None
    if payload.get("enchantment") is not None:
        enchantment = _installed_component(
            payload["enchantment"], item_slot, item_level, kind="enchantment"
        )
    armor_class = armor_class_of(
        slot=item_slot, template_id=payload.get("template_id"), item_name=payload.get("item_name")
    )
    if payload.get("armor_class") is not None:
        # Frozen snapshots carry the class already resolved from the template.
        if payload["armor_class"] not in ARMOR_CLASSES or item_slot not in ARMOR_SLOTS:
            raise EquipmentConfigurationError("Invalid armor class.")
        armor_class = payload["armor_class"]
    return EquippedItemSnapshot(
        item_instance_id=item_instance_id,
        slot=parsed_slot.value,
        item_slot=item_slot,
        item_level=item_level,
        rarity=rarity,
        enhancement=enhancement,
        core=tuple(sorted(core)),
        secondaries=tuple(secondaries),
        rune=rune,
        enchantment=enchantment,
        runes=runes,
        armor_class=armor_class,
    )


def equipment_stat_contribution(item: EquippedItemSnapshot) -> EquipmentStatContribution:
    """Compose core/secondaries, enhancement, then component stages."""
    values = {name: ZERO for name in ATTRIBUTE_NAMES}
    for name, value in item.core:
        values[name] += value
    for name, value in item.secondaries:
        values[name] += value
    multiplier = ENHANCEMENT_MULTIPLIERS[item.enhancement]
    rune_percent = list(ZERO_STAGE)
    rune_points = list(ZERO_STAGE)
    enchant_percent = list(ZERO_STAGE)
    enchant_points = list(ZERO_STAGE)
    installed_runes = ((item.rune,) if item.rune is not None else ()) + tuple(
        value for _, value in item.runes
    )
    for component in installed_runes:
        _add_component_power(component, rune_percent, rune_points)
    if item.enchantment is not None:
        _add_component_power(
            item.enchantment,
            enchant_percent,
            enchant_points,
            multiplier=enchantment_multiplier(item.item_slot, item.enchantment.effect),
        )
    totals = {name: values[name] * multiplier for name in ATTRIBUTE_NAMES}
    if item.armor_class is not None:
        # Separate layer (spec Classes de Armadura §2): not multiplied by enhancement.
        evasion, block = ARMOR_CLASS_BONUS[item.armor_class]
        totals["Esquiva"] += D(evasion)
        totals["Bloqueio"] += D(block)
    return EquipmentStatContribution(
        *(totals[name] for name in ATTRIBUTE_NAMES),
        rune_percent=tuple(rune_percent),
        rune_points=tuple(rune_points),
        enchantment_percent=tuple(enchant_percent),
        enchantment_points=tuple(enchant_points),
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
            "runes": raw.get("runes"),
            "enchantment": raw.get("enchantment"),
            "item_instance_id": raw.get("item_instance_id"),
            "armor_class": raw.get("armor_class"),
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


def _add_stage(left: tuple[Decimal, ...], right: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
    return tuple(a + b for a, b in zip(left, right, strict=True))


def _add_component_power(
    component: InstalledComponent,
    percentages: list[Decimal],
    points: list[Decimal],
    *,
    multiplier: int = 1,
) -> None:
    position = tuple(ATTRIBUTE_NAMES).index(component.effect)
    try:
        amount = parse_component_potency(component.potency, component.effect) * multiplier
    except EquipmentModificationError as exc:
        raise EquipmentConfigurationError(str(exc)) from exc
    (points if component.effect in POINT_ATTRIBUTES else percentages)[position] += amount


def _installed_component(
    raw: Any, item_slot: str, item_level: int, *, kind: str, affinity: str = "A"
) -> InstalledComponent:
    if not isinstance(raw, Mapping):
        raise EquipmentConfigurationError("Installed component is invalid.")
    family = raw.get("family")
    rarity = raw.get("rarity")
    grade = raw.get("grade")
    potency = raw.get("potency")
    bound = raw.get("bound")
    if (
        not isinstance(family, str)
        or not isinstance(rarity, str)
        or isinstance(grade, bool)
        or not isinstance(grade, int)
        or not isinstance(potency, str)
        or not isinstance(bound, bool)
    ):
        raise EquipmentConfigurationError("Installed component fields are invalid.")
    try:
        if not 1 <= grade <= equipment_grade(item_level):
            raise EquipmentModificationError("Component Grade exceeds equipment Grade.")
        if kind == "rune":
            if not rune_compatible(item_slot, family, affinity):
                raise EquipmentModificationError("Rune effect is incompatible with equipment.")
            effect = RUNE_FAMILIES[family][0]
            expected = rune_potency_for(family, rarity, grade)
        else:
            if not enchantment_compatible(item_slot, family):
                raise EquipmentModificationError(
                    "Enchantment effect is incompatible with equipment."
                )
            effect = ENCHANTMENT_FAMILIES[family]
            expected = enchantment_potency_for(family, rarity, grade)
        if raw.get("effect", effect) != effect:
            raise EquipmentModificationError("Component effect contradicts its family.")
        parse_component_potency(potency, effect)
        if potency != expected:
            raise EquipmentModificationError(
                "Component potency contradicts its family, rarity or Grade."
            )
    except EquipmentModificationError as exc:
        raise EquipmentConfigurationError(str(exc)) from exc
    identifier = raw.get("enchantment_id")
    name = raw.get("name")
    if (identifier is not None and not isinstance(identifier, str)) or (
        name is not None and not isinstance(name, str)
    ):
        raise EquipmentConfigurationError("Enchantment identity is invalid.")
    return InstalledComponent(family, effect, rarity, grade, potency, bound, identifier, name)
