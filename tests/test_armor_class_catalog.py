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
        item = materialize_equipment(f"seed{i}", "Comum", 10, region_key="confins", forced_slot="Torso")
        cls = armor_class_of(slot=item["slot"], template_id=item.get("template_id"), item_name=item["item_name"])
        assert cls in ARMOR_CLASSES
