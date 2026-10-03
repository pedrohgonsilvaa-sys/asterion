from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, EditMessageText

from asterion.application.equipment_view import (
    EquipmentCandidatesView,
    EquipmentDetailView,
    EquipmentItemView,
    EquipmentRootView,
    EquipmentSlotView,
)
from asterion.application.inventory import InventoryEntry, InventoryView
from asterion.application.world import WorldView
from asterion.bot.character_ui import render_character
from asterion.bot.equipment_handlers import equipment_router
from asterion.bot.equipment_ui import (
    SLOT_PRESENTATION,
    render_equipment_candidates,
    render_equipment_detail,
    render_equipment_root,
)
from asterion.bot.inventory_ui import render_inventory
from asterion.bot.world_ui import render_world
from asterion.domain.equipment import EquipmentSlot
from asterion.domain.equipment_stats import EquipmentStatContribution
from tests.test_creation_ui import callback_update


def _buttons(screen):
    return [button for row in screen.keyboard.inline_keyboard for button in row]


def _item(
    *,
    slot=EquipmentSlot.CABECA,
    item_slot=None,
    name="Elmo de Teste",
    rarity="Raro",
    enhancement=0,
    level=3,
    bound=False,
    eligible=True,
    equipped_slot=None,
    contribution=None,
    lore=None,
    reroll_available=False,
    secondaries=(),
):
    return EquipmentItemView(
        item_instance_id=uuid4(),
        name=name,
        rarity=rarity,
        item_slot=item_slot or slot.value,
        slot=slot,
        item_level=level,
        enhancement=enhancement,
        bound=bound,
        contribution=contribution or EquipmentStatContribution(),
        equipped_slot=equipped_slot,
        lore=lore,
        eligible=eligible,
        reroll_available=reroll_available,
        secondaries=secondaries,
    )


def _root(items=None, *, version=4, blocked_secondary=False):
    items = items or {}
    slots = tuple(
        EquipmentSlotView(
            slot,
            items.get(slot),
            blocked_by_two_handed=(slot == EquipmentSlot.SECUNDARIA and blocked_secondary),
        )
        for slot, _, _, _ in SLOT_PRESENTATION
    )
    return EquipmentRootView(uuid4(), 20, version, slots)


def test_character_hub_has_canonical_copy_and_only_live_navigation():
    screen = render_character()
    assert screen.text.startswith("🪪 Personagem\n\n")
    assert "Consulte os atributos, escolhas e recursos" in screen.text
    assert [[button.text for button in row] for row in screen.keyboard.inline_keyboard] == [
        ["Inventário", "Equipamentos"],
        ["Artes", "Talentos"],
        ["Atributos", "Ofícios"],
        ["Perfil", "Caminho"],
        ["Doutrinas", "Cosméticos"],
        ["← Menu"],
    ]
    callbacks = [button.callback_data for button in _buttons(screen)]
    assert callbacks == [
        "inventory:root",
        "eq:r",
        "character:arts",
        "character:talents",
        "character:attributes",
        "character:professions",
        "character:profile",
        "character:path",
        "character:doctrines",
        "character:cosmetics",
        "menu:back",
    ]
    assert "🎴 Artes · Combate" in screen.text
    assert all("menu:noop" not in value for value in callbacks)
    assert screen.image_key == "character"


def test_main_menu_personagem_button_has_real_character_destination():
    screen = render_world(
        WorldView(
            kind="world",
            character_id=uuid4(),
            name="Heroa",
            race="remanescente",
            character_class="sentinela",
            hp=Decimal("702"),
            max_hp=Decimal("702"),
            vigor=100,
            max_vigor=100,
            xp=0,
            region="Terras do Ocaso",
            location="Refúgio do Ocaso",
            quest_title=None,
        )
    )
    button = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Personagem"
    )
    assert button.callback_data == "character:root"


def test_equipment_root_always_renders_eight_slots_and_stable_numeric_callbacks():
    screen = render_equipment_root(_root(version=2147483647))
    expected = [
        "1 🗡️ Arma Principal · Vazio",
        "2 ⚔️ Arma Secundária · Vazio",
        "3 🪖 Cabeça · Vazio",
        "4 🥋 Torso · Vazio",
        "5 🧤 Mãos · Vazio",
        "6 🥾 Pés · Vazio",
        "7 💍 Acessório · Vazio",
        "8 🧿 Artefato · Vazio",
    ]
    assert all(line in screen.text for line in expected)
    buttons = _buttons(screen)
    assert [button.text for button in buttons] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "← Personagem",
    ]
    assert [button.callback_data for button in buttons[:8]] == [
        "eq:s:p:2147483647",
        "eq:s:s:2147483647",
        "eq:s:h:2147483647",
        "eq:s:t:2147483647",
        "eq:s:m:2147483647",
        "eq:s:f:2147483647",
        "eq:s:a:2147483647",
        "eq:s:r:2147483647",
    ]
    assert all(len(button.callback_data.encode()) <= 64 for button in buttons)


def test_equipment_root_shows_partial_equipment_and_blocks_secondary_for_two_handed():
    weapon = _item(
        slot=EquipmentSlot.PRINCIPAL,
        item_slot="2H",
        name="Lâmina <da Ruptura>",
        rarity="Mítico",
        enhancement=6,
        equipped_slot=EquipmentSlot.PRINCIPAL,
    )
    screen = render_equipment_root(_root({EquipmentSlot.PRINCIPAL: weapon}, blocked_secondary=True))
    assert "1 🗡️ Arma Principal · Lâmina &lt;da Ruptura&gt; · +6" in screen.text
    assert "2 ⚔️ Arma Secundária · Bloqueada" in screen.text
    assert "🔒 Arma de 2 mãos equipada" in screen.text
    assert "3 🪖 Cabeça · Vazio" in screen.text
    buttons = _buttons(screen)
    assert [button.text for button in buttons] == [
        "1",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "← Personagem",
    ]
    assert all(button.callback_data != "eq:s:s:4" for button in buttons)
    assert "ATQ" not in screen.text


@pytest.mark.parametrize(
    ("rarity", "icon"),
    [
        ("Comum", "⚪"),
        ("Raro", "🔵"),
        ("Épico", "🟣"),
        ("Lendário", "🟠"),
        ("Mítico", "🔴"),
    ],
)
def test_equipment_detail_localizes_rarity_and_displays_actual_contribution(rarity, icon):
    item = _item(
        name="Elmo <Cinério>",
        rarity=rarity,
        enhancement=10,
        level=60,
        bound=True,
        contribution=EquipmentStatContribution(
            hp=Decimal("12"),
            attack=Decimal("3.5"),
            defense=Decimal("0"),
            agility=Decimal("1.75"),
            per=Decimal("0.25"),
            crit=Decimal("1.5"),
            evasion=Decimal("0"),
            block=Decimal("2.00"),
        ),
    )
    view = EquipmentDetailView(uuid4(), 60, 2_147_483_647, item)
    screen = render_equipment_detail(view, context="i")
    assert "🪖 Elmo &lt;Cinério&gt; · +10" in screen.text
    assert f"{icon} {rarity} · Cabeça" in screen.text
    assert "🔗 Vinculado" in screen.text
    assert "📈 Nível do Item · 60" in screen.text
    assert "❤️ HP +12" in screen.text
    assert "⚔️ ATQ +3.5" in screen.text
    assert "💨 AGI +1.75" in screen.text
    assert "🗡️ PER +0.25%" in screen.text
    assert "💥 CRIT +1.5%" in screen.text
    assert "🛡️ Bloqueio +2%" in screen.text
    assert "DEF" not in screen.text and "Esquiva" not in screen.text
    assert all(len(button.callback_data.encode()) <= 64 for button in _buttons(screen))
    assert "Aprimorar" not in [button.text for button in _buttons(screen)]
    assert "Runas" in [button.text for button in _buttons(screen)]
    assert "Encantamento" in [button.text for button in _buttons(screen)]


def test_equipment_detail_requires_level_without_equip_action_and_inventory_return():
    item = _item(level=25, eligible=False)
    screen = render_equipment_detail(EquipmentDetailView(uuid4(), 10, 9, item), context="i")
    assert "📈 Nível do Item · 25" in screen.text
    assert "⏳ Requer Nv. 25" in screen.text
    buttons = _buttons(screen)
    assert [button.text for button in buttons] == [
        "Runas",
        "Encantamento",
        "Aprimorar",
        "Favoritar",
        "Bloquear",
        "Desmontar",
        "← Equipamentos",
    ]
    assert buttons[-1].callback_data == "inventory:category:equipment"
    assert "[Trocar]" not in screen.text


def test_equipment_detail_hides_reroll_when_no_legal_secondary_identity_exists():
    item = _item(
        slot=EquipmentSlot.TORSO,
        item_slot="Torso",
        secondaries=(("HP", "1"), ("DEF", "1"), ("Bloqueio", "0.25")),
        reroll_available=False,
    )
    screen = render_equipment_detail(EquipmentDetailView(uuid4(), 10, 3, item), context="i")
    assert "Reroll" not in [button.text for button in _buttons(screen)]


def test_equipped_detail_and_inventory_context_never_offers_swap():
    item = _item(equipped_slot=EquipmentSlot.CABECA)
    view = EquipmentDetailView(uuid4(), 20, 15, item)
    slot_detail = render_equipment_detail(view, context="s")
    assert [button.text for button in _buttons(slot_detail)] == [
        "Trocar",
        "Desequipar",
        "Runas",
        "Encantamento",
        "Aprimorar",
        "Favoritar",
        "Bloquear",
        "Desmontar",
        "← Equipamentos",
    ]
    inventory_detail = render_equipment_detail(view, context="i")
    assert [button.text for button in _buttons(inventory_detail)] == [
        "Desequipar",
        "Runas",
        "Encantamento",
        "Aprimorar",
        "Favoritar",
        "Bloquear",
        "Desmontar",
        "← Equipamentos",
    ]
    assert "✅ Equipado" in inventory_detail.text
    assert "Trocar" not in [button.text for button in _buttons(inventory_detail)]


def test_candidate_selection_uses_stable_item_identity_and_no_lore():
    candidate = _item(
        name="Capacete de Cinzas",
        item_slot="Cabeça",
        rarity="common",
        enhancement=2,
        level=4,
        contribution=EquipmentStatContribution(hp=Decimal("3.25")),
        lore="LOR E NÃO DEVE SER LISTADO",
    )
    view = EquipmentCandidatesView(
        uuid4(), 4, 9999999999999999999, EquipmentSlot.CABECA, (candidate,)
    )
    screen = render_equipment_candidates(view)
    assert "1 Capacete de Cinzas · +2" in screen.text
    assert "⚪ Comum · Cabeça" in screen.text
    assert "📈 Nível do Item · 4" in screen.text
    assert "❤️ HP +3.25" in screen.text
    assert "LOR E NÃO DEVE SER LISTADO" not in screen.text
    buttons = _buttons(screen)
    assert buttons[0].text == "1"
    assert buttons[0].callback_data == (
        f"eq:e:{candidate.item_instance_id.hex}:9999999999999999999:s"
    )
    assert buttons[-1].callback_data == "eq:r"
    assert all(len(button.callback_data.encode()) <= 64 for button in buttons)


def test_inventory_equipment_rows_are_clickable_localized_and_show_equipped_state():
    item_id = uuid4()
    screen = render_inventory(
        InventoryView(
            "inventory_category",
            uuid4(),
            used_slots=1,
            category="equipment",
            entries=(
                InventoryEntry(
                    kind="equipment",
                    key=str(item_id),
                    title="Lâmina de Teste",
                    rarity="common",
                    slot="main_hand",
                    item_level=3,
                    payload={"enhancement": 4, "core": {"ATQ": 9}},
                    equipped_slot="Principal",
                ),
            ),
        )
    )
    assert "1 🗡️ Lâmina de Teste · +4" in screen.text
    assert "⚪ Comum · Arma Principal" in screen.text
    assert "✅ Equipado" in screen.text
    assert "ATQ" not in screen.text
    assert [button.callback_data for button in _buttons(screen)] == [
        f"eq:v:{item_id.hex}",
        "inventory:root",
    ]


def test_empty_candidates_show_text_state_and_return_without_dead_action():
    screen = render_equipment_candidates(
        EquipmentCandidatesView(uuid4(), 1, 0, EquipmentSlot.CABECA, ())
    )
    assert "Nenhum Equipamento compatível disponível." in screen.text
    assert [button.callback_data for button in _buttons(screen)] == ["eq:r"]
    assert screen.image_key == "equipment"


@pytest.mark.asyncio
async def test_stale_slot_read_replies_and_rebuilds_authoritative_equipment_root():
    equipped = _item(equipped_slot=EquipmentSlot.CABECA)
    root = _root({EquipmentSlot.CABECA: equipped}, version=4)
    read_service = AsyncMock()
    read_service.root.return_value = root
    read_service.detail.return_value = None
    read_service.candidates.return_value = None
    equipment_service = AsyncMock()
    inventory = AsyncMock()
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(equipment_router(read_service, equipment_service, inventory, {}))
    telegram = Bot("123456:local-test-token")
    telegram.session.make_request = AsyncMock(return_value=True)

    await dispatcher.feed_raw_update(
        telegram,
        callback_update("eq:s:h:4", update_id=99, actor=42),
    )

    methods = [call.args[1] for call in telegram.session.make_request.call_args_list]
    answer = next(method for method in methods if isinstance(method, AnswerCallbackQuery))
    screen = next(method for method in reversed(methods) if isinstance(method, EditMessageText))
    assert answer.text == "Configuração atualizada."
    assert "3 🪖 Cabeça · Elmo de Teste · +0" in screen.text
    assert equipment_service.equip_item.await_count == 0
    assert equipment_service.unequip_slot.await_count == 0
