"""Telegram presentation for the Vales S7/P8 mission slice."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.vde_missions import (
    P9_ID,
    S7_ID,
    S8_ID,
    S9_ID,
    VDEMissionView,
)
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
        kind = "secondary" if quest in {S7_ID, S8_ID, S9_ID} else "principal"
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
        gate = {
            S7_ID: "P7 concluída · Nv.12 · Garganta dos Laços",
            "P8": "P7 concluída · Nv.13 · Vigília do Vale",
            S8_ID: "P8 concluída · Nv.14 · Mata Suspensa",
            P9_ID: "P8 concluída · Nv.15 · Mata Suspensa",
            S9_ID: "P9 ativa ou concluída · Nv.15 · Baixios Enredados",
        }[quest]
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
        gate = {
            S7_ID: "P7 concluída, Nv.12 e estar na Garganta dos Laços",
            "P8": "P7 concluída, Nv.13 e estar na Vigília do Vale",
            S8_ID: "P8 concluída, Nv.14 e estar na Mata Suspensa",
            P9_ID: "P8 concluída, Nv.15 e estar na Mata Suspensa",
            S9_ID: "P9 ativa ou concluída, Nv.15 e estar nos Baixios Enredados",
        }[quest]
        return _screen(
            f"📜 {title} · Indisponível\n\nRequer {gate}.",
            [[_button("← Missões", "world:missions")]],
        )

    if view.kind == "completed":
        reward = {
            S7_ID: "✨ 3.840 XP · 🪙 140 Coroas",
            "P8": (
                "✨ 10.500 XP · 🪙 300 Coroas\n"
                "📦 Ferro Enredado · 1 · Vinculado\n"
                "📦 Erva de Turfa · 2 · Vinculada\n"
                "📦 Resina Enredada · 1 · Vinculada"
            ),
            S8_ID: (
                "✨ 8.015 XP · 🪙 230 Coroas\n"
                "📦 Erva de Turfa · 1 · Vinculada\n"
                "📦 Resina Enredada · 1 · Vinculada"
            ),
            P9_ID: (
                "✨ 12.450 XP · 🪙 330 Coroas\n"
                "🎁 "
                + escape(
                    {
                        "1": "Capuz das Copas Suspensas",
                        "2": "Selo do Caminho Enredado",
                        "3": "Relicário do Nó Velado",
                    }.get(str((view.progress or {}).get("reward_choice")), "Equipamento Raro Nv.15")
                )
                + " · Vinculado"
            ),
            S9_ID: (
                "✨ 4.980 XP · 🪙 170 Coroas\n"
                "📦 Couro Musgoso · 2 · Vinculado"
            ),
        }.get(quest, "")
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
    elif view.kind == "report" and quest == S7_ID:
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
    elif view.kind == "passage":
        text = (
            f"📜 {title} · Mata Suspensa\n\n"
            "🎯 Alcançar uma passagem de suprimentos entre as passarelas."
        )
        if view.location == "Mata Suspensa":
            rows.append([_button("Examinar a passagem", f"vde:{quest}:{version}:passage")])
        else:
            rows.append([_button("Seguir para a Mata", "road:route:vde_mata")])
    elif view.kind == "structures":
        found_key = "structures"
        found = set(progress.get(found_key, ()))
        for point, label in (
            ("a", "Examinar ponto estrutural 1"),
            ("b", "Examinar ponto estrutural 2"),
            ("c", "Examinar ponto estrutural 3"),
        ):
            if point not in found:
                rows.append([_button(label, f"vde:{quest}:{version}:ex:{point}")])
        objective = (
            "Examinar três pontos estruturais."
            if quest == S8_ID
            else "Examinar três estruturas parcialmente soterradas."
        )
        text = f"📜 {title} · {location}\n\n🎯 {objective}\nProgresso · {len(found)}/3"
    elif view.kind == "hardware":
        found = len((progress or {}).get("hardware_sets", ()))
        text = (
            f"📜 {title} · Mata Suspensa\n\n"
            "🎯 Recuperar dois conjuntos de ferragens antigas ainda utilizáveis.\n"
            f"Progresso · {found}/2"
        )
        if view.location == "Mata Suspensa":
            rows.append(
                [_button("Recuperar conjunto de ferragens", f"vde:{quest}:{version}:hardware")]
            )
    elif view.kind == "alternate_route":
        text = f"📜 {title} · Mata Suspensa\n\n🎯 Marcar uma rota alternativa segura."
        if view.location == "Mata Suspensa":
            rows.append([_button("Marcar rota alternativa", f"vde:{quest}:{version}:route")])
    elif view.kind == "follow":
        text = (
            f"📜 {title} · Mata Suspensa\n\n"
            "🎯 Seguir o traçado encontrado durante a investigação anterior."
        )
        if view.location == "Mata Suspensa":
            rows.append([_button("Seguir o traçado", f"vde:{quest}:{version}:follow")])
        else:
            rows.append([_button("Retornar à Mata Suspensa", "road:route:vde_mata")])
    elif view.kind == "enter_baixios":
        text = f"📜 {title}\n\n🎯 Alcançar os Baixios Enredados."
        if view.location == "Mata Suspensa":
            rows.append([_button("Descer aos Baixios", "road:route:vde_baixios")])
        elif view.location == "Baixios Enredados":
            rows.append([_button("Registrar chegada", f"vde:{quest}:{version}:baixios")])
    elif view.kind == "inscription":
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "🎯 Encontrar uma inscrição asteriana danificada."
        )
        rows.append([_button("Examinar a inscrição", f"vde:{quest}:{version}:inscription")])
    elif view.kind == "fragment":
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "🎯 Recuperar um fragmento de marcação estrutural."
        )
        rows.append([_button("Recuperar fragmento", f"vde:{quest}:{version}:fragment")])
    elif view.kind == "choice":
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "O registro foi levado a Iven Raal. Escolha uma recompensa individual.\n\n"
            "✨ 12.450 XP · 🪙 330 Coroas\n"
            "🎁 1 Equipamento Raro · Nv.15 · Vinculado"
        )
        for choice, label in (
            ("1", "Capuz das Copas Suspensas · Cabeça"),
            ("2", "Selo do Caminho Enredado · Acessório"),
            ("3", "Relicário do Nó Velado · Artefato"),
        ):
            rows.append([_button(label, f"vde:{quest}:{version}:ch:{choice}")])
    elif view.kind == "locate":
        text = f"📜 {title} · Baixios Enredados\n\n🎯 Localizar uma Casca Errante."
        rows.append([_button("Investigar os rastros", f"vde:{quest}:{version}:locate")])
    elif view.kind == "fragments":
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "🎯 Examinar os fragmentos deixados pela criatura."
        )
        rows.append([_button("Examinar fragmentos", f"vde:{quest}:{version}:fragments")])
    elif view.kind == "sample":
        text = f"📜 {title} · Baixios Enredados\n\n🎯 Recuperar uma amostra sem valor econômico."
        rows.append([_button("Recuperar amostra", f"vde:{quest}:{version}:sample")])
    elif view.kind == "report" and quest == S8_ID:
        text = (
            f"📜 {title} · Vigília do Vale\n\n"
            "🎯 Retornar a Dara Venn. As rotas e passarelas foram adaptadas ao avanço das raízes."
        )
        if view.location == "Vigília do Vale":
            rows.append([_button("Relatar a Dara Venn", f"vde:{quest}:{version}:report")])
        else:
            rows.append([_button("Seguir para a Vigília", "road:route:vde_vigilia")])
    elif view.kind == "report" and quest == P9_ID:
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "🎯 Levar o registro a Iven Raal. "
            "A tradução aproximada permanece uma hipótese documental."
        )
        rows.append([_button("Entregar registro a Iven", f"vde:{quest}:{version}:report")])
    elif view.kind == "report" and quest == S9_ID:
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "A camada externa possui propriedades próximas de matéria vegetal. "
            "O interior não permite concluir com segurança o que a criatura era anteriormente.\n\n"
            "🎯 Retornar a Iven Raal."
        )
        rows.append([_button("Relatar a Iven", f"vde:{quest}:{version}:report")])
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
