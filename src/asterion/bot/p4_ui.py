"""Player-facing screens for P4 and its mission-only Ruins visit."""
# ruff: noqa: E501

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p4 import P4_STRUCTURES, P4View
from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, RUINS
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(label: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=data)


def _keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _combat(view: P4View) -> Screen:
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen("📜 Pedras que Ainda Vigiam · O encontro está sendo reconstruído.", "p4", _keyboard([[_button("Atualizar", "p4:resume")]]))
    hud = render_combat(
        CombatView(
            view.activity_id, view.encounter_id, view.character_id, view.combat,
            "p4", view.xp, context="p4", consumable_options=view.consumable_options,
            consumable_screen=view.consumable_screen,
            selected_consumable_id=view.selected_consumable_id,
            selected_target_id=view.selected_target_id, selection_parent=view.selection_parent,
            consumable_notice=view.consumable_notice,
            consumable_quantities=view.consumable_quantities,
            consumable_budget_limit=view.consumable_budget_limit,
            ready_consumable_option=view.ready_consumable_option,
            combat_actor_key=view.combat_actor_key,
        )
    )
    return Screen("📜 Pedras que Ainda Vigiam · Encontro de Missão\n" + hud.text, "p4", hud.keyboard, parse_mode=hud.parse_mode)


def _objective(view: P4View) -> str:
    if view.step == 1:
        return "Seguir o Caminho Ocidental a partir do Bosque"
    if view.step == 2:
        return "Alcançar os limites das Ruínas do Vigia"
    if view.step == 3:
        return "Derrotar o Vigia Rachado"
    if view.step == 4:
        return f"Examinar estruturas de guarda · {len(set(view.progress.get('structures', [])))}/2"
    if view.step == 5:
        return "Identificar uma rota segura de retorno"
    if view.step == 6:
        reports = set(view.progress.get("reports", []))
        return "Reportar a Alda Veyr e Oren Cal · " + f"{len(reports)}/2"
    return "Concluída"


def render_p4_detail(view: P4View) -> Screen:
    return Screen(
        "📜 Pedras que Ainda Vigiam · Em Andamento\nMissão Principal · Terras do Ocaso\n\n"
        f"🎯 Objetivo · {_objective(view)}\n📍 {view.location or 'Terras do Ocaso'}",
        "p4",
        _keyboard([[_button("Ver Objetivo", "p4:resume")], [_button("← Missões", "world:missions")]]),
    )


def render_p4(view: P4View) -> Screen:
    version = view.state_version
    progress = view.progress or {}
    if view.kind == "combat":
        return _combat(view)
    if view.kind == "offer":
        return Screen(
            "📜 Pedras que Ainda Vigiam\nMissão Principal · Terras do Ocaso\n"
            "Alda Veyr · Refúgio do Ocaso\n\n"
            "🎯 Seguir os vestígios até os limites das Ruínas do Vigia e reportar o que foi observado.",
            "p4",
            _keyboard([[_button("Aceitar Missão", f"p4:{version}:accept")], [_button("← Refúgio do Ocaso", "road:local")]]),
        )
    if view.kind == "unavailable":
        return Screen("🪖 Alda Veyr\n\n📜 Pedras que Ainda Vigiam · Indisponível no momento", "p4", _keyboard([[_button("← Refúgio do Ocaso", "road:local")]]))
    if view.kind == "completed" or view.status == "completed":
        return Screen(
            "✅ Pedras que Ainda Vigiam · Concluída\nMissão Principal · Terras do Ocaso\n\n"
            "✨ XP · 5.700\n🪙 Coroas · 250\n📦 Ferro de Fuligem · 2 · Vinculado\n"
            "📦 Resíduo do Ocaso · 2 · Vinculado\n📖 Antigos Asterianos atualizado",
            "p4",
            _keyboard([[_button("← Refúgio do Ocaso", "road:local")]]),
        )
    if view.kind == "alda":
        rows = []
        if view.status == "active":
            if view.step == 6:
                rows.append([_button("Reportar a Alda Veyr", f"p4:{view.state_version}:report:alda")])
            else:
                rows.append([_button("Ver Pedras que Ainda Vigiam", "p4:resume")])
        elif view.available:
            rows.append([_button("Pedras que Ainda Vigiam", "p4:offer")])
        rows.append([_button("← Refúgio do Ocaso", "road:local")])
        return Screen("🪖 Alda Veyr\nRefúgio do Ocaso · Terras do Ocaso", "p4", _keyboard(rows))
    if view.kind == "path":
        rows = []
        if view.location == BOSQUE:
            rows.append([_button("Seguir o Caminho Ocidental", f"p4:{version}:path")])
        elif view.location == REFUGE:
            rows.append([_button("Seguir para a Charneca", "road:route:charneca")])
        elif view.location == CHARNECA:
            rows.append([_button("Seguir para o Bosque", "road:route:bosque")])
        else:
            rows.append([_button("← Mapa", "world:map")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "📜 Pedras que Ainda Vigiam · Em Andamento\n🎯 Seguir o Caminho Ocidental\n"
            f"📍 {view.location or BOSQUE}",
            "p4",
            _keyboard(rows),
        )
    if view.kind == "enter_ruins":
        return Screen(
            "📜 Pedras que Ainda Vigiam · Em Andamento\n🌲 Bosque Calcinado\n\n"
            "🎯 Alcançar os limites das Ruínas do Vigia.\nA passagem é contextual à missão.",
            "p4",
            _keyboard([[_button("Seguir para as Ruínas", f"p4:{version}:enter")], [_button("← Missões", "world:missions")]]),
        )
    if view.kind == "recovery":
        rows = []
        if view.location == RUINS:
            rows.append([_button("Nova tentativa", f"p4:{version}:retry")])
        elif view.location == BOSQUE:
            rows.append([_button("Retornar às Ruínas", f"p4:{version}:enter")])
        elif view.location == "Charneca da Fuligem":
            rows.append([_button("Seguir para o Bosque", "road:route:bosque")])
        elif view.location == REFUGE:
            rows.append([_button("Seguir para a Charneca", "road:route:charneca")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "💀 Derrota · Vigia Rachado\n"
            f"🔥 {progress.get('recovery_brazier') or 'Braseiro do Refúgio'}\n"
            f"{progress.get('recovery_location') or view.location} · Terras do Ocaso\n"
            "❤️ HP · Restaurado\nVigor e Consumíveis usados permanecem como estavam.\n\n"
            "📜 Pedras que Ainda Vigiam · Em Andamento\n🎯 Retornar às Ruínas para uma nova tentativa.",
            "p4_recovery",
            _keyboard(rows),
        )
    if view.kind == "combat_pending":
        if view.proposal_id is not None:
            return Screen(
                "📜 Pedras que Ainda Vigiam · Confirmação de Grupo\n\n"
                "Confira elegibilidade, checkpoint e recompensa pessoal na tela do Grupo.",
                "p4",
                _keyboard(
                    [
                        [_button("Abrir Grupo", "group:root")],
                        [_button("Atualizar", "p4:resume")],
                    ]
                ),
            )
        rows = []
        if view.group_size > 1:
            rows.append([_button("Propor combate em Grupo", f"p4:{version}:group")])
        rows.append([_button("Enfrentar Solo", f"p4:{version}:solo")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "📜 Pedras que Ainda Vigiam · Em Andamento\n"
            "O caminho está livre para enfrentar o Vigia Rachado.",
            "p4",
            _keyboard(rows),
        )
    if view.kind == "structures":
        found = set(progress.get("structures", ()))
        lines = ["🛡️ Ruínas do Vigia · Contexto de Missão", "📜 Pedras que Ainda Vigiam", f"🎯 Examinar estruturas de guarda · {len(found)}/2", ""]
        buttons = []
        for index, key in enumerate(P4_STRUCTURES, 1):
            if key in found:
                lines.append(f"{index} ✅ Estrutura de Guarda {index}")
            else:
                lines.append(f"{index} ⚪ Estrutura de Guarda {index}")
                buttons.append(_button(str(index), f"p4:{version}:structure:{index}"))
        return Screen("\n".join(lines), "p4", _keyboard([buttons, [_button("← Missões", "world:missions")]]))
    if view.kind == "safe_route":
        return Screen(
            "📜 Pedras que Ainda Vigiam · Em Andamento\n🛡️ Ruínas do Vigia\n\n"
            "🎯 Identificar uma rota segura de retorno.",
            "p4",
            _keyboard([[_button("Identificar rota segura", f"p4:{version}:safe")], [_button("← Missões", "world:missions")]]),
        )
    if view.kind == "return":
        rows = []
        if view.location == RUINS:
            rows.append([_button("Retornar ao Bosque", f"p4:{version}:return")])
        elif view.location == BOSQUE:
            rows.append([_button("Seguir para a Charneca", f"p4:{version}:route:charneca")])
        elif view.location == "Charneca da Fuligem":
            rows.append([_button("Retornar ao Refúgio", f"p4:{version}:route:refuge")])
        else:
            rows.append([_button("Falar com Alda Veyr", f"p4:{version}:report_alda")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen("📜 Pedras que Ainda Vigiam · Em Andamento\n🎯 Retornar a Alda Veyr e Oren Cal no Refúgio do Ocaso.", "p4", _keyboard(rows))
    if view.kind == "reports":
        reports = set(progress.get("reports", ()))
        rows = []
        if "alda" not in reports:
            rows.append([_button("Reportar a Alda Veyr", f"p4:{version}:report_alda")])
        if "oren" not in reports:
            rows.append([_button("Reportar a Oren Cal", f"p4:{version}:report_oren")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(f"📜 Pedras que Ainda Vigiam · Em Andamento\nRefúgio do Ocaso\n\n🎯 Reportar a Alda Veyr e Oren Cal · {len(reports)}/2", "p4", _keyboard(rows))
    return render_p4_detail(view)
