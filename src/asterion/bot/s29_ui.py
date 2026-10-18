"""Player-facing screens for S29 — Os que Disseram Não."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s29 import S29_REFUSAL_RECORDS, S29View
from asterion.bot.creation_ui import Screen

_RECORD_LABELS = {
    S29_REFUSAL_RECORDS[0]: "Registro de recusa A",
    S29_REFUSAL_RECORDS[1]: "Registro de recusa B",
    S29_REFUSAL_RECORDS[2]: "Registro de recusa C",
}
_RECORD_ACTIONS = {
    S29_REFUSAL_RECORDS[0]: "locate_record_a",
    S29_REFUSAL_RECORDS[1]: "locate_record_b",
    S29_REFUSAL_RECORDS[2]: "locate_record_c",
}


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_STEP_COPY = {
    1: (
        "Localizar três registros distintos de recusa a ordens de emergência.",
        None,
        "Bastilha de Carga",
    ),
    2: (
        "Confirmar documentalmente que ao menos dois recusantes continuaram na manutenção civil.",
        "verify_civil_maintenance",
        "Bastilha de Carga",
    ),
    3: (
        "Verificar que as recusas examinadas não correspondem a sabotagem material.",
        "verify_no_material_sabotage",
        "Bastilha de Carga",
    ),
    4: (
        "Comparar os registros com Maro Keln e Sel Ardan.",
        "compare_with_maro_and_sel",
        "Abrigo do Peso ou Bastilha de Carga",
    ),
    5: (
        "Registrar no Códice as recusas corroboradas sem confundi-las com sabotagem.",
        "record_codex",
        "Abrigo do Peso ou Bastilha de Carga",
    ),
}


def render_s29(view: S29View) -> Screen:
    owned = set(view.refusal_records)
    if view.kind == "giver":
        rows: list[list[InlineKeyboardButton]] = []
        if view.status == "active":
            rows.append([_button("Ver Os que Disseram Não", "s29:resume")])
            state = "Em Andamento"
        elif view.status == "completed":
            rows.append([_button("Ver registro da missão", "s29:resume")])
            state = "Concluída"
        elif view.reacceptable:
            rows.append(
                [_button("Reaceitar Missão", f"s29:reaccept:{view.state_version}")]
            )
            state = "Disponível para reaceite"
        elif view.available:
            rows.append([_button("Conhecer a missão", "s29:offer")])
            state = "Disponível"
        else:
            state = "Indisponível · requer P28 concluída, Nv.48 e acesso ao Local"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"📜 Maro Keln\nAltos Cinéreos · {view.location}\n\n"
            f"Os que Disseram Não · {state}",
            "s29_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if not view.available and not view.reacceptable:
            return Screen(
                "📜 Os que Disseram Não\n\nRequer P28 concluída, Nv.48 e acesso legítimo "
                "ao Abrigo do Peso ou à Bastilha de Carga.",
                "s29_offer",
                InlineKeyboardMarkup(inline_keyboard=[[_button("← Maro Keln", "s29:maro")]]),
            )
        accept = (
            _button("Reaceitar Missão", f"s29:reaccept:{view.state_version}")
            if view.reacceptable
            else _button("Aceitar Missão", "s29:accept:0")
        )
        return Screen(
            "📜 Os que Disseram Não\nMissão Secundária · Altos Cinéreos\n\n"
            "Maro Keln · Bastilha de Carga / Abrigo do Peso\n\n"
            "Localize três registros distintos de recusa, confirme as evidências de "
            "manutenção civil "
            "e verifique que os casos examinados não envolveram sabotagem material. Compare os "
            "registros com Maro e Sel antes de registrar a conclusão no Códice.\n\n"
            "Dissidência não é automaticamente sabotagem; o resultado não absolve integralmente "
            "todos os dissidentes nem desfaz a sabotagem corroborada em P30.\n\n"
            "✨ 48.685 XP · 🪙 620 Coroas\n"
            "🧰 1 Ferro de Contrapeso · 1 Líquen de Pedreira · 2 Cinzas de Basalto",
            "s29_offer",
            InlineKeyboardMarkup(
                inline_keyboard=[[accept], [_button("← Maro Keln", "s29:maro")]]
            ),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 Os que Disseram Não\n\n"
            f"Registros permanentes já identificados: {len(owned)}/3. "
            "O reaceite reconstruirá os registros já preservados.",
            "s29_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s29:abandon_confirm:{view.state_version}")],
                    [_button("← Missão", "s29:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 Os que Disseram Não · Abandonada\n\n"
            f"Registros permanentes preservados: {len(owned)}/3.",
            "s29_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Maro Keln", "s29:maro")]]),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ Os que Disseram Não · Concluída\nMissão Secundária · Altos Cinéreos\n\n"
            "📖 Códice · Dissidência sem Sabotagem\n"
            f"Registros distintos: {len(owned)}/3 · Manutenção civil confirmada · "
            "Ausência de sabotagem material corroborada\n"
            f"🏆 Dizer Não · {'Conquistado' if view.achievement_owned else 'Registrado'}\n\n"
            "Dissidência não é automaticamente sabotagem. Esta conclusão não absolve todos os "
            "dissidentes e não altera a confirmação da sabotagem em P30.",
            "s29_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    objective = _STEP_COPY.get(view.step)
    rows: list[list[InlineKeyboardButton]] = []
    if view.step == 1:
        if view.action_available:
            for record_id in S29_REFUSAL_RECORDS:
                if record_id not in owned:
                    rows.append(
                        [
                            _button(
                                f"Localizar {_RECORD_LABELS[record_id]}",
                                f"s29:action:{view.state_version}:{_RECORD_ACTIONS[record_id]}",
                            )
                        ]
                    )
        else:
            rows.append([_button("Ver Mapa", "world:map")])
    elif objective is not None and objective[1] is not None and view.action_available:
        rows.append(
            [_button("Executar etapa", f"s29:action:{view.state_version}:{objective[1]}")]
        )
    elif objective is not None:
        rows.append([_button("Ver Mapa", "world:map")])
    else:
        rows.append([_button("Ver objetivo", "s29:objective")])

    if view.kind != "objective":
        rows.append(
            [
                _button(
                    "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                    f"s29:track:{view.state_version}",
                )
            ]
        )
    rows.extend(
        [
            [_button("Abandonar Missão", "s29:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    if objective is None:
        step_text, destination = "Retome a etapa atual.", ""
    else:
        step_text, _action, destination = objective
    progress_text = (
        f"\nRegistros de recusa identificados: {len(owned)}/3"
        if view.step == 1
        else ""
    )
    if view.step == 2:
        progress_text = "\nRegistros que comprovam continuidade na manutenção civil: ao menos 2/3"
    elif view.step == 3:
        progress_text = "\nA verificação se limita aos três casos documentados."
    action_hint = (
        ""
        if view.action_available or objective is None
        else f"\n\n📍 Local necessário · {destination}"
    )
    return Screen(
        "📜 Os que Disseram Não · Em Andamento\n"
        f"Altos Cinéreos · {view.location or 'Bastilha de Carga'}\n\n"
        f"🎯 Etapa {min(view.step, 5)}/5 · {step_text}{progress_text}{action_hint}\n\n"
        "Conclusão individual: dissidência não é automaticamente sabotagem; não representa "
        "absolvição integral nem altera as evidências de P30.",
        "s29_objective" if view.kind == "objective" else "s29_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
