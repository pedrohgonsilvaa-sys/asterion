"""Profession progression and the Terras do Ocaso C1 recipe catalog."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum

from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.economy import crowns_per_level, round_10

D = Decimal


class ProfessionSlot(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass(frozen=True, slots=True)
class ProfessionDefinition:
    profession_id: str
    name: str
    descriptor: str
    emoji: str


PROFESSIONS = (
    ProfessionDefinition("blacksmith", "Ferreiro", "Armas e Armaduras", "⚒️"),
    ProfessionDefinition("artificer", "Artífice", "Runas e Encantamentos", "⚙️"),
    ProfessionDefinition("alchemist", "Alquimista", "Consumíveis", "⚗️"),
    ProfessionDefinition("leatherworker", "Curteiro", "Armaduras", "🧵"),
    ProfessionDefinition("jeweler", "Joalheiro", "Acessórios", "💎"),
)
PROFESSION_BY_ID = {entry.profession_id: entry for entry in PROFESSIONS}
PROFESSION_IDS = tuple(entry.profession_id for entry in PROFESSIONS)
SLOT_CAPS = {ProfessionSlot.PRIMARY: 30, ProfessionSlot.SECONDARY: 15}


@dataclass(frozen=True, slots=True)
class MaterialRequirement:
    material_id: str
    quantity: int
    transmits_bind: bool = True


@dataclass(frozen=True, slots=True)
class RecipeDefinition:
    recipe_id: str
    profession_id: str
    name: str
    output_kind: str
    required_level: int
    grade: int = 1
    rarity: str | None = None
    output_name: str | None = None
    output_slot: str | None = None
    output_id: str | None = None
    output_family: str | None = None
    sw: int = 1
    basic_materials: int = 0
    primary_material_id: str | None = None
    secondary_material_id: str | None = None
    primary_ratio: Decimal = D("0.70")
    fragment_per_sw: int = 0
    catalyst_per_sw: int = 0
    fixed_materials: tuple[MaterialRequirement, ...] = ()
    fixed_crown_cost: int | None = None
    creation_enabled: bool = True
    unlock_id: str | None = None
    description: str = ""


IRON = "material.tdo.ferro_de_fuligem"
LEATHER = "material.tdo.couro_escoriado"
HERB = "material.tdo.erva_cinzenta"
RESIDUE = "material.tdo.residuo_ocaso"
CATALYST_I = "material.tdo.catalisador_elite_i"
FRAGMENT_I = "material.tdo.fragmento_aprimoramento_i"
CRYPT_CORE = "material.tdo.nucleo_cripta_ocaso"
GALLERIES_CORE = "material.tdo.nucleo_galerias_vigia"
VIGIA_CORE = "material.tdo.nucleo_vigia_partido"

MATERIAL_NAMES = {
    IRON: "Ferro de Fuligem",
    LEATHER: "Couro Escoriado",
    HERB: "Erva Cinzenta",
    RESIDUE: "Resíduo do Ocaso",
    CATALYST_I: "Catalisador de Elite I",
    FRAGMENT_I: "Fragmento de Aprimoramento I",
    CRYPT_CORE: "Núcleo da Cripta do Ocaso",
    GALLERIES_CORE: "Núcleo das Galerias do Vigia",
    VIGIA_CORE: "Núcleo do Vigia Partido",
}

SLOT_ECONOMY_SW = {
    "Principal": 2,
    "Secundária": 1,
    "2H": 3,
    "Cabeça": 1,
    "Torso": 2,
    "Mãos": 1,
    "Pés": 1,
    "Acessório": 2,
    "Artefato": 2,
}
RARITY_REQUIREMENTS = {"Comum": 1, "Raro": 5, "Épico": 10}
RARITY_COST_FACTORS = {"Comum": D("0.25"), "Raro": D("0.35"), "Épico": D("0.50")}
RARITY_COSTS_PER_SW = {"Comum": 5, "Raro": 8, "Épico": 10}


def _equipment_recipes() -> list[RecipeDefinition]:
    rarity_ids = {"Comum": "comum", "Raro": "raro", "Épico": "epico"}
    families = (
        (
            "blacksmith",
            "walker_weapon",
            "Arma do Caminhante",
            "Principal",
            IRON,
            RESIDUE,
            D("0.70"),
        ),
        (
            "blacksmith",
            "walker_guard",
            "Guarda do Caminhante",
            "Secundária",
            IRON,
            RESIDUE,
            D("0.70"),
        ),
        (
            "blacksmith",
            "walker_greatweapon",
            "Arma Pesada do Caminhante",
            "2H",
            IRON,
            RESIDUE,
            D("0.70"),
        ),
        ("blacksmith", "fuligem_helm", "Elmo de Fuligem", "Cabeça", IRON, RESIDUE, D("0.70")),
        ("blacksmith", "fuligem_cuirass", "Couraça de Fuligem", "Torso", IRON, RESIDUE, D("0.70")),
        (
            "blacksmith",
            "fuligem_gauntlets",
            "Manoplas de Fuligem",
            "Mãos",
            IRON,
            RESIDUE,
            D("0.70"),
        ),
        ("blacksmith", "fuligem_steps", "Passos de Fuligem", "Pés", IRON, RESIDUE, D("0.70")),
        ("leatherworker", "ash_hood", "Capuz das Cinzas", "Cabeça", LEATHER, HERB, D("0.70")),
        ("leatherworker", "walker_vest", "Veste do Caminhante", "Torso", LEATHER, HERB, D("0.70")),
        ("leatherworker", "fuligem_gloves", "Luvas de Fuligem", "Mãos", LEATHER, HERB, D("0.70")),
        ("leatherworker", "road_boots", "Botas da Estrada", "Pés", LEATHER, HERB, D("0.70")),
        ("jeweler", "blackened_seal", "Selo Enegrecido", "Acessório", IRON, RESIDUE, D("0.60")),
        ("jeweler", "ash_reliquary", "Relicário de Cinzas", "Artefato", IRON, RESIDUE, D("0.60")),
    )
    recipes = []
    for profession_id, family_id, name, slot, primary, secondary, ratio in families:
        sw = SLOT_ECONOMY_SW[slot]
        for rarity in ("Comum", "Raro", "Épico"):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.tdo.{profession_id}.{family_id}.{rarity_ids[rarity]}",
                    profession_id=profession_id,
                    name=name,
                    output_kind="equipment",
                    required_level=RARITY_REQUIREMENTS[rarity],
                    rarity=rarity,
                    output_name=name,
                    output_slot=slot,
                    sw=sw,
                    basic_materials=RARITY_COSTS_PER_SW[rarity],
                    primary_material_id=primary,
                    secondary_material_id=secondary,
                    primary_ratio=ratio,
                    fragment_per_sw=4 if rarity == "Raro" else 6 if rarity == "Épico" else 0,
                    catalyst_per_sw=2 if rarity == "Épico" else 0,
                    description=f"{rarity} · {slot}",
                )
            )
    return recipes


def _alchemy_recipes() -> list[RecipeDefinition]:
    recipes = []
    for item_id in (
        "consumable.heal",
        "consumable.purification",
        "consumable.antidote.tdo.i",
        "consumable.vigor.tdo.i",
    ):
        item = consumable_definition(item_id)
        if item is None or item.region != "Terras do Ocaso":
            raise RuntimeError(
                f"TDO alchemy recipe {item_id!r} is missing from the canonical catalog"
            )
        materials = []
        for ingredient in item.recipe.ingredients:
            material_id = {
                "Ervas Cinzentas": HERB,
                "Erva Cinzenta": HERB,
                "Resíduo do Ocaso": RESIDUE,
                "Resíduos do Ocaso": RESIDUE,
                "Catalisador de Elite I": CATALYST_I,
            }.get(ingredient.name)
            if material_id is None:
                raise RuntimeError(f"No canonical TDO material ID for {ingredient.name!r}")
            materials.append(
                MaterialRequirement(material_id, ingredient.quantity, material_id != CATALYST_I)
            )
        recipes.append(
            RecipeDefinition(
                recipe_id=f"recipe.tdo.alchemist.{item.id.removeprefix('consumable.')}",
                profession_id="alchemist",
                name=item.name,
                output_kind="consumable",
                required_level=item.recipe.profession_level,
                output_id=item.id,
                fixed_materials=tuple(materials),
                fixed_crown_cost=item.recipe.crown_cost,
                description=f"Consumível · Grau {item.grade}",
            )
        )
    return recipes


def _special_recipes() -> list[RecipeDefinition]:
    return [
        RecipeDefinition(
            recipe_id="recipe.tdo.cripta.relicario_sem_nome",
            profession_id="jeweler",
            name="Relicário dos Sem-Nome",
            output_kind="equipment",
            required_level=5,
            rarity="Raro",
            output_name="Relicário dos Sem-Nome",
            output_slot="Artefato",
            sw=2,
            fixed_materials=(
                MaterialRequirement(IRON, 10),
                MaterialRequirement(RESIDUE, 6),
                MaterialRequirement(FRAGMENT_I, 8, False),
                MaterialRequirement(CRYPT_CORE, 1),
            ),
            unlock_id="recipe.tdo.cripta.relicario_sem_nome",
            description="Artefato · Raro · Grau I · SW2",
        ),
        RecipeDefinition(
            recipe_id="recipe.tdo.galerias.guarda_primeiro_selo",
            profession_id="blacksmith",
            name="Guarda do Primeiro Selo",
            output_kind="equipment",
            required_level=10,
            rarity="Épico",
            output_name="Guarda do Primeiro Selo",
            output_slot="Secundária",
            sw=1,
            fixed_materials=(
                MaterialRequirement(IRON, 7),
                MaterialRequirement(RESIDUE, 3),
                MaterialRequirement(CATALYST_I, 2, False),
                MaterialRequirement(FRAGMENT_I, 6, False),
                MaterialRequirement(GALLERIES_CORE, 1),
            ),
            unlock_id="recipe.tdo.galerias.guarda_primeiro_selo",
            description="Arma Secundária · Épico · Grau I · SW1",
        ),
        RecipeDefinition(
            recipe_id="recipe.tdo.vigia_partido.eco",
            profession_id="artificer",
            name="Eco do Vigia Partido",
            output_kind="enchantment",
            required_level=10,
            rarity="Épico",
            output_id="PER",
            output_family="Marca da Fresta",
            sw=2,
            fixed_materials=(
                MaterialRequirement(RESIDUE, 5),
                MaterialRequirement(IRON, 2),
                MaterialRequirement(CATALYST_I, 1, False),
                MaterialRequirement(VIGIA_CORE, 1),
            ),
            fixed_crown_cost=100,
            creation_enabled=False,
            unlock_id="recipe.tdo.vigia_partido.eco",
            description="Encantamento Épico de PER · Grau I",
        ),
    ]


def _enchantment_recipes() -> list[RecipeDefinition]:
    """Known TDO enchantments are applied directly to an equipment instance."""
    families = (
        ("fio_cinereo", "Fio Cinéreo", "ATQ"),
        ("pele_de_pedra", "Pele de Pedra", "DEF"),
        ("passo_de_fuligem", "Passo de Fuligem", "AGI"),
        ("marca_da_fresta", "Marca da Fresta", "PER"),
        ("eco_do_pressagio", "Eco do Presságio", "CRIT"),
        ("sopro_persistente", "Sopro Persistente", "HP"),
        ("veu_de_desvio", "Véu de Desvio", "Esquiva"),
        ("selo_de_guarda", "Selo de Guarda", "Bloqueio"),
    )
    result = []
    for family_id, name, stat in families:
        for rarity, rarity_id, level, residue, iron, catalysts, cost in (
            ("Raro", "raro", 5, 3, 1, 0, 50),
            ("Épico", "epico", 10, 5, 2, 1, 100),
        ):
            result.append(
                RecipeDefinition(
                    recipe_id=f"recipe.tdo.artificer.enchantment.{family_id}.{rarity_id}",
                    profession_id="artificer",
                    name=name,
                    output_kind="enchantment",
                    required_level=level,
                    rarity=rarity,
                    output_id=stat,
                    output_family=name,
                    fixed_materials=(
                        MaterialRequirement(RESIDUE, residue),
                        MaterialRequirement(IRON, iron),
                        *(
                            (MaterialRequirement(CATALYST_I, catalysts, False),)
                            if catalysts
                            else ()
                        ),
                    ),
                    fixed_crown_cost=cost,
                    creation_enabled=False,
                    description=f"Encantamento {rarity} · {stat} · Grau I",
                )
            )
    return result


def _rune_recipes() -> list[RecipeDefinition]:
    from asterion.domain.road import RUNE_FAMILIES

    recipes = []
    rarity_ids = {"Rara": "rara", "Épica": "epica"}
    rarities = (
        ("Rara", 5, 80, 4, 2, 0, 2),
        ("Épica", 10, 150, 7, 3, 1, 4),
    )
    for family, stat in RUNE_FAMILIES:
        for rarity, required_level, crowns, essences, metal, catalysts, fragments in rarities:
            family_id = family.casefold().replace("á", "a").replace("ê", "e")
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.tdo.artificer.rune.{family_id}.{rarity_ids[rarity]}",
                    profession_id="artificer",
                    name=f"Runa da {family}",
                    output_kind="rune",
                    required_level=required_level,
                    rarity=rarity,
                    output_id=f"rune.tdo.{family_id}",
                    output_family=family,
                    fixed_materials=(
                        MaterialRequirement(RESIDUE, essences),
                        MaterialRequirement(IRON, metal),
                        *(
                            (MaterialRequirement(CATALYST_I, catalysts, False),)
                            if catalysts
                            else ()
                        ),
                        MaterialRequirement(FRAGMENT_I, fragments, False),
                    ),
                    fixed_crown_cost=crowns,
                    description=f"{rarity} · {stat} · Grau I",
                )
            )
    return recipes


RECIPE_DEFINITIONS = tuple(
    _equipment_recipes()
    + _alchemy_recipes()
    + _rune_recipes()
    + _enchantment_recipes()
    + _special_recipes()
)
RECIPE_BY_ID = {recipe.recipe_id: recipe for recipe in RECIPE_DEFINITIONS}
RECIPES_BY_PROFESSION = {
    profession_id: tuple(
        recipe for recipe in RECIPE_DEFINITIONS if recipe.profession_id == profession_id
    )
    for profession_id in PROFESSION_IDS
}


def required_pxp(level: int) -> int:
    """PXP needed for the transition from ``level`` to ``level + 1``."""
    if not 1 <= level < 30:
        raise ValueError("A profession transition level must be between 1 and 29.")
    return round_10(100 + 20 * level + 5 * level * level)


def profession_grade(level: int) -> int:
    if level < 1:
        return 0
    return max(
        grade
        for grade, minimum in ((1, 1), (2, 3), (3, 6), (4, 9), (5, 12), (6, 15))
        if level >= minimum
    )


def recipe_pxp_multiplier(current_level: int, recipe_grade: int) -> int:
    distance = profession_grade(current_level) - recipe_grade
    if distance <= 0:
        return 100
    if distance == 1:
        return 50
    if distance == 2:
        return 20
    return 0


def recipe_pxp(recipe_level: int, current_level: int, recipe_grade: int = 1) -> int:
    return (80 + 20 * recipe_level) * recipe_pxp_multiplier(current_level, recipe_grade) // 100


def apply_profession_pxp(level: int, pxp: int, gained: int, cap: int) -> tuple[int, int]:
    """Apply exact PXP, crossing levels without storing progress past the slot cap."""
    if not 1 <= level <= cap or pxp < 0 or gained < 0:
        raise ValueError("Invalid profession progression state.")
    if level >= cap:
        return cap, 0
    remaining = pxp + gained
    while level < cap:
        threshold = required_pxp(level)
        if remaining < threshold:
            return level, remaining
        remaining -= threshold
        level += 1
    return cap, 0


def profession_change_cost(character_level: int, *, replacement: bool) -> int:
    factor = D("1.00") if replacement else D("0.50")
    return round_10(D(crowns_per_level(character_level)) * factor)


def recipe_materials(recipe: RecipeDefinition, item_level: int) -> tuple[MaterialRequirement, ...]:
    if recipe.fixed_materials:
        return recipe.fixed_materials
    if recipe.output_kind != "equipment":
        return ()
    total = recipe.basic_materials * recipe.sw
    if recipe.primary_material_id is None or recipe.secondary_material_id is None:
        raise ValueError("Equipment recipe is missing its material proportion.")
    primary = int(
        (D(total) * recipe.primary_ratio + D("0.5")).to_integral_value(rounding=ROUND_FLOOR)
    )
    result = [
        MaterialRequirement(recipe.primary_material_id, primary),
        MaterialRequirement(recipe.secondary_material_id, total - primary),
    ]
    if recipe.catalyst_per_sw:
        result.append(MaterialRequirement(CATALYST_I, recipe.catalyst_per_sw * recipe.sw, False))
    if recipe.fragment_per_sw:
        result.append(MaterialRequirement(FRAGMENT_I, recipe.fragment_per_sw * recipe.sw, False))
    return tuple(item for item in result if item.quantity > 0)


def recipe_crown_cost(recipe: RecipeDefinition, item_level: int) -> int:
    if recipe.fixed_crown_cost is not None:
        return recipe.fixed_crown_cost
    if recipe.output_kind != "equipment" or recipe.rarity is None:
        return 0
    return round_10(
        D(crowns_per_level(item_level)) * recipe.sw * RARITY_COST_FACTORS[recipe.rarity]
    )


def recipe_item_level(character_level: int, recipe_grade: int = 1) -> int:
    floors = (1, 11, 21, 31, 41, 51)
    ceilings = (10, 20, 30, 40, 50, 60)
    if not 1 <= recipe_grade <= 6:
        raise ValueError("Recipe grade must be between I and VI.")
    floor_level, ceiling = floors[recipe_grade - 1], ceilings[recipe_grade - 1]
    if character_level < floor_level:
        raise ValueError("Character does not meet the recipe grade level floor.")
    return min(character_level, ceiling)


def slot_cap(slot: ProfessionSlot | str) -> int:
    return SLOT_CAPS[ProfessionSlot(slot)]


def profession_name(profession_id: str) -> str:
    return PROFESSION_BY_ID[profession_id].name


def recipes_for(profession_id: str) -> tuple[RecipeDefinition, ...]:
    return RECIPES_BY_PROFESSION.get(profession_id, ())


def canonical_recipe(recipe_id: str) -> RecipeDefinition | None:
    return RECIPE_BY_ID.get(recipe_id)
