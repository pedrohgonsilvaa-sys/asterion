from uuid import UUID

import pytest

from asterion.domain.equipment import (
    EquipmentSlot,
    assign_equipment_instance_id,
    assignment_for_item_slot,
    parse_equipment_slot,
)


@pytest.mark.parametrize(
    ("item_slot", "expected_slot", "two_handed"),
    [
        ("Principal", EquipmentSlot.PRINCIPAL, False),
        ("Arma Principal", EquipmentSlot.PRINCIPAL, False),
        ("2H", EquipmentSlot.PRINCIPAL, True),
        ("Secundária", EquipmentSlot.SECUNDARIA, False),
        ("Cabeça", EquipmentSlot.CABECA, False),
        ("Torso", EquipmentSlot.TORSO, False),
        ("Mãos", EquipmentSlot.MAOS, False),
        ("Pés", EquipmentSlot.PES, False),
        ("Acessório", EquipmentSlot.ACESSORIO, False),
        ("Artefato", EquipmentSlot.ARTEFATO, False),
    ],
)
def test_existing_item_slot_names_map_to_eight_canonical_slots(
    item_slot, expected_slot, two_handed
):
    assignment = assignment_for_item_slot(item_slot)
    assert assignment is not None
    assert assignment.slot == expected_slot
    assert assignment.two_handed is two_handed


def test_two_handed_item_uses_principal_and_is_not_a_ninth_slot():
    assert parse_equipment_slot("2H") is None
    assert parse_equipment_slot("Arma Principal") == EquipmentSlot.PRINCIPAL
    assert len(EquipmentSlot) == 8


def test_equipment_item_identity_survives_payload_materialization_round_trip():
    item_id, payload = assign_equipment_instance_id({"item_name": "Lâmina"})
    recovered_id, recovered_payload = assign_equipment_instance_id(payload)
    assert isinstance(item_id, UUID)
    assert recovered_id == item_id
    assert recovered_payload == payload


def test_equipment_payload_rejects_mismatched_explicit_identity():
    with pytest.raises(ValueError, match="do not match"):
        assign_equipment_instance_id(
            {"item_instance_id": "00000000-0000-0000-0000-000000000001"},
            instance_id=UUID("00000000-0000-0000-0000-000000000002"),
        )
