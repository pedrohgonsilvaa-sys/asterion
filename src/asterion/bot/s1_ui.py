"""Player-facing S1 — Luzes sob as Cinzas screens."""
# ruff: noqa: E501

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s1 import REFUGE, ROAD, S1View
from asterion.bot.creation_ui import Screen
from asterion.bot.narrative_choice_ui import immediate_reaction, narrative_option_rows


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _detail_objective(view: S1View) -> str:
    if view.step == 1:
        count = len(set(view.progress.get("points", [])))
        return f"🎯 Pontos Marcados · {count}/3"
    if view.step == 2:
        return "🎯 Objetivo · Examinar cinzas sem fonte de calor recente"
    if view.step == 3:
        return "🎯 Objetivo · Observar uma luz distante"
    return "🎯 Objetivo · Retornar a Oren Cal"


def render_s1(view: S1View) -> Screen:
    version = view.state_version

    if view.kind == "oren":
        lines = ["✒️ Oren Cal", "Refúgio do Ocaso · Terras do Ocaso"]
        keyboard: list[list[InlineKeyboardButton]] = []
        if view.status == "completed":
            lines.extend(["", "✅ Luzes sob as Cinzas · Concluída"])
        elif view.status == "active":
            lines.extend(["", "🕯️ Luzes sob as Cinzas · Em Andamento"])
            if view.step == 4:
                lines.extend(["", "🎯 Objetivo · Retornar a Oren Cal"])
                choice_rows = narrative_option_rows(view.narrative, f"s1:{version}:o")
                if choice_rows:
                    keyboard.extend(choice_rows)
                else:
                    keyboard.append([_button("Falar com Oren", f"s1:{version}:complete")])
        elif view.reacceptable:
            lines.extend(["", "🕯️ Luzes sob as Cinzas · Reaceitável", "Missão Secundária"])
            keyboard.append([_button("Luzes sob as Cinzas", "s1:offer")])
        elif view.available:
            lines.extend(["", "🕯️ Luzes sob as Cinzas · Disponível", "Missão Secundária"])
            keyboard.append([_button("Luzes sob as Cinzas", "s1:offer")])
        keyboard.append([_button("← Refúgio do Ocaso", "road:local")])
        return Screen(
            "\n".join(lines),
            "oren_cal",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.kind == "offer":
        reaccept = view.reacceptable
        action = (
            _button("Reaceitar Missão", "s1:reaccept")
            if reaccept
            else _button("Aceitar Missão", "s1:accept")
        )
        text = (
            "🕯️ Luzes sob as Cinzas\n"
            "Missão Secundária · Terras do Ocaso\n\n"
            "<i>— Luz é uma coisa simples quando há fogo. Quando não há, ela se torna uma pergunta.</i>\n\n"
            "🎯 Objetivo · Investigar três pontos marcados da Estrada\n\n"
            "📍 Estrada das Cinzas · Terras do Ocaso\n\n"
            "🎁 Recompensas\n\n"
            "✨ XP · 1.140\n"
            "🪙 Coroas · 60"
        )
        return Screen(
            text,
            "s1_offer",
            InlineKeyboardMarkup(
                inline_keyboard=[[action], [_button("← Oren Cal", "s1:oren")]]
            ),
            parse_mode="HTML",
        )

    if view.kind == "abandon_confirm":
        text = (
            "⚠️ Abandonar Missão\n\n"
            "🕯️ Luzes sob as Cinzas\n\n"
            "Progresso · Reiniciado\n"
            "Reaceitação · Disponível com Oren Cal\n\n"
            "Etapa, contadores e progresso transitório desta missão serão reiniciados.\n\n"
            "Registros permanentes já obtidos permanecem preservados."
        )
        return Screen(
            text,
            "s1_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s1:{version}:abandon:confirm")],
                    [_button("← Luzes sob as Cinzas", "s1:detail")],
                ]
            ),
        )

    if view.kind == "completed" or view.status == "completed":
        lines = [
            "✅ Luzes sob as Cinzas · Concluída",
            "Missão Secundária · Terras do Ocaso",
            "",
            "🎁 Recompensas",
            "",
            "✨ XP · 1.140",
            "🪙 Coroas · 60",
            "",
            "📖 Códice · Estrada das Cinzas atualizada",
        ]
        if view.fragment_new_this_attempt:
            lines.append("📖 Trecho · Luzes na Estrada")
        return Screen(
            "\n".join(lines),
            "s1_completed",
            InlineKeyboardMarkup(
                inline_keyboard=[[_button("← Refúgio do Ocaso", "road:local")]]
            ),
        )

    if view.kind == "objective":
        return _render_objective(view)

    # Active mission detail.
    text = (
        "🕯️ Luzes sob as Cinzas · Em Andamento\n"
        "Missão Secundária · Terras do Ocaso\n\n"
        f"{_detail_objective(view)}\n\n"
        f"📍 {ROAD if view.step < 4 else REFUGE} · Terras do Ocaso\n\n"
        "🎁 Recompensas\n\n"
        "✨ XP · 1.140\n"
        "🪙 Coroas · 60"
    )
    track = (
        _button("Deixar de Acompanhar", f"s1:{version}:track")
        if view.tracked
        else _button("Acompanhar", f"s1:{version}:track")
    )
    keyboard = [
        [track],
        [
            _button("Ver Objetivo", "s1:objective"),
            _button("Ver no Mapa", "world:map"),
        ],
        [_button("Abandonar Missão", "s1:abandon")],
        [_button("← Missões", "world:missions")],
    ]
    return Screen(
        text,
        "s1_detail",
        InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


def _render_objective(view: S1View) -> Screen:
    version = view.state_version
    if view.step == 1:
        points = {int(value) for value in view.progress.get("points", [])}
        count = len(points)
        lines = [
            "🕯️ Luzes sob as Cinzas · Em Andamento",
            "Estrada das Cinzas · Terras do Ocaso",
            "",
            f"🎯 Pontos Marcados · {count}/3",
        ]
        keyboard: list[list[InlineKeyboardButton]] = []
        if view.location == ROAD:
            buttons = []
            for point in (1, 2, 3):
                if point in points:
                    lines.append(f"{point} ✅ Ponto Marcado · Investigado")
                else:
                    lines.append(f"{point} 📍 Ponto Marcado · Pendente")
                    buttons.append(_button(str(point), f"s1:{version}:point:{point}"))
            if buttons:
                keyboard.append(buttons)
        else:
            keyboard.append([_button("Ver no Mapa", "world:map")])
        keyboard.append([_button("← Luzes sob as Cinzas", "s1:detail")])
        return Screen(
            "\n".join(lines),
            "s1_objective",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.step == 2:
        text = (
            "🕯️ Luzes sob as Cinzas · Em Andamento\n"
            "Estrada das Cinzas · Terras do Ocaso\n\n"
            "🎯 Objetivo · Examinar cinzas sem fonte de calor recente"
        )
        keyboard = (
            [[_button("Examinar Cinzas", f"s1:{version}:ashes")]]
            if view.location == ROAD
            else [[_button("Ver no Mapa", "world:map")]]
        )
        keyboard.append([_button("← Luzes sob as Cinzas", "s1:detail")])
        return Screen(
            text,
            "s1_objective",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.step == 3:
        text = (
            "🕯️ Luzes sob as Cinzas · Em Andamento\n"
            "Estrada das Cinzas · Terras do Ocaso\n\n"
            "🎯 Objetivo · Observar uma luz distante"
        )
        keyboard = (
            [[_button("Observar Luz", f"s1:{version}:light")]]
            if view.location == ROAD
            else [[_button("Ver no Mapa", "world:map")]]
        )
        keyboard.append([_button("← Luzes sob as Cinzas", "s1:detail")])
        return Screen(
            text,
            "s1_objective",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    text = (
        "🕯️ Luzes sob as Cinzas · Em Andamento\n"
        "Refúgio do Ocaso · Terras do Ocaso\n\n"
        "🎯 Objetivo · Retornar a Oren Cal"
    )
    reaction = immediate_reaction(view.narrative)
    if reaction:
        text += f"\n\n{reaction}"
    keyboard = narrative_option_rows(view.narrative, f"s1:{version}")
    if view.location != REFUGE:
        keyboard.append([_button("Ver no Mapa", "world:map")])
    keyboard.append([_button("← Luzes sob as Cinzas", "s1:detail")])
    return Screen(
        text,
        "s1_objective",
        InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


def render_missions_after_s1_abandon() -> Screen:
    text = (
        "📜 Missões\n\n"
        "Objetivos, promessas e caminhos ainda inacabados acompanham sua jornada por Asterion."
    )
    return Screen(
        text,
        "missions",
        InlineKeyboardMarkup(
            inline_keyboard=[[_button("← Aventura", "world:adventure")]]
        ),
    )
