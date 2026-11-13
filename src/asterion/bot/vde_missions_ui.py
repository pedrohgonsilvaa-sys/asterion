"""Telegram presentation for the Vales S7/P8 mission slice."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.vde_missions import (
    BAIXIOS,
    BERCO,
    CLAUSTRO,
    GARGANTA,
    MATA,
    P9_ID,
    P10_ID,
    P11_ID,
    P12_ID,
    P12_REWARD_CHOICES,
    S7_ID,
    S8_ID,
    S9_ID,
    S10_ID,
    S11_ID,
    S12_ID,
    VIGILIA,
    VDEMissionView,
)
from asterion.bot.asset_catalog import with_mission_art
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen
from asterion.domain.mission_coop import mission_coop_allowed


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _screen(text: str, rows: list[list[InlineKeyboardButton]], image: str = "missions"):
    return Screen(text, image, InlineKeyboardMarkup(inline_keyboard=rows))


def _route_toward(current: str, target: str) -> str | None:
    edges = {
        GARGANTA: (VIGILIA,),
        VIGILIA: (GARGANTA, MATA),
        MATA: (VIGILIA, BAIXIOS),
        BAIXIOS: (MATA, CLAUSTRO),
        CLAUSTRO: (BAIXIOS, BERCO),
        BERCO: (CLAUSTRO,),
    }
    route_keys = {
        GARGANTA: "vde_garganta",
        VIGILIA: "vde_vigilia",
        MATA: "vde_mata",
        BAIXIOS: "vde_baixios",
        CLAUSTRO: "vde_claustro",
        BERCO: "vde_berco",
    }
    if current == target or current not in edges or target not in edges:
        return None
    queue = [(current, None)]
    visited = {current}
    for location, first_hop in queue:
        for neighbor in edges[location]:
            if neighbor in visited:
                continue
            next_hop = neighbor if first_hop is None else first_hop
            if neighbor == target:
                return f"road:route:{route_keys[next_hop]}"
            visited.add(neighbor)
            queue.append((neighbor, next_hop))
    return None


def _render_vde_mission(view: VDEMissionView) -> Screen:
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
        kind = (
            "secondary"
            if quest in {S7_ID, S8_ID, S9_ID, S10_ID, S11_ID, S12_ID}
            else "principal"
        )
        encounter_type = "Chefe de Campanha" if quest == P12_ID else "Encontro Roteirizado"
        return Screen(
            f"📜 {title} · Vales dos Enforcados\n⚔️ {encounter_type} · {location}\n\n{hud.text}",
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
            P10_ID: "P9 concluída · Nv.17 · Baixios Enredados",
            S10_ID: "P10 ativa ou concluída · Nv.17 · Baixios Enredados",
            S11_ID: "Claustro das Raízes descoberto · Nv.18",
            P11_ID: "P10 concluída · Nv.19 · Claustro das Raízes",
            P12_ID: "P11 concluída · Nv.20 · Berço da Matriarca",
            S12_ID: "S10 e P11 concluídas · Nv.20 · Claustro das Raízes",
        }[quest]
        return _screen(
            f"📜 {title}\nMissão "
            f"{('Secundária' if quest in {S7_ID, S8_ID, S9_ID, S10_ID, S11_ID} else 'Principal')} "
            "· "
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
            P10_ID: "P9 concluída, Nv.17 e estar nos Baixios Enredados",
            S10_ID: "P10 ativa ou concluída, Nv.17 e estar nos Baixios Enredados",
            S11_ID: "Claustro das Raízes descoberto, Nv.18 e estar no Claustro",
            P11_ID: "P10 concluída, Nv.19 e estar no Claustro das Raízes",
            P12_ID: "P11 concluída e Nv.20",
            S12_ID: "S10 e P11 concluídas, Nv.20 e estar no Claustro das Raízes",
        }[quest]
        return _screen(
            f"📜 {title} · Indisponível\n\nRequer {gate}.",
            [[_button("← Missões", "world:missions")]],
        )

    if view.kind == "choice" and quest == P12_ID:
        text = (
            f"📜 {title} · Berço da Matriarca\n\n"
            "A Campanha dos Vales foi concluída. Escolha individualmente um equipamento Épico.\n\n"
            "✨ 32.580 XP · 🪙 800 Coroas\n"
            "📦 Ferro Enredado · 4 · Vinculado\n"
            "📦 Resina Enredada · 4 · Vinculada\n"
            "🧭 O Berço permanece acessível."
        )
        rows = [
            [_button(f"{name} · {slot}", f"vde:{quest}:{version}:ch:{choice}")]
            for choice, (name, slot) in P12_REWARD_CHOICES.items()
        ]
        rows.append([_button("← Missões", "world:missions")])
        return _screen(text, rows, "vde_missions")

    if view.kind == "completed":
        progress = view.progress or {}
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
            P10_ID: (
                "✨ 14.600 XP · 🪙 450 Coroas\n"
                "📦 Ferro Enredado · 2 · Vinculado\n"
                "📦 Resina Enredada · 2 · Vinculada"
            ),
            S10_ID: (
                "✨ 10.220 XP · 🪙 270 Coroas\n"
                "📦 Ferro Enredado · 2 · Vinculado\n"
                "📦 Couro Musgoso · 1 · Vinculado\n"
                "📦 Resina Enredada · 1 · Vinculada"
            ),
            S11_ID: (
                "✨ 10.990 XP · 🪙 280 Coroas\n"
                "📦 Ferro Enredado · 1 · Vinculado\n"
                "📦 Erva de Turfa · 1 · Vinculada\n"
                "📦 Resina Enredada · 2 · Vinculadas"
            ),
            P11_ID: (
                "✨ 16.900 XP · 🪙 490 Coroas\n"
                "📦 Ferro Enredado · 3 · Vinculado\n"
                "📦 Resina Enredada · 1 · Vinculada"
            ),
            P12_ID: (
                "✨ 32.580 XP · 🪙 800 Coroas\n"
                "📦 Ferro Enredado · 4 · Vinculado\n"
                "📦 Resina Enredada · 4 · Vinculada\n"
                "🎁 "
                + escape(
                    P12_REWARD_CHOICES.get(
                        str(progress.get("reward_choice")), ("Equipamento Épico", "")
                    )[0]
                )
                + " · Épico · Nv.20 · Vinculado"
            ),
            S12_ID: (
                "✨ 18.100 XP · 🪙 500 Coroas\n"
                "📦 Ferro Enredado · 2 · Vinculado\n"
                "📦 Couro Musgoso · 2 · Vinculado\n"
                "📦 Erva de Turfa · 2 · Vinculada\n"
                "📦 Resina Enredada · 2 · Vinculada"
            ),
        }.get(quest, "")
        text = f"✅ {title} · Concluída\n\n{reward}"
        rows = []
        if quest == S11_ID:
            text += (
                "\n\nAlguns Vigias continuam executando rotinas antigas mesmo "
                "deformados e atravessados por raízes."
            )
        elif quest == P11_ID:
            text += (
                "\n\nA estrutura asteriana é mais antiga que o crescimento atual. "
                "A Matriarca não construiu aquilo que existe sob os Vales. "
                "Quase todas as raízes anormais convergem para a área onde ela está.\n\n"
                "🧭 Acesso aberto · Berço da Matriarca"
            )
            if view.location == CLAUSTRO:
                rows.append([_button("Seguir para o Berço", "road:route:vde_berco")])
        elif quest == P12_ID:
            text += "\n\nA Campanha dos Vales foi concluída. O Berço permanece acessível."
        elif quest == S12_ID:
            text += (
                "\n\nAlguns desaparecimentos receberam um destino provável; "
                "outros seguem sem resposta. A Vigília manterá um registro "
                "permanente daqueles que desapareceram mantendo os caminhos abertos."
            )
        rows.append([_button("← Missões", "world:missions")])
        return _screen(text, rows)

    progress = view.progress or {}
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "enter_berco" and quest == P12_ID:
        text = (
            f"📜 {title} · {BERCO}\n\n"
            "🎯 Entrar no Berço da Matriarca e avançar pela rede exterior."
        )
        if view.location == CLAUSTRO:
            rows.append([_button("Seguir para o Berço", "road:route:vde_berco")])
        elif view.location == BERCO:
            rows.append([_button("Entrar no Berço", f"vde:{quest}:{version}:enter_berco")])
        else:
            rows.append([_button("Retornar ao Claustro", "road:route:vde_claustro")])
    elif view.kind == "advance_network" and quest == P12_ID:
        text = (
            f"📜 {title} · {BERCO}\n\n"
            "🎯 Avançar através da rede exterior até as três conexões que bloqueiam o acesso."
        )
        rows.append(
            [
                _button(
                    "Avançar pela rede"
                    if view.location == BERCO
                    else "Seguir para o Berço",
                    f"vde:{quest}:{version}:advance_network"
                    if view.location == BERCO
                    else "road:route:vde_berco",
                )
            ]
        )
    elif view.kind == "connections" and quest == P12_ID:
        found = set(progress.get("external_connections", ()))
        if view.location == BERCO:
            for point, label in (
                ("a", "Romper conexão exterior 1"),
                ("b", "Romper conexão exterior 2"),
                ("c", "Romper conexão exterior 3"),
            ):
                if point not in found:
                    rows.append([_button(label, f"vde:{quest}:{version}:ex:{point}")])
        else:
            rows.append([_button("Seguir para o Berço", "road:route:vde_berco")])
        text = (
            f"📜 {title} · {BERCO}\n\n"
            "🎯 Romper as três grandes conexões exteriores.\n"
            f"Progresso · {len(found)}/3"
        )
    elif view.kind == "central_chamber" and quest == P12_ID:
        text = f"📜 {title} · {BERCO}\n\n🎯 Alcançar a câmara central."
        rows.append(
            [
                _button(
                    "Alcançar a câmara central"
                    if view.location == BERCO
                    else "Seguir para o Berço",
                    f"vde:{quest}:{version}:central_chamber"
                    if view.location == BERCO
                    else "road:route:vde_berco",
                )
            ]
        )
    elif view.kind == "examine_center" and quest == P12_ID:
        text = (
            f"📜 {title} · {BERCO}\n\n"
            "A Matriarca foi derrotada. Examine o centro da câmara e registre a descoberta final."
        )
        rows.append(
            [
                _button(
                    "Examinar o centro"
                    if view.location == BERCO
                    else "Seguir para o Berço",
                    f"vde:{quest}:{version}:examine_center"
                    if view.location == BERCO
                    else "road:route:vde_berco",
                )
            ]
        )
    elif view.kind == "register" and quest == P12_ID:
        text = (
            f"📜 {title} · {BERCO}\n\n"
            "🎯 Registrar a descoberta e concluir a Campanha dos Vales."
        )
        rows.append(
            [
                _button(
                    "Registrar descoberta"
                    if view.location == BERCO
                    else "Seguir para o Berço",
                    f"vde:{quest}:{version}:register"
                    if view.location == BERCO
                    else "road:route:vde_berco",
                )
            ]
        )
    elif quest == S12_ID and view.kind in {
        "read_record", "visit_garganta", "find_mark", "visit_mata", "recover_object",
        "visit_baixios", "examine_site", "visit_claustro", "last_record", "report_iven",
        "register_names",
    }:
        stage = {
            "read_record": (
                "Claustro das Raízes", "Ler o registro recuperado durante S10.",
                "Ler o registro", "read_record", CLAUSTRO, "road:route:vde_claustro",
            ),
            "visit_garganta": (
                "Garganta dos Laços", "Visitar a Garganta dos Laços.",
                "Registrar visita", "visit_garganta", "Garganta dos Laços",
                "road:route:vde_garganta",
            ),
            "find_mark": (
                "Garganta dos Laços", "Encontrar uma antiga marca de passagem.",
                "Examinar a marca", "find_mark", "Garganta dos Laços", "road:route:vde_garganta",
            ),
            "visit_mata": (
                "Mata Suspensa", "Visitar a Mata Suspensa.",
                "Registrar visita", "visit_mata", "Mata Suspensa", "road:route:vde_mata",
            ),
            "recover_object": (
                "Mata Suspensa", "Recuperar um objeto pessoal sem valor econômico.",
                "Recuperar o objeto", "recover_object", "Mata Suspensa", "road:route:vde_mata",
            ),
            "visit_baixios": (
                "Baixios Enredados", "Visitar os Baixios Enredados.",
                "Registrar visita", "visit_baixios", "Baixios Enredados", "road:route:vde_baixios",
            ),
            "examine_site": (
                "Baixios Enredados",
                "Examinar o local da marca. O encontro não identifica o Peregrino "
                "como uma pessoa desaparecida.",
                "Examinar o local", "examine_site", "Baixios Enredados",
                "road:route:vde_baixios",
            ),
            "visit_claustro": (
                "Claustro das Raízes", "Ir ao Claustro das Raízes.",
                "Registrar chegada", "visit_claustro", CLAUSTRO, "road:route:vde_claustro",
            ),
            "last_record": (
                "Claustro das Raízes", "Encontrar o último registro ainda legível.",
                "Examinar o registro", "last_record", CLAUSTRO, "road:route:vde_claustro",
            ),
            "report_iven": (
                "Claustro das Raízes", "Retornar a Iven Raal com os registros.",
                "Relatar a Iven", "report_iven", CLAUSTRO, "road:route:vde_claustro",
            ),
            "register_names": (
                "Vigília do Vale", "Registrar na Vigília os nomes preservados.",
                "Registrar os nomes", "register_names", "Vigília do Vale", "road:route:vde_vigilia",
            ),
        }[view.kind]
        stage_location, objective, label, action, required_location, _route = stage
        text = f"📜 {title} · {stage_location}\n\n🎯 {objective}"
        if view.location == required_location:
            rows.append([_button(label, f"vde:{quest}:{version}:{action}")])
        else:
            route = _route_toward(view.location, required_location)
            if route is not None:
                rows.append([_button(f"Seguir para {stage_location}", route)])
    elif view.kind == "markers":
        found = set(progress.get("markers", ()))
        for point, label in (
            ("a", "Examinar marcação 1"),
            ("b", "Examinar marcação 2"),
            ("c", "Examinar marcação 3"),
        ):
            if point not in found:
                rows.append([_button(label, f"vde:{quest}:{version}:ex:{point}")])
        if quest == S10_ID:
            text = (
                f"📜 {title} · Baixios Enredados\n\n"
                "🎯 Seguir três marcadores deixados por exploradores desaparecidos.\n"
                f"Progresso · {len(found)}/3"
            )
        else:
            text = (
                f"📜 {title} · Garganta dos Laços\n\n"
                "🎯 Examinar três marcações de rota.\n"
                f"Progresso · {len(found)}/3"
            )
    elif view.kind == "inscriptions":
        found = set(progress.get("inscriptions", ()))
        for point, label in (("a", "Examinar inscrição 1"), ("b", "Examinar inscrição 2")):
            if point not in found:
                rows.append([_button(label, f"vde:{quest}:{version}:ex:{point}")])
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Examinar duas inscrições preservadas.\n"
            f"Progresso · {len(found)}/2"
        )
    elif view.kind == "patrols":
        found = set(progress.get("patrols", ()))
        for point, label in (
            ("a", "Observar ponto de patrulha 1"),
            ("b", "Observar ponto de patrulha 2"),
        ):
            if point not in found:
                rows.append([_button(label, f"vde:{quest}:{version}:ex:{point}")])
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Observar dois pontos de patrulha.\n"
            f"Progresso · {len(found)}/2"
        )
    elif view.kind == "pressure_points":
        found = set(progress.get("pressure_points", ()))
        for point, label in (
            ("a", "Investigar ponto de pressão 1"),
            ("b", "Investigar ponto de pressão 2"),
            ("c", "Investigar ponto de pressão 3"),
        ):
            if point not in found:
                rows.append([_button(label, f"vde:{quest}:{version}:ex:{point}")])
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Investigar três pontos de pressão.\n"
            f"Progresso · {len(found)}/3"
        )
    elif view.kind == "combat_start":
        if quest == P12_ID:
            objective = "Enfrentar a Matriarca das Raízes, Chefe de Campanha do Berço."
        elif quest == S11_ID:
            objective = "Derrotar o Vigia Enraizado que patrulha o Claustro."
        elif quest == S12_ID:
            objective = "Derrotar 1 Peregrino Enredado Nv.20 junto a outra marca de passagem."
        elif quest in {S10_ID, P11_ID}:
            location_text = "na região inundada" if quest == S10_ID else "no Claustro das Raízes"
            objective = (
                f"Enfrentar o encontro roteirizado {location_text}. "
                "A espécie não é identificada pelo registro."
            )
        else:
            objective = (
                "Derrotar a criatura que ocupa o ponto investigado. "
                "O conteúdo regional não identifica uma espécie para este encontro."
            )
        text = f"📜 {title} · {location}\n\n🎯 {objective}"
        rows.extend(
            [
                [_button("Enfrentar Solo", f"vde:{quest}:{version}:solo")],
                *(
                    [
                        [_button("Formar/Usar Grupo", f"vde:{quest}:{version}:group")],
                        [_button("Grupo", "group:root")],
                    ]
                    if mission_coop_allowed(quest)
                    else []
                ),
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
                *(
                    [[_button("Formar/Usar Grupo", f"vde:{quest}:{version}:group")]]
                    if mission_coop_allowed(quest)
                    else []
                ),
            ]
        )
    elif view.kind == "rope":
        text = (
            f"📜 {title} · Garganta dos Laços\n\n"
            "🎯 Encontrar a corda ainda presa à estrutura acima do caminho."
        )
        rows.append([_button("Examinar a corda", f"vde:{quest}:{version}:rope")])
    elif view.kind == "return_place":
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Examinar o lugar para onde o Vigia Enraizado retornava."
        )
        rows.append([_button("Examinar o local", f"vde:{quest}:{version}:return_place")])
    elif view.kind == "fragments" and quest == S11_ID:
        found = len(progress.get("marking_fragments", ()))
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Recuperar três fragmentos de marcação.\n"
            f"Progresso · {found}/3"
        )
        if found < 3:
            rows.append([_button("Recuperar fragmento", f"vde:{quest}:{version}:fragment")])
    elif view.kind == "report" and quest == S11_ID:
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "Alguns Vigias continuam executando rotinas antigas mesmo deformados e "
            "atravessados por raízes.\n\n"
            "🎯 Entregar os registros a Iven Raal."
        )
        rows.append([_button("Entregar os registros", f"vde:{quest}:{version}:report")])
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
        if quest == S10_ID:
            text = (
                f"📜 {title}\n\nUm explorador foi encontrado vivo. "
                "O segundo permanece desaparecido.\n\n"
                "🎯 Retornar com ele à rota da Vigília."
            )
            if view.location == "Baixios Enredados":
                rows.append([_button("Retornar à Mata Suspensa", "road:route:vde_mata")])
            elif view.location == "Mata Suspensa":
                rows.append([_button("Seguir para a Vigília", "road:route:vde_vigilia")])
            elif view.location == "Vigília do Vale":
                rows.append([_button("Relatar a Dara Venn", f"vde:{quest}:{version}:report")])
        else:
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
        if quest == P10_ID:
            text = (
                f"📜 {title} · Baixios Enredados\n\n"
                "🎯 Seguir os marcos identificados durante P9."
            )
            rows.append([_button("Seguir os marcos", f"vde:{quest}:{version}:follow")])
        else:
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
    elif view.kind == "open_claustro":
        text = f"📜 {title} · Baixios Enredados\n\n🎯 Abrir passagem até o Claustro das Raízes."
        rows.append([_button("Abrir passagem", f"vde:{quest}:{version}:passage")])
    elif view.kind == "structure" and quest == P10_ID:
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Inspecionar a estrutura protegida pelo Vigia Enraizado."
        )
        rows.append([_button("Inspecionar estrutura", f"vde:{quest}:{version}:structure")])
    elif view.kind == "sanctuary":
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "A entrada do Santuário do Nó Antigo foi localizada. "
            "A descoberta não exige explorar a masmorra.\n\n"
            "🎯 Registrar a informação e retornar a Iven Raal."
        )
        rows.append([_button("Registrar a entrada", f"vde:{quest}:{version}:sanctuary")])
    elif view.kind == "clear_roots":
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Superar as raízes que bloqueiam o caminho e prosseguir."
        )
        rows.append([_button("Prosseguir pelo caminho", f"vde:{quest}:{version}:roots")])
    elif view.kind == "chamber":
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Examinar a câmara deformada pelo crescimento."
        )
        rows.append([_button("Examinar a câmara", f"vde:{quest}:{version}:chamber")])
    elif view.kind == "traces":
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Registrar os vestígios de uma criatura muito maior."
        )
        rows.append([_button("Registrar vestígios", f"vde:{quest}:{version}:traces")])
    elif view.kind == "convergence":
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "🎯 Seguir a convergência das raízes."
        )
        rows.append([_button("Seguir a convergência", f"vde:{quest}:{version}:convergence")])
    elif view.kind == "open_berco":
        text = (
            f"📜 {title} · Claustro das Raízes\n\n"
            "A estrutura asteriana é mais antiga que o crescimento atual. A Matriarca "
            "não construiu aquilo que existe sob os Vales. Quase todas as raízes "
            "anormais convergem para a área onde ela está.\n\n"
            "🎯 Abrir acesso ao Berço da Matriarca."
        )
        rows.append([_button("Abrir acesso ao Berço", f"vde:{quest}:{version}:open_berco")])
    elif view.kind == "zone":
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "🎯 Atravessar a zona ocupada por Sanguessugas de Turfa."
        )
        rows.append([_button("Atravessar a zona", f"vde:{quest}:{version}:zone")])
    elif view.kind == "bag":
        text = f"📜 {title} · Baixios Enredados\n\n🎯 Encontrar a bolsa abandonada."
        rows.append([_button("Examinar a bolsa", f"vde:{quest}:{version}:bag")])
    elif view.kind == "tracks":
        text = f"📜 {title} · Baixios Enredados\n\n🎯 Seguir as pegadas até a região inundada."
        rows.append([_button("Seguir pegadas", f"vde:{quest}:{version}:tracks")])
    elif view.kind == "survivor":
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "🎯 Encontrar um dos exploradores em posição segura. "
            "O destino do segundo permanece desconhecido."
        )
        rows.append([_button("Ajudar o explorador", f"vde:{quest}:{version}:survivor")])
    elif view.kind == "report" and quest == P10_ID:
        text = (
            f"📜 {title} · Baixios Enredados\n\n"
            "As inscrições indicam alguma forma de organização ou ligação entre diferentes pontos; "
            "a função da rede permanece desconhecida.\n\n"
            "🎯 Registrar a informação com Iven Raal."
        )
        if view.location == "Baixios Enredados":
            rows.append([_button("Relatar a Iven Raal", f"vde:{quest}:{version}:report")])
        else:
            rows.append([_button("Retornar aos Baixios", "road:route:vde_baixios")])
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


def render_vde_mission(view: VDEMissionView) -> Screen:
    """Mission screen with the art of its quest (see asset_catalog)."""
    return with_mission_art(_render_vde_mission(view), view.quest_id)
