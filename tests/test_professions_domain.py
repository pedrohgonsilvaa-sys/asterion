from decimal import Decimal

import pytest

from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.professions import (
    CATALYST_I,
    FRAGMENT_I,
    IRON,
    MATERIAL_NAMES,
    PROFESSION_IDS,
    RECIPE_DEFINITIONS,
    RESIDUE,
    ProfessionSlot,
    apply_profession_pxp,
    profession_change_cost,
    profession_grade,
    recipe_crown_cost,
    recipe_materials,
    recipe_pxp,
    required_pxp,
    slot_cap,
)


def test_catalog_contains_regional_equipment_alchemy_runes_and_special_recipes():
    assert PROFESSION_IDS == (
        "blacksmith",
        "artificer",
        "alchemist",
        "leatherworker",
        "jeweler",
    )
    assert (
        len(
            [
                recipe
                for recipe in RECIPE_DEFINITIONS
                if recipe.output_kind == "equipment" and recipe.unlock_id is None
            ]
        )
        == 78
    )
    assert len([recipe for recipe in RECIPE_DEFINITIONS if recipe.output_kind == "consumable"]) == 9
    runes = [recipe for recipe in RECIPE_DEFINITIONS if recipe.output_kind == "rune"]
    assert len(runes) == 32
    assert {recipe.rarity for recipe in runes} == {"Rara", "Épica"}
    assert {recipe.required_level for recipe in runes} == {5, 10}
    assert len(
        [
            recipe
            for recipe in RECIPE_DEFINITIONS
            if recipe.unlock_id and recipe.recipe_id.startswith("recipe.tdo.")
        ]
    ) == 3
    echo = next(
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.unlock_id == "recipe.tdo.vigia_partido.eco"
    )
    assert echo.creation_enabled is False
    matriarch = next(
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.recipe_id == "recipe.vde.matriarca.seiva"
    )
    assert matriarch.unlock_id == "recipe.vde.matriarca.seiva"
    assert (matriarch.profession_id, matriarch.required_level, matriarch.grade) == (
        "artificer",
        10,
        2,
    )
    assert (matriarch.output_kind, matriarch.output_id, matriarch.rarity) == (
        "enchantment",
        "HP",
        "Épico",
    )
    assert tuple(
        (material.material_id, material.quantity)
        for material in recipe_materials(matriarch, 20)
    ) == (
        ("material.vde.resina_enredada", 5),
        ("material.vde.ferro_enredado", 2),
        ("material.vde.catalisador_elite_ii", 1),
        ("material.vde.nucleo_matriarca_das_raizes", 1),
    )
    assert recipe_crown_cost(matriarch, 20) == 160
    assert matriarch.creation_enabled is False
    assert MATERIAL_NAMES[IRON] == "Ferro de Fuligem"
    assert MATERIAL_NAMES[RESIDUE] == "Resíduo do Ocaso"
    assert MATERIAL_NAMES[CATALYST_I] == "Catalisador de Elite I"
    assert MATERIAL_NAMES[FRAGMENT_I] == "Fragmento de Aprimoramento I"


def test_profession_curve_caps_grades_and_antispam_match_global_rules():
    assert sum(required_pxp(level) for level in range(1, 15)) == 8540
    assert sum(required_pxp(level) for level in range(1, 30)) == 54300
    assert slot_cap(ProfessionSlot.PRIMARY) == 30
    assert slot_cap(ProfessionSlot.SECONDARY) == 15
    assert [profession_grade(level) for level in (1, 3, 6, 9, 12, 15)] == [1, 2, 3, 4, 5, 6]
    assert recipe_pxp(1, 1, 1) == 100
    assert recipe_pxp(5, 3, 1) == 90
    assert recipe_pxp(5, 6, 1) == 36
    assert recipe_pxp(1, 12, 1) == 0
    assert apply_profession_pxp(1, 0, 250, 15) == (2, 130)
    assert apply_profession_pxp(14, 1000, 9999, 15) == (15, 0)


@pytest.mark.parametrize(
    ("recipe_id", "expected_sw", "expected_materials", "expected_crowns"),
    [
        (
            "recipe.tdo.blacksmith.walker_weapon.comum",
            2,
            {"material.tdo.ferro_de_fuligem": 7, "material.tdo.residuo_ocaso": 3},
            120,
        ),
        (
            "recipe.tdo.blacksmith.walker_greatweapon.raro",
            3,
            {
                "material.tdo.ferro_de_fuligem": 17,
                "material.tdo.residuo_ocaso": 7,
                "material.tdo.fragmento_aprimoramento_i": 12,
            },
            260,
        ),
        (
            "recipe.tdo.jeweler.ash_reliquary.epico",
            2,
            {
                "material.tdo.ferro_de_fuligem": 12,
                "material.tdo.residuo_ocaso": 8,
                "material.tdo.catalisador_elite_i": 4,
                "material.tdo.fragmento_aprimoramento_i": 12,
            },
            250,
        ),
    ],
)
def test_equipment_economy_sw_material_proportions_and_crown_fee(
    recipe_id, expected_sw, expected_materials, expected_crowns
):
    recipe = next(item for item in RECIPE_DEFINITIONS if item.recipe_id == recipe_id)
    assert recipe.sw == expected_sw
    assert {
        item.material_id: item.quantity for item in recipe_materials(recipe, 10)
    } == expected_materials
    assert recipe_crown_cost(recipe, 10) == expected_crowns


def test_profession_change_cost_uses_global_crowns_curve():
    assert profession_change_cost(10, replacement=False) == round_10(
        Decimal(crowns_per_level(10)) * Decimal("0.50")
    )
    assert profession_change_cost(10, replacement=True) == crowns_per_level(10)
    assert profession_change_cost(60, replacement=False) == 500
    assert profession_change_cost(60, replacement=True) == 1000


def test_normal_recipes_use_expected_requirements_and_recipe_pxp_levels():
    common = next(
        item
        for item in RECIPE_DEFINITIONS
        if item.recipe_id == "recipe.tdo.blacksmith.walker_weapon.comum"
    )
    rare = next(
        item
        for item in RECIPE_DEFINITIONS
        if item.recipe_id == "recipe.tdo.blacksmith.walker_weapon.raro"
    )
    epic = next(
        item
        for item in RECIPE_DEFINITIONS
        if item.recipe_id == "recipe.tdo.blacksmith.walker_weapon.epico"
    )
    assert (common.required_level, rare.required_level, epic.required_level) == (1, 5, 10)
    assert Decimal("0.70") == common.primary_ratio
