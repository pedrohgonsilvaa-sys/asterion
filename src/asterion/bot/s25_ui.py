"""Player-facing screens for S25 — A Ponte que Espera."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s25 import S25View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_STEP_COPY = {
    1: ("Examinar a ponte interditada pelo ponto de observação da Escarpa.", "inspect_bridge"),
    2: ("Localizar o selo físico da última autorização válida.", "locate_seal"),
    3: ("Comparar as duas ordens posteriores que mandam aguardar.", "compare_orders"),
    4: (
        "Verificar estruturalmente que a ponte não deve ser aberta pela missão.",
        "verify_structure",
    ),
    5: ("Retornar a Doren Vask.", "return_to_doren"),
    6: ("Registrar no Códice o trecho Autorização que Nunca Veio.", "record_codex"),
}


def render_s25(view: S25View) -> Screen:
    if view.kind == "giver":
        lines = ["✒️ Doren Vask", "Escarpa da Cinza · Altos Cinéreos", ""]
        rows: list[list[InlineKeyboardButton]] = []
        if view.status == "active":
            lines.append("📜 A Ponte que Espera · Em Andamento")
            rows.append([_button("Ver A Ponte que Espera", "s25:resume")])
        elif view.status == "completed":
            lines.append("✅ A Ponte que Espera · Concluída")
            rows.append([_button("Ver registro da missão", "s25:resume")])
        elif view.reacceptable:
            lines.append("📜 A Ponte que Espera · Disponível para reaceite")
            rows.append(
                [
                    _button(
                        "Reaceitar A Ponte que Espera",
                        f"s25:reaccept:{view.state_version}",
                    )
                ]
            )
        elif view.available:
            lines.append("📜 A Ponte que Espera · Disponível")
            rows.append([_button("Conhecer a missão", "s25:offer")])
        else:
            lines.append("A missão requer P25 concluída e Nv.42.")
        rows.append([_button("← Local Atual", "world:local")])
        return Screen("\n".join(lines), "s25_giver", InlineKeyboardMarkup(inline_keyboard=rows))

    if view.kind == "offer":
        if not (view.available or view.reacceptable):
            return Screen(
                "📜 A Ponte que Espera\n\n"
                "Requer P25 concluída, Nv.42 e presença na Escarpa da Cinza.",
                "s25_offer",
                InlineKeyboardMarkup(
                    inline_keyboard=[[_button("← Doren Vask", "s25:doren")]]
                ),
            )
        action = (
            _button("Reaceitar Missão", f"s25:reaccept:{view.state_version}")
            if view.reacceptable
            else _button("Aceitar Missão", "s25:accept:0")
        )
        text = (
            "📜 A Ponte que Espera\n"
            "Missão Secundária · Altos Cinéreos\n\n"
            "Doren Vask · Escarpa da Cinza\n\n"
            "🎯 Examinar a ponte interditada pelo lado acessível da Escarpa, "
            "comparar os registros e registrar o trecho no Códice.\n\n"
            "📍 Ponto de observação da aproximação da ponte\n\n"
            "🎁 Recompensas\n\n"
            "✨ XP · 22.280\n"
            "🪙 Coroas · 370"
        )
        return Screen(
            text,
            "s25_offer",
            InlineKeyboardMarkup(
                inline_keyboard=[[action], [_button("← Doren Vask", "s25:doren")]]
            ),
        )

    if view.status == "completed" or view.kind == "completed":
        text = (
            "✅ A Ponte que Espera · Concluída\n"
            "Missão Secundária · Altos Cinéreos\n\n"
            "✨ XP · 22.280\n"
            "🪙 Coroas · 370\n\n"
            "📖 Códice · Infraestrutura de Sustentação\n"
            "📄 Trecho · Autorização que Nunca Veio"
        )
        return Screen(
            text,
            "s25_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n"
            "📜 A Ponte que Espera\n\n"
            "Os objetivos temporários serão reiniciados. Descobertas, registros do "
            "Códice e claims permanentes permanecem preservados.",
            "s25_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s25:abandon_confirm:{view.state_version}")],
                    [_button("← A Ponte que Espera", "s25:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 A Ponte que Espera · Abandonada\n\n"
            "Os registros permanentes já obtidos permanecem preservados.",
            "s25_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Doren Vask", "s25:doren")]]),
        )

    objective = _STEP_COPY.get(view.step)
    text = (
        "📜 A Ponte que Espera · Em Andamento\n"
        "Altos Cinéreos · Escarpa da Cinza\n\n"
        f"🎯 Etapa {min(view.step, 6)}/6 · "
        f"{objective[0] if objective else 'Retome a etapa atual.'}\n\n"
        "🎁 22.280 XP · 370 Coroas"
    )
    version = view.state_version
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "objective" and objective is not None:
        rows.append([_button("Executar etapa", f"s25:action:{version}:{objective[1]}")])
    else:
        rows.append([_button("Ver objetivo", "s25:objective")])
    rows.append(
        [
            _button(
                "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                f"s25:track:{version}",
            )
        ]
    )
    rows.extend(
        [
            [_button("Abandonar Missão", "s25:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    return Screen(text, "s25_detail", InlineKeyboardMarkup(inline_keyboard=rows))
