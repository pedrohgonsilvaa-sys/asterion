from uuid import uuid4

from asterion.application.inventory import (
    InventoryView,
    consumable_inventory_entry,
)
from asterion.application.round import CONSUMABLE_LIMITS as ROUND_CONSUMABLE_LIMITS
from asterion.bot.inventory_ui import render_inventory
from asterion.domain.consumables import (
    COMBAT_CD_GROUP,
    CONSUMABLE_CATALOG,
    CONSUMABLE_FAMILIES,
    DUNGEON_RUN_CONSUMABLE_LIMITS,
    ENCOUNTER_CONSUMABLE_LIMITS,
    FAMILY_POLICIES,
    OTHER_CONSUMABLE_LIMITS,
    VIGOR_CYCLE_TIMEZONE,
    VIGOR_DAILY_RESET_HOUR,
    VIGOR_MAXIMUM,
    VIGOR_RESTORE,
    VIGOR_USABLE_AT_OR_BELOW,
    ConsumableFamily,
    ConsumableTarget,
    UseContext,
    consumable_limit,
    definition,
    family_definitions,
    grade_label,
    round_eligible,
)


def test_catalog_has_all_seven_families_and_stable_item_ids():
    assert set(CONSUMABLE_FAMILIES) == set(FAMILY_POLICIES)
    assert set(CONSUMABLE_FAMILIES) == {
        ConsumableFamily.HEALING,
        ConsumableFamily.PURIFICATION,
        ConsumableFamily.ANTIDOTE,
        ConsumableFamily.VIGOR,
        ConsumableFamily.PROTECTION,
        ConsumableFamily.DISPELLER,
        ConsumableFamily.WARDING,
    }
    assert len(CONSUMABLE_CATALOG) == 24
    assert len(CONSUMABLE_CATALOG) == len(set(CONSUMABLE_CATALOG))
    assert all(len(item_id) <= 64 for item_id in CONSUMABLE_CATALOG)
    assert all(family_definitions(family) for family in CONSUMABLE_FAMILIES)
    assert definition("consumable.heal").id == "consumable.heal"
    assert definition("consumable.purification").id == "consumable.purification"


def test_catalog_names_real_grades_regions_and_targets():
    expected = {
        "consumable.heal": ("Poção de Cura", 1, "Terras do Ocaso", ConsumableTarget.SELF),
        "consumable.purification": (
            "Preparado de Purificação",
            1,
            "Terras do Ocaso",
            ConsumableTarget.SELF_NEGATIVE_EFFECT,
        ),
        "consumable.antidote.tdo.i": (
            "Antídoto Cinzento",
            1,
            "Terras do Ocaso",
            ConsumableTarget.SELF_DOT,
        ),
        "consumable.vigor.tdo.i": (
            "Poção de Vigor",
            1,
            "Terras do Ocaso",
            ConsumableTarget.SELF,
        ),
        "consumable.heal.vde.ii": (
            "Poção de Cura do Vale",
            2,
            "Vales dos Enforcados",
            ConsumableTarget.SELF,
        ),
        "consumable.purification.vde.ii": (
            "Preparado de Purificação Enredada",
            2,
            "Vales dos Enforcados",
            ConsumableTarget.SELF_NEGATIVE_EFFECT,
        ),
        "consumable.antidote.vde.ii": (
            "Antídoto de Turfa",
            2,
            "Vales dos Enforcados",
            ConsumableTarget.SELF_DOT,
        ),
        "consumable.vigor.vde.ii": (
            "Poção de Vigor dos Laços",
            2,
            "Vales dos Enforcados",
            ConsumableTarget.SELF,
        ),
        "consumable.protection.vde.ii": (
            "Preparado de Proteção Enredada",
            2,
            "Vales dos Enforcados",
            ConsumableTarget.SELF,
        ),
        "consumable.heal.nareth.iii": (
            "Poção de Cura de Nareth",
            3,
            "Planícies de Nareth",
            ConsumableTarget.SELF,
        ),
        "consumable.purification.nareth.iii": (
            "Preparado de Purificação do Eixo",
            3,
            "Planícies de Nareth",
            ConsumableTarget.SELF_NEGATIVE_EFFECT,
        ),
        "consumable.antidote.nareth.iii": (
            "Antídoto das Campinas",
            3,
            "Planícies de Nareth",
            ConsumableTarget.SELF_DOT,
        ),
        "consumable.vigor.nareth.iii": (
            "Poção de Vigor do Meridiano",
            3,
            "Planícies de Nareth",
            ConsumableTarget.SELF,
        ),
        "consumable.protection.nareth.iii": (
            "Preparado de Proteção do Prumo",
            3,
            "Planícies de Nareth",
            ConsumableTarget.SELF,
        ),
        "consumable.dispeller.nareth.iii": (
            "Dissipador de Referência",
            3,
            "Planícies de Nareth",
            ConsumableTarget.ENEMY_POSITIVE_EFFECT,
        ),
        "consumable.dispeller.iii": ("Dissipador", 3, None, ConsumableTarget.ENEMY_POSITIVE_EFFECT),
        "consumable.warding.iv": ("Preparado de Resguardo", 4, None, ConsumableTarget.SELF),
        "consumable.heal.varzeas.iv": (
            "Poção de Cura da Salmoura", 4, "Várzeas Carmesins", ConsumableTarget.SELF
        ),
        "consumable.purification.varzeas.iv": (
            "Preparado de Purificação dos Juncos",
            4,
            "Várzeas Carmesins",
            ConsumableTarget.SELF_NEGATIVE_EFFECT,
        ),
        "consumable.antidote.varzeas.iv": (
            "Antídoto Ferruginoso", 4, "Várzeas Carmesins", ConsumableTarget.SELF_DOT
        ),
        "consumable.vigor.varzeas.iv": (
            "Poção de Vigor do Porto", 4, "Várzeas Carmesins", ConsumableTarget.SELF
        ),
        "consumable.protection.varzeas.iv": (
            "Preparado de Proteção do Dique",
            4,
            "Várzeas Carmesins",
            ConsumableTarget.SELF,
        ),
        "consumable.dispeller.varzeas.iv": (
            "Dissipador Hemaris",
            4,
            "Várzeas Carmesins",
            ConsumableTarget.ENEMY_POSITIVE_EFFECT,
        ),
        "consumable.warding.varzeas.iv": (
            "Preparado de Resguardo Clínico",
            4,
            "Várzeas Carmesins",
            ConsumableTarget.SELF,
        ),
    }
    assert set(expected) == set(CONSUMABLE_CATALOG)
    for item_id, (name, grade, region, target) in expected.items():
        item = definition(item_id)
        assert item is not None
        assert (item.name, item.grade, item.region, item.target) == (name, grade, region, target)
        assert item.recipe is not None


def test_only_healing_and_purification_are_round_eligible_and_combat_items_share_cd2():
    eligible_families = {
        item.family for item in CONSUMABLE_CATALOG.values() if item.round_eligible
    }
    assert eligible_families == {
        ConsumableFamily.HEALING,
        ConsumableFamily.PURIFICATION,
    }
    assert round_eligible("consumable.heal") is True
    assert round_eligible("consumable.purification") is True
    assert round_eligible("consumable.heal.nareth.iii") is True
    assert round_eligible("consumable.purification.nareth.iii") is True
    assert round_eligible("consumable.antidote.tdo.i") is False
    assert round_eligible("consumable.vigor.tdo.i") is False
    assert round_eligible("consumable.protection.vde.ii") is False
    assert round_eligible("consumable.dispeller.iii") is False
    assert round_eligible("consumable.warding.iv") is False
    for item in CONSUMABLE_CATALOG.values():
        if item.family == ConsumableFamily.VIGOR:
            assert item.use_context is UseContext.OUT_OF_COMBAT
            assert item.cooldown_group is None
        else:
            assert item.use_context is UseContext.COMBAT_PVE
            assert item.cooldown_group == COMBAT_CD_GROUP


def test_global_dispeller_and_warding_have_no_invented_regional_names():
    dispeller = definition("consumable.dispeller.iii")
    warding = definition("consumable.warding.iv")
    assert dispeller is not None and dispeller.region is None and dispeller.name == "Dissipador"
    assert warding is not None and warding.region is None
    assert warding.name == "Preparado de Resguardo"


def test_official_recipe_and_cycle_metadata():
    protection = definition("consumable.protection.vde.ii")
    assert protection is not None
    assert protection.recipe.profession_level == 5
    assert protection.recipe.crown_cost == 80
    assert [(part.name, part.quantity) for part in protection.recipe.ingredients] == [
        ("Ervas de Turfa", 3),
        ("Resinas Enredadas", 2),
    ]
    assert VIGOR_RESTORE == 20
    assert VIGOR_USABLE_AT_OR_BELOW == 80
    assert VIGOR_MAXIMUM == 100
    assert VIGOR_DAILY_RESET_HOUR == 6
    assert VIGOR_CYCLE_TIMEZONE == "America/Sao_Paulo"
    assert grade_label(1) == "I"
    assert grade_label(2) == "II"


def test_official_consumable_budget_policy():
    assert dict(ENCOUNTER_CONSUMABLE_LIMITS) == {
        "common": 1,
        "uncommon": 1,
        "elite": 2,
        "boss": 3,
    }
    assert dict(DUNGEON_RUN_CONSUMABLE_LIMITS) == {
        "stable": 6,
        "fractured": 5,
        "rupture": 4,
    }
    assert dict(OTHER_CONSUMABLE_LIMITS) == {"world_event": 2, "oath_trial": 3, "pvp": 0}
    assert consumable_limit("encounter", "elite") == 2
    assert consumable_limit("dungeon_run", "rupture") == 4
    assert consumable_limit("world_event") == 2
    assert consumable_limit("oath_trial") == 3
    assert consumable_limit("pvp") == 0
    assert dict(ROUND_CONSUMABLE_LIMITS) == dict(ENCOUNTER_CONSUMABLE_LIMITS)


def test_inventory_resolves_stable_id_and_renders_actual_grade():
    entry = consumable_inventory_entry("consumable.heal", 4)
    assert entry.key == "consumable.heal"
    assert entry.title == "Poção de Cura"
    assert entry.quantity == 4
    assert entry.grade == 1
    assert entry.payload["family"] == "healing"
    screen = render_inventory(
        InventoryView(
            "inventory_category",
            uuid4(),
            used_slots=1,
            category="consumables",
            entries=(entry,),
        )
    )
    assert "1 🧪 Poção de Cura · 4" in screen.text
    assert "Consumível · Grau I" in screen.text

    protection = consumable_inventory_entry("consumable.protection.vde.ii", 3)
    assert protection.title == "Preparado de Proteção Enredada"
    assert protection.grade == 2
    screen = render_inventory(
        InventoryView(
            "inventory_category",
            uuid4(),
            used_slots=1,
            category="consumables",
            entries=(protection,),
        )
    )
    assert "Preparado de Proteção Enredada · 3" in screen.text
    assert "Consumível · Grau II" in screen.text


def test_inventory_keeps_unknown_legacy_stock_visible():
    entry = consumable_inventory_entry("consumable.legacy.unknown", 2)
    assert entry.title == "consumable.legacy.unknown"
    assert entry.grade is None
