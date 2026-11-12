"""Telegram screens for S32 — A Casa que Não Chegou."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s32 import (
    S32_DOCUMENT_CARDS,
    S32_FOUNDATION_ELEMENTS,
    S32View,
)
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_FOUNDATION_LABELS = {
    S32_FOUNDATION_ELEMENTS[0]: "Reconhecer a primeira parte da fundação",
    S32_FOUNDATION_ELEMENTS[1]: "Reconhecer a segunda parte da fundação",
    S32_FOUNDATION_ELEMENTS[2]: "Reconhecer a terceira parte da fundação",
}
_CARD_LABELS = {
    S32_DOCUMENT_CARDS[0]: "Recuperar a ficha de presença",
    S32_DOCUMENT_CARDS[1]: "Recuperar a ficha de ausência",
}


def render_s32(view: S32View) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "giver":
        if view.status == "active":
            state = "Em Andamento"
            rows.append([_button("Retomar missão", "s32:resume")])
        elif view.status == "completed":
            state = "Concluída"
            rows.append([_button("Ver registro da missão", "s32:resume")])
        elif view.reacceptable:
            state = "Disponível para reaceite"
            rows.append([_button("Reaceitar Missão", f"s32:reaccept:{view.state_version}")])
        elif view.available:
            state = "Disponível"
            rows.append([_button("Conhecer a missão", "s32:offer")])
        else:
            state = "Indisponível · requer P32 concluída + Nv.54"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"📜 Haro Sen · Último Refúgio\n\nA Casa que Não Chegou · {state}",
            "s32_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if view.status in {"active", "completed"}:
            rows.append([_button("Abrir missão", "s32:resume")])
            body = "O relato já possui um estado persistente."
        elif view.available or view.reacceptable:
            callback = (
                f"s32:reaccept:{view.state_version}"
                if view.reacceptable
                else "s32:accept:0"
            )
            rows.append(
                [_button("Reaceitar Missão" if view.reacceptable else "Aceitar Missão", callback)]
            )
            body = (
                "Haro relata uma casa cuja base aparece em dois registros. A missão compara "
                "presença e ausência sem apagar nenhum dos relatos."
            )
        else:
            body = "Disponível após P32 concluída e ao atingir Nv.54."
        rows.append([_button("← Haro Sen", "s32:haro")])
        return Screen(
            "📜 A Casa que Não Chegou\nMissão Secundária Padrão · Confins do Véu\n\n"
            f"Haro Sen · Último Refúgio\n\n{body}\n\n"
            "✨ 59.465 XP · 🪙 680 Coroas · Couro de Marcha ×1 · Musgo de Limiar ×1",
            "s32_offer",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 A Casa que Não Chegou\n\n"
            f"Fundação: {len(view.foundation_elements)}/3 · Fichas: {len(view.document_cards)}/2 · "
            f"Vitória roteirizada: {'registrada' if view.victory_recorded else 'não registrada'}. "
            "Evidências consolidadas e fragmentos do Códice serão preservados.",
            "s32_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s32:abandon_confirm:{view.state_version}")],
                    [_button("← Missão", "s32:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 A Casa que Não Chegou · Abandonada\n\n"
            f"Fundação preservada: {len(view.foundation_elements)}/3 · "
            f"Fichas preservadas: {len(view.document_cards)}/2 · "
            f"Vitória preservada: {'sim' if view.victory_recorded else 'não'}.",
            "s32_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Haro Sen", "s32:haro")]]),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ A Casa que Não Chegou · Concluída\nMissão Secundária · Confins do Véu\n\n"
            "📖 Códice · presença e ausência permanecem registradas como evidências distintas. "
            "A discrepância não prova viagem temporal, portal, dimensão adicional ou pessoa "
            "duplicada.\n\n"
            "✨ 59.465 XP · 🪙 680 Coroas · Couro de Marcha ×1 · Musgo de Limiar ×1",
            "s32_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    if view.step == 2 and view.action_available:
        for evidence_id, action in zip(
            S32_FOUNDATION_ELEMENTS,
            ("recognize_foundation_a", "recognize_foundation_b", "recognize_foundation_c"),
            strict=True,
        ):
            if evidence_id not in view.foundation_elements:
                rows.append(
                    [
                        _button(
                            _FOUNDATION_LABELS[evidence_id],
                            f"s32:action:{view.state_version}:{action}",
                        )
                    ]
                )
    elif view.step == 3 and view.action_available:
        for evidence_id, action in zip(
            S32_DOCUMENT_CARDS,
            ("recover_presence_card", "recover_absence_card"),
            strict=True,
        ):
            if evidence_id not in view.document_cards:
                rows.append(
                    [
                        _button(
                            _CARD_LABELS[evidence_id],
                            f"s32:action:{view.state_version}:{action}",
                        )
                    ]
                )
    elif view.step == 4 and view.action_available:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:S32:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Enfrentar Solo", f"altos:combat:S32:{view.state_version}:solo")],
                )
            )
    elif view.step == 5 and view.action_available:
        rows.append(
            [
                _button(
                    "Comparar as fichas com Roven",
                    f"s32:action:{view.state_version}:compare_with_roven",
                )
            ]
        )
    elif view.step == 6 and view.action_available:
        if not view.codex_recorded:
            rows.append(
                [_button("Registrar no Códice", f"s32:action:{view.state_version}:record_codex")]
            )
        else:
            rows.append(
                [
                    _button(
                        "Concluir com Haro Sen",
                        f"s32:action:{view.state_version}:conclude_with_haro",
                    )
                ]
            )
    else:
        rows.append([_button("Ver Mapa", "world:map")])

    rows.append(
        [
            _button(
                "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                f"s32:track:{view.state_version}",
            )
        ]
    )
    rows.extend(
        [
            [_button("Abandonar Missão", "s32:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    objectives = {
        2: "Reconheça três elementos físicos distintos da fundação nas Estradas Ausentes.",
        3: "Recupere as fichas distintas que registram presença e ausência.",
        4: "Enfrente uma Aranha de Limiar Nv.54 em combate roteirizado.",
        5: "Compare pessoalmente as duas fichas com Roven Pell no Último Refúgio.",
        6: "Registre as evidências no Códice e conclua pessoalmente com Haro Sen.",
    }
    text = (
        "📜 A Casa que Não Chegou · Em Andamento\n"
        f"Confins do Véu · {view.location or 'Último Refúgio'}\n\n"
        f"🎯 Etapa {view.step}/6 · {objectives.get(view.step, 'Retome a etapa atual.')}"
    )
    if view.step == 2:
        text += f"\nElementos físicos reconhecidos: {len(view.foundation_elements)}/3"
    elif view.step == 3:
        text += f"\nFichas recuperadas: {len(view.document_cards)}/2"
    elif view.step == 4 and view.progress.get("awaiting_retry"):
        text += "\nA derrota não avançou a missão; o encontro pode ser tentado novamente."
    elif view.step == 6 and view.exploration_fragment_owned:
        text += (
            "\nO fragmento Memória de Fundação já consta no Códice; "
            "a conclusão de S32 permanece independente."
        )
    if not view.action_available:
        expected = "Estradas Ausentes" if view.step in {2, 3, 4} else "Último Refúgio"
        text += f"\n\n📍 Esta etapa requer estar em {expected}, P32 concluída e Nv.54."
    return Screen(
        text,
        "s32_objective" if view.kind == "objective" else "s32_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
