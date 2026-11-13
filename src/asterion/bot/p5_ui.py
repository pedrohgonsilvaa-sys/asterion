"""Player-facing screens for P5, rendered only from the persistent mission view."""
# ruff: noqa: E501

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p5 import P5_ELEMENTS, P5_TITLE, P5View
from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, RUINS
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(label: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=data)


def _keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _combat(view: P5View) -> Screen:
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen(
            f"📜 {P5_TITLE} · O encontro está sendo reconstruído.",
            "p5",
            _keyboard([[_button("Atualizar", "p5:resume")]]),
        )
    hud = render_combat(
        CombatView(
            view.activity_id,
            view.encounter_id,
            view.character_id,
            view.combat,
            "p5",
            view.xp,
            context="p5",
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
        f"📜 {P5_TITLE} · Encontro de Missão\n🛡️ Custódio do Poente · Nv.9\n" + hud.text,
        "p5",
        hud.keyboard,
        parse_mode=hud.parse_mode,
    )


def _objective(view: P5View) -> str:
    progress = view.progress or {}
    if view.step == 1:
        return "Seguir as estruturas de guarda mais profundas das Ruínas"
    if view.step == 2:
        return "Encontrar a Porta do Poente"
    if view.step == 3:
        return "Derrotar o Custódio do Poente"
    if view.step == 4:
        found = set(progress.get("door_elements", ()))
        return f"Examinar elementos da estrutura · {len(found)}/3"
    if view.step == 5:
        return "Registrar o símbolo recorrente"
    if view.step == 6:
        reports = set(progress.get("reports", ()))
        return f"Reportar a Alda Veyr e Oren Cal · {len(reports)}/2"
    return "Concluída"


def _route_back_to_ruins(view: P5View):
    if view.location == REFUGE:
        return _button("Seguir para a Charneca", "road:route:charneca")
    if view.location == CHARNECA:
        return _button("Seguir para o Bosque", "road:route:bosque")
    if view.location == BOSQUE:
        return _button("Seguir para as Ruínas", "road:route:ruinas")
    return _button("Abrir Mapa", "world:map")


def _route_back_to_refuge(view: P5View):
    if view.location == RUINS:
        return _button("Retornar ao Bosque", "road:route:bosque")
    if view.location == BOSQUE:
        return _button("Seguir para a Charneca", "road:route:charneca")
    if view.location == CHARNECA:
        return _button("Retornar ao Refúgio", "road:route:refuge")
    return _button("Abrir Mapa", "world:map")


def render_p5_detail(view: P5View) -> Screen:
    return Screen(
        f"📜 {P5_TITLE} · Em Andamento\nMissão Principal · Terras do Ocaso\n\n"
        f"🎯 Objetivo · {_objective(view)}\n📍 {view.location or 'Terras do Ocaso'}",
        "p5",
        _keyboard([[_button("Ver Objetivo", "p5:resume")], [_button("← Missões", "world:missions")]]),
    )


def render_p5(view: P5View) -> Screen:
    version = view.state_version
    progress = view.progress or {}
    if view.kind == "combat":
        return _combat(view)
    if view.kind == "offer":
        return Screen(
            f"📜 {P5_TITLE}\nMissão Principal · Terras do Ocaso\n"
            "Alda Veyr · Refúgio do Ocaso\n\n"
            "🎯 Investigar as estruturas mais profundas das Ruínas do Vigia e registrar o que foi encontrado.",
            "p5",
            _keyboard(
                [[_button("Aceitar Missão", f"p5:{version}:accept")],
                 [_button("← Refúgio do Ocaso", "road:local")]]
            ),
        )
    if view.kind == "unavailable":
        return Screen(
            f"📜 {P5_TITLE} · Indisponível no momento\nMissão Principal · Terras do Ocaso\n"
            "Requer P4 concluída, Nv.9+ e conversa com Alda no Refúgio.",
            "p5",
            _keyboard([[_button("← Missões", "world:missions")]]),
        )
    if view.kind == "completed" or view.status == "completed":
        return Screen(
            f"✅ {P5_TITLE} · Concluída\nMissão Principal · Terras do Ocaso\n\n"
            "✨ XP · 7.100\n🪙 Coroas · 300\n"
            "📦 Ferro de Fuligem · 3 · Vinculado\n"
            "📦 Resíduo do Ocaso · 1 · Vinculado\n"
            "📖 Antigos Asterianos · Atualizado",
            "p5",
            _keyboard([[_button("← Refúgio do Ocaso", "road:local")]]),
        )
    if view.kind in {"alda", "oren"}:
        rows = []
        if view.status == "active":
            if view.step == 6 and view.location == REFUGE:
                reports = set(progress.get("reports", ()))
                person = view.kind
                if person not in reports:
                    name = "Alda Veyr" if person == "alda" else "Oren Cal"
                    rows.append([_button(f"Reportar a {name}", f"p5:{version}:report:{person}")])
            else:
                rows.append([_button(f"Ver {P5_TITLE}", "p5:resume")])
        elif view.status == "completed":
            rows.append([_button(f"{P5_TITLE} · Concluída", "p5:resume")])
        elif view.available and view.kind == "alda":
            rows.append([_button(P5_TITLE, "p5:offer")])
        rows.append([_button("← Refúgio do Ocaso", "road:local")])
        npc = "Alda Veyr" if view.kind == "alda" else "Oren Cal"
        return Screen(
            f"🪖 {npc}\nRefúgio do Ocaso · Terras do Ocaso",
            "p5",
            _keyboard(rows),
        )
    if view.kind == "travel":
        return Screen(
            f"📜 {P5_TITLE} · Em Andamento\n\n"
            f"🎯 Objetivo · {_objective(view)}\n📍 {view.location}\n\n"
            "Use as rotas terrestres ou uma Travessia dos Braseiros já disponível para chegar às Ruínas.",
            "p5",
            _keyboard([[_route_back_to_ruins(view)], [_button("← Missões", "world:missions")]]),
        )
    if view.kind == "follow_structures":
        return Screen(
            f"🛡️ Ruínas do Vigia\n📜 {P5_TITLE} · Em Andamento\n\n"
            "🎯 Seguir as estruturas de guarda mais profundas.",
            "p5",
            _keyboard(
                [[_button("Seguir estruturas de guarda", f"p5:{version}:follow")],
                 [_button("← Missões", "world:missions")]]
            ),
        )
    if view.kind == "find_door":
        return Screen(
            f"🛡️ Ruínas do Vigia\n📜 {P5_TITLE} · Em Andamento\n\n"
            "🎯 Encontrar a Porta do Poente.",
            "p5",
            _keyboard(
                [[_button("Encontrar Porta do Poente", f"p5:{version}:door")],
                 [_button("← Missões", "world:missions")]]
            ),
        )
    if view.kind == "combat_pending":
        rows = []
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Nova tentativa Solo", f"p5:{version}:retry")])
        else:
            rows.append([_button("Enfrentar Solo", f"p5:{version}:start_boss")])
        if view.progress.get("door_known") and view.location == RUINS:
            rows.append([_button("Formar Grupo", f"p5:{version}:group")])
        rows.extend([[_button("Grupo", "group:root")], [_button("← Missões", "world:missions")]])
        return Screen(
            f"📜 {P5_TITLE} · Em Andamento\n🎯 Enfrentar o Custódio do Poente.\n\n"
            "Você pode seguir sozinho ou confirmar uma formação cooperativa.",
            "p5",
            _keyboard(rows),
        )
    if view.kind == "recovery":
        rows = []
        if view.location == RUINS:
            rows.append([_button("Nova tentativa", f"p5:{version}:retry")])
            rows.append([_button("Formar Grupo", f"p5:{version}:group")])
        else:
            rows.append([_route_back_to_ruins(view)])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "💀 Derrota · Custódio do Poente\n"
            f"🔥 {progress.get('recovery_brazier') or 'Braseiro do Refúgio'}\n"
            f"{progress.get('recovery_location') or view.location} · Terras do Ocaso\n"
            "❤️ HP · Restaurado\nVigor e Consumíveis usados permanecem como estavam.\n\n"
            f"📜 {P5_TITLE} · Em Andamento\n🎯 Retornar às Ruínas para uma nova tentativa.",
            "p5_recovery",
            _keyboard(rows),
        )
    if view.kind == "elements":
        found = set(progress.get("door_elements", ()))
        labels = ("Batente da Porta", "Verga Entalhada", "Soleira Gasta")
        lines = [
            "🚪 Porta do Poente",
            f"📜 {P5_TITLE} · Em Andamento",
            f"🎯 Elementos da Estrutura · {len(found)}/3",
            "",
        ]
        buttons = []
        for index, (key, label) in enumerate(zip(P5_ELEMENTS, labels, strict=True), 1):
            if key in found:
                lines.append(f"✅ {label}")
            else:
                lines.append(f"⚪ {label}")
                buttons.append([_button(label, f"p5:{version}:element:{index}")])
        return Screen(
            "\n".join(lines),
            "p5",
            _keyboard([*buttons, [_button("← Missões", "world:missions")]]),
        )
    if view.kind == "record_symbol":
        return Screen(
            f"🚪 Porta do Poente\n📜 {P5_TITLE} · Em Andamento\n\n"
            "🎯 Registrar o símbolo recorrente sem atribuir a ele um significado ainda não comprovado.",
            "p5",
            _keyboard(
                [[_button("Registrar símbolo", f"p5:{version}:symbol")],
                 [_button("← Missões", "world:missions")]]
            ),
        )
    if view.kind == "return":
        return Screen(
            f"📜 {P5_TITLE} · Em Andamento\n\n"
            "🎯 Retornar às Ruínas do Vigia ao Refúgio do Ocaso pelas rotas disponíveis.",
            "p5",
            _keyboard([[_route_back_to_refuge(view)], [_button("← Missões", "world:missions")]]),
        )
    if view.kind == "reports":
        reports = set(progress.get("reports", ()))
        rows = []
        if "alda" not in reports:
            rows.append([_button("Reportar a Alda Veyr", f"p5:{version}:report:alda")])
        if "oren" not in reports:
            rows.append([_button("Reportar a Oren Cal", f"p5:{version}:report:oren")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {P5_TITLE} · Em Andamento\nRefúgio do Ocaso\n\n"
            f"🎯 Reportar a Alda Veyr e Oren Cal · {len(reports)}/2"
            + (
                "\n\nAlda Veyr\n<i>— Se puseram um guardião diante dessa porta, então o que existe depois dela importava mais do que estas ruínas inteiras.</i>"
                if "alda" in reports
                else ""
            ),
            "p5",
            _keyboard(rows),
            parse_mode="HTML",
        )
    return render_p5_detail(view)
