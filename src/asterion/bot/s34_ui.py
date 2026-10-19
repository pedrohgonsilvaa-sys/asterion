"""Telegram screens for S34 — A Testemunha de Ontem."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s34 import S34_EVIDENCE, S34View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_EVIDENCE_LABELS = {
    S34_EVIDENCE[0]: ("Inspecionar a primeira marca física", "inspect_mark_a"),
    S34_EVIDENCE[1]: ("Inspecionar a segunda marca física", "inspect_mark_b"),
    S34_EVIDENCE[2]: ("Verificar a ficha de cadeia de custódia", "inspect_chain_of_custody"),
}
_EVIDENCE_LOCATIONS = {
    S34_EVIDENCE[0]: "Fraturas do Limiar",
    S34_EVIDENCE[1]: "Nó Central",
    S34_EVIDENCE[2]: "Nó Central",
}


def render_s34(view: S34View) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "giver":
        if view.status == "active":
            state = "Em Andamento"
            rows.append([_button("Retomar missão", "s34:resume")])
        elif view.status == "completed":
            state = "Concluída"
            rows.append([_button("Ver registro da missão", "s34:resume")])
        elif view.reacceptable:
            state = "Disponível para reaceite"
            rows.append([_button("Reaceitar Missão", f"s34:reaccept:{view.state_version}")])
        elif view.available:
            state = "Disponível"
            rows.append([_button("Conhecer a missão", "s34:offer")])
        else:
            state = "Indisponível · requer P34 concluída + Nv.57"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"🧭 Talen Nyr · {view.location}\n\nA Testemunha de Ontem · {state}",
            "s34_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if view.status in {"active", "completed"}:
            rows.append([_button("Abrir missão", "s34:resume")])
            body = "O depoimento já possui um estado persistente."
        elif view.available or view.reacceptable:
            callback = (
                f"s34:reaccept:{view.state_version}"
                if view.reacceptable
                else "s34:accept:0"
            )
            rows.append(
                [_button("Reaceitar Missão" if view.reacceptable else "Aceitar Missão", callback)]
            )
            body = (
                "Talen pede que a data do depoimento seja comparada com a emissão aparente, "
                "as marcas no terreno e a cadeia de custódia. A discrepância não prova "
                "profecia nem deslocamento temporal."
            )
        else:
            body = "Disponível após P34 concluída e ao atingir Nv.57."
        rows.append([_button("← Talen Nyr", "s34:talen")])
        return Screen(
            "📜 A Testemunha de Ontem\nMissão Secundária Padrão · Confins do Véu\n\n"
            f"Talen Nyr · {view.location}\n\n{body}\n\n"
            "✨ 65.275 XP · 🪙 720 Coroas · 1 Ferro · 1 Couro · 1 Musgo · 1 Pó",
            "s34_offer",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 A Testemunha de Ontem\n\n"
            f"Evidências físicas preservadas: {len(view.evidence)}/3 · "
            f"Códice preservado: {'sim' if view.codex_owned else 'não'}.",
            "s34_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s34:abandon_confirm:{view.state_version}")],
                    [_button("← Missão", "s34:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 A Testemunha de Ontem · Abandonada\n\n"
            f"Evidências preservadas: {len(view.evidence)}/3 · "
            f"Vitória preservada: {'sim' if view.andarilho_victory else 'não'} · "
            f"Códice preservado: {'sim' if view.codex_owned else 'não'}.",
            "s34_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Talen Nyr", "s34:talen")]]),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ A Testemunha de Ontem · Concluída\nMissão Secundária · Confins do Véu\n\n"
            "O Códice preserva a data, as marcas e a cadeia de custódia. A ordem local é "
            "discrepante, mas sua causa permanece sem explicação completa.\n\n"
            "✨ 65.275 XP · 🪙 720 Coroas · 1 Ferro · 1 Couro · 1 Musgo · 1 Pó",
            "s34_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    if view.step == 2 and view.action_available:
        for evidence_id in S34_EVIDENCE:
            label, action = _EVIDENCE_LABELS[evidence_id]
            if (
                evidence_id not in view.evidence
                and _EVIDENCE_LOCATIONS[evidence_id] == view.location
            ):
                rows.append([_button(label, f"s34:action:{view.state_version}:{action}")])
    elif view.step == 3 and view.action_available:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:S34:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Enfrentar Solo", f"altos:combat:S34:{view.state_version}:solo")],
                    [_button("Enfrentar em Grupo", f"altos:combat:S34:{view.state_version}:group")],
                )
            )
    elif view.step == 4 and view.action_available:
        rows.append(
            [
                _button(
                    "Reconciliar o depoimento com Talen",
                    f"s34:action:{view.state_version}:reconcile_testimony",
                )
            ]
        )
    elif view.step == 5 and view.action_available:
        if not view.codex_recorded:
            rows.append(
                [_button("Registrar no Códice", f"s34:action:{view.state_version}:record_codex")]
            )
        else:
            rows.append(
                [
                    _button(
                        "Concluir com Talen Nyr",
                        f"s34:action:{view.state_version}:conclude_with_talen",
                    )
                ]
            )
    else:
        rows.append([_button("Ver Mapa", "world:map")])

    rows.append(
        [
            _button(
                "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                f"s34:track:{view.state_version}",
            )
        ]
    )
    rows.extend(
        [
            [_button("Abandonar Missão", "s34:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    objectives = {
        2: "Confira as duas marcas físicas e a ficha com cadeia de custódia.",
        3: "Enfrente um Andarilho Repetido Nv.57 em combate roteirizado, sem Variante ou economia.",
        4: "Reconcilie pessoalmente com Talen a data, as marcas e a ordem aparente.",
        5: "Registre A Testemunha de Ontem no Códice e conclua com Talen.",
    }
    text = (
        "📜 A Testemunha de Ontem · Em Andamento\n"
        f"Confins do Véu · {view.location or 'Fraturas do Limiar'}\n\n"
        f"🎯 Etapa {view.step}/5 · {objectives.get(view.step, 'Retome a etapa atual.')}"
    )
    if view.step == 2:
        text += f"\nEvidências: {len(view.evidence)}/3"
    elif view.step == 3 and view.progress.get("awaiting_retry"):
        text += "\nA derrota não avançou a missão; o encontro pode ser tentado novamente."
    elif view.step == 5 and view.codex_recorded:
        text += "\nO Códice está registrado; conclua pessoalmente com Talen."
    if not view.action_available:
        text += (
            "\n\n📍 Esta etapa requer uma das áreas já abertas: "
            "Fraturas do Limiar ou Nó Central."
        )
    return Screen(
        text,
        "s34_objective" if view.kind == "objective" else "s34_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
