from asterion.domain.consumables import ConsumableFamily
from asterion.domain.consumables import definition as consumable
from asterion.domain.equipment_modifications import (
    enchantment_potency_for,
    rune_potency_for,
)
from asterion.domain.professions import (
    NARETH_ARCHON_CORE,
    NARETH_BRONZE,
    NARETH_CATALYST_III,
    NARETH_FRAGMENT_III,
    NARETH_GALLERIES_CORE,
    NARETH_HERB,
    NARETH_LEATHER,
    NARETH_OBSERVATORY_CORE,
    NARETH_POWDER,
    RECIPE_BY_ID,
    RECIPE_DEFINITIONS,
    MaterialRequirement,
    canonical_recipe,
    recipe_materials,
)

NARETH_RUNES = {
    "Meridiano": ("ATQ", "Runa do Meridiano"),
    "Prumo": ("DEF", "Runa do Prumo"),
    "Horizonte": ("AGI", "Runa do Horizonte"),
    "Marco": ("PER", "Runa do Marco"),
    "Distância": ("CRIT", "Runa da Distância"),
    "Abrigo": ("HP", "Runa do Abrigo"),
    "Desvio": ("Esquiva", "Runa do Desvio"),
    "Referência": ("Bloqueio", "Runa da Referência"),
}


def test_nareth_has_all_thirteen_grade_iii_equipment_families_for_published_rarities():
    regional = [
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.recipe_id.startswith(
            ("recipe.nareth.blacksmith.", "recipe.nareth.leatherworker.", "recipe.nareth.jeweler.")
        )
    ]
    assert len(regional) == 39
    assert {recipe.grade for recipe in regional} == {3}
    assert {recipe.rarity for recipe in regional} == {"Comum", "Raro", "Épico"}
    assert len({recipe.name for recipe in regional}) == 13
    assert all(recipe.required_level >= 6 for recipe in regional)

    weapon = canonical_recipe("recipe.nareth.blacksmith.meridian_weapon.raro")
    assert weapon is not None
    assert recipe_materials(weapon, 21) == (
        MaterialRequirement(NARETH_BRONZE, 11),
        MaterialRequirement(NARETH_POWDER, 5),
        MaterialRequirement(NARETH_FRAGMENT_III, 8, False),
    )

    leather = canonical_recipe("recipe.nareth.leatherworker.horizon_hood.comum")
    assert leather is not None
    assert recipe_materials(leather, 21) == (
        MaterialRequirement(NARETH_LEATHER, 4),
        MaterialRequirement(NARETH_HERB, 1),
    )

    jeweler = canonical_recipe("recipe.nareth.jeweler.axis_seal.epico")
    assert jeweler is not None
    assert recipe_materials(jeweler, 21) == (
        MaterialRequirement(NARETH_BRONZE, 12),
        MaterialRequirement(NARETH_POWDER, 8),
        MaterialRequirement(NARETH_CATALYST_III, 4, False),
        MaterialRequirement(NARETH_FRAGMENT_III, 12, False),
    )


def test_nareth_grade_iii_rune_catalog_uses_source_potencies_and_costs():
    recipes = [
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.recipe_id.startswith("recipe.nareth.artificer.rune.")
    ]
    assert len(recipes) == 16
    assert {recipe.output_family for recipe in recipes} == set(NARETH_RUNES)
    assert {recipe.grade for recipe in recipes} == {3}

    expected_potencies = {
        "HP": ("0.40%", "0.55%"),
        "ATQ": ("0.40%", "0.55%"),
        "DEF": ("0.70%", "1.00%"),
        "AGI": ("0.70%", "1.00%"),
        "PER": ("0.25 p.p.", "0.50 p.p."),
        "CRIT": ("0.25 p.p.", "0.50 p.p."),
        "Esquiva": ("0.25 p.p.", "0.25 p.p."),
        "Bloqueio": ("0.25 p.p.", "0.50 p.p."),
    }
    for family, (stat, name) in NARETH_RUNES.items():
        assert name in {recipe.name for recipe in recipes if recipe.output_family == family}
        assert tuple(
            rune_potency_for(family, rarity, 3) for rarity in ("Rara", "Épica")
        ) == expected_potencies[stat]

    rare = canonical_recipe("recipe.nareth.artificer.rune.meridiano.rara")
    epic = canonical_recipe("recipe.nareth.artificer.rune.referencia.epica")
    assert rare is not None and rare.fixed_crown_cost == 160
    assert rare.fixed_materials == (
        MaterialRequirement(NARETH_POWDER, 4),
        MaterialRequirement(NARETH_BRONZE, 2),
        MaterialRequirement(NARETH_FRAGMENT_III, 2, False),
    )
    assert epic is not None and epic.fixed_crown_cost == 330
    assert epic.fixed_materials == (
        MaterialRequirement(NARETH_POWDER, 7),
        MaterialRequirement(NARETH_BRONZE, 3),
        MaterialRequirement(NARETH_CATALYST_III, 1, False),
        MaterialRequirement(NARETH_FRAGMENT_III, 4, False),
    )


def test_nareth_grade_iii_enchantments_and_calibration_match_source_values():
    recipes = [
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.recipe_id.startswith("recipe.nareth.artificer.enchantment.")
    ]
    assert len(recipes) == 16
    assert {recipe.grade for recipe in recipes} == {3}
    expected = {
        "Fio do Meridiano": ("ATQ", "0.15%", "0.25%"),
        "Pele do Prumo": ("DEF", "0.30%", "0.50%"),
        "Passo do Horizonte": ("AGI", "0.30%", "0.50%"),
        "Marca de Referência": ("PER", "0.25 p.p.", "0.25 p.p."),
        "Eco da Distância": ("CRIT", "0.25 p.p.", "0.25 p.p."),
        "Sopro do Posto": ("HP", "0.15%", "0.25%"),
        "Véu do Desvio": ("Esquiva", "0.25 p.p.", "0.25 p.p."),
        "Selo do Eixo": ("Bloqueio", "0.25 p.p.", "0.25 p.p."),
    }
    for family, (stat, rare, epic) in expected.items():
        assert tuple(
            enchantment_potency_for(family, rarity, 3) for rarity in ("Raro", "Épico")
        ) == (rare, epic)
        family_recipes = [recipe for recipe in recipes if recipe.output_family == family]
        assert {recipe.output_id for recipe in family_recipes} == {stat}

    calibration = canonical_recipe("recipe.nareth.arconte.calibracao")
    assert calibration is not None
    assert calibration.grade == 3 and calibration.rarity == "Épico"
    assert calibration.output_family == "Calibração do Arconte"
    assert enchantment_potency_for("Calibração do Arconte", "Épico", 3) == "0.25 p.p."
    assert calibration.fixed_crown_cost == 220
    assert calibration.fixed_materials == (
        MaterialRequirement(NARETH_POWDER, 5),
        MaterialRequirement(NARETH_BRONZE, 2),
        MaterialRequirement(NARETH_CATALYST_III, 1, False),
        MaterialRequirement(NARETH_ARCHON_CORE, 1),
    )


def test_nareth_grade_iii_consumables_and_special_recipe_costs_match_source():
    expected_consumables = {
        "consumable.heal.nareth.iii": (ConsumableFamily.HEALING, 6, 60),
        "consumable.purification.nareth.iii": (ConsumableFamily.PURIFICATION, 6, 80),
        "consumable.antidote.nareth.iii": (ConsumableFamily.ANTIDOTE, 6, 80),
        "consumable.vigor.nareth.iii": (ConsumableFamily.VIGOR, 10, 280),
        "consumable.protection.nareth.iii": (ConsumableFamily.PROTECTION, 6, 110),
        "consumable.dispeller.nareth.iii": (ConsumableFamily.DISPELLER, 10, 140),
    }
    for item_id, (family, profession_level, crown_cost) in expected_consumables.items():
        item = consumable(item_id)
        assert item is not None
        assert item.grade == 3 and item.region == "Planícies de Nareth"
        assert item.family == family
        assert item.recipe.profession_level == profession_level
        assert item.recipe.crown_cost == crown_cost
        recipe = RECIPE_BY_ID[f"recipe.nareth.alchemist.{item_id.removeprefix('consumable.')}"]
        assert recipe.output_id == item_id and recipe.grade == 3

    assert consumable("consumable.warding.nareth.iii") is None

    relic = canonical_recipe("recipe.nareth.galerias.relicario_circuito_retornado")
    guard = canonical_recipe("recipe.nareth.observatorio.guarda_referencia")
    assert relic is not None and relic.output_slot == "Artefato" and relic.rarity == "Raro"
    assert relic.fixed_crown_cost is None and relic.unlock_id == relic.recipe_id
    assert relic.fixed_materials == (
        MaterialRequirement(NARETH_BRONZE, 10),
        MaterialRequirement(NARETH_POWDER, 6),
        MaterialRequirement(NARETH_FRAGMENT_III, 8, False),
        MaterialRequirement(NARETH_GALLERIES_CORE, 1),
    )
    assert guard is not None and guard.output_slot == "Secundária" and guard.rarity == "Épico"
    assert guard.fixed_crown_cost is None and guard.unlock_id == guard.recipe_id
    assert guard.fixed_materials == (
        MaterialRequirement(NARETH_BRONZE, 7),
        MaterialRequirement(NARETH_POWDER, 3),
        MaterialRequirement(NARETH_CATALYST_III, 2, False),
        MaterialRequirement(NARETH_FRAGMENT_III, 6, False),
        MaterialRequirement(NARETH_OBSERVATORY_CORE, 1),
    )
