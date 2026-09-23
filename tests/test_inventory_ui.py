from uuid import uuid4

from asterion.application.inventory import InventoryEntry, InventoryView
from asterion.bot.inventory_ui import render_inventory


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
    assert callbacks == ["inventory:root", "menu:back"]
    assert "menu:noop" not in callbacks
