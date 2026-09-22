"""Player-facing screens for the Estrada loop."""
# ruff: noqa: E501

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.road import ROAD, RoadView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def render_road(view: RoadView) -> Screen:
    if view.kind == "combat" and view.combat is not None:
        return render_combat(
            CombatView(
                view.activity_id,
                view.encounter_id,
                view.character_id,
                view.combat,
                "road",
                0,
                "road",
            )
        )
    if view.kind == "hunt_defeat":
        text = (
            "💀 Derrota\n\n🔥 Braseiro da Estrada\nEstrada das Cinzas · Terras do Ocaso\n\n"
            "❤️ HP · Restaurado\n\n🦌 Caçada · Encerrada"
        )
        keyboard = [
            [InlineKeyboardButton(text="Caçar Novamente", callback_data="road:prepare")],
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        return Screen(text, "road_defeat", InlineKeyboardMarkup(inline_keyboard=keyboard))
    if view.kind == "hunt_prepare":
        text = (
            "🦌 Caçada\n\n🔥 Estrada das Cinzas\nTerras do Ocaso · Nv. 1–10\n\n"
            f"👤 {escape(view.name or 'Personagem')}\n❤️ <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ Vigor · <code>{view.vigor} / {view.max_vigor}</code>\n\n👤 Grupo\n⚔️ Escolha o formato da Caçada."
        )
        keyboard = [
            [InlineKeyboardButton(text="[1] Solo", callback_data="road:hunt")],
            [InlineKeyboardButton(text="[2] Grupo", callback_data="menu:noop")],
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        return Screen(text, "hunt_prepare", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "hunt_victory":
        text = "🏆 Vitória\n\n🦌 Caçada concluída"
        if view.creature:
            text += f"\n🐾 {escape(view.creature)}"
        if view.variant:
            text += f"\n🧬 Variante · {escape(view.variant)}"
        if view.reward_lines:
            text += "\n\n" + "\n".join(view.reward_lines)
        keyboard = [
            [InlineKeyboardButton(text="Caçar Novamente", callback_data="road:prepare")],
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        return Screen(text, "road_victory", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "exploration":
        text = f"🧭 Desbravar\n\n🔥 Estrada das Cinzas\nTerras do Ocaso · Nv. 1–10\n\n{escape(view.result_text or '')}"
        buttons = [
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        if view.retry_available:
            buttons.insert(0, [InlineKeyboardButton(text="Desbravar Novamente", callback_data="road:explore")])
        return Screen(
            text, "exploration", InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML"
        )
    if view.kind == "explore_prepare":
        text = (
            "🧭 Desbravar\n\n🔥 Estrada das Cinzas · Local Atual\n"
            "Terras do Ocaso · Nv. 1–10\n\n👤 Solo\n"
            f"❤️ <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ 4 Vigor quando a economia for concedida · <code>{view.vigor} / {view.max_vigor}</code>"
        )
        keyboard = [
            [InlineKeyboardButton(text="Desbravar", callback_data="road:explore:start")],
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        return Screen(text, "explore_prepare", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "explore_cooldown":
        text = (
            "🧭 Desbravar\n\n"
            "⏳ Desbravar · Disponível em "
            f"<code>{escape(view.result_text or '00:00')}</code>"
        )
        return Screen(
            text,
            "explore_cooldown",
            InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")]]),
            parse_mode="HTML",
        )
    if view.kind == "explore_limit":
        text = (
            "🧭 Desbravar\n\n"
            "🔒 Desbravar · Limite recente atingido\n"
            f"⏳ Disponível em · <code>{escape(view.result_text or '00:00')}</code>"
        )
        return Screen(
            text,
            "explore_limit",
            InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")]]),
            parse_mode="HTML",
        )
    if view.location == ROAD:
        round_line = "[Ronda ×5] [Ronda ×10] [Ronda ×20]" if view.familiar else "🔒 Ronda de Caça · Vença uma Caçada neste Local"
        text = (
            "🔥 Estrada das Cinzas · Local Atual\nTerras do Ocaso · Nv. 1–10\n\n"
            "🔥 Braseiro · Descoberto\n"
            + ("🧭 Desbravar · Disponível\n" if view.explore_available else "⏳ Desbravar · Em recarga\n")
            + "🦌 Caçada · Disponível\n\n"
            + round_line
        )
        keyboard = [
            [InlineKeyboardButton(text="Caçar", callback_data="road:prepare")],
            *([[InlineKeyboardButton(text="Desbravar", callback_data="road:explore")]] if view.explore_available else []),
            *([[InlineKeyboardButton(text="Ronda ×5", callback_data="menu:noop"), InlineKeyboardButton(text="Ronda ×10", callback_data="menu:noop"), InlineKeyboardButton(text="Ronda ×20", callback_data="menu:noop")]] if view.familiar else []),
            [
                InlineKeyboardButton(
                    text="Travessia dos Braseiros", callback_data="road:travel:refuge"
                )
            ],
            [InlineKeyboardButton(text="← Terras do Ocaso", callback_data="menu:back")],
        ]
    else:
        text = "🔥 Braseiro do Refúgio\nRefúgio do Ocaso · Terras do Ocaso"
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Travessia dos Braseiros", callback_data="road:travel:road"
                )
            ],
            [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
        ]
    return Screen(text, "road", InlineKeyboardMarkup(inline_keyboard=keyboard))
