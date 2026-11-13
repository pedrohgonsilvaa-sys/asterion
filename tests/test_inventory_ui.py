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
    assert "🛡️ Equipamentos · 3" in screen.text
    assert "🧪 Consumíveis · 2" in screen.text
    assert "🧱 Materiais · 5" in screen.text
    assert "🔷 Runas · 2" in screen.text
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
    assert "⛏️ Ferro de Fuligem · 23" in screen.text
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
    assert "warehouse:inventory:consumable" in _callbacks(safe)
    assert "warehouse:inventory:rune" in _callbacks(safe)


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
    assert "Origem · Recompensa" in screen.text
    assert "mission:P18:choice" not in screen.text
    assert _callbacks(screen) == ["pending:retry", "inventory:root"]


def test_consumable_inventory_is_catalog_driven_and_callbacks_keep_stable_ids():
    entries = tuple(
        consumable_inventory_entry(item_id, index)
        for index, item_id in enumerate(CONSUMABLE_CATALOG, start=1)
    )
    view = InventoryView(
        "inventory_category",
        uuid4(),
        used_slots=len(entries),
        category="consumables",
        entries=entries,
    )
    screen = render_inventory(view)
    assert "🧪 Poção de Cura · 1" in screen.text
    assert "Consumível · Grau I" in screen.text
    assert "Preparado de Proteção Enredada · 9" in screen.text
    assert "Consumível · Grau II" in screen.text
    assert "Consumível · Proteção" not in screen.text
    assert not any(
        button.text.startswith("Usar")
        for row in screen.keyboard.inline_keyboard
        for button in row
    )
    pages = -(-len(entries) // 15)
    callbacks = [
        callback for page in range(pages) for callback in _callbacks(render_inventory(view, page))
    ]
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
    assert "🧪 legacy.unknown · 2" in screen.text
    assert "Consumível" in screen.text
    assert _callbacks(screen) == ["inventory:root"]


def _warehouse_entries(count, **overrides):
    from asterion.application.warehouse import WarehouseEntry

    values = {
        "kind": "equipment",
        "title": "X" * 120,
        "bound": True,
        "rarity": "Mítico",
        "slot": "main_hand",
        "item_level": 60,
        "source_key": "test:warehouse",
        "payload": {"enhancement": 15, "favorite": True, "locked": True, "runes": [1, 2, 3]},
    }
    values.update(overrides)
    return tuple(WarehouseEntry(id=str(uuid4()), **values) for _ in range(count))


def test_full_warehouse_pages_fit_telegram_and_reach_every_item():
    from asterion.application.warehouse import WarehouseView
    from asterion.bot.warehouse_ui import render_warehouse

    view = WarehouseView(
        "warehouse_root", uuid4(), True, "Refúgio do Ocaso", 60, 100, _warehouse_entries(100)
    )
    withdraw = []
    for page in range(7):
        screen = render_warehouse(view, page)
        assert len(screen.text) <= 4096
        assert f"Página {page + 1}/7" in screen.text
        withdraw.extend(
            callback
            for callback in _callbacks(screen)
            if callback.startswith("warehouse:withdraw:")
        )
    assert len(set(withdraw)) == 100

    first, second, last = (render_warehouse(view, page) for page in (0, 1, 6))
    assert "warehouse:page:1" in _callbacks(first)
    assert "warehouse:page:-1" not in _callbacks(first)
    assert {"warehouse:page:0", "warehouse:page:2"} <= set(_callbacks(second))
    assert "warehouse:page:5" in _callbacks(last)
    assert "warehouse:page:7" not in _callbacks(last)
    assert "16. " in second.text
    assert render_warehouse(view, 99).text == last.text


def test_short_warehouse_list_has_no_page_controls():
    from asterion.application.warehouse import WarehouseView
    from asterion.bot.warehouse_ui import render_warehouse

    screen = render_warehouse(
        WarehouseView(
            "warehouse_root", uuid4(), True, "Refúgio do Ocaso", 1, 15, _warehouse_entries(15)
        )
    )
    assert "Página" not in screen.text
    assert not any(callback.startswith("warehouse:page:") for callback in _callbacks(screen))


def test_warehouse_sources_page_and_explain_unavailable_items_to_the_player():
    from asterion.application.warehouse import WarehouseView
    from asterion.bot.warehouse_ui import render_warehouse

    entries = _warehouse_entries(59) + _warehouse_entries(
        1, eligible=False, reason="EQUIPPED"
    )
    view = WarehouseView(
        "warehouse_inventory_sources",
        uuid4(),
        True,
        "Refúgio do Ocaso",
        60,
        0,
        entries,
        item_kind="equipment",
    )
    first = render_warehouse(view)
    last = render_warehouse(view, 3)
    assert "warehouse:inventory:equipment:1" in _callbacks(first)
    assert "warehouse:inventory:equipment:2" in _callbacks(last)
    assert len(last.text) <= 4096
    assert "Indisponível · Equipado" in last.text
    assert "EQUIPPED" not in last.text


def test_empty_warehouse_source_list_keeps_the_requested_title():
    from asterion.application.warehouse import WarehouseView
    from asterion.bot.warehouse_ui import render_warehouse

    for kind, title in (
        ("equipment", "Equipamentos"),
        ("material", "Materiais"),
        ("consumable", "Consumíveis"),
        ("rune", "Runas"),
    ):
        screen = render_warehouse(
            WarehouseView(
                "warehouse_inventory_sources",
                uuid4(),
                True,
                "Refúgio do Ocaso",
                0,
                0,
                item_kind=kind,
            )
        )
        assert f"🗄️ {title} disponíveis para guardar" in screen.text


def test_warehouse_shows_player_labels_and_official_icons():
    from asterion.application.warehouse import WarehouseView
    from asterion.bot.warehouse_ui import render_warehouse

    root = render_warehouse(
        WarehouseView(
            "warehouse_root",
            uuid4(),
            True,
            "Refúgio do Ocaso",
            1,
            1,
            _warehouse_entries(1, title="Lâmina", rarity="rare", slot="main_hand"),
        )
    )
    assert "🗄️ Armazém" in root.text
    assert "Arma Principal" in root.text and "main_hand" not in root.text
    assert "rare" not in root.text

    deposit = render_warehouse(
        WarehouseView(
            "warehouse_operation",
            uuid4(),
            True,
            "Refúgio do Ocaso",
            1,
            0,
            operation_id=uuid4(),
            direction="deposit",
            item_kind="equipment",
            title="Lâmina",
            quantity=1,
            status="preview",
        )
    )
    assert "🗄️ Confirmar transferência" in deposit.text
    assert "preview" not in deposit.text


def test_protected_equipment_offers_store_but_equipped_equipment_does_not():
    protected, equipped = uuid4(), uuid4()
    screen = render_inventory(
        InventoryView(
            kind="inventory_category",
            character_id=uuid4(),
            used_slots=2,
            category="equipment",
            entries=(
                InventoryEntry(
                    kind="equipment",
                    key=str(protected),
                    title="Lâmina Protegida",
                    payload={"locked": True},
                ),
                InventoryEntry(
                    kind="equipment",
                    key=str(equipped),
                    title="Elmo em uso",
                    equipped_slot="Cabeça",
                ),
            ),
        )
    )
    assert f"warehouse:deposit:equipment:{protected.hex}" in _callbacks(screen)
    assert f"warehouse:deposit:equipment:{equipped.hex}" not in _callbacks(screen)


def _quantity_view(quantity, kind="consumable", direction="withdraw"):
    from asterion.application.warehouse import WarehouseView

    return WarehouseView(
        "warehouse_quantity",
        uuid4(),
        True,
        "Refúgio do Ocaso",
        1,
        1,
        direction=direction,
        item_kind=kind,
        title="Poção",
        quantity=quantity,
        source_id=uuid4(),
    )


def _button_texts(screen):
    return [button.text for row in screen.keyboard.inline_keyboard for button in row]


def test_quantity_screen_offers_only_steps_that_make_sense():
    from asterion.bot.warehouse_ui import render_warehouse_quantity

    small = render_warehouse_quantity(_quantity_view(5), 5)
    assert _button_texts(small) == ["−1", "Continuar", "← Armazém"]

    middle = render_warehouse_quantity(_quantity_view(999, "material", "deposit"), 500)
    assert {"−100", "−10", "−1", "+1", "+10", "+100", "Tudo", "Continuar"} <= set(
        _button_texts(middle)
    )

    lowest = render_warehouse_quantity(_quantity_view(50), 1)
    assert not any(text.startswith("−") for text in _button_texts(lowest))
    assert "+100" not in _button_texts(lowest)


def test_quantity_screen_clamps_stale_amounts():
    from asterion.bot.warehouse_ui import render_warehouse_quantity

    view = _quantity_view(5)
    assert "Quantidade · 5" in render_warehouse_quantity(view, 99).text
    assert "Quantidade · 1" in render_warehouse_quantity(view, 0).text


def test_quantity_callbacks_fit_telegram_and_round_trip():
    from asterion.bot.warehouse_ui import parse_quantity_callback, render_warehouse_quantity

    view = _quantity_view(999_999, "consumable", "withdraw")
    screen = render_warehouse_quantity(view, 500_000)
    for callback in _callbacks(screen):
        assert len(callback.encode()) <= 64
    token = next(item for item in _callbacks(screen) if item.startswith("warehouse:go:"))
    assert parse_quantity_callback(token) == ("withdraw", "consumable", view.source_id, 500_000)


def test_quantity_callback_rejects_malformed_data():
    import pytest

    from asterion.bot.warehouse_ui import parse_quantity_callback

    for data in (
        "warehouse:go:d:m",
        "warehouse:go:x:m:" + "0" * 32 + ":1",
        "warehouse:go:d:equipment:" + "0" * 32 + ":1",
        "warehouse:go:d:m:nao-e-uuid:1",
        "warehouse:go:d:m:" + "0" * 32 + ":muitos",
    ):
        with pytest.raises(ValueError):
            parse_quantity_callback(data)


def test_delivery_origins_use_the_five_official_categories():
    from asterion.application.inventory import origin_label

    expected = {
        "activity:6f1c:equipment": "Loot",
        "explore:6f1c:material:1": "Loot",
        "dungeon:6f1c:7a2b:rune": "Loot",
        "dungeon.tdo.cripta_ocaso.run.6f1c:material:x": "Loot",
        "craft:6f1c:equipment": "Crafting",
        "market:return:6f1c": "Mercado",
        "service:repair:6f1c": "Serviço",
        "mission:P18:choice": "Recompensa",
        "P30:equipment:1": "Recompensa",
        "pvpvd:6f1c:7a2b:m": "Recompensa",
        "bestiary.first_victory:cao": "Recompensa",
        "": "Recompensa",
    }
    assert {key: origin_label(key) for key in expected} == expected


def test_pending_claim_preview_shows_the_category_not_the_internal_key():
    from asterion.application.warehouse import WarehouseView
    from asterion.bot.warehouse_ui import render_warehouse

    screen = render_warehouse(
        WarehouseView(
            "warehouse_operation",
            uuid4(),
            True,
            None,
            1,
            0,
            operation_id=uuid4(),
            direction="claim_pending",
            item_kind="equipment",
            title="Lâmina",
            quantity=1,
            status="preview",
            origin="craft:6f1c:equipment",
        )
    )
    assert "Origem · Crafting" in screen.text
    assert "craft:6f1c" not in screen.text


def _longest_equipment(count):
    return tuple(
        InventoryEntry(
            kind="equipment",
            key=str(uuid4()),
            title="X" * 120,
            rarity="Mítico",
            slot="main_hand",
            item_level=60,
            bound=True,
            payload={"enhancement": 15, "favorite": True, "locked": True, "runes": [1, 2, 3]},
        )
        for _ in range(count)
    )


def _category_view(category, entries):
    return InventoryView(
        kind="inventory_category",
        character_id=uuid4(),
        used_slots=len(entries),
        category=category,
        entries=entries,
    )


def test_full_inventory_pages_fit_telegram_and_reach_every_item():
    view = _category_view("equipment", _longest_equipment(60))
    details = []
    stored = []
    for page in range(4):
        screen = render_inventory(view, page)
        assert len(screen.text) <= 4096
        assert f"Página {page + 1}/4" in screen.text
        details.extend(item for item in _callbacks(screen) if item.startswith("eq:v:"))
        stored.extend(item for item in _callbacks(screen) if item.startswith("warehouse:deposit:"))
    assert len(set(details)) == 60 and len(set(stored)) == 60

    first, second, last = (render_inventory(view, page) for page in (0, 1, 3))
    assert "inventory:category:equipment:1" in _callbacks(first)
    assert {"inventory:category:equipment:0", "inventory:category:equipment:2"} <= set(
        _callbacks(second)
    )
    assert "inventory:category:equipment:4" not in _callbacks(last)
    assert render_inventory(view, 99).text == last.text


def test_inventory_page_numbers_continue_across_pages():
    view = _category_view("equipment", _longest_equipment(16))
    screen = render_inventory(view, 1)
    labels = [button.text for row in screen.keyboard.inline_keyboard for button in row]
    assert any(label.startswith("Guardar ") for label in labels)
    assert not any(label.isdigit() for label in labels)


def test_short_inventory_list_has_no_page_controls():
    screen = render_inventory(_category_view("equipment", _longest_equipment(15)))
    assert "Página" not in screen.text
    assert not any(item.startswith("inventory:category:") for item in _callbacks(screen))


def test_every_inventory_category_pages_its_stack_buttons():
    source = str(uuid4())
    entries = tuple(
        InventoryEntry(
            kind="material",
            key="material.tdo.ferro_de_fuligem",
            title="Ferro",
            quantity=1,
            payload={"warehouse_source_id": source},
        )
        for _ in range(16)
    )
    screen = render_inventory(_category_view("materials", entries), 1)
    assert "Guardar Ferro" in [
        button.text for row in screen.keyboard.inline_keyboard for button in row
    ]
    assert "inventory:category:materials:0" in _callbacks(screen)
