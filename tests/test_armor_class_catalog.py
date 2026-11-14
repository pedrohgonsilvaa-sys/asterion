from asterion.domain.regional_equipment import (
    ARMOR_CLASSES,
    LEGACY_ARMOR_CLASS_BY_NAME,
    REGIONAL_ARMOR_TEMPLATES,
    armor_class_of,
)
from asterion.domain.road import EQUIPMENT_CATALOG, materialize_equipment


def test_every_regional_armor_has_a_class_four_per_slot_group():
    assert len(REGIONAL_ARMOR_TEMPLATES) == 96
    for region in {t.region_key for t in REGIONAL_ARMOR_TEMPLATES}:
        pieces = [t for t in REGIONAL_ARMOR_TEMPLATES if t.region_key == region]
        for armor_class in ARMOR_CLASSES:
            group = [t for t in pieces if t.armor_class == armor_class]
            assert [t.slot for t in group] == ["Cabeça", "Torso", "Mãos", "Pés"]


def test_legacy_armor_classes_follow_spec_table():
    legacy = {n for n, slot, _ in EQUIPMENT_CATALOG if slot in {"Cabeça", "Torso", "Mãos", "Pés"}}
    assert legacy == set(LEGACY_ARMOR_CLASS_BY_NAME)
    assert [n for n, c in LEGACY_ARMOR_CLASS_BY_NAME.items() if c == "veste"] == [
        "Capuz das Cinzas", "Veste do Caminhante", "Luvas de Fuligem", "Botas da Estrada"
    ]
    assert armor_class_of(slot="Pés", item_name="Passos de Fuligem") == "leve"


def test_non_armor_and_unknown_have_no_class():
    assert armor_class_of(slot="Acessório", item_name="Selo Enegrecido") is None
    assert armor_class_of(slot="Principal", item_name="x") is None
    assert armor_class_of(slot="Torso", item_name="Desconhecida") is None


def test_regional_drop_resolves_class_by_template_id():
    for i in range(200):
        item = materialize_equipment(
            f"seed{i}", "Comum", 10, region_key="confins", forced_slot="Torso"
        )
        cls = armor_class_of(
            slot=item["slot"], template_id=item.get("template_id"), item_name=item["item_name"]
        )
        assert cls in ARMOR_CLASSES


def _snapshot(slot, item_name, *, template_id=None, enhancement=0, rarity="Comum"):
    from asterion.domain.equipment import assignment_for_item_slot
    from asterion.domain.equipment_stats import item_snapshot_from_persisted

    payload = {
        "item_name": item_name,
        "slot": slot,
        "enhancement": enhancement,
        "core": {"HP": "10"},
        "secondaries": [],
    }
    if template_id:
        payload["template_id"] = template_id
    return item_snapshot_from_persisted(
        item_instance_id="i1",
        equipped_slot=assignment_for_item_slot(slot).slot.value,
        item_slot=slot,
        item_level=10,
        rarity=rarity,
        payload=payload,
    )


def test_armor_class_adds_evasion_and_block_per_piece():
    from decimal import Decimal as D

    from asterion.domain.equipment_stats import equipment_stat_contribution

    expected = {
        "Capuz das Cinzas": ("1.00", "0"),
        "Elmo de Fuligem": ("0.75", "0.25"),
    }
    for name, (ev, bl) in expected.items():
        c = equipment_stat_contribution(_snapshot("Cabeça", name))
        assert (c.evasion, c.block) == (D(ev), D(bl))
    for t in REGIONAL_ARMOR_TEMPLATES:
        if t.region_key == "tdo" and t.slot == "Cabeça" and t.armor_class in {"media", "pesada"}:
            snap = _snapshot("Cabeça", t.display_name, template_id=t.template_id)
            c = equipment_stat_contribution(snap)
            want = {"media": ("0.50", "0.50"), "pesada": ("0", "1.00")}[t.armor_class]
            assert (c.evasion, c.block) == (D(want[0]), D(want[1]))


def test_armor_class_is_not_scaled_by_enhancement_and_core_is_untouched():
    from asterion.domain.equipment_stats import equipment_stat_contribution

    plain = equipment_stat_contribution(_snapshot("Cabeça", "Capuz das Cinzas"))
    plus10 = equipment_stat_contribution(_snapshot("Cabeça", "Capuz das Cinzas", enhancement=10))
    assert plain.evasion == plus10.evasion
    assert plain.hp == 10


def test_accessory_has_no_armor_class_bonus_and_snapshot_roundtrips():
    from asterion.domain.equipment_stats import (
        EquipmentConfigurationSnapshot,
        equipment_configuration_from_data,
        equipment_stat_contribution,
    )

    acc = _snapshot("Acessório", "Selo Enegrecido")
    assert acc.armor_class is None
    assert equipment_stat_contribution(acc).evasion == 0
    head = _snapshot("Cabeça", "Elmo de Fuligem")
    data = EquipmentConfigurationSnapshot(1, (head,)).to_data("v")
    again = equipment_configuration_from_data(data)
    assert again.items[0].armor_class == "leve"
    assert again.contribution().block == equipment_stat_contribution(head).block
