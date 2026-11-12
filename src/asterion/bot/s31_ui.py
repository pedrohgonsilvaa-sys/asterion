"""Telegram screens for S31 — Duas Vezes a Mesma Estrada."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s31 import S31_IMPRESSIONS, S31_TRAIL_POINTS, S31View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_POINT_LABELS = {
    S31_TRAIL_POINTS[0]: "Observar o primeiro ponto da trilha",
    S31_TRAIL_POINTS[1]: "Observar o segundo ponto da trilha",
    S31_TRAIL_POINTS[2]: "Observar o terceiro ponto da trilha",
}
_IMPRESSION_LABELS = {
    S31_IMPRESSIONS[0]: "Registrar a primeira impressão plausível",
    S31_IMPRESSIONS[1]: "Registrar a segunda impressão plausível",
}


def render_s31(view: S31View) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "giver":
        if view.status == "active":
            state = "Em Andamento"
            rows.append([_button("Retomar levantamento", "s31:resume")])
        elif view.status == "completed":
            state = "Concluída"
            rows.append([_button("Ver registro da missão", "s31:resume")])
        elif view.reacceptable:
            state = "Disponível para reaceite"
            rows.append([_button("Reaceitar Missão", f"s31:reaccept:{view.state_version}")])
        elif view.available:
            state = "Disponível"
            rows.append([_button("Conhecer a missão", "s31:offer")])
        else:
            state = "Indisponível · requer P31 concluída + Nv.52"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"📜 Talen Nyr\nConfins do Véu · {view.location}\n\n"
            f"Duas Vezes a Mesma Estrada · {state}",
            "s31_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if view.status in {"active", "completed"}:
            rows.append([_button("Abrir missão", "s31:resume")])
            body = "O levantamento já possui um estado persistente."
        elif view.available or view.reacceptable:
            callback = (
                f"s31:reaccept:{view.state_version}"
                if view.reacceptable
                else "s31:accept:0"
            )
            rows.append(
                [_button("Reaceitar Missão" if view.reacceptable else "Aceitar Missão", callback)]
            )
            body = (
                "Talen propõe observar três pontos da mesma trilha e comparar duas impressões "
                "plausíveis. A diferença será registrada sem afirmar clones ou viagem no tempo."
            )
        else:
            rows.append([_button("← Talen Nyr", "s31:talen")])
            body = "Disponível na Marcha Nebulosa após P31 concluída e ao atingir Nv.52."
        rows.append([_button("← Talen Nyr", "s31:talen")])
        return Screen(
            "📜 Duas Vezes a Mesma Estrada\nMissão Secundária Curta · Confins do Véu\n\n"
            f"Talen Nyr · Marcha Nebulosa\n\n{body}\n\n"
            "✨ 31.860 XP · 🪙 440 Coroas",
            "s31_offer",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 Duas Vezes a Mesma Estrada\n\n"
            f"Pontos permanentes: {len(view.trail_points)}/3 · "
            f"Impressões: {len(view.impressions)}/2 · "
            f"Vitória roteirizada: {'registrada' if view.victory_recorded else 'não registrada'}. "
            "As evidências já consolidadas serão preservadas.",
            "s31_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s31:abandon_confirm:{view.state_version}")],
                    [_button("← Missão", "s31:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 Duas Vezes a Mesma Estrada · Abandonada\n\n"
            f"Pontos preservados: {len(view.trail_points)}/3 · "
            f"Impressões preservadas: {len(view.impressions)}/2 · "
            f"Vitória preservada: {'sim' if view.victory_recorded else 'não'}.",
            "s31_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Talen Nyr", "s31:talen")]]),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ Duas Vezes a Mesma Estrada · Concluída\n"
            "Missão Secundária · Confins do Véu\n\n"
            "📖 Códice · Duas Vezes a Mesma Estrada\n"
            "As duas leituras plausíveis permanecem registradas. A discrepância não demonstra "
            "cópias conscientes de criaturas ou pessoas.\n\n"
            "✨ 31.860 XP · 🪙 440 Coroas",
            "s31_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    if view.step == 2 and view.action_available:
        for point_id in S31_TRAIL_POINTS:
            if point_id not in view.trail_points:
                action = f"observe_trail_point_{point_id.rsplit('_', 1)[-1]}"
                rows.append(
                    [_button(_POINT_LABELS[point_id], f"s31:action:{view.state_version}:{action}")]
                )
    elif view.step == 3 and view.action_available:
        for impression_id in S31_IMPRESSIONS:
            if impression_id not in view.impressions:
                action = f"record_impression_reading_{impression_id.rsplit('_', 1)[-1]}"
                rows.append(
                    [
                        _button(
                            _IMPRESSION_LABELS[impression_id],
                            f"s31:action:{view.state_version}:{action}",
                        )
                    ]
                )
    elif view.step == 4 and view.action_available:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:S31:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Enfrentar Solo", f"altos:combat:S31:{view.state_version}:solo")],
                )
            )
    elif view.step == 5 and view.action_available:
        rows.append(
            [
                _button(
                    "Comparar as evidências com Talen",
                    f"s31:action:{view.state_version}:compare_with_talen",
                )
            ]
        )
    elif view.step == 6 and view.action_available:
        rows.append(
            [_button("Concluir com Talen", f"s31:action:{view.state_version}:conclude_with_talen")]
        )
    else:
        rows.append([_button("Ver Mapa", "world:map")])

    rows.append(
        [
            _button(
                "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                f"s31:track:{view.state_version}",
            )
        ]
    )
    rows.extend(
        [
            [_button("Abandonar Missão", "s31:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    objectives = {
        2: "Observe três pontos físicos distintos da mesma trilha na Marcha Nebulosa.",
        3: "Registre duas impressões plausíveis com quantidades diferentes de passadas.",
        4: "Enfrente uma Gralha de Duas Sombras Nv.52 em encontro roteirizado.",
        5: "Compare pessoalmente as evidências com Talen e registre o Códice.",
        6: "Conclua pessoalmente o levantamento com Talen.",
    }
    text = (
        f"📜 Duas Vezes a Mesma Estrada · Em Andamento\n"
        f"Confins do Véu · {view.location or 'Marcha Nebulosa'}\n\n"
        f"🎯 Etapa {view.step}/6 · {objectives.get(view.step, 'Retome a etapa atual.')}"
    )
    if view.step == 2:
        text += f"\nPontos distintos observados: {len(view.trail_points)}/3"
    elif view.step == 3:
        text += f"\nImpressões incompatíveis: {len(view.impressions)}/2"
    elif view.step == 4 and view.progress.get("awaiting_retry"):
        text += "\nA derrota não avançou a missão; o encontro pode ser tentado novamente."
    if not view.action_available:
        text += "\n\n📍 As interações de S31 exigem a Marcha Nebulosa, P31 concluída e Nv.52."
    return Screen(
        text,
        "s31_objective" if view.kind == "objective" else "s31_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
