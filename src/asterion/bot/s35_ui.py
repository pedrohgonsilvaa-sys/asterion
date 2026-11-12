"""Telegram screens for S35 — O Registro que Discorda."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s35 import S35_EVIDENCE, S35View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_EVIDENCE_LABELS = {
    S35_EVIDENCE[0]: ("Verificar a origem do primeiro lacre", "inspect_seal_a"),
    S35_EVIDENCE[1]: ("Verificar a origem do segundo lacre", "inspect_seal_b"),
    S35_EVIDENCE[2]: ("Verificar a trilha de transmissão", "inspect_transmission"),
}
_EVIDENCE_LOCATIONS = {
    S35_EVIDENCE[0]: "Nó Central",
    S35_EVIDENCE[1]: "Último Refúgio",
    S35_EVIDENCE[2]: "Último Refúgio",
}


def render_s35(view: S35View) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "giver":
        if view.status == "active":
            state = "Em Andamento"
            rows.append([_button("Retomar missão", "s35:resume")])
        elif view.status == "completed":
            state = "Concluída"
            rows.append([_button("Ver registro da missão", "s35:resume")])
        elif view.reacceptable:
            state = "Disponível para reaceite"
            rows.append([_button("Reaceitar Missão", f"s35:reaccept:{view.state_version}")])
        elif view.available:
            state = "Disponível"
            rows.append([_button("Conhecer a missão", "s35:offer")])
        else:
            state = "Indisponível · requer P34 concluída + Nv.58"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"🧭 Roven Pell · {view.location}\n\nO Registro que Discorda · {state}",
            "s35_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if view.status in {"active", "completed"}:
            rows.append([_button("Abrir missão", "s35:resume")])
            body = "As ordens oficiais já possuem um estado persistente."
        elif view.available or view.reacceptable:
            callback = (
                f"s35:reaccept:{view.state_version}"
                if view.reacceptable
                else "s35:accept:0"
            )
            rows.append(
                [_button("Reaceitar Missão" if view.reacceptable else "Aceitar Missão", callback)]
            )
            body = (
                "Disponível após P34 concluída e Nv.58. Roven Pell e Eris Val apresentam "
                "duas ordens oficiais sobre o mesmo intervalo. "
                "As origens dos lacres e a trilha de transmissão devem ser preservadas para "
                "comparação; a divergência não escolhe qual registro apagar."
            )
        else:
            body = "Disponível após P34 concluída e ao atingir Nv.58."
        rows.append([_button("← Roven Pell / Eris Val", "s35:roven")])
        return Screen(
            "📜 O Registro que Discorda\nMissão Secundária Padrão · Confins do Véu\n\n"
            f"Roven Pell · {view.location}\n\n{body}\n\n"
            "✨ 67.270 XP · 🪙 730 Coroas · 1 Ferro · 2 Musgos · 1 Pó",
            "s35_offer",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 O Registro que Discorda\n\n"
            f"Evidências físicas preservadas: {len(view.evidence)}/3 · "
            f"Códice preservado: {'sim' if view.codex_owned else 'não'}.",
            "s35_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s35:abandon_confirm:{view.state_version}")],
                    [_button("← Missão", "s35:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 O Registro que Discorda · Abandonada\n\n"
            f"Evidências preservadas: {len(view.evidence)}/3 · "
            f"Vitória preservada: {'sim' if view.vigia_victory else 'não'} · "
            f"Códice preservado: {'sim' if view.codex_owned else 'não'}.",
            "s35_abandoned",
            InlineKeyboardMarkup(
                inline_keyboard=[[_button("← Roven Pell / Eris Val", "s35:roven")]]
            ),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ O Registro que Discorda · Concluída\nMissão Secundária · Confins do Véu\n\n"
            "O Códice mantém as duas ordens oficiais, suas origens e a trilha de transmissão "
            "lado a lado. A divergência permanece sem conclusão definitiva.\n\n"
            "✨ 67.270 XP · 🪙 730 Coroas · 1 Ferro · 2 Musgos · 1 Pó",
            "s35_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    if view.step == 2 and view.action_available:
        for evidence_id in S35_EVIDENCE:
            label, action = _EVIDENCE_LABELS[evidence_id]
            if (
                evidence_id not in view.evidence
                and _EVIDENCE_LOCATIONS[evidence_id] == view.location
            ):
                rows.append([_button(label, f"s35:action:{view.state_version}:{action}")])
    elif view.step == 3 and view.action_available:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:S35:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Enfrentar Solo", f"altos:combat:S35:{view.state_version}:solo")],
                )
            )
    elif view.step == 4 and view.action_available:
        rows.append(
            [
                _button(
                    "Preservar a divergência com Roven e Eris",
                    f"s35:action:{view.state_version}:compare_official_orders",
                )
            ]
        )
    elif view.step == 5 and view.action_available:
        if not view.codex_recorded:
            rows.append(
                [_button("Registrar no Códice", f"s35:action:{view.state_version}:record_codex")]
            )
        else:
            rows.append(
                [
                    _button(
                        "Concluir com Roven Pell",
                    f"s35:action:{view.state_version}:conclude_with_roven",
                    )
                ]
            )
    else:
        rows.append([_button("Ver Mapa", "world:map")])

    rows.append(
        [
            _button(
                "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                f"s35:track:{view.state_version}",
            )
        ]
    )
    rows.extend(
        [
            [_button("Abandonar Missão", "s35:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    objectives = {
        2: "Verifique as origens dos dois lacres oficiais e a trilha de transmissão.",
        3: "Enfrente um Vigia Desfasado Nv.58 em combate roteirizado, sem Variante ou economia.",
        4: "Preserve pessoalmente as duas ordens incompatíveis lado a lado.",
        5: "Registre Ordens Discordantes no Códice e conclua com Roven ou Eris.",
    }
    text = (
        "📜 O Registro que Discorda · Em Andamento\n"
        f"Confins do Véu · {view.location or 'Nó Central'}\n\n"
        f"🎯 Etapa {view.step}/5 · {objectives.get(view.step, 'Retome a etapa atual.')}"
    )
    if view.step == 2:
        text += f"\nEvidências: {len(view.evidence)}/3"
    elif view.step == 3 and view.progress.get("awaiting_retry"):
        text += "\nA derrota não avançou a missão; o encontro pode ser tentado novamente."
    elif view.step == 5 and view.codex_recorded:
        text += "\nO Códice está registrado; conclua pessoalmente com Roven ou Eris."
    if not view.action_available:
        text += (
            "\n\n📍 Esta etapa requer uma das áreas já abertas: "
            "Nó Central ou Último Refúgio."
        )
    return Screen(
        text,
        "s35_objective" if view.kind == "objective" else "s35_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
