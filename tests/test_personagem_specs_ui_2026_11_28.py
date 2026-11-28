"""Especificações visuais de 2026-11-28: Personagem, Inventário, Armazém e skin.

Personagem, Artes e Equipamentos também são cobertos em ``test_equipment_telegram_ui``
e ``test_consolidated_specs_ui``; aqui ficam as partes novas sem cobertura anterior.
"""

from uuid import uuid4

from asterion.application.inventory import InventoryEntry, InventoryView
from asterion.application.warehouse import WarehouseView
from asterion.bot.inventory_ui import render_inventory, render_material_detail
from asterion.bot.warehouse_ui import (
    parse_quantity_callback,
    render_warehouse,
    render_warehouse_quantity,
    render_warehouse_store_menu,
)

SKIN = "character"


def _labels(screen):
    return [[button.text for button in row] for row in screen.keyboard.inline_keyboard]


def _callbacks(screen):
    return [button.callback_data for row in screen.keyboard.inline_keyboard for button in row]


def _couro(quantity=1):
    return InventoryEntry(
        kind="material",
        key="material.tdo.couro_escoriado",
        title="Couro Escoriado",
        quantity=quantity,
        bound=True,
        payload={"warehouse_source_id": "0f0f0f0f-0000-0000-0000-000000000002"},
    )


def test_inventory_shows_quantity_for_equipment_too():
    adaga = InventoryEntry(
        kind="equipment", key=str(uuid4()), title="Adaga", rarity="Comum", slot="main_hand",
        payload={"attack": 6},
    )  # fmt: skip
    view = InventoryView(
        "inventory_category", uuid4(), 4, category="all", entries=(adaga, _couro())
    )
    screen = render_inventory(view)
    assert "#1 ⚪️ <b>Adaga</b> · <code>×1</code>" in screen.text
    assert "#2 🧱 <b>Couro Escoriado</b> · <code>×1</code>\n✨ <code>Grau I</code>" in screen.text
    assert "🗳️ <b>Espaço</b> · <code>4/60</code>" in screen.text
    assert screen.image_key == SKIN


def test_couro_escoriado_detail_follows_the_spec():
    screen = render_material_detail(_couro())
    assert screen.text == (
        "🐾 <b>Couro Escoriado</b>\n\n"
        "<i>Um couro áspero e marcado por cortes, arrancado de criaturas que percorrem as "
        "terras cobertas pela fuligem. Apesar da aparência ressecada, ainda conserva "
        "resistência suficiente para ser aproveitado em trabalhos de couro.</i>\n\n"
        "✨ <b>Grau</b> · <code>I</code>\n📦 <b>Quantidade</b> · <code>1</code>\n\n"
        "🧱 <b>Tipo</b> · <code>Material</code>\n🔗 <b>Vínculo</b> · <code>Vinculado</code>"
    )
    assert _labels(screen) == [["📥 Guardar", "🗑️ Descartar"], ["↩️ Retornar"]]
    assert all(len(data.encode()) <= 64 for data in _callbacks(screen))
    assert screen.image_key == SKIN


def test_material_detail_quantity_follows_the_stack():
    assert "📦 <b>Quantidade</b> · <code>7</code>" in render_material_detail(_couro(7)).text


def test_pending_empty_state_uses_the_explanatory_text():
    view = InventoryView("pending", uuid4(), 0)
    screen = render_inventory(view)
    assert screen.text == (
        "<b>📦 Entregas Pendentes</b>\n\n"
        "<i>Itens recebidos durante a jornada permanecem aqui quando não podem ser enviados "
        "diretamente para o inventário.</i>\n\n"
        "🗳️ <b>Espaço</b> · <code>0/20</code>\n📄 <b>Página</b> · <code>1/1</code>\n\n"
        "<i>Não há entregas aguardando recebimento. Quando um item não puder ser enviado "
        "diretamente ao inventário, ele aparecerá aqui.</i>"
    )
    assert "Nenhuma Entrega Pendente" not in screen.text
    assert _labels(screen) == [["↩️ Retornar"]]
    assert screen.image_key == SKIN


def _warehouse(**overrides):
    data = dict(
        kind="warehouse_root", character_id=uuid4(), accessible=True, location=None,
        inventory_used=4, warehouse_used=0,
    )  # fmt: skip
    data.update(overrides)
    return WarehouseView(**data)


def test_warehouse_empty_state_uses_the_explanatory_text():
    screen = render_warehouse(_warehouse())
    assert screen.text == (
        "<b>🗄️ Armazém</b>\n\n"
        "<i>Itens armazenados permanecem guardados separadamente do inventário e podem ser "
        "retirados quando necessário.</i>\n\n"
        "🗳️ <b>Espaço</b> · <code>0/100</code>\n📄 <b>Página</b> · <code>1/1</code>\n\n"
        "<i>O Armazém ainda não possui itens armazenados. Os itens depositados aqui ficarão "
        "disponíveis para retirada quando necessário.</i>"
    )
    assert "O Armazém está vazio." not in screen.text
    # Decisão do autor 2026-11-28: o botão Guardar continua no Armazém.
    assert _labels(screen) == [["📥 Guardar"], ["↩️ Retornar"]]


def test_warehouse_shows_skin_only_when_opened_from_character():
    assert render_warehouse(_warehouse()).image_key == SKIN
    assert render_warehouse(_warehouse(), back_to_refuge=True).image_key != SKIN
    assert render_warehouse_store_menu().image_key == SKIN
    assert render_warehouse_store_menu(back_to_refuge=True).image_key != SKIN


def _store_preview(**overrides):
    operation = uuid4()
    return operation, _warehouse(
        kind="warehouse_operation", operation_id=operation, direction="deposit",
        item_kind="material", title="Couro Escoriado", quantity=1, status="preview",
        **overrides,
    )  # fmt: skip


def test_store_confirmation_follows_the_spec():
    operation, view = _store_preview()
    screen = render_warehouse(view, from_item=True)
    assert screen.text == (
        "<b>🗄️ Confirmar Armazenamento</b>\n\n"
        "<i>O item será retirado do inventário e transferido para o Armazém, onde permanecerá "
        "guardado separadamente até que você decida retirá-lo novamente.</i>\n\n"
        "🎒 <b>Item</b> · <code>Couro Escoriado</code>\n📦 <b>Quantidade</b> · <code>1</code>\n\n"
        "💼 <b>Inventário</b> · <code>4/60</code>\n🗄️ <b>Armazém</b> · <code>0/100</code>"
    )
    assert _labels(screen) == [["✅ Confirmar"], ["❌ Cancelar"], ["↩️ Retornar"]]
    # Pelo detalhe do item, Cancelar e Retornar cancelam a prévia e voltam ao detalhe.
    assert _callbacks(screen) == [
        f"warehouse:confirm:{operation.hex}",
        f"warehouse:cancel:{operation.hex}",
        f"warehouse:cancel:{operation.hex}",
    ]
    assert screen.image_key == SKIN


def test_store_confirmation_from_the_warehouse_returns_to_the_warehouse():
    operation, view = _store_preview()
    assert _callbacks(render_warehouse(view))[-1] == "warehouse:root"


def test_withdraw_confirmation_keeps_its_previous_layout():
    _, view = _store_preview()
    from dataclasses import replace

    screen = render_warehouse(replace(view, direction="withdraw"))
    assert "Confirmar Armazenamento" not in screen.text


def test_quantity_screen_keeps_the_item_detail_origin_in_its_callbacks():
    source = uuid4()
    view = _warehouse(
        kind="warehouse_quantity", direction="deposit", item_kind="material",
        title="Couro Escoriado", quantity=5, source_id=source,
    )  # fmt: skip
    screen = render_warehouse_quantity(view, 2, from_item=True)
    callbacks = [data for data in _callbacks(screen) if data.startswith("warehouse:go:")]
    assert callbacks == [f"warehouse:go:d:m:{source.hex}:2:i"]
    assert parse_quantity_callback(callbacks[0]) == ("deposit", "material", source, 2)
    assert all(len(data.encode()) <= 64 for data in _callbacks(screen))
    assert screen.image_key == SKIN
