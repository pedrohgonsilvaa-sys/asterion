"""Canonical equipment slots and stable item-instance identity helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class EquipmentSlot(StrEnum):
    PRINCIPAL = "Principal"
    SECUNDARIA = "Secundária"
    CABECA = "Cabeça"
    TORSO = "Torso"
    MAOS = "Mãos"
    PES = "Pés"
    ACESSORIO = "Acessório"
    ARTEFATO = "Artefato"


EQUIPMENT_SLOT_VALUES = tuple(slot.value for slot in EquipmentSlot)


@dataclass(frozen=True, slots=True)
class EquipmentAssignment:
    slot: EquipmentSlot
    two_handed: bool = False


_ITEM_SLOT_ASSIGNMENTS = {
    "Principal": EquipmentAssignment(EquipmentSlot.PRINCIPAL),
    "Arma Principal": EquipmentAssignment(EquipmentSlot.PRINCIPAL),
    "main_hand": EquipmentAssignment(EquipmentSlot.PRINCIPAL),
    "Secundária": EquipmentAssignment(EquipmentSlot.SECUNDARIA),
    "Arma Secundária": EquipmentAssignment(EquipmentSlot.SECUNDARIA),
    "off_hand": EquipmentAssignment(EquipmentSlot.SECUNDARIA),
    "Cabeça": EquipmentAssignment(EquipmentSlot.CABECA),
    "head": EquipmentAssignment(EquipmentSlot.CABECA),
    "Torso": EquipmentAssignment(EquipmentSlot.TORSO),
    "torso": EquipmentAssignment(EquipmentSlot.TORSO),
    "Mãos": EquipmentAssignment(EquipmentSlot.MAOS),
    "hands": EquipmentAssignment(EquipmentSlot.MAOS),
    "Pés": EquipmentAssignment(EquipmentSlot.PES),
    "feet": EquipmentAssignment(EquipmentSlot.PES),
    "Acessório": EquipmentAssignment(EquipmentSlot.ACESSORIO),
    "accessory": EquipmentAssignment(EquipmentSlot.ACESSORIO),
    "Artefato": EquipmentAssignment(EquipmentSlot.ARTEFATO),
    "artifact": EquipmentAssignment(EquipmentSlot.ARTEFATO),
    "2H": EquipmentAssignment(EquipmentSlot.PRINCIPAL, two_handed=True),
}


def assignment_for_item_slot(value: str) -> EquipmentAssignment | None:
    """Map a persisted/drop slot label to its canonical equipment assignment."""
    assignment = _ITEM_SLOT_ASSIGNMENTS.get(value)
    if isinstance(assignment, EquipmentSlot):
        return EquipmentAssignment(assignment)
    return assignment


def parse_equipment_slot(value: EquipmentSlot | str) -> EquipmentSlot | None:
    """Parse one of the eight actual slots, accepting current UI labels."""
    if isinstance(value, EquipmentSlot):
        return value
    assignment = assignment_for_item_slot(value)
    if assignment is None or assignment.two_handed:
        return None
    return assignment.slot


def assign_equipment_instance_id(
    payload: Mapping[str, Any], *, instance_id: UUID | None = None
) -> tuple[UUID, dict[str, Any]]:
    """Preserve one item UUID across Inventory, Pending and delivery materialization.

    ``EquipmentItem.id`` is the durable item identity. Before a pending reward has
    an EquipmentItem row, the same UUID is carried in its already-persisted payload
    and becomes that row's primary key when the item reaches Inventory.
    """
    result = dict(payload)
    raw_id = result.get("item_instance_id")
    if raw_id is None:
        resolved_id = instance_id or uuid4()
    else:
        try:
            resolved_id = UUID(str(raw_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError("Invalid persisted equipment item_instance_id") from exc
        if instance_id is not None and resolved_id != instance_id:
            raise ValueError("Equipment payload and row identity do not match")
    result["item_instance_id"] = str(resolved_id)
    return resolved_id, result
