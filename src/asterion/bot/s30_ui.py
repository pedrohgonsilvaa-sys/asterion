"""Telegram screens for S30 — A Ordem que Restou."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s30 import S30_PHYSICAL_SEALS, S30View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_SEAL_LABELS = {
    S30_PHYSICAL_SEALS[0]: "selo de validade física 1",
    S30_PHYSICAL_SEALS[1]: "selo de validade física 2",
    S30_PHYSICAL_SEALS[2]: "selo de validade física 3",
}

_STEPS = {
    1: (
        "Recomponha, pelas Cartas de Emergência, a existência do posto que continuou "
        "recebendo ordens.",
        "reconstruct_from_letters",
    ),
    2: ("Localize os três selos distintos de validade física dentro da Bastilha.", None),
    3: (
        "Autorize narrativamente a abertura do posto de serviço lacrado.",
        "authorize_service_post",
    ),
    4: (
        "Verifique que o protocolo em execução já não possui função civil vigente.",
        "verify_no_current_civil_function",
    ),
    5: ("Enfrente o Custódio do Último Turno no posto de serviço.", None),
    6: ("Derrote o Custódio do Último Turno.", None),
    7: ("Registre no Bestiário apenas os fatos observados no encontro.", "record_bestiary_facts"),
    8: ("Registre no Códice A Ordem que Restou.", "record_codex"),
    9: ("Retorne a Sel Ardan para concluir a missão.", "conclude_with_sel"),
}


def render_s30(view: S30View) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "giver":
        if view.status == "active":
            state = "Em Andamento"
            rows.append([_button("Retomar A Ordem que Restou", "s30:resume")])
        elif view.status == "completed":
            state = "Concluída"
            rows.append([_button("Ver registro da missão", "s30:resume")])
        elif view.reacceptable:
            state = "Disponível para reaceite"
            rows.append([_button("Reaceitar Missão", f"s30:reaccept:{view.state_version}")])
        elif view.available:
            state = "Disponível"
            rows.append([_button("Conhecer a missão", "s30:offer")])
        else:
            state = "Indisponível · requer S28, P29, Nv.50 e acesso à Bastilha"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"📜 Sel Ardan\nAltos Cinéreos · {view.location}\n\nA Ordem que Restou · {state}",
            "s30_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if not view.available and not view.reacceptable:
            body = (
                "Requer S28 concluída, P29 concluída, Nv.50 e acesso legítimo à Bastilha. "
                "P30 e S29 não são requisitos."
            )
            accept_rows = [[_button("← Sel Ardan", "s30:sel")]]
        else:
            body = (
                "Reconstrua a existência do posto, examine três selos físicos, autorize sua "
                "abertura durante a missão e verifique o protocolo em execução. O encontro "
                "com o Custódio não concede recompensas econômicas; a recompensa pertence "
                "à conclusão de S30."
            )
            accept = (
                _button("Reaceitar Missão", f"s30:reaccept:{view.state_version}")
                if view.reacceptable
                else _button("Aceitar Missão", "s30:accept:0")
            )
            accept_rows = [[accept], [_button("← Sel Ardan", "s30:sel")]]
        return Screen(
            "📜 A Ordem que Restou\nMissão Secundária Longa · Altos Cinéreos\n\n"
            f"Sel Ardan · Bastilha de Carga\n\n{body}\n\n"
            "✨ 74.500 XP · 🪙 1.060 Coroas\n"
            "🧰 2 Ferros de Contrapeso · 2 Couros de Escarpa · "
            "2 Líquens de Pedreira · 2 Cinzas de Basalto",
            "s30_offer",
            InlineKeyboardMarkup(inline_keyboard=accept_rows),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 A Ordem que Restou\n\n"
            f"Selos permanentes: {len(view.physical_seals)}/3 · "
            f"Vitória do Custódio: "
            f"{'preservada' if view.boss_victory_recorded else 'não registrada'}. "
            "Evidências permanentes serão mantidas no reaceite.",
            "s30_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s30:abandon_confirm:{view.state_version}")],
                    [_button("← Missão", "s30:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 A Ordem que Restou · Abandonada\n\n"
            f"Selos permanentes preservados: {len(view.physical_seals)}/3. "
            f"Vitória do Custódio: "
            f"{'preservada' if view.boss_victory_recorded else 'não registrada'}.",
            "s30_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Sel Ardan", "s30:sel")]]),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ A Ordem que Restou · Concluída\nMissão Secundária · Altos Cinéreos\n\n"
            "📖 Códice · A Ordem que Restou\n"
            f"🏆 A Ordem que Restou · "
            f"{'Conquistado' if view.achievement_owned else 'Registrado'}\n\n"
            "O protocolo antigo permanece em execução, embora já não tenha função civil válida. "
            "O registro descreve o que foi observado; não atribui consciência ou intenção "
            "ao Custódio.\n\n"
            "✨ 74.500 XP · 🪙 1.060 Coroas\n"
            "🧰 2 Ferros de Contrapeso · 2 Couros de Escarpa · "
            "2 Líquens de Pedreira · 2 Cinzas de Basalto",
            "s30_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    objective = _STEPS.get(view.step, ("Retome a etapa atual.", None))
    rows = []
    if view.step == 2 and view.action_available:
        for seal_id in S30_PHYSICAL_SEALS:
            if seal_id not in view.physical_seals:
                suffix = seal_id.rsplit("_", 1)[-1]
                rows.append(
                    [
                        _button(
                            f"Localizar {_SEAL_LABELS[seal_id]}",
                            f"s30:action:{view.state_version}:locate_seal_{suffix}",
                        )
                    ]
                )
    elif view.step == 5:
        if view.progress.get("awaiting_retry"):
            if view.location == "Bastilha de Carga":
                rows.append([_button("Tentar novamente", f"altos:retry:S30:{view.state_version}")])
            else:
                rows.append([_button("Retornar à Bastilha", "road:route:altos_bastilha")])
        elif view.location == "Bastilha de Carga":
            rows.extend(
                (
                    [_button("Enfrentar Solo", f"altos:combat:S30:{view.state_version}:solo")],
                    [_button("Enfrentar em Grupo", f"altos:combat:S30:{view.state_version}:group")],
                )
            )
        else:
                rows.append([_button("Ir à Bastilha", "road:route:altos_bastilha")])
    elif objective[1] is not None and view.action_available:
        rows.append([_button("Executar etapa", f"s30:action:{view.state_version}:{objective[1]}")])
    else:
        rows.append([_button("Ver Mapa", "world:map")])

    rows.append(
        [
            _button(
                "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                f"s30:track:{view.state_version}",
            )
        ]
    )
    rows.extend(
        [
            [_button("Abandonar Missão", "s30:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    text = (
        f"📜 A Ordem que Restou · Em Andamento\nAltos Cinéreos · "
        f"{view.location or 'Bastilha de Carga'}\n\n"
        f"🎯 Etapa {min(view.step, 9)}/9 · {objective[0]}"
    )
    if view.step == 2:
        text += f"\nSelos localizados: {len(view.physical_seals)}/3"
    if view.step == 7:
        text += "\nOs fatos de Conhecimento refletem somente ações e comportamentos observados."
    if not view.action_available and view.step not in {5}:
        text += "\n\n📍 Esta etapa exige acesso atual à Bastilha de Carga."
    return Screen(
        text,
        "s30_objective" if view.kind == "objective" else "s30_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
