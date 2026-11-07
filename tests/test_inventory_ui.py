from uuid import uuid4

from asterion.application.inventory import (
    InventoryEntry,
    InventoryView,
    consumable_inventory_entry,
)
from asterion.bot.inventory_ui import render_inventory
from asterion.domain.consumables import CONSUMABLE_CATALOG, grade_label


def _callbacks(screen):
    return [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]


def test_inventory_root_uses_official_categories_and_real_callbacks():
    screen = render_inventory(
        InventoryView(
            "inventory_root",
            uuid4(),
            used_slots=12,
            equipment_slots=3,
            consumable_slots=2,
            material_slots=5,
            rune_slots=2,
        )
    )
    assert "🎒 Inventário" in screen.text
    assert "📦 Espaço · 12/60" in screen.text
    assert "1 🛡️ Equipamentos · 3" in screen.text
    assert "2 🧪 Consumíveis · 2" in screen.text
    assert "3 🧱 Materiais · 5" in screen.text
    assert "4 🔷 Runas · 2" in screen.text
    callbacks = _callbacks(screen)
    assert "inventory:category:equipment" in callbacks
    assert "inventory:category:consumables" in callbacks
    assert "inventory:category:materials" in callbacks
    assert "inventory:category:runes" in callbacks
    assert callbacks[-1] == "character:root"
    assert all(callback != "menu:noop" for callback in callbacks)


def test_inventory_category_renders_source_supported_item_metadata():
    screen = render_inventory(
        InventoryView(
            "inventory_category",
            uuid4(),
            used_slots=2,
            category="materials",
            entries=(
                InventoryEntry(
                    kind="material",
                    key="material.tdo.ferro_de_fuligem",
                    title="Ferro de Fuligem",
                    quantity=23,
                    bound=True,
                ),
            ),
        )
    )
    assert "🧱 Materiais" in screen.text
    assert "1 ⛏️ Ferro de Fuligem · 23" in screen.text
    assert "Metal · Grau I" in screen.text
    assert "🔗 Vinculado" in screen.text
    assert _callbacks(screen) == ["inventory:root"]


def test_pending_root_is_real_read_model_without_placeholder_actions():
    screen = render_inventory(
        InventoryView(
            "pending_root",
            uuid4(),
            used_slots=60,
            entries=(
                InventoryEntry(
                    kind="material",
                    key="pending-1",
                    title="Couro Escoriado",
                    quantity=3,
                ),
            ),
            pending_count=20,
            blocked_delivery_count=1,
        )
    )
    assert "📦 Entregas Pendentes" in screen.text
    assert "📦 Espaço · 20/20" in screen.text
    assert "⚠️ Entregas aguardando espaço · 1" in screen.text
    assert "Couro Escoriado · 3" in screen.text
    callbacks = _callbacks(screen)
    assert callbacks == ["pending:claim:pending1", "pending:retry", "inventory:root"]
    assert "menu:noop" not in callbacks


def test_warehouse_root_requires_safe_access_and_shows_canonical_capacities():
    from asterion.application.warehouse import WarehouseView
    from asterion.bot.warehouse_ui import render_warehouse

    unsafe = render_warehouse(
        WarehouseView("warehouse_root", uuid4(), False, None, 60, 0)
    )
    assert "Braseiro permanente descoberto" in unsafe.text
    assert _callbacks(unsafe) == ["inventory:root"]

    safe = render_warehouse(
        WarehouseView("warehouse_root", uuid4(), True, "Refúgio do Ocaso", 60, 100)
    )
    assert "Inventário · 60/60" in safe.text
    assert "Armazém · 100/100" in safe.text
    assert "warehouse:inventory:equipment" in _callbacks(safe)
    assert "warehouse:inventory:material" in _callbacks(safe)


def test_blocked_delivery_shows_reward_identity_and_only_exposes_retry():
    screen = render_inventory(
        InventoryView(
            "pending_root",
            uuid4(),
            used_slots=60,
            entries=(
                InventoryEntry(
                    kind="blocked_delivery",
                    key="blocked-1",
                    title="Guarda da Câmara",
                    quantity=1,
                    rarity="Épico",
                    slot="Torso",
                    item_level=30,
                    bound=True,
                    payload={
                        "delivery_kind": "equipment",
                        "origin": "mission:P18:choice",
                        "enhancement": 2,
                        "favorite": True,
                    },
                ),
            ),
            pending_count=20,
            blocked_delivery_count=1,
        )
    )
    assert "Guarda da Câmara" in screen.text
    assert "Épico" in screen.text
    assert "Nv.30" in screen.text
    assert "Vinculado" in screen.text
    assert "Favorito" in screen.text
    assert "Origem · mission:P18:choice" in screen.text
    assert _callbacks(screen) == ["pending:retry", "inventory:root"]


def test_consumable_inventory_is_catalog_driven_and_callbacks_keep_stable_ids():
    entries = tuple(
        consumable_inventory_entry(item_id, index)
        for index, item_id in enumerate(CONSUMABLE_CATALOG, start=1)
    )
    screen = render_inventory(
        InventoryView(
            "inventory_category",
            uuid4(),
            used_slots=len(entries),
            category="consumables",
            entries=entries,
        )
    )
    assert "1 🧪 Poção de Cura · 1" in screen.text
    assert "Consumível · Grau I" in screen.text
    assert "Preparado de Proteção Enredada · 9" in screen.text
    assert "Consumível · Grau II" in screen.text
    assert "Consumível · Proteção" not in screen.text
    assert not any(
        button.text.startswith("Usar")
        for row in screen.keyboard.inline_keyboard
        for button in row
    )
    callbacks = _callbacks(screen)
    for item_id in CONSUMABLE_CATALOG:
        assert f"inventory:consumable:{item_id}" in callbacks
    assert all(len(value.encode("utf-8")) <= 64 for value in callbacks)


def test_protection_detail_matches_player_facing_source_without_floor():
    item_id = "consumable.protection.vde.ii"
    screen = render_inventory(
        InventoryView(
            "inventory_consumable_detail",
            uuid4(),
            used_slots=1,
            entries=(consumable_inventory_entry(item_id, 4),),
        )
    )
    assert "🧪 Preparado de Proteção Enredada · Grau II" in screen.text
    assert "Consumível · Proteção" in screen.text
    assert "🎒 Quantidade · 4" in screen.text
    assert "🔰 Barreira · 12% do HP Máximo" in screen.text
    assert "⏳ Duração · 2T" in screen.text
    assert "🎯 Alvo · Próprio" in screen.text
    assert "⚔️ Uso · Somente em Combate PvE" in screen.text
    assert "floor(" not in screen.text
    assert "Usar" not in [button.text for row in screen.keyboard.inline_keyboard for button in row]
    assert _callbacks(screen) == ["inventory:category:consumables"]


def test_all_seven_families_resolve_names_grades_and_context_in_details():
    expected_family_lines = {
        "healing": "Consumível · Cura",
        "purification": "Consumível · Purificação",
        "antidote": "Consumível · Antídoto",
        "vigor": "Consumível · Vigor",
        "protection": "Consumível · Proteção",
        "dispeller": "Consumível · Dissipador",
        "warding": "Consumível · Resguardo",
    }
    families = set()
    for item_id, item in CONSUMABLE_CATALOG.items():
        families.add(item.family.value)
        screen = render_inventory(
            InventoryView(
                "inventory_consumable_detail",
                uuid4(),
                used_slots=1,
                entries=(consumable_inventory_entry(item_id, 2),),
            )
        )
        assert f"🧪 {item.name} · Grau {grade_label(item.grade)}" in screen.text
        assert expected_family_lines[item.family.value] in screen.text
        assert "🎒 Quantidade · 2" in screen.text
        assert "consumable." not in screen.text
        assert not any(
            button.text == "Usar"
            for row in screen.keyboard.inline_keyboard
            for button in row
        )
    assert families == set(expected_family_lines)


def test_vigor_detail_only_exposes_use_when_backend_marks_it_available():
    entry = consumable_inventory_entry("consumable.vigor.tdo.i", 1)
    usable = render_inventory(
        InventoryView(
            "inventory_consumable_detail",
            uuid4(),
            used_slots=1,
            entries=(entry,),
            vigor=60,
            vigor_usable=True,
        )
    )
    assert "🧪 Poção de Vigor · Grau I" in usable.text
    assert "Consumível · Vigor" in usable.text
    assert "⚡ Vigor · +20" in usable.text
    assert "🌙 Uso · Fora de Combate" in usable.text
    assert [button.text for row in usable.keyboard.inline_keyboard for button in row] == [
        "Usar",
        "← Consumíveis",
    ]
    assert _callbacks(usable)[0] == "consumable:vigor:consumable.vigor.tdo.i"

    unavailable = render_inventory(
        InventoryView(
            "inventory_consumable_detail",
            uuid4(),
            used_slots=1,
            entries=(entry,),
            vigor=90,
            vigor_usable=False,
        )
    )
    assert [button.text for row in unavailable.keyboard.inline_keyboard for button in row] == [
        "← Consumíveis"
    ]


def test_unknown_legacy_consumable_does_not_break_inventory_renderer():
    screen = render_inventory(
        InventoryView(
            "inventory_category",
            uuid4(),
            used_slots=1,
            category="consumables",
            entries=(
                InventoryEntry(
                    kind="consumable",
                    key="legacy.unknown",
                    title="legacy.unknown",
                    quantity=2,
                ),
            ),
        )
    )
    assert "1 🧪 legacy.unknown · 2" in screen.text
    assert "Consumível" in screen.text
    assert _callbacks(screen) == ["inventory:root"]
