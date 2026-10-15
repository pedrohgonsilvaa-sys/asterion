"""Telegram screens for Várzeas missions and scripted encounters."""

# ruff: noqa: E501

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.varzeas_missions import (
    P19_ID,
    P20_ID,
    S19_ID,
    S20_ID,
    VarzeasMissionView,
)
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen
from asterion.domain.road import VARZEAS_PORTO


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
        }[view.quest_id]
        text = f"📜 {title} · Indisponível\n\nRequer {gate}."
        rows.append([_button("← Missões", "world:missions")])
    elif view.kind == "offer":
        gate = (
            "P19 concluída · Nv.32 · Porto da Salmoura"
            if view.quest_id == S19_ID
            else "P20 concluída · Nv.34 · Porto da Salmoura"
        )
        mission_type = "Missão Curta" if view.quest_id == S19_ID else "Missão Padrão"
        text = f"📜 {title}\n{mission_type} · Várzeas Carmesins\n\nRequer {gate}."
        rows.extend(([_button("Aceitar Missão", f"varzeas:start:{view.quest_id}")], [_button("← Missões", "world:missions")]))
    elif view.kind == "completed":
        reward = {
            P19_ID: "34.300 XP · 570 Coroas · Ferro de Salmoura · Couro de Várzea",
            S19_ID: "14.400 XP · 290 Coroas",
            P20_ID: "37.800 XP · 600 Coroas · Ferro de Salmoura · 2 Juncos Ferruginosos · Soro Antigo",
            S20_ID: "27.720 XP · 460 Coroas · Junco Ferruginoso · Soro Antigo",
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
