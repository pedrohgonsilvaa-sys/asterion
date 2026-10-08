"""Player-facing S6 screens rendered from the persistent Quest view."""
# ruff: noqa: E501

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, RUINS
from asterion.application.s6 import S6_MARKS, S6_TITLE, S6View
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _b(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)


def _kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _combat(view):
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen(f"📜 {S6_TITLE} · O encontro está sendo reconstruído.", "s6",
                      _kb([[_b("Atualizar", "s6:resume")]]))
    hud = render_combat(CombatView(
        view.activity_id, view.encounter_id, view.character_id, view.combat,
        "s6", view.xp, context="s6", consumable_options=view.consumable_options,
        consumable_screen=view.consumable_screen,
        selected_consumable_id=view.selected_consumable_id,
        selected_target_id=view.selected_target_id, selection_parent=view.selection_parent,
        consumable_notice=view.consumable_notice,
        consumable_quantities=view.consumable_quantities,
        consumable_budget_limit=view.consumable_budget_limit,
        ready_consumable_option=view.ready_consumable_option,
        combat_actor_key=view.combat_actor_key,
    ))
    enemy_name = view.combat.fighters.get("enemy").name if view.combat and view.combat.fighters.get("enemy") else "Guardião do Último Rastro"
    return Screen(f"📜 {S6_TITLE} · Encontro de Missão\n🛡️ {enemy_name} · Nv.10\n" + hud.text,
                  "s6", hud.keyboard, parse_mode=hud.parse_mode)


def _objective(view):
    if view.step == 1:
        return "Revisar com Oren os fragmentos recuperados em S2"
    if view.step == 2:
        return f"Seguir três marcas de passagem · {len(view.progress.get('pilgrim_marks', ()) )}/3"
    if view.step == 3:
        return "Examinar o abrigo abandonado"
    if view.step == 4:
        return "Derrotar o Custódio Sem Rosto"
    if view.step == 5:
        return "Encontrar o último registro legível da rota"
    if view.step == 6:
        return "Retornar a Oren Cal no Refúgio"
    return "Concluída"


def _to_ruins(view):
    destination = {REFUGE: ("Seguir para a Charneca", "road:route:charneca"),
                   CHARNECA: ("Seguir para o Bosque", "road:route:bosque"),
                   BOSQUE: ("Seguir para as Ruínas", "road:route:ruinas")}
    label, callback = destination.get(view.location, ("Abrir Mapa", "world:map"))
    return _b(label, callback)


def _to_refuge(view):
    destination = {RUINS: ("Retornar ao Bosque", "road:route:bosque"),
                   BOSQUE: ("Seguir para a Charneca", "road:route:charneca"),
                   CHARNECA: ("Retornar ao Refúgio", "road:route:refuge")}
    label, callback = destination.get(view.location, ("Abrir Mapa", "world:map"))
    return _b(label, callback)


def _render_s6_screen(view: S6View) -> Screen:
    v, p = view.state_version, view.progress or {}
    if view.kind == "combat":
        return _combat(view)
    if view.status == "abandoned" or view.kind == "abandoned":
        return Screen(f"📜 {S6_TITLE} · Abandonada\nO progresso desta missão pode ser recomeçado com Oren.",
                      "s6", _kb([[_b("Reaceitar", f"s6:{v}:reaccept")], [_b("← Refúgio", "road:local")]]))
    if view.kind in {"offer", "oren"} and view.available:
        rows = [[_b("Aceitar missão", f"s6:{v}:accept")], [_b("← Refúgio", "road:local")]]
        return Screen(f"📜 {S6_TITLE}\nMissão Secundária · Terras do Ocaso\nOren Cal · Refúgio do Ocaso\n\n"
                      "🎯 Registrar onde a trilha dos Peregrinos deixou de ser uma estrada e virou vestígio.",
                      "s6", _kb(rows))
    if view.status == "completed" or view.kind == "completed":
        return Screen(f"✅ {S6_TITLE} · Concluída\nMissão Secundária · Terras do Ocaso\n\n"
                      "✨ XP · 7.900\n🪙 Coroas · 310\n📦 Ferro de Fuligem · 2 · Vinculado\n"
                      "📦 Couro Escoriado · 2 · Vinculado\n📦 Erva Cinzenta · 2 · Vinculado\n"
                      "📦 Resíduo do Ocaso · 2 · Vinculado\n"
                      "📖 Peregrinos do Ocaso · Atualizado\n📖 Ruínas do Vigia · Atualizado",
                      "s6", _kb([[_b("← Refúgio", "road:local")]]))
    if view.kind in {"travel_ruins", "return_refuge", "travel_refuge"}:
        route = _to_ruins(view) if view.kind == "travel_ruins" else _to_refuge(view)
        return Screen(f"📜 {S6_TITLE} · Em Andamento\n\n🎯 {_objective(view)}\n📍 {view.location}\n\n"
                      "Use as rotas terrestres conhecidas para continuar.", "s6",
                      _kb([[route], [_b("← Missões", "world:missions")]]))
    if view.kind == "review":
        return Screen(f"📜 {S6_TITLE} · Em Andamento\nRefúgio do Ocaso\n\n🎯 Revisar com Oren os fragmentos recuperados em S2.",
                      "s6", _kb([[_b("Revisar fragmentos", f"s6:{v}:review")], [_b("← Missões", "world:missions")]]))
    if view.kind == "marks":
        found = set(p.get("pilgrim_marks", ()))
        rows, lines = [], ["🛡️ Ruínas do Vigia", f"📜 {S6_TITLE} · Em Andamento", f"🎯 Marcas de passagem · {len(found)}/3", ""]
        for i, key in enumerate(S6_MARKS, 1):
            lines.append(f"{i} {'✅' if key in found else '⚪'} Marca de passagem")
            if key not in found:
                rows.append([_b(f"Examinar marca {i}", f"s6:{v}:mark:{i}")])
        rows.append([_b("← Missões", "world:missions")])
        return Screen("\n".join(lines), "s6", _kb(rows))
    if view.kind == "shelter":
        return Screen(f"🛡️ Ruínas do Vigia\n📜 {S6_TITLE} · Em Andamento\n\n🎯 Examinar o abrigo abandonado.",
                      "s6", _kb([[_b("Examinar abrigo", f"s6:{v}:shelter")], [_b("← Missões", "world:missions")]]))
    if view.kind in {"combat_pending", "recovery"}:
        if view.kind == "recovery":
            rows = [[_to_ruins(view)]]
            if view.location == RUINS:
                rows = [[_b("Nova tentativa", f"s6:{v}:retry")]]
                rows.append([_b("Formar Grupo", f"s6:{v}:group")])
            text = (f"❌ Derrota · Custódio Sem Rosto\n🔥 {p.get('recovery_brazier') or 'Braseiro do Refúgio'}\n"
                    f"{p.get('recovery_location') or view.location} · Terras do Ocaso\n❤️ HP · Restaurado\nVigor e Consumíveis usados permanecem.\n\n"
                    "As marcas e o abrigo permanecem registrados.")
            rows.append([_b("← Missões", "world:missions")])
            return Screen(text, "s6_recovery", _kb(rows))
        return Screen(
            f"📜 {S6_TITLE} · Em Andamento\n🎯 Enfrentar o Guardião do Último Rastro.",
            "s6",
            _kb(
                [
                    [_b("Enfrentar Solo", f"s6:{v}:start_boss")],
                    [_b("Formar Grupo", f"s6:{v}:group")],
                    [_b("Grupo", "group:root")],
                    [_b("← Missões", "world:missions")],
                ]
            ),
        )
    if view.kind == "last_record":
        return Screen(f"🛡️ Ruínas do Vigia\n📜 {S6_TITLE} · Em Andamento\n\n🎯 Encontrar o último registro legível da rota.",
                      "s6", _kb([[_b("Examinar registro", f"s6:{v}:record")], [_b("← Missões", "world:missions")]]))
    if view.kind == "report":
        return Screen(f"📜 {S6_TITLE} · Em Andamento\nRefúgio do Ocaso\n\n🎯 Reportar a Oren Cal.\n\n"
                      "<i>“Não encontrei o nome de cada um. Talvez nunca encontremos. Mas sabemos onde a trilha deles deixou de ser uma estrada e virou apenas vestígio.”</i>",
                      "s6", _kb([[_b("Reportar a Oren Cal", f"s6:{v}:report")], [_b("← Missões", "world:missions")]]), parse_mode="HTML")
    if view.kind == "unavailable":
        return Screen(f"📜 {S6_TITLE} · Indisponível no momento\nRequer S2 e P5 concluídas, Nv.10 e conversa com Oren no Refúgio.",
                      "s6", _kb([[_b("← Missões", "world:missions")]]))
    return Screen(f"📜 {S6_TITLE} · Em Andamento\n🎯 {_objective(view)}", "s6",
                  _kb([[_b("Ver objetivo", "s6:resume")], [_b("← Missões", "world:missions")]]))


def render_s6(view: S6View) -> Screen:
    screen = _render_s6_screen(view)
    if view.status != "active" or view.kind == "combat":
        return screen
    rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
    tracking_label = "Parar acompanhamento" if view.tracked else "Acompanhar missão"
    rows.append([_b(tracking_label, f"s6:{view.state_version}:track")])
    rows.append([_b("Abandonar missão", f"s6:{view.state_version}:abandon")])
    return Screen(screen.text, screen.image_key, _kb(rows), parse_mode=screen.parse_mode)
