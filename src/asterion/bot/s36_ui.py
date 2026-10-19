"""Player-facing screens for S36 — Depois da Última Ordem."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s36 import (
    S36_CONTROL_POINTS,
    S36_MATERIAL_PROOFS,
    S36View,
)
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_FIELD_ACTIONS = {
    S36_CONTROL_POINTS[0]: ("Inspecionar o controle de segurança", "inspect_control_safety"),
    S36_CONTROL_POINTS[1]: ("Verificar a ordem sem função civil", "inspect_control_obsolete_order"),
    S36_CONTROL_POINTS[2]: (
        "Verificar o controle que ainda exige conferência",
        "inspect_control_verification",
    ),
    S36_MATERIAL_PROOFS[0]: ("Registrar a primeira prova material", "collect_return_proof_a"),
    S36_MATERIAL_PROOFS[1]: ("Registrar a segunda prova material", "collect_return_proof_b"),
}


def render_s36(view: S36View) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "giver":
        if view.status == "active":
            state = "Em Andamento"
            rows.append([_button("Retomar missão", "s36:resume")])
        elif view.status == "completed":
            state = "Concluída"
            rows.append([_button("Ver registro da missão", "s36:resume")])
        elif view.reacceptable:
            state = "Disponível para reaceite"
            rows.append([_button("Reaceitar Missão", f"s36:reaccept:{view.state_version}")])
        elif view.available:
            state = "Disponível"
            rows.append([_button("Conhecer a missão", "s36:offer")])
        else:
            state = "Indisponível · requer P36 concluída + Nv.60 atual"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"🧭 Haro Sen e Sera Nol · {view.location}\n\nDepois da Última Ordem · {state}",
            "s36_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if view.status in {"active", "completed"}:
            rows.append([_button("Abrir missão", "s36:resume")])
            body = "A missão mantém seu progresso pessoal depois do encerramento da campanha."
        elif view.available or view.reacceptable:
            callback = f"s36:reaccept:{view.state_version}" if view.reacceptable else "s36:accept:0"
            rows.append(
                [
                    _button(
                        "Reaceitar Missão" if view.reacceptable else "Aceitar Missão",
                        callback,
                    )
                ]
            )
            body = (
                "Disponível após concluir P36 e enquanto estiver no Nv.60. A missão opcional "
                "observa rotinas civis ainda úteis e uma verificação antiga que continua "
                "bloqueando retornos. A interpretação não encerra riscos do Véu nem altera "
                "o mundo dos demais personagens."
            )
        else:
            body = "Requer P36 concluída, Nv.60 atual e aceite pessoal no Último Refúgio."
        rows.append([_button("← Haro Sen / Sera Nol", "s36:haro")])
        return Screen(
            "📜 Depois da Última Ordem\nMissão Secundária Longa · Confins do Véu\n\n"
            f"{view.location}\n\n{body}\n\n"
            "✨ 101.900 XP nominais (descartados no Nv.60) · 🪙 1.250 Coroas\n"
            "📦 2 Ferros de Baliza · 2 Couros de Marcha · 2 Musgos de Limiar · "
            "2 Pós de Referência\n"
            "🏅 Depois da Ordem · Título Guardião de Testemunhas",
            "s36_offer",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 Depois da Última Ordem\n\n"
            f"Evidências preservadas: {len(view.evidence)}/5 · Códice preservado: "
            f"{'sim' if view.codex_owned else 'não'} · "
            f"Vitória do Verificador preservada: {'sim' if view.verifier_victory else 'não'}.",
            "s36_abandon",
            InlineKeyboardMarkup(inline_keyboard=[
                [_button("Confirmar Abandono", f"s36:abandon_confirm:{view.state_version}")],
                [_button("← Missão", "s36:resume")],
            ]),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 Depois da Última Ordem · Abandonada\n\n"
            f"Evidências permanentes: {len(view.evidence)}/5 · Vitória preservada: "
            f"{'sim' if view.verifier_victory else 'não'} · "
            f"Códice preservado: {'sim' if view.codex_owned else 'não'}.",
            "s36_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Haro Sen / Sera Nol", "s36:haro")]]),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ Depois da Última Ordem · Concluída\nMissão Secundária · Confins do Véu\n\n"
            "A rotina civil razoável continua. O protocolo impossível foi encerrado, mas o Véu "
            "não foi curado e os riscos locais permanecem. Esta conclusão não altera a campanha "
            "nem o direito de Legado.\n\n"
            "✨ 101.900 XP nominais (descartados no Nv.60) · 🪙 1.250 Coroas\n"
            "📦 2 de cada Material Básico Grau VI\n🏅 Depois da Ordem · "
            "Título Guardião de Testemunhas",
            "s36_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    if view.step == 1 and view.action_available:
        rows.append(
            [
                _button(
                    "Ouvir e examinar as rotinas civis",
                    f"s36:action:{view.state_version}:examine_civil_routines",
                )
            ]
        )
    elif view.step in {2, 3} and view.action_available:
        required = S36_CONTROL_POINTS if view.step == 2 else S36_MATERIAL_PROOFS
        for evidence_id in required:
            if evidence_id not in view.evidence:
                label, action = _FIELD_ACTIONS[evidence_id]
                rows.append([_button(label, f"s36:action:{view.state_version}:{action}")])
    elif view.step == 4 and view.action_available:
        if view.progress.get("awaiting_retry"):
            rows.append(
                [_button("Confirmar nova tentativa Solo", f"altos:retry:S36:{view.state_version}")]
            )
            rows.append(
                [
                    _button(
                        "Solicitar nova tentativa em Grupo",
                        f"altos:retry:S36:{view.state_version}",
                    )
                ]
            )
        else:
            rows.append(
                [
                    _button(
                        "Confirmar e enfrentar Solo",
                        f"altos:combat:S36:{view.state_version}:solo",
                    )
                ]
            )
            rows.append(
                [
                    _button(
                        "Confirmar confronto em Grupo",
                        f"altos:combat:S36:{view.state_version}:group",
                    )
                ]
            )
    elif view.step == 5 and view.action_available and not view.bestiary_recorded:
        rows.append(
            [
                _button(
                    "Registrar fatos observados no Bestiário",
                    f"s36:action:{view.state_version}:record_bestiary",
                )
            ]
        )
    elif view.step == 6 and view.action_available and not view.codex_recorded:
        rows.append(
            [
                _button(
                    "Narrar como continuidade civil necessária",
                    f"s36:action:{view.state_version}:narrate_civil_continuity",
                )
            ]
        )
        rows.append(
            [
                _button(
                    "Narrar como rotina que exige verificação",
                    f"s36:action:{view.state_version}:narrate_verification_needed",
                )
            ]
        )
    elif view.step == 7 and view.action_available and view.codex_recorded:
        rows.append(
            [
                _button(
                    "Concluir com Sera Nol e Haro Sen",
                    f"s36:action:{view.state_version}:conclude_with_haro_sera",
                )
            ]
        )
    else:
        rows.append([_button("Ver Mapa", "world:map")])

    rows.append(
        [
            _button(
                "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                f"s36:track:{view.state_version}",
            )
        ]
    )
    rows.extend(
        [[_button("Abandonar Missão", "s36:abandon")], [_button("← Missões", "world:missions")]]
    )
    objectives = {
        1: "No Último Refúgio, examine quais rotinas ainda protegem os moradores.",
        2: "No Nó Central, inspecione três controles civis distintos.",
        3: "Reúna duas provas materiais independentes do retorno bloqueado.",
        4: "Confirme conscientemente o encontro com o Verificador sem Testemunhas Nv.60.",
        5: "Registre fatos que você observou no Bestiário, sem atribuir consciência ao mecanismo.",
        6: "Registre Rotinas Depois da Ordem e escolha como narrar a continuidade civil.",
        7: "Conclua pessoalmente com Sera Nol e Haro Sen.",
    }
    text = (
        "📜 Depois da Última Ordem · Em Andamento\n"
        f"Confins do Véu · {view.location or 'Último Refúgio'}\n\n"
        f"🎯 Etapa {view.step}/7 · {objectives.get(view.step, 'Retome a etapa atual.')}"
    )
    if view.step in {2, 3}:
        text += f"\nEvidências únicas: {len(view.evidence)}/5"
    if view.step == 4 and view.progress.get("awaiting_retry"):
        text += (
            "\nA derrota não avançou S36; recupere-se no Braseiro da Testemunha e viaje "
            "de volta ao Nó Central."
        )
    if view.step == 7 and view.codex_recorded:
        text += "\nCódice registrado; o pagamento ocorre apenas ao concluir pessoalmente."
    if not view.action_available:
        text += (
            "\n\n📍 Esta etapa requer o local correspondente no percurso Último Refúgio "
            "→ Nó Central."
        )
    return Screen(
        text,
        "s36_objective" if view.kind == "objective" else "s36_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
