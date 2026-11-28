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




# ---------------------------------------------------------------------------
# UI aprovada: Inventário, Entregas Pendentes e Armazém.
# ---------------------------------------------------------------------------
import pytest  # noqa: E402

from asterion.bot.ui_format import numeric_row_sizes  # noqa: E402


def _rows(screen):
    return [[button.text for button in row] for row in screen.keyboard.inline_keyboard]


def _numbered(screen):
    return [row for row in _rows(screen) if row and row[0].endswith("️⃣")]


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, [1]), (2, [2]), (3, [3]), (4, [2, 2]), (5, [3, 2]), (6, [3, 3]), (7, [3, 2, 2])],
)
def test_numeric_buttons_adapt_to_the_item_count(count, expected):
    assert numeric_row_sizes(count) == expected


def _materials(count):
    return tuple(
        InventoryEntry(
            kind="material",
            key="material.tdo.ferro_de_fuligem",
            title="Ferro de Fuligem",
            quantity=7,
            payload={"warehouse_source_id": str(uuid4())},
        )
        for _ in range(count)
    )


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (1, [["1️⃣"]]),
        (2, [["1️⃣", "2️⃣"]]),
        (3, [["1️⃣", "2️⃣", "3️⃣"]]),
        (4, [["1️⃣", "2️⃣"], ["3️⃣", "4️⃣"]]),
        (5, [["1️⃣", "2️⃣", "3️⃣"], ["4️⃣", "5️⃣"]]),
        (6, [["1️⃣", "2️⃣", "3️⃣"], ["4️⃣", "5️⃣", "6️⃣"]]),
    ],
)
def test_inventory_numeric_rows_follow_the_approved_distribution(count, expected):
    screen = render_inventory(_category_view("all", _materials(count)))
    assert _numbered(screen) == expected
    assert screen.text.count("#") == count


def test_inventory_opens_on_the_listing_with_filters_and_approved_layout():
    entries = (
        InventoryEntry(
            kind="consumable", key="consumable.cura.i", title="Poção de Vida", quantity=4,
            grade=1, payload={"family": "healing"},
        ),
        InventoryEntry(
            kind="material", key="material.tdo.ferro_de_fuligem", title="Ferro de Fuligem",
            quantity=7, payload={"warehouse_source_id": str(uuid4())},
        ),
        InventoryEntry(
            kind="rune", key=str(uuid4()), title="Runa Cinérea", quantity=2, rarity="Comum",
            grade=1, payload={"warehouse_source_id": str(uuid4())},
        ),
    )
    view = InventoryView(
        "inventory_category", uuid4(), used_slots=8, category="all", entries=entries
    )
    screen = render_inventory(view)
    assert screen.text.startswith("<b>💼 Inventário</b>\n\n<i>Cada item encontrado")
    assert "🔎 <b>Filtro</b> · <code>Todos</code>" in screen.text
    assert "🗳️ <b>Espaço</b> · <code>8/60</code>" in screen.text
    assert "📄 <b>Página</b> · <code>1/1</code>" in screen.text
    assert "#2 🧱 <b>Ferro de Fuligem</b> · <code>×7</code>\n✨ <code>Grau I</code>" in screen.text
    assert "#3 🔷 <b>Runa Cinérea</b> · <code>×2</code>\n⚪️ <code>Grau I</code>" in screen.text
    assert "4 un." not in screen.text and "[×" not in screen.text
    assert _rows(screen)[1:] == [
        ["📋 Todos"],
        ["🛡️ Equipamentos", "🧪 Consumíveis"],
        ["🧱 Materiais", "🔷 Runas"],
        ["📦 Entregas", "🗄️ Armazém"],
        ["↩️ Retornar"],
    ]
    callbacks = _callbacks(screen)
    for expected in (
        "inventory:category:all",
        "inventory:category:equipment",
        "inventory:category:consumables",
        "inventory:category:materials",
        "inventory:category:runes",
        "pending:root",
        "warehouse:root",
    ):
        assert expected in callbacks
    assert callbacks[-1] == "character:root"


def test_inventory_consumable_line_shows_catalog_effect_and_stable_ids():
    entries = tuple(
        consumable_inventory_entry(item_id, index)
        for index, item_id in enumerate(list(CONSUMABLE_CATALOG)[:6], start=1)
    )
    screen = render_inventory(_category_view("consumables", entries))
    assert "#1 🧪 <b>Poção de Cura</b> · <code>×1</code>" in screen.text
    assert "❤️ <code>Cura 22% HP</code>" in screen.text
    callbacks = _callbacks(screen)
    for entry in entries:
        assert f"inventory:consumable:{entry.key}" in callbacks
    assert all(len(value.encode("utf-8")) <= 64 for value in callbacks)


def test_unknown_legacy_consumable_does_not_break_inventory_renderer():
    screen = render_inventory(
        _category_view(
            "consumables",
            (InventoryEntry(kind="consumable", key="legacy.unknown", title="legacy.unknown", quantity=2),),  # noqa: E501
        )
    )
    assert "#1 🧪 <b>legacy.unknown</b> · <code>×2</code>" in screen.text


def test_inventory_paginates_six_items_per_page_with_nav_above_return():
    view = _category_view("all", _materials(14))
    first = render_inventory(view)
    assert "📄 <b>Página</b> · <code>1/3</code>" in first.text
    assert _rows(first)[-2:] == [["▶️ Próxima"], ["↩️ Retornar"]]
    middle = render_inventory(view, 1)
    assert _rows(middle)[-2:] == [["◀️ Anterior", "▶️ Próxima"], ["↩️ Retornar"]]
    assert "inventory:category:all:0" in _callbacks(middle)
    assert "inventory:category:all:2" in _callbacks(middle)
    last = render_inventory(view, 2)
    assert _rows(last)[-2:] == [["◀️ Anterior"], ["↩️ Retornar"]]
    assert len(_numbered(last)[0]) == 2  # 14 = 6 + 6 + 2
    assert render_inventory(view, 99).text == last.text
    assert all(len(render_inventory(view, page).text) <= 4096 for page in range(3))


def test_inventory_numeric_buttons_open_each_item_detail():
    item = uuid4()
    entries = (
        InventoryEntry(kind="equipment", key=str(item), title="Adaga", rarity="Comum", slot="main_hand"),  # noqa: E501
        *_materials(1),
        InventoryEntry(
            kind="rune", key="r", title="Runa Cinérea", quantity=1,
            payload={"warehouse_source_id": str(uuid4())},
        ),
    )
    callbacks = _callbacks(render_inventory(_category_view("all", entries)))
    assert callbacks[0] == f"eq:v:{item.hex}"
    assert callbacks[1].startswith("inventory:material:")
    assert callbacks[2].startswith("inventory:rune:")


def test_equipment_shows_name_without_zero_enhancement_and_with_real_enhancement():
    plain = InventoryEntry(
        kind="equipment", key=str(uuid4()), title="Adaga", rarity="Comum", slot="main_hand",
        payload={"enhancement": 0},
    )
    refined = InventoryEntry(
        kind="equipment", key=str(uuid4()), title="Espada Curta", rarity="Raro", slot="main_hand",
        payload={"enhancement": 1},
    )
    screen = render_inventory(_category_view("equipment", (plain, refined)))
    assert "#1 ⚪️ <b>Adaga</b>" in screen.text and "+0" not in screen.text
    assert "#2 🔵 <b>Espada Curta +1</b>" in screen.text


def _pending_view(entries, pending_count=None, blocked=0):
    return InventoryView(
        "pending_root", uuid4(), used_slots=60, entries=entries,
        pending_count=len(entries) if pending_count is None else pending_count,
        blocked_delivery_count=blocked,
    )


def test_pending_deliveries_use_the_approved_layout_and_claim_buttons():
    entries = (
        InventoryEntry(kind="material", key="pending-1", title="Ferro de Fuligem", quantity=7,
                       payload={"material_id": "material.tdo.ferro_de_fuligem"}),
        InventoryEntry(kind="consumable", key="pending-2", title="Poção de Cura", quantity=4,
                       payload={"consumable_id": next(iter(CONSUMABLE_CATALOG))}),
    )
    screen = render_inventory(_pending_view(entries))
    assert screen.text.startswith("<b>📦 Entregas Pendentes</b>\n\n<i>Itens recebidos")
    assert "🗳️ <b>Espaço</b> · <code>2/20</code>" in screen.text
    assert "📄 <b>Página</b> · <code>1/1</code>" in screen.text
    assert "#1 🧱 <b>Ferro de Fuligem</b> · <code>×7</code>\n✨ <code>Grau I</code>" in screen.text
    assert "Origem" not in screen.text and "⚠️" not in screen.text
    assert _rows(screen) == [["1️⃣", "2️⃣"], ["↩️ Retornar"]]
    assert _callbacks(screen) == ["pending:claim:pending1", "pending:claim:pending2", "inventory:root"]  # noqa: E501


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6])
def test_pending_numeric_rows_follow_the_distribution(count):
    entries = tuple(
        InventoryEntry(kind="material", key=f"pending-{n}", title="Ferro", quantity=1)
        for n in range(count)
    )
    sizes = [len(row) for row in _numbered(render_inventory(_pending_view(entries)))]
    assert sizes == numeric_row_sizes(count)


def test_pending_paginates_and_keeps_capacity():
    entries = tuple(
        InventoryEntry(kind="material", key=f"pending-{n}", title="Ferro", quantity=1)
        for n in range(20)
    )
    view = _pending_view(entries)
    first = render_inventory(view)
    assert "<code>20/20</code>" in first.text
    assert "📄 <b>Página</b> · <code>1/4</code>" in first.text
    assert "pending:root:1" in _callbacks(first)
    assert _rows(first)[-2:] == [["▶️ Próxima"], ["↩️ Retornar"]]


def test_blocked_deliveries_stay_visible_and_only_expose_retry():
    entries = (
        InventoryEntry(
            kind="blocked_delivery", key="blocked-1", title="Guarda da Câmara", rarity="Épico",
            slot="main_hand", item_level=30, bound=True,
            payload={"delivery_kind": "equipment", "enhancement": 2, "origin": "mission:P18:choice"},  # noqa: E501
        ),
    )
    screen = render_inventory(_pending_view(entries, pending_count=20, blocked=1))
    assert "⚠️ <b>Entregas aguardando espaço</b> · <code>1</code>" in screen.text
    assert "#1 ⚠️ 🟣 <b>Guarda da Câmara +2</b>" in screen.text
    assert "mission:P18:choice" not in screen.text
    assert _callbacks(screen) == ["pending:retry", "inventory:root"]


def _warehouse_view(entries, kind="warehouse_root", **extra):
    from asterion.application.warehouse import WarehouseView

    return WarehouseView(kind, uuid4(), True, "Refúgio do Ocaso", 8, len(entries), tuple(entries), **extra)  # noqa: E501


def test_warehouse_uses_the_approved_layout_and_withdraw_buttons():
    from asterion.application.warehouse import WarehouseEntry
    from asterion.bot.warehouse_ui import render_warehouse

    entries = [
        WarehouseEntry(id=str(uuid4()), kind="material", title="Ferro de Fuligem", quantity=7,
                       payload={"material_id": "material.tdo.ferro_de_fuligem"}),
        WarehouseEntry(id=str(uuid4()), kind="rune", title="Runa Cinérea", quantity=2,
                       rarity="Comum", grade=1),
    ]
    screen = render_warehouse(_warehouse_view(entries))
    assert screen.text.startswith("<b>🗄️ Armazém</b>\n\n<i>Itens armazenados permanecem")
    assert "🗳️ <b>Espaço</b> · <code>2/100</code>" in screen.text
    assert "📄 <b>Página</b> · <code>1/1</code>" in screen.text
    assert "#1 🧱 <b>Ferro de Fuligem</b> · <code>×7</code>\n✨ <code>Grau I</code>" in screen.text
    assert "#2 🔷 <b>Runa Cinérea</b> · <code>×2</code>\n⚪️ <code>Grau I</code>" in screen.text
    assert "Braseiro" not in screen.text
    callbacks = _callbacks(screen)
    assert callbacks[0].startswith("warehouse:withdraw:material:")
    assert callbacks[1].startswith("warehouse:withdraw:rune:")
    assert "warehouse:store" in callbacks and callbacks[-1] == "inventory:root"


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6])
def test_warehouse_numeric_rows_follow_the_distribution(count):
    from asterion.bot.warehouse_ui import render_warehouse

    screen = render_warehouse(_warehouse_view(_warehouse_entries(count, kind="material", title="Ferro")))  # noqa: E501
    assert [len(row) for row in _numbered(screen)] == numeric_row_sizes(count)


def test_warehouse_paginates_every_item_with_nav_above_return():
    from asterion.bot.warehouse_ui import render_warehouse

    view = _warehouse_view(_warehouse_entries(100))
    withdraw = []
    for page in range(17):
        screen = render_warehouse(view, page)
        assert len(screen.text) <= 4096
        assert f"📄 <b>Página</b> · <code>{page + 1}/17</code>" in screen.text
        withdraw.extend(c for c in _callbacks(screen) if c.startswith("warehouse:withdraw:"))
    assert len(set(withdraw)) == 100
    first, second, last = (render_warehouse(view, page) for page in (0, 1, 16))
    assert "warehouse:page:1" in _callbacks(first)
    assert {"warehouse:page:0", "warehouse:page:2"} <= set(_callbacks(second))
    assert "warehouse:page:17" not in _callbacks(last)
    assert _rows(second)[-2:] == [["◀️ Anterior", "▶️ Próxima"], ["↩️ Retornar"]]
    assert render_warehouse(view, 99).text == last.text


def test_warehouse_sources_keep_deposit_buttons_and_explain_unavailable_items():
    from asterion.bot.warehouse_ui import render_warehouse, render_warehouse_store_menu

    entries = _warehouse_entries(59) + _warehouse_entries(1, eligible=False, reason="EQUIPPED")
    view = _warehouse_view(entries, "warehouse_inventory_sources", item_kind="equipment")
    first, last = render_warehouse(view), render_warehouse(view, 9)
    assert "warehouse:inventory:equipment:1" in _callbacks(first)
    assert any(c.startswith("warehouse:deposit:equipment:") for c in _callbacks(first))
    assert "Equipado" in last.text and "EQUIPPED" not in last.text
    assert _callbacks(last)[5] == "warehouse:inventory:equipment"  # item indisponível não deposita
    assert _callbacks(last)[-1] == "warehouse:store"
    menu = render_warehouse_store_menu()
    assert {"warehouse:inventory:equipment", "warehouse:inventory:consumable",
            "warehouse:inventory:material", "warehouse:inventory:rune"} <= set(_callbacks(menu))
