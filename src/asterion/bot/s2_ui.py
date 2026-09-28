"""Player-facing S2 screens reconstructed from S2View."""
# ruff: noqa: E501

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.road import CHARNECA, REFUGE
from asterion.application.s2 import S2View
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _objective(view: S2View) -> str:
    if view.step == 1:
        return "🎯 Encontrar o acampamento abandonado"
    if view.step == 2:
        count = len(set(view.progress.get("vestiges", [])))
        return f"🎯 Examinar vestígios pessoais · {count}/3"
    if view.step == 3:
        return "🎯 Derrotar o Peregrino Calcinado"
    if view.step == 5:
        return "🎯 Recuperar o fragmento de registro carbonizado"
    return "🎯 Retornar a Oren Cal"


def render_s2(view: S2View) -> Screen:
    if view.kind == "combat" and view.combat is not None:
        hud = render_combat(view)
        return Screen(
            "📖 Os Nomes Esquecidos · Combate\n\n" + hud.text,
            "s2",
            hud.keyboard,
            parse_mode=hud.parse_mode,
        )

    version = view.state_version
    keyboard: list[list[InlineKeyboardButton]] = []

    if view.kind == "offer":
        label = "Reaceitar Missão" if view.reacceptable else "Aceitar Missão"
        action = "reaccept" if view.reacceptable else "accept"
        keyboard.append([_button(label, f"s2:{version}:{action}")])
        keyboard.append([_button("← Oren Cal", "s2:oren")])
        return Screen(
            "📖 Os Nomes Esquecidos\n"
            "Missão Secundária · Terras do Ocaso\n"
            "Oren Cal\n\n"
            "<i>Não preciso saber quem eram todos eles. Preciso apenas provar que foram pessoas antes de virarem aquilo que encontramos.</i>\n\n"
            "🎯 Investigar o acampamento abandonado na Charneca da Fuligem.\n\n"
            "🎁 Recompensas\n\n"
            "✨ XP · 2.695\n"
            "🪙 Coroas · 120\n"
            "🌿 Erva Cinzenta · 1 · Vinculada\n"
            "💧 Resíduo do Ocaso · 1 · Vinculado",
            "s2_offer",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML",
        )

    if view.kind == "unavailable":
        return Screen(
            "✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso\n\n"
            "📖 Os Nomes Esquecidos · Indisponível no momento",
            "oren_cal",
            InlineKeyboardMarkup(
                inline_keyboard=[[_button("← Refúgio do Ocaso", "road:local")]]
            ),
        )

    if view.kind == "oren":
        lines = ["✒️ Oren Cal", "Refúgio do Ocaso · Terras do Ocaso"]
        if view.status == "active":
            lines.extend(["", "📖 Os Nomes Esquecidos · Em Andamento"])
            if view.step == 6:
                lines.append("🎯 Entregar o fragmento de registro carbonizado")
                keyboard.append(
                    [_button("Falar com Oren", f"s2:{version}:complete")]
                )
            else:
                keyboard.append([_button("Ver Objetivo", "s2:objective")])
        elif view.status == "completed":
            lines.extend(["", "✅ Os Nomes Esquecidos · Concluída"])
            keyboard.append([_button("Ver registro", "s2:detail")])
        elif view.reacceptable:
            lines.extend(["", "📖 Os Nomes Esquecidos · Reaceitável"])
            keyboard.append([_button("Os Nomes Esquecidos", "s2:offer")])
        elif view.available:
            lines.extend(["", "📖 Os Nomes Esquecidos · Disponível"])
            keyboard.append([_button("Os Nomes Esquecidos", "s2:offer")])
        keyboard.append([_button("← Refúgio do Ocaso", "road:local")])
        return Screen(
            "\n".join(lines), "oren_cal", InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n"
            "📖 Os Nomes Esquecidos\n\n"
            "Etapa e progresso transitório serão reiniciados ao reaceitar.\n"
            "Registros permanentes já obtidos permanecem preservados.",
            "s1_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s2:{version}:abandon:confirm")],
                    [_button("← Os Nomes Esquecidos", "s2:detail")],
                ]
            ),
        )

    if view.kind == "abandoned" or view.status == "abandoned":
        return Screen(
            "📖 Os Nomes Esquecidos · Abandonada\n"
            "Missão Secundária · Terras do Ocaso",
            "s2_detail",
            InlineKeyboardMarkup(
                inline_keyboard=[[_button("← Oren Cal", "s2:oren")]]
            ),
        )

    if view.kind == "completed" or view.status == "completed":
        return Screen(
            "✅ Os Nomes Esquecidos · Concluída\n"
            "Missão Secundária · Terras do Ocaso\n\n"
            "🎁 Recompensas\n\n"
            "✨ XP · 2.695\n"
            "🪙 Coroas · 120\n"
            "🌿 Erva Cinzenta · 1 · Vinculada\n"
            "💧 Resíduo do Ocaso · 1 · Vinculado\n"
            "📖 Códice · Peregrinos do Ocaso atualizado",
            "s2_completed",
            InlineKeyboardMarkup(
                inline_keyboard=[[_button("← Refúgio do Ocaso", "road:local")]]
            ),
        )

    if view.kind == "recovery":
        recovery_brazier = view.progress.get("recovery_brazier") or "Braseiro do Refúgio"
        recovery_location = view.progress.get("recovery_location") or view.location
        lines = [
            "💀 Derrota · Peregrino Calcinado",
            f"🔥 {recovery_brazier}",
            f"{recovery_location} · Terras do Ocaso",
            "❤️ HP · Restaurado",
            "📖 Os Nomes Esquecidos · Em Andamento",
            "🎯 Retornar à Charneca para uma nova tentativa",
        ]
        if view.location == REFUGE:
            keyboard.append(
                [_button("Seguir para a Charneca", "road:route:charneca")]
            )
        elif view.location == CHARNECA:
            lines[-1] = "🎯 Enfrentar novamente o Peregrino Calcinado"
            keyboard.append([_button("Nova tentativa", f"s2:{version}:retry")])
        else:
            keyboard.append([_button("Ver no Mapa", "world:map")])
        keyboard.append([_button("← Missões", "world:missions")])
        return Screen("\n".join(lines), "s2_recovery", InlineKeyboardMarkup(inline_keyboard=keyboard))

    if view.kind == "fragment" or (view.step == 5 and view.status == "active"):
        if view.location == CHARNECA:
            keyboard.append([_button("Recuperar fragmento", f"s2:{version}:fragment")])
        elif view.location == REFUGE:
            keyboard.append([_button("Seguir para a Charneca", "road:route:charneca")])
        else:
            keyboard.append([_button("Ver no Mapa", "world:map")])
        keyboard.append([_button("← Missões", "world:missions")])
        return Screen(
            "🏆 Peregrino Calcinado derrotado\n"
            "📖 Os Nomes Esquecidos · Em Andamento\n"
            "🌑 Charneca da Fuligem · Terras do Ocaso\n\n"
            "🎯 Recuperar o fragmento de registro carbonizado",
            "s2_fragment",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.kind == "return" or (view.step == 6 and view.status == "active"):
        if view.location == REFUGE:
            keyboard.append([_button("Falar com Oren Cal", "world:oren")])
        elif view.location == CHARNECA:
            keyboard.append([_button("Retornar ao Refúgio", "road:route:refuge")])
        else:
            keyboard.append([_button("Ver no Mapa", "world:map")])
        keyboard.append([_button("← Missões", "world:missions")])
        return Screen(
            "📖 Os Nomes Esquecidos · Em Andamento\n"
            f"{view.location} · Terras do Ocaso\n\n"
            "🎯 Retornar a Oren Cal no Refúgio do Ocaso",
            "s2_objective",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )

    if view.step == 1:
        if view.location == CHARNECA:
            keyboard.append([_button("Examinar acampamento", f"s2:{version}:camp")])
        elif view.location == REFUGE:
            keyboard.append([_button("Seguir para a Charneca", "road:route:charneca")])
        else:
            keyboard.append([_button("Ver no Mapa", "world:map")])
    elif view.step == 2:
        vestiges = set(view.progress.get("vestiges", []))
        lines = [
            "📖 Os Nomes Esquecidos · Em Andamento",
            "🌑 Charneca da Fuligem · Terras do Ocaso",
            "",
            f"🎯 Vestígios Pessoais · {len(vestiges)}/3",
        ]
        buttons = []
        for index, vestige_id in enumerate(
            ("s2.vestige.1", "s2.vestige.2", "s2.vestige.3"), start=1
        ):
            if vestige_id in vestiges:
                lines.append(f"{index} ✅ Vestígio Pessoal {index} · Examinado")
            else:
                lines.append(f"{index} ⚪ Vestígio Pessoal {index}")
                buttons.append(
                    _button(str(index), f"s2:{version}:vestige:{index}")
                )
        if view.location == CHARNECA and buttons:
            keyboard.append(buttons)
            keyboard.append([_button("Ver no Mapa", "world:map")])
            keyboard.append([_button("← Missões", "world:missions")])
        elif view.location != CHARNECA:
            if view.location == REFUGE:
                keyboard.append([_button("Seguir para a Charneca", "road:route:charneca")])
            else:
                keyboard.append([_button("Ver no Mapa", "world:map")])
            keyboard.append([_button("← Missões", "world:missions")])
        return Screen("\n".join(lines), "s2_objective", InlineKeyboardMarkup(inline_keyboard=keyboard))
    else:
        keyboard.append([_button("Ver no Mapa", "world:map")])

    text = (
        "📖 Os Nomes Esquecidos · Em Andamento\n"
        f"Missão Secundária · Terras do Ocaso\n\n{_objective(view)}\n\n"
        f"📍 {view.location} · Terras do Ocaso\n\n"
        "🎁 Recompensas\n"
        "✨ XP · 2.695\n"
        "🪙 Coroas · 120\n"
        "🌿 Erva Cinzenta · 1 · Vinculada\n"
        "💧 Resíduo do Ocaso · 1 · Vinculado"
    )
    keyboard.extend(
        [
            [
                _button(
                    "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                    f"s2:{version}:track",
                )
            ],
            [
                _button("Ver Objetivo", "s2:objective"),
                _button("Ver no Mapa", "world:map"),
            ],
            [_button("Abandonar Missão", "s2:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    return Screen(text, "s2_detail", InlineKeyboardMarkup(inline_keyboard=keyboard))
