"""Telegram screens for S33 — Nomes em Ordem Errada."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.s33 import S33_FIELD_INSCRIPTIONS, S33View
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


_INSCRIPTION_LABELS = {
    S33_FIELD_INSCRIPTIONS[0]: "Examinar a primeira inscrição de campo",
    S33_FIELD_INSCRIPTIONS[1]: "Examinar a segunda inscrição de campo",
}


def render_s33(view: S33View) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "giver":
        if view.status == "active":
            state = "Em Andamento"
            rows.append([_button("Retomar missão", "s33:resume")])
        elif view.status == "completed":
            state = "Concluída"
            rows.append([_button("Ver registro da missão", "s33:resume")])
        elif view.reacceptable:
            state = "Disponível para reaceite"
            rows.append([_button("Reaceitar Missão", f"s33:reaccept:{view.state_version}")])
        elif view.available:
            state = "Disponível"
            rows.append([_button("Conhecer a missão", "s33:offer")])
        else:
            state = "Indisponível · requer P33 concluída + Nv.55"
        rows.append([_button("← Local Atual", "world:local")])
        return Screen(
            f"📜 Roven Pell · Último Refúgio\n\nNomes em Ordem Errada · {state}",
            "s33_giver",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "offer":
        if view.status in {"active", "completed"}:
            rows.append([_button("Abrir missão", "s33:resume")])
            body = "A missão já possui um estado persistente."
        elif view.available or view.reacceptable:
            callback = (
                f"s33:reaccept:{view.state_version}"
                if view.reacceptable
                else "s33:accept:0"
            )
            rows.append(
                [_button("Reaceitar Missão" if view.reacceptable else "Aceitar Missão", callback)]
            )
            body = (
                "Roven apresenta duas listas para reconciliar. Uma diferença é um erro de cópia "
                "comprovável; outra discrepância material permanece sem solução."
            )
        else:
            body = "Disponível após P33 concluída e ao atingir Nv.55."
        rows.append([_button("← Roven Pell", "s33:roven")])
        return Screen(
            "📜 Nomes em Ordem Errada\nMissão Secundária Curta · Confins do Véu\n\n"
            f"Roven Pell · Último Refúgio\n\n{body}\n\n"
            "✨ 35.060 XP · 🪙 460 Coroas · Ferro de Baliza ×1 · Musgo de Limiar ×1",
            "s33_offer",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )

    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 Nomes em Ordem Errada\n\n"
            f"Inscrições preservadas: {len(view.field_inscriptions)}/2. "
            "Evidências consolidadas e o Códice permanecem com o personagem.",
            "s33_abandon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [_button("Confirmar Abandono", f"s33:abandon_confirm:{view.state_version}")],
                    [_button("← Missão", "s33:resume")],
                ]
            ),
        )

    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(
            "📜 Nomes em Ordem Errada · Abandonada\n\n"
            f"Inscrições preservadas: {len(view.field_inscriptions)}/2 · "
            f"Códice preservado: {'sim' if view.codex_owned else 'não'}.",
            "s33_abandoned",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Roven Pell", "s33:roven")]]),
        )

    if view.status == "completed" or view.kind == "completed":
        return Screen(
            "✅ Nomes em Ordem Errada · Concluída\nMissão Secundária · Confins do Véu\n\n"
            "O Códice mantém as duas listas e inscrições: o erro de cópia comprovável e a "
            "discrepância material não resolvida. A diferença não estabelece uma causa além "
            "das evidências observadas.\n\n"
            "✨ 35.060 XP · 🪙 460 Coroas · Ferro de Baliza ×1 · Musgo de Limiar ×1",
            "s33_completed",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Missões", "world:missions")]]),
        )

    if view.step == 2 and view.action_available:
        for inscription_id in S33_FIELD_INSCRIPTIONS:
            if inscription_id not in view.field_inscriptions:
                action = "a" if inscription_id == S33_FIELD_INSCRIPTIONS[0] else "b"
                rows.append(
                    [
                        _button(
                            _INSCRIPTION_LABELS[inscription_id],
                            f"s33:action:{view.state_version}:inspect_inscription_{action}",
                        )
                    ]
                )
    elif view.step == 3 and view.action_available:
        rows.append(
            [
                _button(
                    "Analisar as duas listas com Roven",
                    f"s33:action:{view.state_version}:analyze_documents",
                )
            ]
        )
    elif view.step == 4 and view.action_available:
        rows.append(
            [_button("Registrar no Códice", f"s33:action:{view.state_version}:record_codex")]
        )
    elif view.step == 5 and view.action_available:
        rows.append(
            [
                _button(
                    "Concluir com Roven Pell",
                    f"s33:action:{view.state_version}:conclude_with_roven",
                )
            ]
        )
    else:
        rows.append([_button("Ver Mapa", "world:map")])

    rows.append(
        [
            _button(
                "Deixar de Acompanhar" if view.tracked else "Acompanhar",
                f"s33:track:{view.state_version}",
            )
        ]
    )
    rows.extend(
        [
            [_button("Abandonar Missão", "s33:abandon")],
            [_button("← Missões", "world:missions")],
        ]
    )
    objectives = {
        2: "Localize as duas inscrições físicas distintas nas Fraturas do Limiar.",
        3: "Compare pessoalmente as listas e inscrições com Roven Pell no Último Refúgio.",
        4: "Registre no Códice o erro de cópia comprovável e a discrepância não resolvida.",
        5: "Conclua pessoalmente a missão com Roven Pell.",
    }
    text = (
        "📜 Nomes em Ordem Errada · Em Andamento\n"
        f"Confins do Véu · {view.location or 'Último Refúgio'}\n\n"
        f"🎯 Etapa {view.step}/5 · {objectives.get(view.step, 'Retome a etapa atual.')}"
    )
    if view.step == 2:
        text += f"\nInscrições de campo: {len(view.field_inscriptions)}/2"
    elif view.step == 3:
        text += "\nA análise mantém as duas listas e não atribui toda discrepância ao Avesso."
    if not view.action_available:
        expected = "Fraturas do Limiar" if view.step == 2 else "Último Refúgio"
        text += f"\n\n📍 Esta etapa requer estar em {expected}, P33 concluída e Nv.55."
    return Screen(
        text,
        "s33_objective" if view.kind == "objective" else "s33_detail",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
