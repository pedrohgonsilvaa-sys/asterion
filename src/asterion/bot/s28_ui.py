"""Player-facing screens for S28 — Cartas de Emergência."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s28 import S28_LETTER_FRAGMENTS, S28View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_STEP_COPY = {
    1: (
        "Recuperar a carta civil na rota das Pontes.",
        "recover_civil_letter",
        "Pontes de Fuligem",
    ),
    2: (
        "Recuperar a carta de trabalhadores nas Pedreiras.",
        "recover_workers_letter",
        "Pedreiras Suspensas",
    ),
    3: (
        "Recuperar a carta preservada fora do arquivo oficial.",
        "recover_archive_letter",
        "Bastilha de Carga",
    ),
    4: (
        "Comparar as três cartas com Maro Keln.",
        "compare_with_maro",
        "Abrigo do Peso ou Bastilha de Carga",
    ),
    5: (
        "Registrar os três Trechos e sua corroboração no Códice.",
        "corroborate_codex",
        "Abrigo do Peso ou Bastilha de Carga",
    ),
}


def _owned_count(view: S28View) -> int:
    return len(set(view.codex_fragments).intersection(S28_LETTER_FRAGMENTS))


def render_s28(view: S28View) -> Screen:
    if view.kind == "giver":
        rows: list[list[InlineKeyboardButton]] = []
        if view.status == "active":
            rows.append([_button("Ver Cartas de Emergência", "s28:resume")])
            state = "Em Andamento"
        elif view.status == "completed":
            rows.append([_button("Ver registro da missão", "s28:resume")])
            state = "Concluída"
        elif view.reacceptable:
            rows.append(
                [
                    _button(
                        "Reaceitar Cartas de Emergência",
                        f"s28:reaccept:{view.state_version}",
                    )
                ]
            )
            state = "Disponível para reaceite"
        elif view.available:
            rows.append([_button("Conhecer a missão", "s28:offer")])
            state = "Disponível"
        else:
            state = "Indisponível · requer P28 ativa ou concluída, acesso legítimo e Nv.47"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"✉️ Maro Keln\nAltos Cinéreos · {view.location}\n\n"
            f"📜 Cartas de Emergência · {state}",
            "s28_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if not view.available and not view.reacceptable:
            return Screen(
                "📜 Cartas de Emergência\n\nRequer P28 ativa ou concluída, acesso legítimo "
                "ao Local e Nv.47.",
                "s28_offer",
                InlineKeyboardMarkup(inline_keyboard=[[_button("← Maro Keln", "s28:maro")]]),
            )
        accept = (
            _button("Reaceitar Missão", f"s28:reaccept:{view.state_version}")
            if view.reacceptable
            else _button("Aceitar Missão", "s28:accept:0")
        )
        return Screen(
            "📜 Cartas de Emergência\nMissão Secundária · Altos Cinéreos\n\n"
            "Maro Keln · Abrigo do Peso / Bastilha de Carga\n\n"
            "Recupere uma carta civil nas Pontes, uma carta de trabalhadores nas Pedreiras "
            "e uma carta preservada fora do arquivo oficial na Bastilha. Depois, compare-as "
            "com Maro e registre os três Trechos corroborados.\n\n"
            "Os testemunhos civis complementam os registros oficiais; sua origem não os torna "
            "automaticamente superiores.\n\n"
            "✨ 46.970 XP · 🪙 610 Coroas\n"
            "🧰 1 Ferro de Contrapeso · 1 Líquen de Pedreira · 2 Cinzas de Basalto",
            "s28_offer",
            InlineKeyboardMarkup(
                inline_keyboard=[[accept], [_button("← Maro Keln", "s28:maro")]]
            ),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 Cartas de Emergência\n\n"
            f"Trechos permanentes do Códice preservados: {_owned_count(view)}/3. "
            "Objetivos temporários serão reiniciados; cartas já registradas permanecem.",
            "s28_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s28:abandon_confirm:{view.state_version}")],
                    [_button("← Cartas de Emergência", "s28:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 Cartas de Emergência · Abandonada\n\n"
            f"Trechos permanentes preservados: {_owned_count(view)}/3.",
            "s28_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Maro Keln", "s28:maro")]]),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ Cartas de Emergência · Concluída\nMissão Secundária · Altos Cinéreos\n\n"
            "📖 Códice · Cartas de Emergência\n"
            f"Trechos registrados: {_owned_count(view)}/3 · Corroboração concluída\n"
            f"🏆 Fora do Arquivo · {'Conquistado' if view.achievement_owned else 'Registrado'}\n\n"
            "Os testemunhos civis complementam o arquivo oficial e não substituem "
            "seus registros técnicos.",
            "s28_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    objective = _STEP_COPY.get(view.step)
    rows: list[list[InlineKeyboardButton]] = []
    if objective is not None and view.action_available:
        rows.append(
            [_button("Executar etapa", f"s28:action:{view.state_version}:{objective[1]}")]
        )
    elif objective is not None:
        rows.append([_button("Ver Mapa", "world:map")])
    else:
        rows.append([_button("Ver objetivo", "s28:objective")])
    if view.kind != "objective":
        rows.append(
            [
                _button(
                    "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                    f"s28:track:{view.state_version}",
                )
            ]
        )
    rows.extend(
        [
            [_button("Abandonar Missão", "s28:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    if objective is None:
        step_text = "Retome a etapa atual."
        destination = ""
    else:
        step_text, _action, destination = objective
    action_hint = (
        ""
        if view.action_available or objective is None
        else f"\n\n📍 Local necessário · {destination}"
    )
    return Screen(
        "📜 Cartas de Emergência · Em Andamento\n"
        f"Altos Cinéreos · {view.location or 'Abrigo do Peso'}\n\n"
        f"🎯 Etapa {min(view.step, 5)}/5 · {step_text}{action_hint}\n\n"
        f"📖 Trechos permanentes no Códice: {_owned_count(view)}/3\n"
        "Testemunhos civis complementam o arquivo oficial; não são tratados como verdade superior.",
        "s28_objective" if view.kind == "objective" else "s28_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
