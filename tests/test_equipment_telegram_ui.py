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


def _identity(**overrides):
    from asterion.application.character_surfaces import IdentityView

    data = dict(
        name="Oppan",
        character_class="vigia",
        level=1,
        legacy_level=1,
        selected_title=None,
        guild_tag="CIN",
    )
    data.update(overrides)
    return IdentityView(**data)


def test_character_hub_shows_legado_only_when_applicable():
    def labels(view):
        return [b.text for row in render_character(view).keyboard.inline_keyboard for b in row]

    assert "🏛️ Legado" not in labels(_identity(legacy_level=0, level=59))
    assert "🏛️ Legado" in labels(_identity(legacy_level=0, level=60))
    no_tag = render_character(_identity(guild_tag=None, legacy_level=0)).text
    assert "🏹 <b>Oppan</b> · <code>Nv. 1</code>" in no_tag


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
        if button.text == "👤 Personagem"
    )
    assert button.callback_data == "character:root"


def test_equipment_detail_hides_reroll_when_no_legal_secondary_identity_exists():
    item = _item(
        slot=EquipmentSlot.TORSO,
        item_slot="Torso",
        secondaries=(("HP", "1"), ("DEF", "1"), ("Bloqueio", "0.25")),
        reroll_available=False,
    )
    screen = render_equipment_detail(EquipmentDetailView(uuid4(), 10, 3, item), context="i")
    assert "Reroll" not in [button.text for button in _buttons(screen)]


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
    assert "🪖 <b>Cabeça</b> · 🔵 Elmo de Teste" in screen.text
    assert equipment_service.equip_item.await_count == 0
    assert equipment_service.unequip_slot.await_count == 0




# ---------------------------------------------------------------------------
# UI aprovada: Personagem, Equipamentos, Detalhe e Seleção.
# ---------------------------------------------------------------------------
def _texts(screen):
    return [[b.text for b in row] for row in screen.keyboard.inline_keyboard]


def _stats(**values):
    return EquipmentStatContribution(**values)


def test_character_hub_follows_approved_layout():
    screen = render_character(_identity(legacy_level=0))
    assert screen.text == (
        "👤 <b>Personagem</b>\n\n"
        "🏹 <b>[CIN] Oppan</b> · <code>Nv. 1</code>\n"
        "🎖️ <code>Caminhante das Cinzas</code>"
    )
    assert _texts(screen) == [
        ["⚔️ Equipamentos", "💼 Inventário"],
        ["🧿 Artes", "🌳 Talentos"],
        ["🔱 Doutrinas", "📖 História"],
        ["🎨 Cosméticos", "🏆 Feitos"],
        ["↩️ Retornar"],
    ]
    callbacks = [b.callback_data for b in _buttons(screen)]
    assert callbacks[:2] == ["eq:r", "inventory:root"] and callbacks[-1] == "menu:back"
    assert "🏛️ Legado" in [b.text for b in _buttons(render_character(_identity(level=60)))]


def test_character_stats_keep_vida_and_hp_and_precisao_in_two_columns():
    from asterion.application.character_surfaces import AttributesView

    stats = AttributesView(
        name="Oblek", level=1, character_class="vigia", selected_path=None,
        hp=Decimal("618"), max_hp=Decimal("618"), vigor=100, max_vigor=100,
        attack=Decimal("112"), defense=Decimal("71"), agility=Decimal("83"),
        perception=Decimal("0"), critical=Decimal("5"), evasion=Decimal("0"),
        block=Decimal("0"), xp=320, xp_required=4800, crowns=21,
    )  # fmt: skip
    text = render_character(_identity(legacy_level=0, selected_title=None), stats).text
    assert "🪙 <b>Coroas</b> · <code>21</code>" in text
    assert "❤️ <b>Vida</b> · <code>618/618</code>\n🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥" in text
    assert "✨ <b>XP</b> · <code>320/4.800</code>\n🟦⬜⬜⬜⬜⬜⬜⬜⬜⬜" in text
    assert "⚔️ <b>ATQ</b> · <code>112</code>\u3000💨 <b>AGI</b> · <code>83</code>" in text
    assert "🛡️ <b>DEF</b> · <code>71</code>\u3000❤️ <b>HP</b> · <code>618</code>" in text
    assert "💥 <b>Crítico</b> · <code>5%</code>\u3000⚡️ <b>Esquiva</b> · <code>0%</code>" in text
    assert "💢 <b>Bloqueio</b> · <code>0%</code>\u3000🎯 <b>Precisão</b> · <code>0%</code>" in text
    assert "PER" not in text and "Perfuração" not in text


def _full_root():
    items = {
        EquipmentSlot.PRINCIPAL: _item(
            slot=EquipmentSlot.PRINCIPAL, item_slot="main_hand", name="Adaga", rarity="Comum",
            contribution=_stats(attack=Decimal("6")),
        ),
        EquipmentSlot.SECUNDARIA: _item(
            slot=EquipmentSlot.SECUNDARIA, item_slot="off_hand", name="Espada Curta",
            rarity="Raro", enhancement=1,
            contribution=_stats(attack=Decimal("9"), agility=Decimal("2")),
        ),
        EquipmentSlot.CABECA: _item(
            name="Elmo de Cinza", rarity="Comum",
            contribution=_stats(hp=Decimal("8"), defense=Decimal("3")),
        ),
        EquipmentSlot.TORSO: _item(
            slot=EquipmentSlot.TORSO, item_slot="Torso", name="Gibão do Caminhante",
            rarity="Raro", enhancement=3,
            contribution=_stats(hp=Decimal("18"), defense=Decimal("7")),
        ),
        EquipmentSlot.MAOS: _item(
            slot=EquipmentSlot.MAOS, item_slot="Mãos", name="Luvas de Cinza", rarity="Comum",
            contribution=_stats(agility=Decimal("3"), crit=Decimal("1")),
        ),
        EquipmentSlot.ARTEFATO: _item(
            slot=EquipmentSlot.ARTEFATO, item_slot="Artefato", name="Orbe do Ocaso",
            rarity="Comum", contribution=_stats(per=Decimal("2")),
        ),
    }
    return _root(items)


def test_equipment_root_page_one_follows_the_approved_layout():
    root = _full_root()
    from dataclasses import replace

    favorite = replace(root.slots[0].item, favorite=True)
    slots = (EquipmentSlotView(EquipmentSlot.PRINCIPAL, favorite), *root.slots[1:])
    screen = render_equipment_root(replace(root, slots=slots, combat_configuration_version=4))
    assert screen.text.startswith(
        "<b>🛡️ Equipamentos</b>\n\n<i>Aqui ficam os equipamentos que acompanham seu "
        "personagem."
    )
    assert "✋ <b>Principal</b> · ⭐⚪️ Adaga\n⚔️ <code>+6 ATQ</code>" in screen.text
    assert "🤚 <b>Secundária</b> · 🔵 Espada Curta +1\n⚔️ <code>+9 ATQ</code> · 💨 <code>+2 AGI</code>" in screen.text  # noqa: E501
    assert "🪖 <b>Cabeça</b> · ⚪️ Elmo de Cinza\n❤️ <code>+8 HP</code> · 🛡️ <code>+3 DEF</code>" in screen.text  # noqa: E501
    assert "🥋 <b>Torso</b> · 🔵 Gibão do Caminhante +3" in screen.text
    assert "+0" not in screen.text and "Luvas" not in screen.text
    assert _texts(screen) == [
        ["✋ Principal", "🤚 Secundária"],
        ["🪖 Cabeça", "🥋 Torso"],
        ["▶️ Próxima"],
        ["↩️ Retornar"],
    ]
    assert [b.callback_data for b in _buttons(screen)] == [
        "eq:s:p:4", "eq:s:s:4", "eq:s:h:4", "eq:s:t:4", "eq:r:1", "character:root",
    ]  # fmt: skip


def test_equipment_root_page_two_and_empty_slots():
    screen = render_equipment_root(_full_root(), 1)
    assert "🧤 <b>Mãos</b> · ⚪️ Luvas de Cinza\n💨 <code>+3 AGI</code> · 💥 <code>+1% Crítico</code>" in screen.text  # noqa: E501
    assert "🥾 <b>Pés</b> · Vazio" in screen.text
    assert "🔮 <b>Artefato</b> · ⚪️ Orbe do Ocaso\n🎯 <code>+2% Precisão</code>" in screen.text
    assert _texts(screen) == [
        ["🧤 Mãos", "🥾 Pés"],
        ["💍 Acessório", "🔮 Artefato"],
        ["◀️ Anterior"],
        ["↩️ Retornar"],
    ]
    assert [b.callback_data for b in _buttons(screen)][-2] == "eq:r"
    assert render_equipment_root(_full_root(), 99).text == screen.text


def test_equipment_root_blocks_secondary_for_two_handed_weapon():
    weapon = _item(
        slot=EquipmentSlot.PRINCIPAL, item_slot="2H", name="Lâmina <da Ruptura>",
        rarity="Mítico", enhancement=6, equipped_slot=EquipmentSlot.PRINCIPAL,
    )
    screen = render_equipment_root(_root({EquipmentSlot.PRINCIPAL: weapon}, blocked_secondary=True))
    assert "🔴 Lâmina &lt;da Ruptura&gt; +6" in screen.text
    assert "🤚 <b>Secundária</b> · Bloqueada" in screen.text
    assert all(button.callback_data != "eq:s:s:4" for button in _buttons(screen))


def test_equipment_detail_follows_approved_layout():
    item = _item(
        slot=EquipmentSlot.PRINCIPAL, item_slot="main_hand", name="Adaga", rarity="Comum",
        level=1, bound=True, equipped_slot=EquipmentSlot.PRINCIPAL,
        lore="Uma lâmina curta e leve.", contribution=_stats(attack=Decimal("6")),
    )
    from dataclasses import replace

    item = replace(
        item,
        weapon_handedness_label="1 mão",
        weapon_proficiency_label="Arma · Lâminas",
        runes=({"family": "Fresta", "grade": 1, "potency": "2.00 p.p."},),
        enchantment={"family": "Marca da Fresta", "name": "Marca do Véu", "potency": "1.00 p.p."},
        special_abilities=(
            {"name": "Golpe da Ruptura", "type": "Passiva", "description": "Dano adicional."},
        ),
    )
    screen = render_equipment_detail(EquipmentDetailView(uuid4(), 20, 7, item), context="s")
    assert screen.text.startswith("<b>🗡️ Adaga</b>\n\n<i>Uma lâmina curta e leve.</i>\n\n")
    assert (
        "🗡️ <b>ATQ</b> · <code>+6</code>\n✨ <b>Grau</b> · <code>I</code>\n"
        "⚪ <b>Raridade</b> · <code>Comum</code>\n✋ <b>Empunhadura</b> · <code>1 Mão</code>\n"
        "🎓 <b>Proficiência</b> · <code>Lâminas</code>\n🔗 <b>Vínculo</b> · <code>Vinculado</code>"
    ) in screen.text
    assert "🔷 <b>Runa</b> · <code>Runa da Fresta</code>\n🎯 <code>+2% Precisão</code>" in screen.text  # noqa: E501
    assert "💫 <b>Encantamento</b> · <code>Marca do Véu</code>\n🎯 <code>+1% Precisão</code>" in screen.text  # noqa: E501
    assert "🌟 <b>Golpe da Ruptura</b> · <code>Passiva</code>\n\n<i>Dano adicional.</i>" in screen.text  # noqa: E501
    assert "+0" not in screen.text
    assert _texts(screen) == [["🔄 Trocar", "❌ Desequipar"], ["⭐ Favoritar"], ["↩️ Retornar"]]
    assert [b.callback_data for b in _buttons(screen)][-1] == "eq:r"
    assert all(len(b.callback_data.encode()) <= 64 for b in _buttons(screen))


def test_equipment_detail_never_offers_block_or_forge_actions():
    item = _item(equipped_slot=EquipmentSlot.CABECA, enhancement=2)
    forbidden = {"🚫 Bloquear", "🚫 Desbloquear", "🔮 Runas", "✨ Encantamento",
                 "🔨 Aprimorar", "🔧 Desmontar", "🎲 Reroll"}  # fmt: skip
    for context in ("s", "i"):
        for view in (item, replace_item(item, favorite=True), replace_item(item, locked=True)):
            screen = render_equipment_detail(EquipmentDetailView(uuid4(), 20, 3, view), context=context)  # noqa: E501
            labels = {b.text for b in _buttons(screen)}
            assert not labels & forbidden
            assert not any(b.callback_data.startswith(("em:k", "em:r", "em:e", "em:h", "em:d", "em:l"))  # noqa: E501
                           for b in _buttons(screen))  # fmt: skip
    favorited = render_equipment_detail(
        EquipmentDetailView(uuid4(), 20, 3, replace_item(item, favorite=True)), context="s"
    )
    assert "⭐ Desfavoritar" in [b.text for b in _buttons(favorited)]


def replace_item(item, **changes):
    from dataclasses import replace

    return replace(item, **changes)


def test_unequipped_detail_offers_trocar_favoritar_and_returns_to_inventory():
    item = _item(level=25, eligible=False)
    screen = render_equipment_detail(EquipmentDetailView(uuid4(), 10, 9, item), context="i")
    assert _texts(screen) == [["🔄 Trocar"], ["⭐ Favoritar"], ["↩️ Retornar"]]
    assert _buttons(screen)[-1].callback_data == "inventory:category:equipment"
    equipped = render_equipment_detail(
        EquipmentDetailView(uuid4(), 10, 9, replace_item(item, equipped_slot=EquipmentSlot.CABECA)),
        context="i",
    )
    assert _texts(equipped)[0] == ["🔄 Trocar", "❌ Desequipar"]
    assert _buttons(equipped)[1].callback_data.endswith(":i")


@pytest.mark.parametrize(
    ("rarity", "icon"),
    [("Comum", "⚪"), ("Raro", "🔵"), ("Épico", "🟣"), ("Lendário", "🟠"), ("Mítico", "🔴")],
)
def test_equipment_detail_localizes_rarity_and_shows_actual_contribution(rarity, icon):
    item = _item(
        name="Elmo <Cinério>", rarity=rarity, enhancement=10, level=60, bound=True,
        contribution=_stats(
            hp=Decimal("12"), attack=Decimal("3.5"), agility=Decimal("1.75"),
            per=Decimal("0.25"), crit=Decimal("1.5"), block=Decimal("2.00"),
        ),
    )  # fmt: skip
    screen = render_equipment_detail(EquipmentDetailView(uuid4(), 60, 1, item), context="i")
    assert "<b>🪖 Elmo &lt;Cinério&gt; +10</b>" in screen.text
    assert f"{icon} <b>Raridade</b> · <code>{rarity}</code>" in screen.text
    assert "✨ <b>Grau</b> · <code>VI</code>" in screen.text
    for line in (
        "❤️ <b>HP</b> · <code>+12</code>",
        "🗡️ <b>ATQ</b> · <code>+3.5</code>",
        "💨 <b>AGI</b> · <code>+1.75</code>",
        "🎯 <b>Precisão</b> · <code>+0.25%</code>",
        "💥 <b>Crítico</b> · <code>+1.5%</code>",
        "💢 <b>Bloqueio</b> · <code>+2%</code>",
    ):
        assert line in screen.text
    assert "DEF" not in screen.text and "Esquiva" not in screen.text


def test_armor_class_is_proficiency_in_detail_and_not_extra_info_in_selection():
    item = replace_item(_item(name="Elmo Pesado"), armor_class_label="Pesada", region_label="Confins")  # noqa: E501
    detail = render_equipment_detail(EquipmentDetailView(uuid4(), 10, 9, item), context="i")
    assert "🎓 <b>Proficiência</b> · <code>Pesada</code>" in detail.text
    assert "Região" not in detail.text
    selection = render_equipment_candidates(
        EquipmentCandidatesView(uuid4(), 10, 1, EquipmentSlot.CABECA, (item,))
    )
    assert "Região" not in selection.text and "Classe de Armadura" not in selection.text
    plain = render_equipment_detail(EquipmentDetailView(uuid4(), 10, 9, _item()), context="i")
    assert "Proficiência" not in plain.text


def test_candidate_selection_equips_directly_with_numbered_buttons():
    first = _item(name="Adaga", rarity="common", contribution=_stats(attack=Decimal("6")))
    second = _item(
        name="Espada Curta", rarity="Raro", enhancement=1, lore="NÃO LISTAR",
        contribution=_stats(attack=Decimal("9"), agility=Decimal("2")),
    )
    view = EquipmentCandidatesView(
        uuid4(), 4, 9999999999999999999, EquipmentSlot.PRINCIPAL, (first, second)
    )
    screen = render_equipment_candidates(view)
    assert screen.text == (
        "<b>🛡️ Equipamentos</b>\n\n<i>Neste espaço, escolha entre os equipamentos "
        "compatíveis disponíveis para equipar.</i>\n\n"
        "#1 ⚪️ <b>Adaga</b>\n🗡️ <code>+6 ATQ</code>\n\n"
        "#2 🔵 <b>Espada Curta +1</b>\n🗡️ <code>+9 ATQ</code> · 💨 <code>+2 AGI</code>"
    )
    assert _texts(screen) == [["1️⃣", "2️⃣"], ["↩️ Retornar"]]
    callbacks = [b.callback_data for b in _buttons(screen)]
    assert callbacks[:2] == [
        f"eq:e:{first.item_instance_id.hex}:9999999999999999999:s",
        f"eq:e:{second.item_instance_id.hex}:9999999999999999999:s",
    ]
    assert callbacks[-1] == "eq:r" and not any(c.startswith("eq:v:") for c in callbacks)
    assert all(len(c.encode()) <= 64 for c in callbacks)


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6])
def test_candidate_buttons_follow_the_numeric_distribution(count):
    from asterion.bot.ui_format import numeric_row_sizes

    candidates = tuple(_item(name=f"Elmo {n}") for n in range(count))
    screen = render_equipment_candidates(
        EquipmentCandidatesView(uuid4(), 10, 1, EquipmentSlot.CABECA, candidates)
    )
    assert [len(row) for row in _texts(screen)[:-1]] == numeric_row_sizes(count)


def test_candidates_paginate_after_six_items():
    candidates = tuple(_item(name=f"Elmo {n}") for n in range(8))
    view = EquipmentCandidatesView(uuid4(), 10, 5, EquipmentSlot.CABECA, candidates)
    first, second = render_equipment_candidates(view), render_equipment_candidates(view, 1)
    assert _texts(first) == [["1️⃣", "2️⃣", "3️⃣"], ["4️⃣", "5️⃣", "6️⃣"], ["▶️ Próxima"], ["↩️ Retornar"]]
    assert _texts(second) == [["1️⃣", "2️⃣"], ["◀️ Anterior"], ["↩️ Retornar"]]
    assert "eq:c:h:5:1" in [b.callback_data for b in _buttons(first)]
    assert "#1" in second.text and "Elmo 6" in second.text and "Elmo 0" not in second.text


def test_candidates_without_compatible_equipment_use_the_approved_empty_state():
    screen = render_equipment_candidates(
        EquipmentCandidatesView(uuid4(), 1, 0, EquipmentSlot.CABECA, ())
    )
    assert screen.text == (
        "<b>🛡️ Equipamentos</b>\n\n<i>Nenhum equipamento compatível está disponível para "
        "esta posição. Obtenha um equipamento compatível para poder equipá-lo.</i>"
    )
    assert [b.callback_data for b in _buttons(screen)] == ["eq:r"]
    assert screen.image_key == "equipment"


def test_inventory_equipment_rows_open_detail_and_hide_zero_enhancement():
    item_id = uuid4()
    screen = render_inventory(
        InventoryView(
            "inventory_category", uuid4(), used_slots=1, category="equipment",
            entries=(
                InventoryEntry(
                    kind="equipment", key=str(item_id), title="Lâmina de Teste", rarity="common",
                    slot="main_hand", item_level=3, payload={"enhancement": 0},
                    equipped_slot="Principal",
                ),
            ),
        )  # fmt: skip
    )
    assert "#1 ⚪️ <b>Lâmina de Teste</b>" in screen.text and "+0" not in screen.text
    assert _buttons(screen)[0].callback_data == f"eq:v:{item_id.hex}"
