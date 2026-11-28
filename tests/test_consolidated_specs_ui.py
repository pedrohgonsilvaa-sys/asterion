"""Especificações consolidadas 2026-11-26: Inventário, Equipamentos, Materiais, Artes,
Doutrinas, História, Cosméticos e Feitos.

Telas puras (sem banco) e fluxos completos no Telegram (com banco descartável).
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from sqlalchemy import select

from asterion.application.active_arts import ActiveArtCharacterView, ActiveArtSlotSnapshot
from asterion.application.character_surfaces import (
    AchievementView,
    CharacterSurfacesService,
    KnowledgeView,
    ProfileView,
)
from asterion.application.doctrines import (
    DoctrineCollectionView,
    DoctrineService,
    DoctrineView,
)
from asterion.application.inventory import InventoryEntry, InventoryView
from asterion.bot.character_progression_handlers import character_progression_router
from asterion.bot.character_progression_ui import render_art_detail, render_art_root
from asterion.bot.character_surfaces_handlers import character_surfaces_router
from asterion.bot.character_surfaces_ui import (
    render_achievement_category,
    render_achievement_detail,
    render_achievement_root,
    render_history,
)
from asterion.bot.doctrines_handlers import doctrines_router
from asterion.bot.doctrines_ui import (
    render_art_slots,
    render_doctrine_detail,
    render_doctrine_root,
    render_editor,
    render_name_prompt,
    render_talent_page,
)
from asterion.bot.inventory_ui import render_material_detail
from asterion.domain.arts import SENTINEL_ART_IDS, VIGIA_ART_IDS
from asterion.domain.economy import crowns_per_level
from asterion.domain.talents import TALENTS_BY_CLASS, talent_points_at_level
from asterion.infrastructure.db.models import Character
from tests.test_character_surfaces_telegram import _button, _last_screen, _message_update
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road


def _labels(screen) -> list[list[str]]:
    markup = getattr(screen, "keyboard", None) or screen.reply_markup
    return [[button.text for button in row] for row in markup.inline_keyboard]


def _flat(screen) -> list[str]:
    return [label for row in _labels(screen) for label in row]


def _talent(name: str) -> str:
    talent = next(item for item in TALENTS_BY_CLASS["sentinela"] if item.name == name)
    return talent.talent_id


def _collection(*doctrines: DoctrineView, level: int = 1, current=None) -> DoctrineCollectionView:
    return DoctrineCollectionView(
        character_name="Olev",
        character_class="sentinela",
        selected_path=None,
        configuration_version=3,
        foreground=False,
        current_configuration=current
        or {"path": None, "equipment": {}, "arts": {}, "talents": []},
        doctrines=doctrines,
        crowns=0,
        level=level,
    )


def _doctrine(name: str, *, current=False, arts=None, talents=(), equipment=None, names=()):
    return DoctrineView(
        doctrine_id=uuid4(),
        name=name,
        revision=2,
        configuration={
            "path": None,
            "equipment": equipment or {},
            "arts": arts or {},
            "talents": [
                {"point_slot": slot, "talent_id": talent_id}
                for slot, talent_id in enumerate(talents, start=1)
            ],
        },
        is_current=current,
        incomplete_reason=None,
        can_apply=not current,
        equipment_names=names,
    )


# --- Doutrinas (Parte II) ---------------------------------------------------------


def test_doctrine_root_has_symmetric_columns_and_a_single_doctrine_in_use():
    doctrines = (
        _doctrine("PvE", current=True),
        _doctrine("PvP", current=True),  # mesma build: só uma fica 🟢
        _doctrine("Caçada"),
        _doctrine("Arena"),
    )
    screen = render_doctrine_root(_collection(*doctrines))
    assert screen.text.startswith("<b>🗂️ Doutrinas</b>\n\n<i>Crie e salve diferentes")
    assert screen.text.count("🟢") == 1 and screen.text.count("🔴") == 3
    assert "Ativa" not in screen.text and "Inativa" not in screen.text
    # Duas colunas de largura fixa e igual: cada nome ocupa a largura do maior.
    assert "🟢 <code>PvE   </code>  🔴 <code>PvP   </code>" in screen.text
    assert "🔴 <code>Caçada</code>  🔴 <code>Arena </code>" in screen.text
    assert "⚠️ Pode criar diferentes Doutrinas" in screen.text
    assert _labels(screen) == [
        ["🟢 PvE", "🔴 PvP"],
        ["🔴 Caçada", "🔴 Arena"],
        ["➕ Criar"],
        ["↩️ Retornar"],
    ]
    # Selecionar uma Doutrina abre direto a Configuração (doc:d).
    assert all(
        button.callback_data.startswith("doc:d:")
        for row in screen.keyboard.inline_keyboard[:2]
        for button in row
    )


def test_doctrine_root_hides_create_at_the_limit():
    doctrines = tuple(_doctrine(f"D{index}") for index in range(5))
    assert "➕ Criar" not in _flat(render_doctrine_root(_collection(*doctrines)))


def test_doctrine_configuration_lists_every_active_talent_without_path_or_slot():
    talents = (
        "Aço Desperto",
        "Ponta Revidada",
        "Firme sob Impacto",
        "Olho de Combate",
        "Vigília",
        "Persistência",
    )
    doctrine = _doctrine(
        "PvE",
        arts={"1": SENTINEL_ART_IDS["golpe_de_guarda"]},
        talents=[_talent(name) for name in talents],
        equipment={"Principal": str(uuid4())},
        names=(("Principal", "Espada"),),
    )
    screen = render_doctrine_detail(_collection(doctrine, level=60), doctrine)
    text = screen.text
    assert text.startswith("<b>⚙️ Configuração</b>")
    assert "⚔️ <b>Principal</b> · <code>Espada</code>" in text
    assert "🔮 <b>Artefato</b> · <code>Vazio</code>" in text
    assert "1️⃣ <code>Golpe de Guarda</code>\n2️⃣ <code>Vazio</code>" in text
    # Quantidade dinâmica: os seis Talentos ativos ficam na própria tela, sem os 18.
    for name in talents:
        assert f"<code>{name}</code>" in text
    assert "6️⃣ <code>Persistência</code>" in text
    assert "Carne de Pedra" not in text
    assert "Caminho" not in text and "Slot" not in text
    assert _labels(screen) == [["✅ Usar", "✏️ Editar"], ["🗑️ Excluir"], ["↩️ Retornar"]]


def test_doctrine_editor_name_and_arts_use_closed_terms():
    doctrine = _doctrine("PvE")
    view = _collection(doctrine)
    editor = render_editor(view, doctrine)
    assert editor.text.startswith("<b>✏️ Editar Doutrina</b>")
    assert _labels(editor) == [
        ["✏️ Nome", "🛡️ Equipamentos"],
        ["🧿 Artes", "🌿 Talentos"],
        ["↩️ Retornar"],
    ]
    assert "Símbolo" not in editor.text and "Caminho" not in editor.text
    prompt = render_name_prompt("doc:r")
    assert "✏️ Envie o novo nome da Doutrina." in prompt.text
    assert _labels(prompt) == [["↩️ Retornar"]]
    arts = render_art_slots(view, doctrine)
    assert _labels(arts) == [["⚔️ Arte 1"], ["⚔️ Arte 2"], ["⚔️ Arte 3"], ["↩️ Retornar"]]
    assert "Slot" not in arts.text and "Slot" not in "".join(_flat(arts))


def test_doctrine_talent_pages_follow_level_requirements_and_states():
    doctrine = _doctrine("PvE", talents=[_talent("Aço Desperto")])
    view = _collection(doctrine, level=15)
    first = render_talent_page(view, doctrine, 0)
    available = talent_points_at_level(15) - 1
    assert f"🎋 <b>Pontos Disponíveis</b> · <code>{available}</code>" in first.text
    for level in (5, 15, 25):
        assert f"📜 <b>Requer Nv. {level}</b>" in first.text
    assert "Requer Nv. 35" not in first.text
    assert "✅ <code>Aço Desperto</code>" in first.text
    assert "✨ <code>Carne de Pedra</code>" in first.text
    assert "✨ <code>Ponta Revidada</code>" in first.text
    assert "🔒 <code>Pressão de Fissuras</code>" in first.text
    labels = _flat(first)
    assert labels[:3] == ["✅ Aço", "✨ Carne", "✨ Ritmo"]
    assert not any(label.startswith("🔒") for label in labels)
    assert labels[-2:] == ["▶️ Próxima", "↩️ Retornar"]
    second = render_talent_page(view, doctrine, 1)
    for level in (35, 45, 55):
        assert f"📜 <b>Requer Nv. {level}</b>" in second.text
    assert _flat(second) == ["◀️ Anterior", "↩️ Retornar"]


# --- História (Parte IV §1) --------------------------------------------------------


def test_history_screen_and_input_state():
    empty = ProfileView("Olev", 1, "sentinela", None, None, 0)
    screen = render_history(empty)
    assert screen.text == (
        "<b>📖 História</b>\n\n<i>Conte quem o personagem era, o que encontrou pelo caminho "
        "e o que ainda busca em Asterion.</i>"
    )
    assert _labels(screen) == [["✍️ Escrever"], ["↩️ Retornar"]]
    assert screen.image_key == "character"
    writing = render_history(empty, writing=True)
    assert writing.text.endswith("✍️ Envie a História do personagem.")
    assert _labels(writing) == [["↩️ Retornar"]]
    saved = render_history(ProfileView("Olev", 1, "sentinela", None, "Veio do <sul>.", 1))
    assert "<blockquote>Veio do &lt;sul&gt;.</blockquote>" in saved.text


# --- Feitos (Parte IV §6–§7) -------------------------------------------------------


def _knowledge(*achievements) -> KnowledgeView:
    return KnowledgeView("sentinela", (), (), achievements, frozenset())


CINZAS = AchievementView(
    "feat.tdo.cinzas_na_estrada",
    "Cinzas na Estrada",
    "exploration",
    "Você atravessou a estrada em meio às cinzas, enfrentou o que surgiu entre as ruínas "
    "e encontrou o primeiro caminho para seguir adiante.",
    None,
    "Comum",
    "Prólogo",
    "🛤️",
)


def test_feats_root_lists_spec_categories_first_and_keeps_the_others():
    screen = render_achievement_root(_knowledge())
    assert screen.text.startswith("<b>🏆 Feitos</b>\n\n<i>Registre as conquistas")
    assert _labels(screen) == [
        ["🧭 Exploração", "⚔️ Combate"],
        ["🏰 Guilda", "🏟️ Arena"],
        ["🌌 Eventos", "⛓️ PvE"],
        ["⚒️ Ofícios", "📖 Crônicas"],
        ["🐾 Bestiário", "👁️ Segredos"],
        ["↩️ Retornar"],
    ]
    assert not any(label.isdigit() for label in _flat(screen))


def test_feat_category_and_detail_show_state_rarity_and_origin_without_use():
    category = render_achievement_category(_knowledge(CINZAS), "exploration")
    assert "🏆 <b>Feitos de Exploração</b>" in category.text
    assert "<i>Descubra regiões, atravesse caminhos esquecidos" in category.text
    assert "🛤️ <b>Cinzas na Estrada</b>\n🏆 <code>Concluído · Prólogo</code>" in category.text
    assert _labels(category) == [["🛤️ Cinzas na Estrada"], ["↩️ Retornar"]]
    detail = render_achievement_detail(_knowledge(CINZAS), CINZAS.achievement_id)
    assert detail.text == (
        "🏆 <b>Cinzas na Estrada</b>\n\n"
        f"<i>{CINZAS.description}</i>\n\n"
        "✨ <b>Raridade</b> · <code>Comum</code>\n"
        "🌐 <b>Origem</b> · <code>Prólogo</code>"
    )
    assert _labels(detail) == [["↩️ Retornar"]]
    empty = render_achievement_category(_knowledge(), "events")
    assert "Nenhum Feito foi conquistado ainda." in empty.text


def test_feat_category_paginates_by_name_buttons():
    from asterion.application.knowledge_catalog import ACHIEVEMENTS

    catalog = [item for item in ACHIEVEMENTS if item.category == "exploration"][1:8]
    feats = tuple(
        AchievementView(item.achievement_id, item.name, "exploration", item.description, None)
        for item in catalog
    )
    first = render_achievement_category(_knowledge(*feats), "exploration")
    assert _flat(first)[:5] == [f"🧭 {item.name}" for item in catalog[:5]]
    assert "▶️ Próxima" in _flat(first)
    second = render_achievement_category(_knowledge(*feats), "exploration", 1)
    assert "◀️ Anterior" in _flat(second) and f"🧭 {catalog[6].name}" in _flat(second)


# --- Materiais (Parte I §6) --------------------------------------------------------


def test_material_detail_shows_grade_quantity_type_and_bind():
    entry = InventoryEntry(
        kind="material",
        key="material.tdo.residuo_ocaso",
        title="Resíduo do Ocaso",
        quantity=1,
        bound=True,
        payload={"warehouse_source_id": "0f0f0f0f-0000-0000-0000-000000000001"},
    )
    screen = render_material_detail(entry)
    assert screen.text == (
        "💧 <b>Resíduo do Ocaso</b>\n\n"
        "<i>Um resíduo condensado das forças que atravessam as regiões de Asterion.</i>\n\n"
        "✨ <b>Grau</b> · <code>I</code>\n"
        "📦 <b>Quantidade</b> · <code>1</code>\n\n"
        "🧱 <b>Tipo</b> · <code>Material</code>\n"
        "🔗 <b>Vínculo</b> · <code>Vinculado</code>"
    )
    assert _labels(screen) == [["📥 Guardar", "🗑️ Descartar"], ["↩️ Retornar"]]
    assert screen.keyboard.inline_keyboard[0][0].callback_data == (
        "warehouse:deposit:material:0f0f0f0f000000000000000000000001:i"
    )
    assert screen.image_key == "character"
    listing = InventoryView("inventory_category", uuid4(), 2, category="materials",
                            entries=(entry,))
    from asterion.bot.inventory_ui import render_inventory

    materials = render_inventory(listing)
    assert "#1 🧱 <b>Resíduo do Ocaso</b> · <code>×1</code>\n✨ <code>Grau I</code>" in materials.text  # noqa: E501
    assert _labels(materials)[0] == ["1️⃣"]


# --- Artes (Parte I §7–§9) ---------------------------------------------------------


def _arts_view(**overrides) -> ActiveArtCharacterView:
    golpe = SENTINEL_ART_IDS["golpe_de_guarda"]
    data = dict(
        character_id=uuid4(),
        character_name="Olev",
        character_class="sentinela",
        level=1,
        selected_path=None,
        combat_configuration_version=0,
        slots=(),
        available_art_ids=(golpe,),
        foreground=False,
    )
    data.update(overrides)
    return ActiveArtCharacterView(**data)


_ARTS_HEADER = (
    "<b>🧿 Artes</b>\n\n<i>Artes são técnicas especiais que permitem canalizar "
    "habilidades únicas durante os confrontos de Asterion.</i>\n\n"
)
_EMPTY_SLOTS = (
    "📜 <b>Artes Equipadas</b>\n\n<code>⛔️ Vazio</code>\n<code>⛔️ Vazio</code>\n"
    "<code>⛔️ Vazio</code>\n\n"
)


def test_arts_page_one_lists_all_class_arts_with_lock_state():
    """Especificação visual 2026-11-28, Página 1."""
    screen = render_art_root(_arts_view())
    assert screen.text == (
        _ARTS_HEADER
        + "📄 <b>Página</b> · <code>1/3</code>\n\n"
        + _EMPTY_SLOTS
        + "🛡️ <b>Artes da Classe</b> · <code>Sentinela</code>\n\n"
        "#1 ⚔️ <b>Golpe de Guarda</b> · <code>Nv. 1</code>\n"
        "#2 🔒 <b>Quebra-Postura</b> · <code>Nv. 4</code>\n"
        "#3 🔒 <b>Muralha Breve</b> · <code>Nv. 7</code>\n"
        "#4 🔒 <b>Impacto Resoluto</b> · <code>Nv. 9</code>\n"
        "#5 🔒 <b>Firmeza</b> · <code>Nv. 18</code>\n"
        "#6 🔒 <b>Golpe de Rechaço</b> · <code>Nv. 34</code>"
    )
    assert _labels(screen) == [
        ["1️⃣", "2️⃣", "3️⃣"],
        ["4️⃣", "5️⃣", "6️⃣"],
        ["▶️ Próxima"],
        ["↩️ Retornar"],
    ]
    assert screen.image_key == "character"


def test_arts_pages_two_and_three_list_each_path():
    second = render_art_root(_arts_view(), 1)
    assert second.text == (
        _ARTS_HEADER
        + "📄 <b>Página</b> · <code>2/3</code>\n\n"
        + _EMPTY_SLOTS
        + "🏰 <b>Artes do Caminho</b> · <code>Bastião</code>\n\n"
        "#1 🔒 <b>Escudo de Cinzas</b> · <code>Nv. 12</code>\n"
        "#2 🔒 <b>Interpor</b> · <code>Nv. 22</code>\n"
        "#3 🔒 <b>Contra-Golpe</b> · <code>Nv. 38</code>\n"
        "#4 🔒 <b>Última Muralha</b> · <code>Nv. 52</code>"
    )
    assert _labels(second) == [
        ["1️⃣", "2️⃣"], ["3️⃣", "4️⃣"], ["◀️ Anterior", "▶️ Próxima"], ["↩️ Retornar"],
    ]
    third = render_art_root(_arts_view(), 2)
    assert "📄 <b>Página</b> · <code>3/3</code>" in third.text
    assert (
        "💥 <b>Artes do Caminho</b> · <code>Devastador</code>\n\n"
        "#1 🔒 <b>Aríete</b> · <code>Nv. 12</code>\n"
        "#2 🔒 <b>Golpe de Ruptura</b> · <code>Nv. 22</code>\n"
        "#3 🔒 <b>Abalo</b> · <code>Nv. 38</code>\n"
        "#4 🔒 <b>Ruptor</b> · <code>Nv. 52</code>"
    ) in third.text
    assert _labels(third) == [["1️⃣", "2️⃣"], ["3️⃣", "4️⃣"], ["◀️ Anterior"], ["↩️ Retornar"]]


def test_arts_equipped_state_fills_slot_and_marks_the_list():
    golpe = SENTINEL_ART_IDS["golpe_de_guarda"]
    screen = render_art_root(_arts_view(slots=(ActiveArtSlotSnapshot(2, golpe),)))
    assert (
        "📜 <b>Artes Equipadas</b>\n\n<code>⛔️ Vazio</code>\n"
        "<code>⚔️ Golpe de Guarda</code>\n<code>⛔️ Vazio</code>"
    ) in screen.text
    assert "#1 ✅ <b>Golpe de Guarda</b> · <code>Nv. 1</code>" in screen.text


def test_unchosen_path_arts_stay_locked_after_level_12():
    escudo = "path_art.sentinela.bastiao.escudo_de_cinzas"
    view = _arts_view(
        level=20,
        selected_path="bastiao",
        available_art_ids=(SENTINEL_ART_IDS["golpe_de_guarda"], escudo),
    )
    chosen = render_art_root(view, 1).text
    assert "<b>Escudo de Cinzas</b>" in chosen and "🔒 <b>Escudo de Cinzas</b>" not in chosen
    assert "#1 🔒 <b>Aríete</b>" in render_art_root(view, 2).text


def test_locked_art_detail_is_read_only_and_returns_to_its_page():
    screen = render_art_detail(_arts_view(), "path_art.sentinela.devastador.ariete")
    assert _labels(screen) == [["↩️ Retornar"]]
    assert screen.keyboard.inline_keyboard[-1][0].callback_data == "art:p:2"
    assert "🔓 <b>Desbloqueio</b> · <code>Nv. 12</code>" in screen.text


def test_art_detail_chooses_the_slot_directly():
    screen = render_art_detail(_arts_view(), SENTINEL_ART_IDS["golpe_de_guarda"])
    assert screen.text == (
        "⚔️ <b>Golpe de Guarda</b>\n\n<i>O golpe usa o peso da lâmina e a firmeza da guarda "
        "para atingir o inimigo em um movimento direto.</i>\n\n"
        "⚔️ <b>Dano</b> · <code>110% ATQ</code>\n🎯 <b>Alvo</b> · <code>1 Inimigo</code>\n"
        "⏳ <b>Recarga</b> · <code>2 Rodadas</code>\n\n"
        "🔓 <b>Desbloqueio</b> · <code>Nv. 1</code>\n"
        "🛡️ <b>Arte Ativa</b> · <code>Sentinela</code>"
    )
    assert _labels(screen) == [
        ["1️⃣ Equipar Arte [Slot 1]"],
        ["2️⃣ Equipar Arte [Slot 2]"],
        ["3️⃣ Equipar Arte [Slot 3]"],
        ["↩️ Retornar"],
    ]


@pytest.mark.asyncio
async def test_equipping_an_art_returns_to_arts_and_incompatible_weapon_alerts():
    art_id = VIGIA_ART_IDS["disparo_preciso"]
    compatible = _arts_view(character_class="vigia", available_art_ids=(art_id,))
    equipped = _arts_view(
        character_class="vigia",
        available_art_ids=(art_id,),
        slots=(ActiveArtSlotSnapshot(2, art_id),),
        combat_configuration_version=1,
    )
    arts = AsyncMock()
    arts.view.side_effect = [compatible, equipped]
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(character_progression_router(AsyncMock(), arts, {}))
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    callback = render_art_detail(compatible, art_id).keyboard.inline_keyboard[1][0].callback_data
    await dispatcher.feed_raw_update(bot, callback_update(callback, actor=55, update_id=1))
    arts.equip_art.assert_awaited_once()
    assert arts.equip_art.await_args.args[1:3] == (2, art_id)
    screen = next(
        call.args[1]
        for call in reversed(bot.session.make_request.call_args_list)
        if isinstance(call.args[1], EditMessageText)
    )
    assert "<b>🧿 Artes</b>" in screen.text
    assert "<code>⛔️ Vazio</code>\n<code>⚔️ Disparo Preciso</code>" in screen.text

    incompatible = _arts_view(
        character_class="vigia",
        available_art_ids=(art_id,),
        weapon_incompatible_art_ids=(art_id,),
    )
    arts.reset_mock()
    arts.view.side_effect = [incompatible]
    bot.session.make_request.reset_mock()
    await dispatcher.feed_raw_update(bot, callback_update(callback, actor=55, update_id=2))
    arts.equip_art.assert_not_awaited()
    answer = next(
        call.args[1]
        for call in bot.session.make_request.call_args_list
        if isinstance(call.args[1], AnswerCallbackQuery)
    )
    assert answer.show_alert and "Arco ou Besta" in answer.text


# --- Fluxos completos no Telegram (banco descartável) ------------------------------


def _bot(actor: int) -> Bot:
    bot = Bot("123456:local-test-token")
    ids = iter(range(5000, 5100))

    async def response(_bot, method, **_kwargs):
        if isinstance(method, (SendMessage, EditMessageText)):
            return TelegramMessage(
                message_id=getattr(method, "message_id", None) or next(ids),
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        return True

    bot.session.make_request = AsyncMock(side_effect=response)
    return bot


@pytest.mark.asyncio
async def test_doctrine_create_rename_talents_use_cost_and_delete_flow(database):
    actor, _ = await _seed_road(database, actor=893401)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 15
        character.crowns = 50_000
    service = DoctrineService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(doctrines_router(service, {}))
    bot = _bot(actor)
    update = iter(range(1, 200))

    async def tap(data):
        await dispatcher.feed_raw_update(bot, callback_update(data, actor=actor,
                                                              update_id=next(update)))
        return _last_screen(bot)

    async def tap_label(screen, label):
        return await tap(_button(screen, label).callback_data)

    async def send(text):
        await dispatcher.feed_raw_update(
            bot, _message_update(text, actor=actor, update_id=next(update))
        )
        return _last_screen(bot)

    root = await tap("character:doctrines")
    assert "<b>🗂️ Doutrinas</b>" in root.text
    prompt = await tap_label(root, "➕ Criar")
    assert "✏️ Envie o novo nome da Doutrina." in prompt.text
    root = await send("Build de Caça")  # nome com espaços
    assert "🟢 <code>Build de Caça</code>" in root.text
    await tap_label(root, "➕ Criar")
    root = await send("PvP")
    assert root.text.count("🟢") == 1 and "🔴 <code>PvP" in root.text

    configuration = await tap_label(root, "🔴 PvP")
    assert configuration.text.startswith("<b>⚙️ Configuração</b>")
    editor = await tap_label(configuration, "✏️ Editar")
    await tap_label(editor, "✏️ Nome")
    editor = await send("Arena Alta")
    assert editor.text.startswith("<b>✏️ Editar Doutrina</b>")
    assert [item.name for item in (await service.view(actor)).doctrines] == [
        "Build de Caça",
        "Arena Alta",
    ]

    talents = await tap_label(editor, "🌿 Talentos")
    points = talent_points_at_level(15)
    assert f"🎋 <b>Pontos Disponíveis</b> · <code>{points}</code>" in talents.text
    talents = await tap_label(talents, "✨ Aço")
    assert "✅ <code>Aço Desperto</code>" in talents.text
    assert f"🎋 <b>Pontos Disponíveis</b> · <code>{points - 1}</code>" in talents.text
    talents = await tap_label(talents, "✅ Aço")  # devolve o ponto
    assert "✨ <code>Aço Desperto</code>" in talents.text
    talents = await tap_label(talents, "✨ Aço")
    editor = await tap_label(talents, "↩️ Retornar")
    configuration = await tap_label(editor, "↩️ Retornar")
    assert "1️⃣ <code>Aço Desperto</code>" in configuration.text

    # Sem custo (só acrescenta Talentos): usa direto e volta às Doutrinas.
    root = await tap_label(configuration, "✅ Usar")
    assert "🟢 <code>Arena Alta" in root.text and "🔴 <code>Build de Caça" in root.text

    # Voltar a uma build sem esse Talento cobra a redistribuição: confirmação curta.
    configuration = await tap_label(root, "🔴 Build de Caça")
    confirm = await tap_label(configuration, "✅ Usar")
    cost = 2 * crowns_per_level(15)
    assert f"<code>{cost:,} Coroas".replace(",", ".") in confirm.text
    assert "Caminho" not in confirm.text
    root = await tap_label(confirm, "✅ Confirmar")
    assert "🟢 <code>Build de Caça" in root.text
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.crowns == 50_000 - cost

    configuration = await tap_label(root, "🔴 Arena Alta")
    root = await tap_label(configuration, "🗑️ Excluir")
    assert "Arena Alta" not in root.text
    assert [item.name for item in (await service.view(actor)).doctrines] == ["Build de Caça"]
    for call in bot.session.make_request.call_args_list:
        markup = getattr(call.args[1], "reply_markup", None)
        assert getattr(markup, "force_reply", None) is None
        for row in getattr(markup, "inline_keyboard", None) or ():
            for button in row:
                assert len(button.callback_data.encode()) <= 64


@pytest.mark.asyncio
async def test_history_prompt_replaces_a_pending_doctrine_name_prompt(database):
    actor, _ = await _seed_road(database, actor=893402)
    sessions = database[1]
    doctrines = DoctrineService(sessions, "ocaso")
    surfaces = CharacterSurfacesService(sessions, "ocaso")
    view = await doctrines.view(actor)
    assert await doctrines.begin_name_input(actor, "create", 700, view.configuration_version)
    # O pedido mais recente vence: a História não fica presa ao pedido de nome.
    assert await surfaces.begin_history_input(actor, 0, 701)
    assert await surfaces.save_history(actor, 701, "Uma estrada.") == "saved"
    assert await doctrines.begin_name_input(actor, "create", 702, view.configuration_version)
    mutation = await doctrines.save_name_reply(actor, 702, "Nova")
    assert mutation is not None and mutation.changed
    assert (await surfaces.profile(actor)).history == "Uma estrada."


@pytest.mark.asyncio
async def test_feats_and_titles_reach_details_through_real_callbacks(database):
    actor, _ = await _seed_road(database, actor=893403)
    sessions = database[1]
    from asterion.infrastructure.db.models import Achievement

    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(Achievement(character_id=character.id,
                                achievement_id="feat.tdo.cinzas_na_estrada"))
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(character_surfaces_router(CharacterSurfacesService(sessions,
                                                                                 "ocaso"), {}))
    bot = _bot(actor)
    await dispatcher.feed_raw_update(bot, callback_update("kb:a", actor=actor, update_id=1))
    root = _last_screen(bot)
    await dispatcher.feed_raw_update(
        bot, callback_update(_button(root, "🧭 Exploração").callback_data, actor=actor,
                             update_id=2)
    )
    category = _last_screen(bot)
    assert "🏆 <code>Concluído · Prólogo</code>" in category.text
    await dispatcher.feed_raw_update(
        bot, callback_update(_button(category, "🛤️ Cinzas na Estrada").callback_data,
                             actor=actor, update_id=3)
    )
    detail = _last_screen(bot)
    assert "✨ <b>Raridade</b> · <code>Comum</code>" in detail.text
    assert "🌐 <b>Origem</b> · <code>Prólogo</code>" in detail.text
    assert "✅ Usar" not in _flat(detail)
