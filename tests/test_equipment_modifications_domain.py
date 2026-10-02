"""Numerical and codec contracts for C2 equipment modifications."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from asterion.application.dungeons import DungeonService
from asterion.domain.combat_math import class_stats, resolve_combat_stats
from asterion.domain.equipment_modifications import (
    EquipmentModificationError,
    dismantle_quantities,
    effective_enchantment_potency,
    enchantment_compatible,
    enchantment_multiplier,
    enchantment_potency_for,
    enhancement_crown_cost,
    enhancement_fragment_cost,
    equipment_grade,
    parse_component_potency,
    reroll_candidates,
    reroll_crown_cost,
    reroll_secondary,
    rune_compatible,
    rune_potency_for,
)
from asterion.domain.equipment_stats import (
    ENHANCEMENT_MULTIPLIERS,
    EquipmentConfigurationError,
    EquipmentConfigurationSnapshot,
    equipment_configuration_from_data,
    equipment_stat_contribution,
    item_snapshot_from_persisted,
)
from asterion.domain.road import materialize_equipment, rune_potency

D = Decimal


@pytest.mark.parametrize(
    ("level", "grade"),
    [(1, 1), (10, 1), (11, 2), (20, 2), (51, 6), (60, 6)],
)
def test_equipment_grade_uses_immutable_item_level(level, grade):
    assert equipment_grade(level) == grade


@pytest.mark.parametrize("level", [0, 61, True, D("10")])
def test_equipment_grade_rejects_invalid_level(level):
    with pytest.raises(EquipmentModificationError):
        equipment_grade(level)


def test_enhancement_uses_slot_weight_and_fragments_use_economy_sw():
    assert enhancement_crown_cost(10, "Principal", "Comum", 1) == 50
    assert enhancement_crown_cost(10, "Torso", "Épico", 6) == 100
    assert enhancement_crown_cost(11, "2H", "Raro", 10) == 650
    assert enhancement_fragment_cost("Secundária", 1) == 1
    assert enhancement_fragment_cost("Principal", 6) == 4
    assert enhancement_fragment_cost("2H", 10) == 15


@pytest.mark.parametrize(
    ("step", "expected"),
    [
        (0, "1.00"), (1, "1.02"), (2, "1.04"), (3, "1.06"), (4, "1.08"),
        (5, "1.10"), (6, "1.125"), (7, "1.15"), (8, "1.175"), (9, "1.20"),
        (10, "1.25"),
    ],
)
def test_all_enhancement_multipliers_apply_to_core_and_secondaries(step, expected):
    assert ENHANCEMENT_MULTIPLIERS[step] == D(expected)
    item = item_snapshot_from_persisted(
        item_instance_id=f"enhancement-{step}",
        equipped_slot="Principal",
        item_slot="Principal",
        item_level=10,
        rarity="Comum",
        payload={
            "slot": "Principal",
            "enhancement": step,
            "core": {"ATQ": "100"},
            "secondaries": [],
        },
    )
    assert equipment_stat_contribution(item).attack == D("100") * D(expected)


def test_component_pools_and_two_handed_affinities():
    assert rune_compatible("2H", "Caminhante", "A")
    assert not rune_compatible("2H", "Caminhante", "B")
    assert rune_compatible("2H", "Guarda", "B")
    assert not rune_compatible("2H", "Guarda", "A")
    assert enchantment_compatible("2H", "Selo de Guarda")
    assert enchantment_multiplier("2H", "ATQ") == 2
    assert enchantment_multiplier("2H", "PER") == 2
    assert enchantment_multiplier("2H", "CRIT") == 2
    assert enchantment_multiplier("2H", "Bloqueio") == 1
    assert effective_enchantment_potency("2H", "Eco do Vigia Partido", "Épico", 1) == (
        "0.50 p.p."
    )
    assert effective_enchantment_potency("2H", "Selo de Guarda", "Épico", 1) == (
        "0.25 p.p."
    )
    assert not rune_compatible("Torso", "Brasa")


@pytest.mark.parametrize(
    ("slot", "pool"),
    [
        ("Principal", {"ATQ", "AGI", "PER", "CRIT"}),
        ("Secundária", {"ATQ", "DEF", "PER", "CRIT", "Bloqueio"}),
        ("Cabeça", {"HP", "DEF", "PER", "CRIT"}),
        ("Torso", {"HP", "DEF", "Bloqueio"}),
        ("Mãos", {"ATQ", "DEF", "AGI", "PER", "CRIT"}),
        ("Pés", {"HP", "DEF", "AGI", "Esquiva"}),
        ("Acessório", {"HP", "ATQ", "AGI", "PER", "CRIT", "Esquiva"}),
        ("Artefato", {"HP", "ATQ", "DEF", "PER", "CRIT", "Bloqueio"}),
    ],
)
def test_all_rune_and_enchantment_slot_pools(slot, pool):
    families = {
        "Brasa": "ATQ", "Pedra": "DEF", "Caminhante": "AGI", "Fresta": "PER",
        "Presságio": "CRIT", "Persistência": "HP", "Desvio": "Esquiva", "Guarda": "Bloqueio",
    }
    for rune_family, effect in families.items():
        assert rune_compatible(slot, rune_family) is (effect in pool)
    for enchantment_family, effect in {
        "Fio Cinéreo": "ATQ", "Pele de Pedra": "DEF", "Passo de Fuligem": "AGI",
        "Marca da Fresta": "PER", "Eco do Presságio": "CRIT", "Sopro Persistente": "HP",
        "Véu de Desvio": "Esquiva", "Selo de Guarda": "Bloqueio",
    }.items():
        assert enchantment_compatible(slot, enchantment_family) is (effect in pool)


def test_regional_and_global_component_potencies_are_exact():
    assert rune_potency_for("Brasa", "Rara", 1) == "0.35%"
    assert rune_potency_for("Guarda", "Épica", 1) == "0.50 p.p."
    assert rune_potency_for("Brasa", "Rara", 2) == "0.40%"
    assert rune_potency_for("Brasa", "Rara", 6) == "0.60%"
    assert enchantment_potency_for("Fio Cinéreo", "Raro", 1) == "0.10%"
    assert enchantment_potency_for("Eco do Vigia Partido", "Épico", 1) == "0.25 p.p."
    assert enchantment_potency_for("Fio Cinéreo", "Raro", 6) == "0.20%"
    assert parse_component_potency("0.35%", "ATQ") == D("0.0035")
    assert parse_component_potency("0.25 p.p.", "PER") == D("0.25")
    assert rune_potency("Brasa", "Rara") == "0.35%"
    assert rune_potency("Brasa", "Rara", 6) == "0.60%"


def test_dungeon_rupture_materializes_grade_six_potency():
    run = SimpleNamespace(difficulty="rupture", reference_level=60, seed="rune-grade-six")
    payload = next(
        result
        for index in range(100)
        if (result := DungeonService._roll_rune(None, run, seed=str(index))) is not None
    )
    assert payload["grade"] == 6
    assert payload["potency"] == rune_potency_for(payload["family"], payload["rarity"], 6)


def test_two_handed_materializer_and_reroll_keep_weight_28():
    item = materialize_equipment(
        "0", "Raro", 60, forced_name="Arma Pesada do Caminhante", forced_slot="2H"
    )
    assert item["secondaries"] == [{"attribute": "AGI", "value": "6"}]
    choices = reroll_candidates("2H", item["secondaries"], 0)
    assert choices == ("ATQ", "PER", "CRIT")
    replacement = reroll_secondary(
        "item-2h", "2H", "Raro", 60, item["secondaries"], 0, 1
    )
    assert replacement["attribute"] in choices
    assert replacement["attribute"] != "AGI"
    assert replacement == reroll_secondary(
        "item-2h", "2H", "Raro", 60, item["secondaries"], 0, 1
    )
    expected_magnitudes = {"ATQ": "3", "PER": "1.50", "CRIT": "1.25"}
    assert replacement["value"] == expected_magnitudes[replacement["attribute"]]


@pytest.mark.parametrize(
    ("count", "expected"),
    [(0, 120), (1, 190), (2, 250), (3, 380), (4, 500), (5, 500)],
)
def test_reroll_cost_counts_operations_for_one_item(count, expected):
    assert reroll_crown_cost(10, count) == expected


@pytest.mark.parametrize(
    ("rarity", "expected"),
    [
        ("Comum", (3, 0, 0)),
        ("Raro", (6, 0, 3)),
        ("Épico", (9, 2, 6)),
        ("Lendário", (12, 3, 12)),
        ("Mítico", (18, 6, 24)),
    ],
)
def test_dismantle_quantities_use_economy_sw_and_ignore_enhancement(rarity, expected):
    result = dismantle_quantities("2H", rarity)
    assert (result.basics, result.catalysts, result.fragments) == expected


@pytest.mark.parametrize(("slot", "sw"), [("Mãos", 1), ("Torso", 2), ("2H", 3)])
@pytest.mark.parametrize(
    ("rarity", "basic_per_sw", "catalyst_per_sw", "fragment_per_sw"),
    [
        ("Comum", 1, 0, 0),
        ("Raro", 2, 0, 1),
        ("Épico", 3, None, 2),
        ("Lendário", 4, 1, 4),
        ("Mítico", 6, 2, 8),
    ],
)
def test_dismantle_returns_for_sw_one_two_and_three(
    slot, sw, rarity, basic_per_sw, catalyst_per_sw, fragment_per_sw
):
    result = dismantle_quantities(slot, rarity)
    expected_catalysts = (
        (sw + 1) // 2 if catalyst_per_sw is None else catalyst_per_sw * sw
    )
    assert result.basics == basic_per_sw * sw
    assert result.catalysts == expected_catalysts
    assert result.fragments == fragment_per_sw * sw


def test_item_snapshot_freezes_two_handed_runes_and_enchantment_with_stages():
    payload = {
        "slot": "2H",
        "enhancement": 10,
        "core": {"ATQ": "35"},
        "secondaries": [],
        "rune": None,
        "runes": {
            "A": {
                "family": "Brasa", "rarity": "Rara", "grade": 1,
                "potency": "0.35%", "bound": False,
            },
            "B": {
                "family": "Guarda", "rarity": "Rara", "grade": 1,
                "potency": "0.25 p.p.", "bound": True,
            },
        },
        "enchantment": {
            "family": "Eco do Vigia Partido", "rarity": "Épico", "grade": 1,
            "potency": "0.25 p.p.", "bound": False,
        },
    }
    item = item_snapshot_from_persisted(
        item_instance_id="two-handed", equipped_slot="Principal", item_slot="2H",
        item_level=10, rarity="Comum", payload=payload,
    )
    contribution = equipment_stat_contribution(item)
    assert contribution.attack == D("43.75")
    assert contribution.rune_percent[1] == D("0.0035")
    assert contribution.rune_points[7] == D("0.25")
    assert contribution.enchantment_points[4] == D("0.50")
    frozen = EquipmentConfigurationSnapshot(7, (item,)).to_data("legacy")
    assert frozen["equipment"][0]["runes"]["B"]["bound"] is True
    restored = equipment_configuration_from_data(frozen)
    assert restored == EquipmentConfigurationSnapshot(7, (item,))


def test_item_snapshot_validates_component_effect_grade_and_potency():
    base = {
        "slot": "Principal", "enhancement": 0, "core": {"ATQ": "10"},
        "secondaries": [], "enchantment": None,
    }
    for rune in (
        {"family": "Pedra", "rarity": "Rara", "grade": 1, "potency": "0.55%", "bound": False},
        {"family": "Brasa", "rarity": "Rara", "grade": 2, "potency": "0.40%", "bound": False},
        {"family": "Brasa", "rarity": "Rara", "grade": 1, "potency": "0.35 p.p.", "bound": False},
    ):
        with pytest.raises(EquipmentConfigurationError):
            item_snapshot_from_persisted(
                item_instance_id="invalid", equipped_slot="Principal", item_slot="Principal",
                item_level=10, rarity="Comum", payload=base | {"rune": rune},
            )


def test_rune_and_enchantment_percentage_follow_enhancement_before_race():
    item = item_snapshot_from_persisted(
        item_instance_id="main-hand",
        equipped_slot="Principal",
        item_slot="Principal",
        item_level=10,
        rarity="Comum",
        payload={
            "slot": "Principal",
            "enhancement": 10,
            "core": {"ATQ": "10"},
            "secondaries": [],
            "rune": {
                "family": "Brasa", "rarity": "Rara", "grade": 1,
                "potency": "0.35%", "bound": False,
            },
            "enchantment": {
                "family": "Fio Cinéreo", "rarity": "Raro", "grade": 1,
                "potency": "0.10%", "bound": False,
            },
        },
    )
    bonus = EquipmentConfigurationSnapshot(1, (item,)).contribution()
    resolved = resolve_combat_stats("sentinela", 10, "remanescente", bonus)
    expected = (class_stats("sentinela", 10).attack + D("12.5"))
    expected *= D("1.0035")
    expected *= D("1.001")
    expected *= D("1.015")
    assert resolved.attack == expected
    incorrect_flat_rune = (
        (class_stats("sentinela", 10).attack + D("12.5")) * D("1.015")
        + D("0.35")
    )
    assert resolved.attack != incorrect_flat_rune
