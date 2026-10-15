"""Telegram screens for Várzeas missions and scripted encounters."""

# ruff: noqa: E501

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.varzeas_missions import (
    P19_ID,
    P20_ID,
    P21_ID,
    P22_ID,
    S19_ID,
    S20_ID,
    S21_ID,
    S22_ID,
    VarzeasMissionView,
)
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen
from asterion.domain.road import VARZEAS_GALERIAS, VARZEAS_PORTO


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def render_varzeas_mission(view: VarzeasMissionView) -> Screen:
    title = escape(view.title)
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "combat" and view.combat is not None and view.activity_id is not None:
        hud = render_combat(
            CombatView(
                activity_id=view.activity_id,
                encounter_id=view.encounter_id or view.activity_id,
                character_id=view.character_id,
                combat=view.combat,
                stage="campaign",
                xp=0,
                context="varzeas",
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
        return Screen(
            f"📜 {title} · Várzeas Carmesins\n⚔️ Encontro Roteirizado · "
            f"{escape(view.location)}\n\n{hud.text}",
            "missions",
            hud.keyboard,
            parse_mode=hud.parse_mode,
        )
    if view.kind == "unavailable":
        gate = {
            P19_ID: "P18 concluída, entrada legítima nas Várzeas e Nv.31",
            S19_ID: "P19 concluída e Nv.32 no Porto da Salmoura",
            P20_ID: "P19 concluída e Nv.33 no Porto da Salmoura",
            S20_ID: "P20 concluída e Nv.34 no Porto da Salmoura",
            P21_ID: "P20 concluída, Nv.35 e acesso aos Hortos Hemaris",
            S21_ID: "P21 ativa ou concluída, acesso aos Hortos e Nv.35",
            P22_ID: "P21 concluída, Nv.37 e acesso às Galerias de Transferência",
            S22_ID: "P22 ativa ou concluída, Enfermaria Afundada descoberta e Nv.37",
        }[view.quest_id]
        text = f"📜 {title} · Indisponível\n\nRequer {gate}."
        rows.append([_button("← Missões", "world:missions")])
    elif view.kind == "offer":
        gate = {
            S19_ID: "P19 concluída · Nv.32 · Porto da Salmoura",
            S20_ID: "P20 concluída · Nv.34 · Porto da Salmoura",
            S21_ID: "P21 ativa ou concluída · Nv.35 · Hortos Hemaris",
            S22_ID: "P22 ativa ou concluída · Enfermaria Afundada descoberta · Nv.37 · Hortos Hemaris",
        }[view.quest_id]
        mission_type = "Missão Padrão" if view.quest_id in {S20_ID, S22_ID} else "Missão Curta"
        text = f"📜 {title}\n{mission_type} · Várzeas Carmesins\n\nRequer {gate}."
        rows.extend(([_button("Aceitar Missão", f"varzeas:start:{view.quest_id}")], [_button("← Missões", "world:missions")]))
    elif view.kind == "completed":
        reward = {
            P19_ID: "34.300 XP · 570 Coroas · Ferro de Salmoura · Couro de Várzea",
            S19_ID: "14.400 XP · 290 Coroas",
            P20_ID: "37.800 XP · 600 Coroas · Ferro de Salmoura · 2 Juncos Ferruginosos · Soro Antigo",
            S20_ID: "27.720 XP · 460 Coroas · Junco Ferruginoso · Soro Antigo",
            P21_ID: "41.450 XP · 630 Coroas · escolha de 1 Equipamento Raro Nv.35",
            S21_ID: "16.580 XP · 320 Coroas · 2 Couros de Várzea",
            P22_ID: "45.300 XP · 830 Coroas · 2 Ferros de Salmoura · 2 Soros Antigos",
            S22_ID: "31.710 XP · 500 Coroas · 2 Ferros · Junco · Soro",
        }[view.quest_id]
        text = f"📜 {title} · Concluída\n\n✨ {reward}"
        rows.extend(([_button("← Missões", "world:missions")], [_button("🗺️ Mapa", "world:map")]))
    elif view.quest_id == P19_ID:
        descriptions = {
            "inspect_water": ("Examine a água ferruginosa e a comporta parcialmente funcional.", "Examinar água e comporta", "inspect_water"),
            "register_dique_brazier": ("Registre o Braseiro do Dique Alto.", "Registrar Braseiro do Dique Alto", "register_dique_brazier"),
            "follow_safe_route": ("Siga a passarela segura indicada por viajantes atuais.", "Registrar passarela segura", "follow_safe_route"),
            "register_porto_brazier": ("Registre o Braseiro do Porto.", "Registrar Braseiro do Porto", "register_porto_brazier"),
            "speak_sera": ("Fale com Sera Morn no Porto da Salmoura.", "Falar com Sera Morn", "speak_sera"),
            "record_codex": ("Registre no Códice Rotas das Várzeas.", "Registrar no Códice", "record_codex"),
        }
        if view.kind == "arrive_porto":
            description = "A rota segura foi estabelecida. Alcance o Porto da Salmoura."
            rows.append([_button("Seguir para o Porto da Salmoura", "road:route:varzeas_porto")])
        else:
            description, label, action = descriptions.get(view.kind, ("Continue a jornada pelos Diques Rubros.", "", ""))
            if action:
                rows.append([_button(label, f"varzeas:action:P19:{view.state_version}:{action}")])
        text = f"📜 {title} · Várzeas Carmesins\n\n{description}\n\n📍 {escape(view.location)}"
        rows.extend(([_button("📍 Local Atual", "world:local")], [_button("← Missões", "world:missions")]))
    elif view.quest_id == S19_ID:
        points = set((view.progress or {}).get("corrosion_points", []))
        if view.kind == "corrosion_points":
            labels = {"a": "Examinar primeiro ponto", "b": "Examinar segundo ponto", "c": "Examinar terceiro ponto"}
            description = "Investigue os três pontos de corrosão acelerada nas passarelas dos Diques."
            for point in ("a", "b", "c"):
                if point not in points:
                    rows.append([_button(labels[point], f"varzeas:action:S19:{view.state_version}:inspect_{point}")])
        elif view.kind == "differentiate_brine_damage":
            description = "Diferencie os efeitos da salmoura de danos recentes nas estruturas."
            rows.append([_button("Registrar a distinção", f"varzeas:action:S19:{view.state_version}:differentiate_brine_damage")])
        else:
            description = "Conclua com o reparo e o registro das observações."
            rows.append([_button("Registrar reparo", f"varzeas:action:S19:{view.state_version}:repair_and_record")])
        text = f"📜 {title} · Várzeas Carmesins\n\n{description}\n\n📍 {escape(view.location)}"
        rows.extend(([_button("📍 Local Atual", "world:local")], [_button("← Missões", "world:missions")]))
    elif view.quest_id == P21_ID:
        beds = set((view.progress or {}).get("beds_examined", []))
        if view.kind == "travel_hortos":
            description = "Entre nos Hortos Hemaris para examinar os cultivos antigos."
            rows.append([_button("Seguir aos Hortos Hemaris", "road:route:varzeas_hortos")])
        elif view.kind == "examine_beds":
            description = "Examine os três canteiros antigos e registre as funções distintas observáveis."
            for point in ("a", "b", "c"):
                if point not in beds:
                    rows.append([_button(f"Examinar canteiro {point.upper()}", f"varzeas:action:P21:{view.state_version}:examine_bed_{point}")])
        elif view.kind == "combat_start":
            description = "O Cervo Ferrugem bloqueia o setor. Prepare-se para a investida telegráfica."
            rows.extend((
                [_button("Enfrentar sozinho", f"varzeas:combat:P21:{view.state_version}:solo")],
                [_button("Propor ao Grupo", f"varzeas:combat:P21:{view.state_version}:group")],
            ))
        elif view.kind == "find_technical_plate":
            description = "Encontre a placa técnica que relaciona cultivo, recuperação e Hemaris."
            rows.append([_button("Examinar placa técnica", f"varzeas:action:P21:{view.state_version}:find_technical_plate")])
        elif view.kind == "report_to_ilyan":
            description = "Leve o registro a Ilyan Korr."
            rows.append([_button("Entregar registro a Ilyan", f"varzeas:action:P21:{view.state_version}:report_to_ilyan")])
        elif view.kind == "record_project_hemaris":
            description = "Registre no Códice Projeto Hemaris — Registro Inicial."
            rows.append([_button("Registrar no Códice", f"varzeas:action:P21:{view.state_version}:record_project_hemaris")])
        elif view.kind == "choose_reward":
            description = "Escolha exatamente um Equipamento Raro Nv.35. A escolha será individual e permanente."
            for key, label in (
                ("mask", "Máscara da Salmoura · Cabeça"),
                ("seal", "Selo dos Diques · Acessório"),
                ("reliquary", "Relicário do Horto Estéril · Artefato"),
            ):
                rows.append([_button(label, f"varzeas:choice:P21:{view.state_version}:{key}")])
        else:
            description = "Continue a investigação dos Hortos Hemaris."
        text = f"📜 {title} · Várzeas Carmesins\n\n{description}\n\n📍 {escape(view.location)}"
        rows.extend(([_button("📍 Local Atual", "world:local")], [_button("← Missões", "world:missions")]))
    elif view.quest_id == S21_ID:
        descriptions = {
            "examine_cultivation_sector": ("Examine o setor de cultivo tomado por Enxertos de Horto.", "Examinar setor", "examine_cultivation_sector"),
            "observe_autonomous_grafts": ("Observe os sinais dos Enxertos e registre que as culturas de suporte se tornaram autônomas.", "Registrar observação", "observe_autonomous_grafts"),
            "analyze_support_function": ("Registre a função de suporte e regeneração sem classificar os organismos como pessoas transformadas.", "Registrar análise", "analyze_support_function"),
            "report_to_ilyan": ("Retorne a Ilyan Korr e conclua o registro.", "Concluir com Ilyan", "report_to_ilyan"),
        }
        description, label, action = descriptions.get(view.kind, ("Continue a investigação do setor de cultivo.", None, None))
        if action is not None:
            rows.append([_button(label, f"varzeas:action:S21:{view.state_version}:{action}")])
        text = f"📜 {title} · Várzeas Carmesins\n\n{description}\n\n📍 {escape(view.location)}"
        rows.extend(([_button("📍 Local Atual", "world:local")], [_button("← Missões", "world:missions")]))
    elif view.quest_id == P22_ID:
        if view.kind == "travel_galerias":
            description = "Acesse as Galerias de Transferência pelas rotas dos Hortos."
            rows.append([_button("Seguir às Galerias de Transferência", "road:route:varzeas_galerias")])
        elif view.kind == "register_valves_brazier":
            description = "Registre o Braseiro das Válvulas ao alcançar as Galerias."
            rows.append([_button("Registrar Braseiro das Válvulas", f"varzeas:action:P22:{view.state_version}:register_valves_brazier")])
        elif view.kind == "examine_transfer_infrastructure":
            description = "Examine os dois reservatórios e a linha de transporte."
            progress = view.progress or {}
            reservoirs = set(progress.get("reservoirs_examined", []))
            if "a" not in reservoirs:
                rows.append([_button("Examinar reservatório A", f"varzeas:action:P22:{view.state_version}:examine_reservoir_a")])
            if "b" not in reservoirs:
                rows.append([_button("Examinar reservatório B", f"varzeas:action:P22:{view.state_version}:examine_reservoir_b")])
            if not progress.get("line_examined"):
                rows.append([_button("Examinar linha de transporte", f"varzeas:action:P22:{view.state_version}:examine_transport_line")])
        elif view.kind == "combat_start":
            description = "Um Vigia Hemaris Nv.37 guarda a linha."
            rows.extend((
                [_button("Enfrentar sozinho", f"varzeas:combat:P22:{view.state_version}:solo")],
                [_button("Propor ao Grupo", f"varzeas:combat:P22:{view.state_version}:group")],
            ))
        elif view.kind == "recover_transfer_record":
            description = "Recupere o registro técnico que contém o termo Transferência."
            rows.append([_button("Registrar documento técnico", f"varzeas:action:P22:{view.state_version}:recover_transfer_record")])
        elif view.kind == "compare_hortos_record":
            description = "Compare o registro técnico com o registro inicial dos Hortos."
            rows.append([_button("Comparar registros", f"varzeas:action:P22:{view.state_version}:compare_hortos_record")])
        elif view.kind == "return_to_ilyan":
            description = "Retorne aos Hortos Hemaris e leve o registro a Ilyan Korr."
            if view.location == VARZEAS_GALERIAS:
                rows.append([_button("Retornar aos Hortos Hemaris", "road:route:varzeas_hortos")])
            else:
                rows.append([_button("Entregar registro a Ilyan", f"varzeas:action:P22:{view.state_version}:report_to_ilyan")])
        else:
            description = "Continue a investigação das Galerias de Transferência."
        text = f"📜 {title} · Várzeas Carmesins\n\n{description}\n\n📍 {escape(view.location)}"
        rows.extend(([_button("📍 Local Atual", "world:local")], [_button("← Missões", "world:missions")]))
    elif view.quest_id == S22_ID:
        prompts = {
            "inspect_automated_routines": ("Inspecione as rotinas automatizadas que continuam operando.", "Inspecionar rotinas", "inspect_automated_routines"),
            "record_treatment_preparation": ("Registre a preparação de tratamento observada.", "Registrar preparação", "record_treatment_preparation"),
            "record_no_valid_patient": ("Registre que as rotinas prosseguem sem paciente válido, sem inferir além dos dados.", "Registrar ausência de paciente válido", "record_no_valid_patient"),
            "report_to_ilyan": ("Leve o registro a Ilyan Korr.", "Concluir com Ilyan", "report_to_ilyan"),
        }
        description, label, action = prompts.get(view.kind, ("Investigue os protocolos observáveis nos Hortos.", None, None))
        if action is not None:
            rows.append([_button(label, f"varzeas:action:S22:{view.state_version}:{action}")])
        text = f"📜 {title} · Várzeas Carmesins\n\n{description}\n\n📍 {escape(view.location)}"
        rows.extend(([_button("📍 Local Atual", "world:local")], [_button("← Missões", "world:missions")]))
    else:
        quest_id = view.quest_id
        if quest_id == P20_ID:
            descriptions = {
                "travel_brejos": ("Viaje dos Diques ao Brejo para observar o nível da água.", None, None),
                "water_occurrences": ("Registre três elevações e baixas periódicas da água.", None, None),
                "compare_valves": ("Compare o pulso da água com as válvulas enterradas.", "Comparar com as válvulas", "compare_buried_valves"),
                "examine_conduit": ("Examine o conduto antigo sem presumir sua origem.", "Examinar o conduto", "examine_conduit"),
                "return_sera": ("Retorne ao Porto da Salmoura e fale com Sera Morn.", None, None),
                "record_pulse": ("Registre a interpretação hidráulica e biológica observada.", "Registrar interpretação", "record_pulse"),
            }
            description, label, action = descriptions.get(view.kind, ("Continue a investigação dos Brejos do Pulso.", None, None))
            if view.kind == "travel_brejos":
                rows.append([_button("Seguir aos Brejos do Pulso", "road:route:varzeas_brejos")])
            elif view.kind == "water_occurrences":
                observed = set((view.progress or {}).get("water_occurrences", []))
                for point, label in (("a", "Primeira ocorrência"), ("b", "Segunda ocorrência"), ("c", "Terceira ocorrência")):
                    if point not in observed:
                        rows.append([_button(label, f"varzeas:action:P20:{view.state_version}:observe_pulse_{point}")])
            elif view.kind == "combat_start":
                rows.extend((
                    [_button("Enfrentar sozinho", f"varzeas:combat:P20:{view.state_version}:solo")],
                    [_button("Propor ao Grupo", f"varzeas:combat:P20:{view.state_version}:group")],
                ))
            elif view.kind == "return_sera":
                rows.append([_button("Retornar ao Porto da Salmoura", "road:route:varzeas_porto")])
            elif action:
                rows.append([_button(label, f"varzeas:action:P20:{view.state_version}:{action}")])
        else:
            descriptions = {
                "observe_tracks": ("Observe os rastros de um Portador Rubro nos Brejos.", "Registrar rastros", "observe_tracks"),
                "follow_continuity_signs": ("Acompanhe sinais de continuidade em uma passagem onde um viajante comum teria recuado.", "Acompanhar sinais", "follow_continuity_signs"),
                "locate_portador": ("Localize o Portador Rubro entre os juncos.", "Localizar alvo", "locate_portador"),
                "record_anatomy_and_environment": ("Registre os fatos anatômicos e ambientais observados.", "Registrar observações", "record_anatomy_and_environment"),
                "report_to_sera": ("Retorne ao Porto da Salmoura para concluir o registro com Sera.", None, None),
            }
            description, label, action = descriptions.get(view.kind, ("Continue os registros nos Brejos do Pulso.", None, None))
            if view.kind == "observe_tracks" and view.location == VARZEAS_PORTO:
                description = "Siga ao Brejo do Pulso para observar os rastros do Portador Rubro."
                rows.append([_button("Seguir aos Brejos do Pulso", "road:route:varzeas_brejos")])
            elif view.kind == "combat_start":
                rows.extend((
                    [_button("Enfrentar sozinho", f"varzeas:combat:S20:{view.state_version}:solo")],
                    [_button("Propor ao Grupo", f"varzeas:combat:S20:{view.state_version}:group")],
                ))
            elif view.kind == "return_sera":
                rows.append([_button("Retornar ao Porto da Salmoura", "road:route:varzeas_porto")])
            elif action:
                rows.append([_button(label, f"varzeas:action:S20:{view.state_version}:{action}")])
        text = f"📜 {title} · Várzeas Carmesins\n\n{description}\n\n📍 {escape(view.location)}"
        rows.extend(([_button("📍 Local Atual", "world:local")], [_button("← Missões", "world:missions")]))
    return Screen(text, "missions", InlineKeyboardMarkup(inline_keyboard=rows))
