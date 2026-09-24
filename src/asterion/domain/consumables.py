"""Canonical catalog and policy for global and regional Consumables."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class ConsumableFamily(StrEnum):
    HEALING = "healing"
    PURIFICATION = "purification"
    ANTIDOTE = "antidote"
    VIGOR = "vigor"
    PROTECTION = "protection"
    DISPELLER = "dispeller"
    WARDING = "warding"


class UseContext(StrEnum):
    COMBAT_PVE = "combat_pve"
    OUT_OF_COMBAT = "out_of_combat"


class ConsumableTarget(StrEnum):
    SELF = "self"
    SELF_NEGATIVE_EFFECT = "self_negative_effect"
    SELF_DOT = "self_dot"
    ENEMY_POSITIVE_EFFECT = "enemy_positive_effect"


@dataclass(frozen=True, slots=True)
class RecipeIngredient:
    name: str
    quantity: int


@dataclass(frozen=True, slots=True)
class ConsumableRecipe:
    profession_level: int
    ingredients: tuple[RecipeIngredient, ...]
    crown_cost: int


@dataclass(frozen=True, slots=True)
class ConsumableFamilyPolicy:
    family: ConsumableFamily
    minimum_grade: int
    use_context: UseContext
    target: ConsumableTarget
    cooldown_group: str | None
    round_eligible: bool
    effect_metadata: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConsumableDefinition:
    id: str
    family: ConsumableFamily
    name: str
    grade: int
    region: str | None
    use_context: UseContext
    target: ConsumableTarget
    cooldown_group: str | None
    round_eligible: bool
    effect_metadata: tuple[str, ...]
    recipe: ConsumableRecipe


# Existing combat snapshots persist this cooldown key; catalog metadata keeps
# using the same key so all combat families resolve through one runtime group.
COMBAT_CD_GROUP = "consumable"
VIGOR_RESTORE = 20
VIGOR_USABLE_AT_OR_BELOW = 80
VIGOR_MAXIMUM = 100
VIGOR_DAILY_RESET_HOUR = 6
VIGOR_CYCLE_TIMEZONE = "America/Sao_Paulo"

CONSUMABLE_FAMILIES = tuple(ConsumableFamily)

FAMILY_POLICIES = MappingProxyType(
    {
        ConsumableFamily.HEALING: ConsumableFamilyPolicy(
            ConsumableFamily.HEALING,
            1,
            UseContext.COMBAT_PVE,
            ConsumableTarget.SELF,
            COMBAT_CD_GROUP,
            True,
            ("heal_max_hp:0.22",),
        ),
        ConsumableFamily.PURIFICATION: ConsumableFamilyPolicy(
            ConsumableFamily.PURIFICATION,
            1,
            UseContext.COMBAT_PVE,
            ConsumableTarget.SELF_NEGATIVE_EFFECT,
            COMBAT_CD_GROUP,
            True,
            ("remove_negative:1",),
        ),
        ConsumableFamily.ANTIDOTE: ConsumableFamilyPolicy(
            ConsumableFamily.ANTIDOTE,
            1,
            UseContext.COMBAT_PVE,
            ConsumableTarget.SELF_DOT,
            COMBAT_CD_GROUP,
            False,
            ("remove_dot_all_stacks:1",),
        ),
        ConsumableFamily.VIGOR: ConsumableFamilyPolicy(
            ConsumableFamily.VIGOR,
            1,
            UseContext.OUT_OF_COMBAT,
            ConsumableTarget.SELF,
            None,
            False,
            (
                "restore_vigor:20",
                "requires_vigor_at_most:80",
                "maximum:100",
                "daily_cycle:06:00:America/Sao_Paulo",
            ),
        ),
        ConsumableFamily.PROTECTION: ConsumableFamilyPolicy(
            ConsumableFamily.PROTECTION,
            2,
            UseContext.COMBAT_PVE,
            ConsumableTarget.SELF,
            COMBAT_CD_GROUP,
            False,
            ("barrier_max_hp:0.12_floor", "duration:2T"),
        ),
        ConsumableFamily.DISPELLER: ConsumableFamilyPolicy(
            ConsumableFamily.DISPELLER,
            3,
            UseContext.COMBAT_PVE,
            ConsumableTarget.ENEMY_POSITIVE_EFFECT,
            COMBAT_CD_GROUP,
            False,
            ("remove_positive:1", "stackable:oldest"),
        ),
        ConsumableFamily.WARDING: ConsumableFamilyPolicy(
            ConsumableFamily.WARDING,
            4,
            UseContext.COMBAT_PVE,
            ConsumableTarget.SELF,
            COMBAT_CD_GROUP,
            False,
            ("ward_charges:1", "duration:2T"),
        ),
    }
)


def _ingredient(name: str, quantity: int) -> RecipeIngredient:
    return RecipeIngredient(name, quantity)


def _recipe(
    profession_level: int,
    ingredients: tuple[RecipeIngredient, ...],
    crown_cost: int,
) -> ConsumableRecipe:
    return ConsumableRecipe(profession_level, ingredients, crown_cost)


def _item(
    item_id: str,
    family: ConsumableFamily,
    name: str,
    grade: int,
    region: str | None,
    recipe: ConsumableRecipe,
) -> ConsumableDefinition:
    policy = FAMILY_POLICIES[family]
    if grade < policy.minimum_grade:
        raise ValueError(f"{family.value} does not have recipes below Grade {policy.minimum_grade}")
    if len(item_id) > 64:
        raise ValueError("Consumable IDs must fit consumable_stacks.consumable_id")
    return ConsumableDefinition(
        id=item_id,
        family=family,
        name=name,
        grade=grade,
        region=region,
        use_context=policy.use_context,
        target=policy.target,
        cooldown_group=policy.cooldown_group,
        round_eligible=policy.round_eligible,
        effect_metadata=policy.effect_metadata,
        recipe=recipe,
    )


_TDO = "Terras do Ocaso"
_VDE = "Vales dos Enforcados"

_CATALOG = (
    # These two IDs are persisted by the remote Ronda and Inventory runtime.
    _item(
        "consumable.heal",
        ConsumableFamily.HEALING,
        "Poção de Cura",
        1,
        _TDO,
        _recipe(
            1,
            (_ingredient("Ervas Cinzentas", 3), _ingredient("Resíduo do Ocaso", 1)),
            20,
        ),
    ),
    _item(
        "consumable.purification",
        ConsumableFamily.PURIFICATION,
        "Preparado de Purificação",
        1,
        _TDO,
        _recipe(
            1,
            (_ingredient("Ervas Cinzentas", 2), _ingredient("Resíduos do Ocaso", 2)),
            40,
        ),
    ),
    _item(
        "consumable.antidote.tdo.i",
        ConsumableFamily.ANTIDOTE,
        "Antídoto Cinzento",
        1,
        _TDO,
        _recipe(
            5,
            (_ingredient("Ervas Cinzentas", 4), _ingredient("Resíduo do Ocaso", 1)),
            40,
        ),
    ),
    _item(
        "consumable.vigor.tdo.i",
        ConsumableFamily.VIGOR,
        "Poção de Vigor",
        1,
        _TDO,
        _recipe(
            10,
            (
                _ingredient("Ervas Cinzentas", 6),
                _ingredient("Resíduos do Ocaso", 4),
                _ingredient("Catalisador de Elite I", 1),
            ),
            120,
        ),
    ),
    _item(
        "consumable.heal.vde.ii",
        ConsumableFamily.HEALING,
        "Poção de Cura do Vale",
        2,
        _VDE,
        _recipe(
            3,
            (_ingredient("Ervas de Turfa", 3), _ingredient("Resina Enredada", 1)),
            40,
        ),
    ),
    _item(
        "consumable.purification.vde.ii",
        ConsumableFamily.PURIFICATION,
        "Preparado de Purificação Enredada",
        2,
        _VDE,
        _recipe(
            3,
            (_ingredient("Ervas de Turfa", 2), _ingredient("Resinas Enredadas", 2)),
            60,
        ),
    ),
    _item(
        "consumable.antidote.vde.ii",
        ConsumableFamily.ANTIDOTE,
        "Antídoto de Turfa",
        2,
        _VDE,
        _recipe(
            5,
            (_ingredient("Ervas de Turfa", 4), _ingredient("Resina Enredada", 1)),
            60,
        ),
    ),
    _item(
        "consumable.vigor.vde.ii",
        ConsumableFamily.VIGOR,
        "Poção de Vigor dos Laços",
        2,
        _VDE,
        _recipe(
            10,
            (
                _ingredient("Ervas de Turfa", 6),
                _ingredient("Resinas Enredadas", 4),
                _ingredient("Catalisador de Elite II", 1),
            ),
            200,
        ),
    ),
    _item(
        "consumable.protection.vde.ii",
        ConsumableFamily.PROTECTION,
        "Preparado de Proteção Enredada",
        2,
        _VDE,
        _recipe(
            5,
            (_ingredient("Ervas de Turfa", 3), _ingredient("Resinas Enredadas", 2)),
            80,
        ),
    ),
    # These are generic family definitions. No regional Dissipador or Resguardo
    # item has been defined by the content sources.
    _item(
        "consumable.dispeller.iii",
        ConsumableFamily.DISPELLER,
        "Dissipador",
        3,
        None,
        _recipe(
            10,
            (_ingredient("Reagentes · Grau III", 2), _ingredient("Essências · Grau III", 3)),
            140,
        ),
    ),
    _item(
        "consumable.warding.iv",
        ConsumableFamily.WARDING,
        "Preparado de Resguardo",
        4,
        None,
        _recipe(
            12,
            (_ingredient("Reagentes · Grau IV", 4), _ingredient("Essências · Grau IV", 2)),
            210,
        ),
    ),
)

CONSUMABLE_CATALOG = MappingProxyType({item.id: item for item in _CATALOG})

ENCOUNTER_CONSUMABLE_LIMITS = MappingProxyType(
    {"common": 1, "uncommon": 1, "elite": 2, "boss": 3}
)
DUNGEON_RUN_CONSUMABLE_LIMITS = MappingProxyType(
    {"stable": 6, "fractured": 5, "rupture": 4}
)
OTHER_CONSUMABLE_LIMITS = MappingProxyType(
    {"world_event": 2, "oath_trial": 3, "pvp": 0}
)


def definition(item_id: str) -> ConsumableDefinition | None:
    return CONSUMABLE_CATALOG.get(item_id)


def family_definitions(family: ConsumableFamily) -> tuple[ConsumableDefinition, ...]:
    return tuple(item for item in _CATALOG if item.family == family)


def round_eligible(item_id: str) -> bool:
    item = definition(item_id)
    return bool(item and item.round_eligible)


def consumable_limit(scope: str, key: str | None = None) -> int:
    if scope == "encounter":
        if key is None:
            raise KeyError("Encounter category is required")
        return ENCOUNTER_CONSUMABLE_LIMITS[key]
    if scope == "dungeon_run":
        if key is None:
            raise KeyError("Dungeon difficulty is required")
        return DUNGEON_RUN_CONSUMABLE_LIMITS[key]
    if key is not None:
        raise KeyError(f"Unexpected key for Consumable budget scope: {scope}")
    return OTHER_CONSUMABLE_LIMITS[scope]


def grade_label(grade: int) -> str:
    try:
        return {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI"}[grade]
    except KeyError as exc:
        raise ValueError(f"Unsupported Consumable grade: {grade}") from exc
