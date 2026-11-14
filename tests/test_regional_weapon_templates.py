from asterion.domain.regional_equipment import (
    REGION_IDS,
    REGIONAL_WEAPON_TEMPLATES,
    regional_weapon_templates,
)
from asterion.domain.road import materialize_equipment
from asterion.domain.weapon_metadata import weapon_definition


def test_catalog_has_120_unique_templates_with_valid_regions():
    ids = [t.template_id for t in REGIONAL_WEAPON_TEMPLATES]
    assert len(ids) == len(set(ids)) == 120
    assert {t.region_id for t in REGIONAL_WEAPON_TEMPLATES} == set(REGION_IDS.values())
    for t in REGIONAL_WEAPON_TEMPLATES:
        assert weapon_definition(t.weapon_type_id) is not None


def test_every_region_covers_19_weapon_types_plus_shield():
    for region in REGION_IDS:
        types = {t.weapon_type_id for t in regional_weapon_templates(region)}
        assert len(types) == 20
        assert "weapon.type.base.escudo" in types


def test_regional_drop_is_deterministic_and_stays_in_region():
    seen = set()
    for i in range(1500):
        a = materialize_equipment(f"seed{i}", "Raro", 25, region_key="nareth")
        assert a == materialize_equipment(f"seed{i}", "Raro", 25, region_key="nareth")
        if "weapon_type_id" in a:
            assert a["template_id"].startswith("equipment.nareth.")
            assert a["region_id"] == REGION_IDS["nareth"]
            definition = weapon_definition(a["weapon_type_id"])
            assert a["slot"] == definition.persisted_item_slot
            seen.add(a["weapon_type_id"])
    assert len(seen) == 20


def test_without_region_nothing_changes():
    payload = materialize_equipment("seed", "Raro", 25)
    assert "template_id" not in payload and "region_id" not in payload


def test_region_cannot_combine_with_forced_weapon():
    import pytest

    with pytest.raises(ValueError):
        materialize_equipment(
            "s", "Raro", 5, region_key="tdo", weapon_type_id="weapon.type.base.espada"
        )


def test_jewelry_pool_has_three_accessories_and_three_artifacts_per_region():
    from asterion.domain.regional_equipment import (
        REGIONAL_JEWEL_TEMPLATES,
        regional_jewel_templates,
    )

    assert len(REGIONAL_JEWEL_TEMPLATES) == 36
    assert len({t.template_id for t in REGIONAL_JEWEL_TEMPLATES}) == 36
    for region in REGION_IDS:
        slots = [t.slot for t in regional_jewel_templates(region)]
        assert slots.count("Acessório") == 3 and slots.count("Artefato") == 3


def test_regional_jewelry_drops_stay_in_region():
    seen = set()
    for i in range(3000):
        item = materialize_equipment(f"j{i}", "Raro", 45, region_key="altos")
        if item["slot"] in {"Acessório", "Artefato"}:
            assert item["template_id"].startswith("equipment.altos.")
            seen.add(item["item_name"])
        assert item["item_name"] != "Relicário de Cinzas"
    assert len(seen) == 6


def test_boss_rarity_table_matches_author_bands():
    from collections import Counter

    from asterion.domain.road import equipment_rarity

    counts = Counter(equipment_rarity(f"b{i}", "boss") for i in range(20000))
    for rarity, expected in (("Comum", 25), ("Raro", 45), ("Épico", 25)):
        assert abs(counts[rarity] / 200 - expected) < 2
    assert 0 < counts["Mítico"] < 200


def test_armor_catalog_is_editorial_only_and_stays_in_region():
    from asterion.domain.regional_equipment import REGIONAL_ARMOR_TEMPLATES

    assert len(REGIONAL_ARMOR_TEMPLATES) == 96
    assert len({t.template_id for t in REGIONAL_ARMOR_TEMPLATES}) == 96
    plain = materialize_equipment("armor-seed", "Raro", 35)
    seen = set()
    for i in range(4000):
        item = materialize_equipment(f"a{i}", "Comum", 35, region_key="varzeas")
        assert "armor_class" not in item
        if item["slot"] in {"Cabeça", "Torso", "Mãos", "Pés"}:
            assert item["template_id"].startswith("equipment.varzeas.armor.")
            seen.add(item["item_name"])
    assert len(seen) == 16
    assert "armor_class" not in plain


def test_regional_core_stats_match_the_unchanged_slot_budget():
    base = materialize_equipment("same", "Comum", 35, forced_slot="Torso")
    regional = materialize_equipment("same", "Comum", 35, forced_slot="Torso", region_key="altos")
    assert regional["core"] == base["core"]
