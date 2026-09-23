"""Player-facing P2 — Fuligem sem Fogo screens."""
# ruff: noqa: E501

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p2 import CHARNECA, REFUGE, ROAD, P2View
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _rewards() -> str:
    return (
        "🎁 Recompensas\n\n"
        "✨ XP · 3.300\n"
        "🪙 Coroas · 140\n"
        "⛏️ Ferro de Fuligem · 1\n"
        "🌿 Erva Cinzenta · 2\n"
        "💧 Resíduo do Ocaso · 1"
    )


def _objective(view: P2View) -> tuple[str, str]:
    p = view.progress or {}
    if view.step == 1:
        return "Viajar até a Charneca da Fuligem", CHARNECA
    if view.step == 2:
        return f"Pontos de Fuligem · {len(set(p.get('points', [])))}/3", CHARNECA
    if view.step == 3:
        return "Derrotar o inimigo roteirizado da Charneca", CHARNECA
    if view.step == 4:
        return "Examinar a Pedra Marcada", CHARNECA
    if view.step == 5:
        return "Levar um registro da marca a Oren Cal", REFUGE
    return "Reportar a situação a Alda Veyr", REFUGE


def render_p2(view: P2View) -> Screen:
    if view.combat is not None:
        return render_combat(
            CombatView(
                view.activity_id,
                view.encounter_id,
                view.character_id,
                view.combat,
                "p2",
                0,
                "p2",
            )
        )

    version = view.state_version
    p = view.progress or {}

    if view.kind == "alda":
        lines = ["🪖 Alda Veyr", "Refúgio do Ocaso · Terras do Ocaso"]
        keyboard: list[list[InlineKeyboardButton]] = []
        if view.status == "completed":
            lines.extend(["", "✅ Fuligem sem Fogo · Concluída"])
        elif view.status == "active":
            lines.extend(["", "📜 Fuligem sem Fogo · Em Andamento"])
            if view.step == 6:
                lines.extend(["", "🎯 Objetivo · Reportar a situação a Alda Veyr"])
                keyboard.append(
                    [_button("Reportar a Alda", f"p2:{version}:complete")]
                )
        elif view.available:
            lines.extend(["", "📜 Fuligem sem Fogo · Disponível", "Missão Principal"])
            keyboard.append([_button("Fuligem sem Fogo", "p2:offer")])
        else:
            lines.extend(["", "📜 Fuligem sem Fogo · Indisponível", "🔒 Requer · Nv. 3"])
        keyboard.append([_button("← Refúgio do Ocaso", "world:map:local:refuge")])
        return Screen(
            "\n".join(lines),
            "alda_veyr",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.kind == "offer":
        text = (
            "📜 Fuligem sem Fogo\n"
            "Missão Principal · Terras do Ocaso\n\n"
            "<i>— Fuligem sem fogo significa que alguém chegou antes de nós — ou que estamos olhando para o problema errado.</i>\n\n"
            "🎯 Objetivo · Viajar até a Charneca da Fuligem\n\n"
            "📍 Charneca da Fuligem · Terras do Ocaso\n\n"
            f"{_rewards()}"
        )
        return Screen(
            text,
            "p2_offer",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Aceitar Missão", "p2:accept")],
                    [_button("← Alda Veyr", "p2:alda")],
                ]
            ),
            parse_mode="HTML",
        )

    if view.kind == "oren":
        lines = ["✒️ Oren Cal", "Refúgio do Ocaso · Terras do Ocaso"]
        keyboard = []
        if view.status == "active" and view.step == 5:
            lines.extend(
                [
                    "",
                    "📜 Fuligem sem Fogo · Em Andamento",
                    "",
                    "🎯 Objetivo · Levar um registro da marca a Oren Cal",
                ]
            )
            keyboard.append(
                [_button("Entregar Registro", f"p2:{version}:oren:deliver")]
            )
        keyboard.append([_button("← Refúgio do Ocaso", "world:map:local:refuge")])
        return Screen(
            "\n".join(lines),
            "oren_cal",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.kind == "oren_reported":
        text = (
            "✒️ Oren Cal\n"
            "Refúgio do Ocaso · Terras do Ocaso\n\n"
            "<i>— Esta marca não é decoração. Também não vou chamá-la de escrita até termos prova.</i>\n\n"
            "📜 Fuligem sem Fogo · Em Andamento\n\n"
            "🎯 Objetivo · Reportar a situação a Alda Veyr"
        )
        return Screen(
            text,
            "oren_cal",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Alda Veyr", "p2:alda")],
                    [_button("← Refúgio do Ocaso", "world:map:local:refuge")],
                ]
            ),
            parse_mode="HTML",
        )

    if view.kind == "completed" or view.status == "completed":
        text = (
            "✅ Fuligem sem Fogo · Concluída\n"
            "Missão Principal · Terras do Ocaso\n\n"
            f"{_rewards()}\n\n"
            "📖 Códice · Marcas na Fuligem"
        )
        return Screen(
            text,
            "p2_completed",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("← Refúgio do Ocaso", "world:map:local:refuge")]
                ]
            ),
        )

    if view.kind in {"objective", "arrival"}:
        return _render_objective(view)

    objective, local = _objective(view)
    text = (
        "📜 Fuligem sem Fogo · Em Andamento\n"
        "Missão Principal · Terras do Ocaso\n\n"
        f"🎯 Objetivo · {objective}\n\n"
        f"📍 {local} · Terras do Ocaso\n\n"
        f"{_rewards()}"
    )
    keyboard = []
    charneca_known = "tdo.location.charneca_da_fuligem" in view.known_locations
    if view.step == 1 and not charneca_known:
        keyboard.append([_button("Ir para Charneca da Fuligem", "world:walk:charneca")])
    elif local in {ROAD, REFUGE, CHARNECA}:
        keyboard.append([_button("Ver no Mapa", "world:map")])
    keyboard.append([_button("Ver Objetivo", "p2:objective")])
    keyboard.append([_button("← Missões", "world:missions")])
    return Screen(
        text,
        "p2_detail",
        InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


def _render_objective(view: P2View) -> Screen:
    version = view.state_version
    p = view.progress or {}

    if view.step == 1:
        text = (
            "📜 Fuligem sem Fogo · Em Andamento\n"
            "Missão Principal · Terras do Ocaso\n\n"
            "🎯 Objetivo · Viajar até a Charneca da Fuligem\n\n"
            "📍 Charneca da Fuligem · Terras do Ocaso"
        )
        return Screen(
            text,
            "p2_objective",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Ir para Charneca da Fuligem", "world:walk:charneca")],
                    [_button("← Missões", "world:missions")],
                ]
            ),
        )

    if view.step == 2:
        points = {int(value) for value in p.get("points", [])}
        count = len(points)
        lines = []
        if view.kind == "arrival":
            lines.extend(
                [
                    "🌫️ Charneca da Fuligem · Local Atual",
                    "Terras do Ocaso · Nv. 3–5",
                    "",
                    "🗺️ Local · Descoberto",
                    "",
                ]
            )
        lines.extend(
            [
                "📜 Fuligem sem Fogo · Em Andamento",
                "Charneca da Fuligem · Terras do Ocaso",
                "",
                f"🎯 Pontos de Fuligem · {count}/3",
                "",
            ]
        )
        pending = []
        for point in (1, 2, 3):
            if point in points:
                lines.append(f"{point} ✅ Ponto de Fuligem · Examinado")
            else:
                lines.append(f"{point} 📍 Ponto de Fuligem · Pendente")
                pending.append(_button(str(point), f"p2:{version}:point:{point}"))
        keyboard = []
        if view.location == CHARNECA and pending:
            keyboard.append(pending)
        elif view.location != CHARNECA:
            keyboard.append([_button("Ver no Mapa", "world:map")])
        keyboard.append([_button("← Missões", "world:missions")])
        return Screen(
            "\n".join(lines),
            "p2_charneca",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.step == 3:
        if p.get("defeat"):
            text = (
                "💀 Derrota\n\n"
                "🔥 Braseiro do Refúgio\n"
                "Refúgio do Ocaso · Terras do Ocaso\n\n"
                "❤️ HP · Restaurado\n\n"
                "📜 Fuligem sem Fogo · Em Andamento\n\n"
                "🎯 Objetivo · Derrotar o inimigo roteirizado da Charneca"
            )
            return Screen(
                text,
                "p2_defeat",
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [_button("Ver no Mapa", "world:map")],
                        [_button("← Missões", "world:missions")],
                    ]
                ),
            )
        return Screen(
            "📜 Fuligem sem Fogo · Em Andamento\n"
            "Charneca da Fuligem · Terras do Ocaso\n\n"
            "🎯 Objetivo · Derrotar o inimigo roteirizado da Charneca",
            "p2_objective",
            InlineKeyboardMarkup(
                inline_keyboard=[[_button("← Missões", "world:missions")]]
            ),
        )

    if view.step == 4:
        text = (
            "📜 Fuligem sem Fogo · Em Andamento\n"
            "Charneca da Fuligem · Terras do Ocaso\n\n"
            "🪨 Pedra Marcada\n\n"
            "🎯 Objetivo · Examinar a Pedra Marcada"
        )
        keyboard = []
        if view.location == CHARNECA:
            keyboard.append(
                [_button("Examinar Pedra Marcada", f"p2:{version}:stone")]
            )
        else:
            keyboard.append([_button("Ver no Mapa", "world:map")])
        keyboard.append([_button("← Missões", "world:missions")])
        return Screen(
            text,
            "p2_stone",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.step == 5:
        text = (
            "📜 Fuligem sem Fogo · Em Andamento\n"
            "Missão Principal · Terras do Ocaso\n\n"
            "🎯 Objetivo · Levar um registro da marca a Oren Cal\n\n"
            "📍 Refúgio do Ocaso · Terras do Ocaso"
        )
        keyboard = [[_button("Ver no Mapa", "world:map")]]
        if view.location == REFUGE:
            keyboard.insert(0, [_button("Oren Cal", "p2:oren")])
        keyboard.append([_button("← Missões", "world:missions")])
        return Screen(
            text,
            "p2_objective",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    text = (
        "📜 Fuligem sem Fogo · Em Andamento\n"
        "Missão Principal · Terras do Ocaso\n\n"
        "🎯 Objetivo · Reportar a situação a Alda Veyr\n\n"
        "📍 Refúgio do Ocaso · Terras do Ocaso"
    )
    keyboard = []
    if view.location == REFUGE:
        keyboard.append([_button("Alda Veyr", "p2:alda")])
    else:
        keyboard.append([_button("Ver no Mapa", "world:map")])
    keyboard.append([_button("← Missões", "world:missions")])
    return Screen(
        text,
        "p2_objective",
        InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
