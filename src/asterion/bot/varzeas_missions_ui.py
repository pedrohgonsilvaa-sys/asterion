"""Telegram screens for P19 and S19."""

# ruff: noqa: E501

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.varzeas_missions import P19_ID, VarzeasMissionView
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def render_varzeas_mission(view: VarzeasMissionView) -> Screen:
    title = escape(view.title)
    rows: list[list[InlineKeyboardButton]] = []
    if view.kind == "unavailable":
        gate = "P18 concluída, entrada legítima nas Várzeas e Nv.31" if view.quest_id == P19_ID else "P19 concluída e Nv.32 no Porto da Salmoura"
        text = f"📜 {title} · Indisponível\n\nRequer {gate}."
        rows.append([_button("← Missões", "world:missions")])
    elif view.kind == "offer":
        text = f"📜 {title}\nMissão Curta · Várzeas Carmesins\n\nRequer P19 concluída · Nv.32 · Porto da Salmoura."
        rows.extend(([_button("Aceitar Missão", "varzeas:start:S19")], [_button("← Missões", "world:missions")]))
    elif view.kind == "completed":
        reward = "34.300 XP · 570 Coroas · Ferro de Salmoura · Couro de Várzea" if view.quest_id == P19_ID else "14.400 XP · 290 Coroas"
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
    else:
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
    return Screen(text, "missions", InlineKeyboardMarkup(inline_keyboard=rows))
