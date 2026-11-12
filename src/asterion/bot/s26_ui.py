"""Player-facing screens for S26 — Turno sem Fim."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s26 import S26View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_STEP_COPY = {
    1: ("Receber de Hesa Tor as três marcações de turno.", "receive_shift_marks"),
    2: (
        "Acompanhar a equipe moderna de resgate no trabalho de campo.",
        "accompany_rescue_team",
    ),
    3: (
        "Vencer o Carneiro do Peso (Nv.44) em combate roteirizado.",
        None,
    ),
    4: (
        "Encontrar o registro antigo que elogia o mesmo turno e prolonga sua obrigação.",
        "find_old_shift_record",
    ),
    5: (
        "Concluir com Hesa que heroísmo individual e exploração institucional podem coexistir.",
        "discuss_heroism_and_exploitation",
    ),
    6: ("Registrar Turno sem Fim no Códice.", "record_codex"),
}


def render_s26(view: S26View) -> Screen:
    location = view.location or "Abrigo do Peso / Pontes de Fuligem"
    if view.kind == "giver":
        rows: list[list[InlineKeyboardButton]] = []
        if view.status == "active":
            state = "Em Andamento"
            rows.append([_button("Ver Turno sem Fim", "s26:resume")])
        elif view.status == "completed":
            state = "Concluída"
            rows.append([_button("Ver registro da missão", "s26:resume")])
        elif view.reacceptable:
            state = "Disponível para reaceite"
            rows.append(
                [_button("Reaceitar Turno sem Fim", f"s26:reaccept:{view.state_version}")]
            )
        elif view.available:
            state = "Disponível"
            rows.append([_button("Conhecer a missão", "s26:offer")])
        else:
            state = "Indisponível · requer P26 concluída e Nv.44"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"✒️ Hesa Tor\nAltos Cinéreos · {location}\n\n"
            f"📜 Turno sem Fim · {state}",
            "s26_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if not view.available and not view.reacceptable:
            return Screen(
                "📜 Turno sem Fim\n\nRequer P26 concluída, Nv.44 e presença "
                "no Abrigo do Peso ou em Pontes de Fuligem.",
                "s26_offer",
                InlineKeyboardMarkup(
                    inline_keyboard=[[_button("← Hesa Tor", "s26:hesa")]]
                ),
            )
        accept = (
            _button("Reaceitar Missão", f"s26:reaccept:{view.state_version}")
            if view.reacceptable
            else _button("Aceitar Missão", "s26:accept:0")
        )
        return Screen(
            "📜 Turno sem Fim\nMissão Secundária · Altos Cinéreos\n\n"
            "Hesa Tor · Abrigo do Peso / Pontes de Fuligem\n\n"
            "Acompanhe uma equipe moderna de resgate, confronte um registro antigo "
            "e registre no Códice a coexistência entre heroísmo individual e "
            "exploração institucional.\n\n"
            "✨ 42.070 XP · 🪙 570 Coroas\n"
            "🧰 1 Couro de Escarpa · 1 Líquen de Pedreira",
            "s26_offer",
            InlineKeyboardMarkup(
                inline_keyboard=[[accept], [_button("← Hesa Tor", "s26:hesa")]]
            ),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ Turno sem Fim · Concluída\nMissão Secundária · Altos Cinéreos\n\n"
            "✨ 42.070 XP · 🪙 570 Coroas\n"
            "🧰 1 Couro de Escarpa · 1 Líquen de Pedreira\n\n"
            "📖 Códice · Turno sem Fim",
            "s26_completed",
            InlineKeyboardMarkup(
                inline_keyboard=[[_button("← Missões", "world:missions")]]
            ),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 Turno sem Fim\n\n"
            "Objetivos temporários serão reiniciados. Códice e recompensas já "
            "concedidos permanecem preservados.",
            "s26_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s26:abandon_confirm:{view.state_version}")],
                    [_button("← Turno sem Fim", "s26:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 Turno sem Fim · Abandonada\n\n"
            "Registros permanentes já obtidos permanecem preservados.",
            "s26_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Hesa Tor", "s26:hesa")]]),
        )

    objective = _STEP_COPY.get(view.step)
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "objective" and objective is not None:
        action = objective[1]
        if view.step == 3:
            rows.extend(
                (
                    [
                        _button(
                            "Iniciar encontro Solo",
                            f"altos:combat:S26:{view.state_version}:solo",
                        )
                    ],
                )
            )
        elif action is not None:
            rows.append([_button("Executar etapa", f"s26:action:{view.state_version}:{action}")])
    else:
        rows.append([_button("Ver objetivo", "s26:objective")])
    if view.kind != "objective":
        rows.append(
            [
                _button(
                    "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                    f"s26:track:{view.state_version}",
                )
            ]
        )
    if objective is not None:
        step_text = objective[0]
    else:
        step_text = "Retome a etapa atual."
    rows.extend(
        [
            [_button("Abandonar Missão", "s26:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    return Screen(
        "📜 Turno sem Fim · Em Andamento\n"
        f"Altos Cinéreos · {location}\n\n"
        f"🎯 Etapa {min(view.step, 6)}/6 · {step_text}\n\n"
        "✨ 42.070 XP · 570 Coroas · 1 Couro de Escarpa · 1 Líquen de Pedreira",
        "s26_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
