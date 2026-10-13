from asterion.domain.equipment_modifications import (
    enchantment_compatible,
    enchantment_potency_for,
    rune_compatible,
    rune_potency_for,
)
from asterion.domain.professions import (
    RECIPE_DEFINITIONS,
    VDE_CATALYST_II,
    VDE_FRAGMENT_II,
    VDE_HERB,
    VDE_IRON,
    VDE_LEATHER,
    VDE_RESIN,
    canonical_recipe,
    recipe_crown_cost,
    recipe_materials,
)


def _materials(recipe_id: str) -> dict[str, int]:
    recipe = canonical_recipe(recipe_id)
    assert recipe is not None
    return {item.material_id: item.quantity for item in recipe_materials(recipe, 20)}


def test_vde_grade_ii_equipment_catalog_has_all_thirteen_families():
    recipes = [
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.recipe_id.startswith("recipe.vde.")
        and recipe.output_kind == "equipment"
        and recipe.unlock_id is None
    ]
    assert len(recipes) == 39
    assert {recipe.name for recipe in recipes} == {
        "Arma do Vale",
        "Guarda Enredada",
        "Arma Pesada dos Laços",
        "Elmo Enlaçado",
        "Couraça do Vale",
        "Manoplas Enredadas",
        "Grevas de Turfa",
        "Capuz Musgoso",
        "Veste da Mata Suspensa",
        "Luvas de Turfa",
        "Botas dos Laços",
        "Selo dos Laços",
        "Relicário Enredado",
    }
    assert {recipe.grade for recipe in recipes} == {2}
    assert {
        rarity: {recipe.required_level for recipe in recipes if recipe.rarity == rarity}
        for rarity in ("Comum", "Raro", "Épico")
    } == {"Comum": {3}, "Raro": {5}, "Épico": {10}}

    assert _materials("recipe.vde.blacksmith.vale_weapon.comum") == {
        VDE_IRON: 7,
        VDE_RESIN: 3,
    }
    assert _materials("recipe.vde.blacksmith.bonds_greatweapon.raro") == {
        VDE_IRON: 17,
        VDE_RESIN: 7,
        VDE_FRAGMENT_II: 12,
    }
    assert _materials("recipe.vde.leatherworker.suspended_forest_vest.epico") == {
        VDE_LEATHER: 14,
        VDE_HERB: 6,
        VDE_CATALYST_II: 4,
        VDE_FRAGMENT_II: 12,
    }
    assert _materials("recipe.vde.jeweler.entwined_reliquary.epico") == {
        VDE_IRON: 12,
        VDE_RESIN: 8,
        VDE_CATALYST_II: 4,
        VDE_FRAGMENT_II: 12,
    }


def test_vde_grade_ii_alchemy_catalog_matches_published_five_recipes():
    expected = {
        "recipe.vde.alchemist.heal.vde.ii": (
            "consumable.heal.vde.ii",
            3,
            40,
            {VDE_HERB: 3, VDE_RESIN: 1},
        ),
        "recipe.vde.alchemist.purification.vde.ii": (
            "consumable.purification.vde.ii",
            3,
            60,
            {VDE_HERB: 2, VDE_RESIN: 2},
        ),
        "recipe.vde.alchemist.antidote.vde.ii": (
            "consumable.antidote.vde.ii",
            5,
            60,
            {VDE_HERB: 4, VDE_RESIN: 1},
        ),
        "recipe.vde.alchemist.vigor.vde.ii": (
            "consumable.vigor.vde.ii",
            10,
            200,
            {VDE_HERB: 6, VDE_RESIN: 4, VDE_CATALYST_II: 1},
        ),
        "recipe.vde.alchemist.protection.vde.ii": (
            "consumable.protection.vde.ii",
            5,
            80,
            {VDE_HERB: 3, VDE_RESIN: 2},
        ),
    }
    recipes = [
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.recipe_id.startswith("recipe.vde.alchemist.")
    ]
    assert {recipe.recipe_id for recipe in recipes} == set(expected)
    for recipe_id, (output_id, level, crowns, materials) in expected.items():
        recipe = canonical_recipe(recipe_id)
        assert recipe is not None
        assert recipe.grade == 2
        assert recipe.output_id == output_id
        assert recipe.required_level == level
        assert recipe_crown_cost(recipe, 20) == crowns
        assert _materials(recipe_id) == materials


def test_vde_grade_ii_rune_recipes_and_potencies_are_canonical():
    recipes = [
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.recipe_id.startswith("recipe.vde.artificer.rune.")
    ]
    assert len(recipes) == 16
    assert {recipe.name for recipe in recipes} == {
        "Runa do Espinho",
        "Runa da Casca",
        "Runa das Copas",
        "Runa do Nó",
        "Runa da Caçada",
        "Runa da Seiva",
        "Runa da Névoa",
        "Runa das Raízes",
    }
    assert {recipe.grade for recipe in recipes} == {2}
    assert {recipe.rarity for recipe in recipes} == {"Rara", "Épica"}
    assert not any("lendaria" in recipe.recipe_id for recipe in recipes)

    rare = canonical_recipe("recipe.vde.artificer.rune.espinho.rara")
    epic = canonical_recipe("recipe.vde.artificer.rune.espinho.epica")
    assert rare is not None and epic is not None
    assert recipe_crown_cost(rare, 20) == 120
    assert recipe_crown_cost(epic, 20) == 240
    assert _materials(rare.recipe_id) == {
        VDE_RESIN: 4,
        VDE_IRON: 2,
        VDE_FRAGMENT_II: 2,
    }
    assert _materials(epic.recipe_id) == {
        VDE_RESIN: 7,
        VDE_IRON: 3,
        VDE_CATALYST_II: 1,
        VDE_FRAGMENT_II: 4,
    }

    assert rune_potency_for("Espinho", "Rara", 2) == "0.40%"
    assert rune_potency_for("Espinho", "Lendária", 2) == "0.65%"
    assert rune_potency_for("Casca", "Rara", 2) == "0.65%"
    assert rune_potency_for("Raízes", "Lendária", 2) == "0.75 p.p."
    assert rune_compatible("Principal", "Espinho")
    assert not rune_compatible("Torso", "Espinho")


def test_vde_grade_ii_enchantment_recipes_and_potencies_are_canonical():
    recipes = [
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.recipe_id.startswith("recipe.vde.artificer.enchantment.")
    ]
    assert len(recipes) == 16
    assert {recipe.name for recipe in recipes} == {
        "Fio Enredado",
        "Pele de Casca",
        "Passo das Copas",
        "Marca do Nó",
        "Eco da Caçada",
        "Sopro de Seiva",
        "Véu da Mata",
        "Selo das Raízes",
    }
    assert {recipe.grade for recipe in recipes} == {2}
    assert {recipe.rarity for recipe in recipes} == {"Raro", "Épico"}
    assert all(recipe.creation_enabled is False for recipe in recipes)
    assert not any("lendario" in recipe.recipe_id for recipe in recipes)

    rare = canonical_recipe("recipe.vde.artificer.enchantment.fio_enredado.raro")
    epic = canonical_recipe("recipe.vde.artificer.enchantment.fio_enredado.epico")
    assert rare is not None and epic is not None
    assert recipe_crown_cost(rare, 20) == 80
    assert recipe_crown_cost(epic, 20) == 160
    assert _materials(rare.recipe_id) == {VDE_RESIN: 3, VDE_IRON: 1}
    assert _materials(epic.recipe_id) == {
        VDE_RESIN: 5,
        VDE_IRON: 2,
        VDE_CATALYST_II: 1,
    }

    assert enchantment_potency_for("Fio Enredado", "Raro", 2) == "0.15%"
    assert enchantment_potency_for("Pele de Casca", "Épico", 2) == "0.45%"
    assert enchantment_potency_for("Seiva da Matriarca", "Épico", 2) == "0.20%"
    assert enchantment_compatible("Principal", "Fio Enredado")
    assert not enchantment_compatible("Torso", "Fio Enredado")
