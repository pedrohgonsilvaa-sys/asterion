"""Telegram presentation for the Vales S7/P8 mission slice."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.vde_missions import S7_ID, VDEMissionView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _screen(text: str, rows: list[list[InlineKeyboardButton]], image: str = "missions"):
    return Screen(text, image, InlineKeyboardMarkup(inline_keyboard=rows))


def render_vde_mission(view: VDEMissionView) -> Screen:
    quest = view.quest_id
    version = view.state_version
    title = escape(view.title)
    location = escape(view.location)

    if view.kind == "combat" and view.combat is not None and view.activity_id is not None:
        hud = render_combat(
            CombatView(
                activity_id=view.activity_id,
                encounter_id=view.encounter_id or view.activity_id,
                character_id=view.character_id,
                combat=view.combat,
                stage="campaign",
                xp=0,
                context="vde",
                consumable_options=view.consumable_options,
                consumable_screen=view.consumable_screen,
                selected_consumable_id=view.selected_consumable_id,
                selected_target_id=view.selected_target_id,
                selection_parent=view.selection_parent,
                consumable_notice=view.consumable_notice,
                consumable_quantities=view.consumable_quantities,
                consumable_budget_limit=view.consumable_budget_limit,
                ready_consumable_option=view.ready_consumable_option,
                combat_actor_key=view.combat_actor_key,
            )
        )
        kind = "secondary" if quest == S7_ID else "principal"
        return Screen(
            f"📜 {title} · Vales dos Enforcados\n⚔️ Encontro Roteirizado · {location}\n\n{hud.text}",
            f"vde_{kind}",
            hud.keyboard,
            parse_mode=hud.parse_mode,
        )

    if view.kind == "combat_result":
        result = (
            "Vitória"
            if (view.progress or {}).get("result") == "completed"
            else "Encontro encerrado"
        )
        return _screen(
            f"⚔️ Encontro roteirizado · {result}\n\nSua participação foi registrada.",
            [[_button("← Missões", "world:missions")]],
            "vde_missions",
        )

    if view.kind == "offer":
        gate = (
            "P7 concluída · Nv.12 · Garganta dos Laços"
            if quest == S7_ID
            else "P7 concluída · Nv.13 · Vigília do Vale"
        )
        return _screen(
            f"📜 {title}\nMissão {('Secundária' if quest == S7_ID else 'Principal')} · "
            "Vales dos Enforcados\n\n"
            f"Requer · {gate}\n\n"
            "Acompanhe os sinais e os caminhos registrados nesta etapa.",
            [
                [_button("Aceitar Missão", f"vde:{quest}:start")],
                [_button("← Missões", "world:missions")],
            ],
        )

    if view.kind == "unavailable":
        gate = (
            "P7 concluída, Nv.12 e estar na Garganta dos Laços"
            if quest == S7_ID
            else "P7 concluída, Nv.13 e estar na Vigília do Vale"
        )
        return _screen(
            f"📜 {title} · Indisponível\n\nRequer {gate}.",
            [[_button("← Missões", "world:missions")]],
        )

    if view.kind == "completed":
        reward = (
            "✨ 3.840 XP · 🪙 140 Coroas"
            if quest == S7_ID
            else (
                "✨ 10.500 XP · 🪙 300 Coroas\n"
                "📦 Ferro Enredado · 1 · Vinculado\n"
                "📦 Erva de Turfa · 2 · Vinculada\n"
                "📦 Resina Enredada · 1 · Vinculada"
            )
        )
        return _screen(
            f"✅ {title} · Concluída\n\n{reward}",
            [[_button("← Missões", "world:missions")]],
        )

    progress = view.progress or {}
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "markers":
        found = set(progress.get("markers", ()))
        for point, label in (
            ("a", "Examinar marcação 1"),
            ("b", "Examinar marcação 2"),
            ("c", "Examinar marcação 3"),
        ):
            if point not in found:
                rows.append([_button(label, f"vde:{quest}:{version}:ex:{point}")])
        text = (
            f"📜 {title} · Garganta dos Laços\n\n"
            "🎯 Examinar três marcações de rota.\n"
            f"Progresso · {len(found)}/3"
        )
    elif view.kind == "combat_start":
        text = (
            f"📜 {title} · {location}\n\n🎯 Derrotar a criatura que ocupa o ponto investigado.\n\n"
            "O conteúdo regional não identifica uma espécie para este encontro."
        )
        rows.extend(
            [
                [_button("Enfrentar Solo", f"vde:{quest}:{version}:solo")],
                [_button("Formar/Usar Grupo", f"vde:{quest}:{version}:group")],
                [_button("Grupo", "group:root")],
            ]
        )
    elif view.kind == "retry":
        text = (
            "❌ Encontro encerrado\n✅ Etapas anteriores preservadas\n"
            f"📍 {location}\n❤️ HP restaurado\n\nVocê pode tentar novamente."
        )
        rows.extend(
            [
                [_button("Tentar Solo", f"vde:{quest}:{version}:solo")],
                [_button("Formar/Usar Grupo", f"vde:{quest}:{version}:group")],
            ]
        )
    elif view.kind == "rope":
        text = (
            f"📜 {title} · Garganta dos Laços\n\n"
            "🎯 Encontrar a corda ainda presa à estrutura acima do caminho."
        )
        rows.append([_button("Examinar a corda", f"vde:{quest}:{version}:rope")])
    elif view.kind == "report":
        text = (
            f"📜 {title} · Vigília do Vale\n\n"
            "🎯 Retornar a Dara Venn.\n\n"
            "As raízes alteraram fisicamente o terreno e deslocaram as marcações. "
            "Não há confirmação de sabotagem."
        )
        if view.location == "Vigília do Vale":
            rows.append([_button("Relatar a Dara Venn", f"vde:{quest}:{version}:report")])
        else:
            rows.append([_button("Seguir para a Vigília", "road:route:vde_vigilia")])
    elif view.kind == "enter_mata":
        text = (
            f"📜 {title}\n\n🎯 Entrar na Mata Suspensa.\n\n"
            "A rota narrativa está aberta a partir da Vigília do Vale."
        )
        if view.location == "Vigília do Vale":
            rows.append([_button("Seguir para a Mata", "road:route:vde_mata")])
        elif view.location == "Mata Suspensa":
            rows.append([_button("Registrar entrada na Mata", f"vde:{quest}:{version}:enter")])
    elif view.kind == "roots":
        found = set(progress.get("roots", ()))
        for point, label in (
            ("a", "Examinar concentração 1"),
            ("b", "Examinar concentração 2"),
            ("c", "Examinar concentração 3"),
        ):
            if point not in found:
                rows.append([_button(label, f"vde:{quest}:{version}:ex:{point}")])
        text = (
            f"📜 {title} · Mata Suspensa\n\n"
            "🎯 Examinar três concentrações de raízes.\n"
            f"Progresso · {len(found)}/3"
        )
    elif view.kind == "compare":
        text = (
            f"📜 {title} · Mata Suspensa\n\n"
            "🎯 Comparar a direção das três concentrações de raízes."
        )
        rows.append([_button("Comparar as direções", f"vde:{quest}:{version}:compare")])
    elif view.kind == "masonry":
        text = (
            f"📜 {title} · Mata Suspensa\n\n"
            "🎯 Encontrar fragmentos de alvenaria antiga sob uma das concentrações."
        )
        rows.append([_button("Examinar sob as raízes", f"vde:{quest}:{version}:masonry")])
    elif view.kind == "record":
        text = (
            f"📜 {title} · Mata Suspensa\n\n"
            "As raízes convergem para linhas antigas sob o solo; "
            "o crescimento não parece aleatório.\n\n"
            "🎯 Registrar o achado no Códice."
        )
        rows.append([_button("Registrar no Códice", f"vde:{quest}:{version}:record")])
    elif view.kind == "return_vigilia":
        text = f"📜 {title}\n\n🎯 Retornar à Vigília do Vale."
        if view.location == "Mata Suspensa":
            rows.append([_button("Retornar à Vigília", "road:route:vde_vigilia")])
        elif view.location == "Vigília do Vale":
            rows.append([_button("Relatar a Dara Venn", f"vde:{quest}:{version}:return")])
    else:
        text = f"📜 {title} · Em Andamento\n\nLocal · {location}"
        rows.append([_button("Atualizar", f"vde:{quest}:resume")])

    rows.append([_button("← Missões", "world:missions")])
    return _screen(text, rows, "vde_missions")


def render_vde_board(s7: VDEMissionView | None, p8: VDEMissionView | None) -> Screen:
    lines = ["📜 Missões · Vales dos Enforcados", ""]
    rows: list[list[InlineKeyboardButton]] = []
    for view, required_level, required_location, icon in (
        (s7, 12, "Garganta dos Laços", "📖"),
        (p8, 13, "Vigília do Vale", "🔥"),
    ):
        if view is None:
            continue
        label = view.title
        if view.status == "active":
            state, action = "Em Andamento", f"vde:{view.quest_id}:resume"
        elif view.status == "completed":
            state, action = "Concluída", f"vde:{view.quest_id}:resume"
        elif view.available:
            state, action = "Disponível", f"vde:{view.quest_id}:start"
        else:
            state, action = f"Requer Nv.{required_level} · {required_location}", None
        lines.append(f"{icon} {label} · {state}")
        if action:
            rows.append([_button(label, action)])
    rows.append([_button("← Aventura", "world:adventure")])
    return _screen("\n".join(lines), rows)
