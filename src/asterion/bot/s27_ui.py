"""Player-facing screens for S27 — Cabo Partido."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s27 import S27View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_STEP_COPY = {
    1: ("Inspecionar o cabo antigo rompido.", "inspect_broken_cable"),
    2: (
        "Verificar que não é necessário reconstruir integralmente o sistema antigo.",
        "confirm_full_rebuild_unneeded",
    ),
    3: (
        "Validar o reparo moderno redundante com materiais apenas narrativos, sem custo econômico.",
        "validate_redundant_repair",
    ),
    4: (
        "Atravessar a rota reparada. O avanço é da missão e não abre uma rota pública.",
        "cross_repaired_route",
    ),
    5: ("Retornar a Doren Vask.", "return_to_doren"),
    6: ("Registrar Reparo Redundante no Códice.", "record_codex"),
}


def render_s27(view: S27View) -> Screen:
    if view.kind == "giver":
        rows: list[list[InlineKeyboardButton]] = []
        if view.status == "active":
            rows.append([_button("Ver Cabo Partido", "s27:resume")])
            state = "Em Andamento"
        elif view.status == "completed":
            rows.append([_button("Ver registro da missão", "s27:resume")])
            state = "Concluída"
        elif view.reacceptable:
            rows.append(
                [_button("Reaceitar Cabo Partido", f"s27:reaccept:{view.state_version}")]
            )
            state = "Disponível para reaceite"
        elif view.available:
            rows.append([_button("Conhecer a missão", "s27:offer")])
            state = "Disponível"
        else:
            state = "Indisponível · requer P27 ativa ou concluída, acesso às Pedreiras e Nv.45"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"✒️ Doren Vask\nPedreiras Suspensas · Altos Cinéreos\n\n"
            f"📜 Cabo Partido · {state}",
            "s27_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if not view.available and not view.reacceptable:
            return Screen(
                "📜 Cabo Partido\n\nRequer P27 ativa ou concluída, acesso às "
                "Pedreiras Suspensas e Nv.45.",
                "s27_offer",
                InlineKeyboardMarkup(
                    inline_keyboard=[[_button("← Doren Vask", "s27:doren")]]
                ),
            )
        accept = (
            _button("Reaceitar Missão", f"s27:reaccept:{view.state_version}")
            if view.reacceptable
            else _button("Aceitar Missão", "s27:accept:0")
        )
        return Screen(
            "📜 Cabo Partido\nMissão Secundária · Altos Cinéreos\n\n"
            "Doren Vask · Pedreiras Suspensas\n\n"
            "Inspecione o cabo, valide um reparo moderno redundante, atravesse a "
            "rota e registre no Códice que uma solução menor pode ser suficiente.\n\n"
            "O reparo usa materiais apenas narrativos: não consome itens, não cria "
            "estado global e não abre uma rota pública.\n\n"
            "✨ 24.960 XP · 🪙 390 Coroas\n"
            "🧰 1 Ferro de Contrapeso · 1 Couro de Escarpa",
            "s27_offer",
            InlineKeyboardMarkup(
                inline_keyboard=[[accept], [_button("← Doren Vask", "s27:doren")]]
            ),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ Cabo Partido · Concluída\nMissão Secundária · Altos Cinéreos\n\n"
            "✨ 24.960 XP · 🪙 390 Coroas\n"
            "🧰 1 Ferro de Contrapeso · 1 Couro de Escarpa\n\n"
            "📖 Códice · Reparo Redundante\n"
            "O registro é pessoal; o reparo não criou uma rota pública.",
            "s27_completed",
            InlineKeyboardMarkup(
                inline_keyboard=[[_button("← Missões", "world:missions")]]
            ),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 Cabo Partido\n\n"
            "Objetivos temporários serão reiniciados. O Códice e recompensas já "
            "concedidos permanecem preservados.",
            "s27_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s27:abandon_confirm:{view.state_version}")],
                    [_button("← Cabo Partido", "s27:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 Cabo Partido · Abandonada\n\n"
            "Registros permanentes já obtidos permanecem preservados.",
            "s27_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Doren Vask", "s27:doren")]]),
        )

    objective = _STEP_COPY.get(view.step)
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "objective" and objective is not None:
        rows.append([_button("Executar etapa", f"s27:action:{view.state_version}:{objective[1]}")])
    else:
        rows.append([_button("Ver objetivo", "s27:objective")])
    if view.kind != "objective":
        rows.append(
            [
                _button(
                    "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                    f"s27:track:{view.state_version}",
                )
            ]
        )
    step_text = objective[0] if objective else "Retome a etapa atual."
    rows.extend(
        [
            [_button("Abandonar Missão", "s27:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    return Screen(
        "📜 Cabo Partido · Em Andamento\n"
        f"Altos Cinéreos · {view.location or 'Pedreiras Suspensas'}\n\n"
        f"🎯 Etapa {min(view.step, 6)}/6 · {step_text}\n\n"
        "✨ 24.960 XP · 390 Coroas · 1 Ferro de Contrapeso · 1 Couro de Escarpa",
        "s27_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
