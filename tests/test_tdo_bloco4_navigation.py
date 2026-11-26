"""Bloco 4 (TdO v1.0.18): navegação, Refúgio no lugar do Menu Principal, Caçar e textos.

Fontes: UI v1.6.2 seção 66 e Fonte Regional TdO v1.0.18 seção 33.
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.road import CAMARA, CHARNECA, REFUGE, ROAD, RoadView
from asterion.application.world import WorldView
from asterion.bot.groups_ui import render_hunt_unlock_blocked
from asterion.bot.p2_ui import render_p2
from asterion.bot.p3_ui import render_p3
from asterion.bot.p4_ui import render_p4
from asterion.bot.p6_ui import render_p6
from asterion.bot.road_ui import render_current_local, render_road
from asterion.bot.tdo_hub_ui import TEXT_EXPLORE_FOR_PLACE, render_hunt_choice
from asterion.bot.tdo_navigation_labels import (
    BACK_TO_REFUGE_LABEL,
    TDO_REGION,
    TdoReturnLabelMiddleware,
    has_legacy_return,
    relabel_returns_to_refuge,
)
from asterion.bot.world_ui import render_refuge_dashboard

SRC = Path(__file__).resolve().parents[1] / "src" / "asterion" / "bot"


class _View(SimpleNamespace):
    """View mínima: atributo não informado vale None."""

    def __getattr__(self, name):
        return None


def _markup(*rows):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
            for row in rows
        ]
    )


def _pairs(markup):
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


async def _run(region, method):
    sent = {}

    async def make_request(bot, call):
        sent["method"] = call
        return "ok"

    async def region_of(chat_id):
        return region

    middleware = TdoReturnLabelMiddleware(region_of)
    await middleware(make_request, None, method)
    return sent["method"]


def _send(markup, chat_id=10):
    return SendMessage(chat_id=chat_id, text="t", reply_markup=markup)


# --- retorno nas Terras do Ocaso (66.1 item 6) -----------------------------


def test_tdo_returns_use_voltar_ao_refugio_and_keep_callbacks():
    markup = _markup(
        [("← Menu", "menu:back")],
        [("← Aventura", "adv:hub")],
        [("← Campanha", "world:adventure")],
        [("Mercado", "mkt:root")],
    )
    sent = asyncio.run(_run(TDO_REGION, _send(markup)))
    assert _pairs(sent.reply_markup) == [
        (BACK_TO_REFUGE_LABEL, "menu:back"),
        (BACK_TO_REFUGE_LABEL, "adv:hub"),
        (BACK_TO_REFUGE_LABEL, "world:adventure"),
        ("Mercado", "mkt:root"),
    ]


def test_tdo_relabel_also_applies_to_edits():
    markup = _markup([("← Menu", "menu:back")])
    call = EditMessageText(chat_id=10, message_id=1, text="t", reply_markup=markup)
    sent = asyncio.run(_run(TDO_REGION, call))
    assert _pairs(sent.reply_markup) == [(BACK_TO_REFUGE_LABEL, "menu:back")]


def test_other_regions_keep_menu_aventura_campanha_unchanged():
    markup = _markup(
        [("← Menu", "menu:back")],
        [("← Aventura", "adv:hub")],
        [("← Campanha", "world:adventure")],
    )
    for region in ("Vales dos Enforcados", "Planícies de Nareth", None):
        sent = asyncio.run(_run(region, _send(markup)))
        assert sent.reply_markup is markup


def test_relabel_never_touches_unrelated_buttons():
    markup = _markup(
        [("← Menu", "outro:callback"), ("← Missões", "world:missions")],
        [("← Local", "world:local")],
    )
    assert not has_legacy_return(markup)
    sent = asyncio.run(_run(TDO_REGION, _send(markup)))
    assert sent.reply_markup is markup
    assert _pairs(relabel_returns_to_refuge(markup)) == _pairs(markup)


def test_relabel_ignores_group_chats_and_lookup_failures():
    markup = _markup([("← Menu", "menu:back")])
    assert asyncio.run(_run(TDO_REGION, _send(markup, chat_id=-100))).reply_markup is markup

    async def make_request(bot, call):
        return call

    async def broken(chat_id):
        raise RuntimeError("db down")

    method = _send(markup)
    asyncio.run(TdoReturnLabelMiddleware(broken)(make_request, None, method))
    assert method.reply_markup is markup


# --- Refúgio no lugar do Menu Principal (66.1 itens 1-4) --------------------


def _world_view():
    return WorldView(
        kind="menu",
        character_id=uuid4(),
        name="Heroa",
        race="remanescente",
        character_class="sentinela",
        hp=100,
        max_hp=100,
        vigor=100,
        max_vigor=100,
        xp=0,
        region=TDO_REGION,
        location=REFUGE,
        quest_title=None,
    )


def test_refuge_keyboard_follows_source_order_and_grouping():
    screen = render_refuge_dashboard(
        _world_view(),
        route_destinations=(ROAD, CHARNECA, CAMARA),
        explore_remaining=1,
        can_hunt=True,
        known_dungeons=True,
    )
    rows = [[b.text for b in row] for row in screen.keyboard.inline_keyboard]
    # HUD congelado: Menu Principal em duas colunas, sem Locais avulsos nem NPCs.
    assert rows[0] == ["⛰️ Desbravar", "🗺️ Mapa"]
    assert rows[-1] == ["🌐 Comunidade", "⚙️ Configurações"]
    flat = [text for row in rows for text in row]
    for absent in ("Campanha", "Aventura", "← Menu", "Local Atual", "Alda Veyr"):
        assert absent not in flat
    assert "Travessia" not in screen.text


def test_menu_principal_rendering_is_not_used_inside_tdo_refuge_screen():
    screen = render_refuge_dashboard(
        _world_view(),
        route_destinations=(ROAD,),
        explore_remaining=0,
        can_hunt=True,
        known_dungeons=False,
    )
    callbacks = [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]
    # entradas Campanha e Aventura do Menu Principal geral não existem no Refúgio
    assert "world:adventure" not in callbacks
    assert "adv:hub" not in callbacks
    assert screen.image_key == "local:Refúgio do Ocaso"


def test_outside_tdo_local_screen_keeps_campanha_return():
    view = RoadView("vde_garganta", uuid4(), "Garganta dos Laços", name="Heroa", hp=10, max_hp=10)
    screen = render_current_local(view)
    pairs = [(b.text, b.callback_data) for row in screen.keyboard.inline_keyboard for b in row]
    assert ("← Campanha", "world:adventure") in pairs
    assert all(text != BACK_TO_REFUGE_LABEL for text, _ in pairs)


# --- Caçar (66.1 item 3, 66.4) ---------------------------------------------


def test_hunt_choice_lists_hunt_locals_then_back_to_refuge():
    screen = render_hunt_choice((ROAD, CHARNECA, CAMARA))
    pairs = [(b.text, b.callback_data) for row in screen.keyboard.inline_keyboard for b in row]
    assert pairs == [
        ("🔥 Estrada das Cinzas", "road:route:road"),
        ("🌫️ Charneca da Fuligem", "road:route:charneca"),
        (BACK_TO_REFUGE_LABEL, "world:local"),
    ]


def test_group_hunt_block_cites_every_member_without_level_number():
    one = render_hunt_unlock_blocked(["Ana"]).text
    many = render_hunt_unlock_blocked(["Ana", "Bia", "Caio"]).text
    assert one.startswith("⚠ Caçada indisponível\n\nAna ainda não cumpre o nível mínimo")
    assert "Ana, Bia e Caio ainda não cumprem o nível mínimo de nenhuma criatura" in many
    assert "nada para caçar" not in many
    assert not any(ch.isdigit() for ch in many)


# --- Explorar e Missão aguardando Local (66.2) ------------------------------


def test_waiting_texts_use_the_source_text():
    assert TEXT_EXPLORE_FOR_PLACE == "Explore para encontrar este lugar."
    base = dict(
        awaiting_exploration=True,
        state_version=1,
        location=REFUGE,
        status="active",
        step=1,
        title="x",
    )
    screens = {
        "p2": render_p2(_View(kind="travel", **base)),
        "p3": render_p3(_View(kind="travel", **base)),
        "p4": render_p4(_View(kind="enter_ruins", **base)),
        "p6": render_p6(_View(kind="enter_chamber", **base)),
    }
    for name, screen in screens.items():
        assert TEXT_EXPLORE_FOR_PLACE in screen.text, name
        assert "Use Explorar" not in screen.text, name
        assert "tdo:explore" in [
            b.callback_data for row in screen.keyboard.inline_keyboard for b in row
        ], name


def test_map_has_no_removed_level_lock_text():
    source = (SRC / "world_handlers.py").read_text(encoding="utf-8")
    assert "P4 concluída e Nv. 8+" not in source
    assert "P4 concluída + Nv. 8+" not in source


# --- Tela de Vitória da Caçada (UI v1.6.2, 47.3) ---------------------------


def _victory(**kwargs):
    base = dict(
        activity_id=uuid4(),
        name="Heroa",
        creature="Cão Cinéreo",
        reward_lines=("✨ XP · 120", "🪙 Coroas · 15"),
    )
    base.update(kwargs)
    return RoadView("hunt_victory", uuid4(), CHARNECA, **base)


def test_hunt_victory_follows_47_3_structure():
    view = _victory()
    screen = render_road(view)
    # Bloco UI 1 §4 substitui a 47.3: narrativa + Recompensas sem linha vazia.
    assert screen.text.startswith("🏆 <b>Vitória</b>\n\n<i>O confronto chega ao fim")
    assert screen.text.endswith("🎁 <b>Recompensas:</b>\n✨ XP · 120\n🪙 Coroas · 15")
    pairs = [(b.text, b.callback_data) for row in screen.keyboard.inline_keyboard for b in row]
    assert pairs == [("🎯 Caçar novamente", "tdo:hunt:manual"), ("↩️ Voltar", "tdo:hunt")]
    # nada de texto inventado: sem "Caçada concluída" nem flavor
    assert "Caçada concluída" not in screen.text


def test_hunt_victory_without_rewards_omits_the_block_and_invents_no_flavor():
    screen = render_road(_victory(reward_lines=()))
    assert "Recompensas" not in screen.text


def test_hunt_victory_group_keeps_no_repeat_button():
    screen = render_road(_victory(combat_context="group_hunt"))
    texts = [b.text for row in screen.keyboard.inline_keyboard for b in row]
    assert texts == ["← Caçada"]


def test_hunt_victory_back_button_leaves_other_screens_untouched():
    # o botão do Local em derrota continua sendo o retorno ao Local
    screen = render_road(RoadView("hunt_defeat", uuid4(), CHARNECA))
    assert "Vitória" not in screen.text
