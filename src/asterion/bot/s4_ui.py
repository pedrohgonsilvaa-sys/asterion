"""Telegram screens for S4, derived only from the persistent S4 view."""
# ruff: noqa: E501

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, RUINS
from asterion.application.s4 import S4_TITLE, S4_WATCH_POINTS, S4View
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(label: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=data)


def _keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _combat(view: S4View) -> Screen:
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen(
            f"📜 {S4_TITLE} · O encontro está sendo reconstruído.", "s4",
            _keyboard([[_button("Atualizar", "s4:resume")]]),
        )
    hud = render_combat(
        CombatView(
            view.activity_id, view.encounter_id, view.character_id, view.combat,
            "s4", view.xp, context="s4", consumable_options=view.consumable_options,
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
    return Screen(
        f"📜 {S4_TITLE} · Encontro de Missão\n" + hud.text,
        "s4", hud.keyboard, parse_mode=hud.parse_mode,
    )


def _routes(view: S4View):
    if view.location == REFUGE:
        return [[_button("Seguir para a Charneca", "road:route:charneca")]]
    if view.location == CHARNECA:
        return [[_button("Seguir para o Bosque", "road:route:bosque")]]
    if view.location == BOSQUE:
        if view.level >= 7:
            return [[_button("Seguir para as Ruínas", "road:route:ruinas")]]
        return []
    if view.location == RUINS:
        return []
    return []


def _objective(view: S4View) -> str:
    if view.step == 1:
        return f"Investigar os antigos pontos de vigia · {len(set(view.progress.get('watch_points', ())) )}/3"
    if view.step == 2:
        return "Registrar a orientação das marcas de patrulha"
    if view.step == 3:
        return "Derrotar o Vigia Rachado · Nv.7"
    if view.step == 4:
        return "Localizar onde a patrulha muda de direção"
    if view.step == 5:
        return "Examinar o ponto de mudança"
    return "Retornar a Oren Cal no Refúgio do Ocaso"


def render_s4_detail(view: S4View) -> Screen:
    return Screen(
        f"📜 {S4_TITLE} · Em Andamento\nMissão Secundária · Terras do Ocaso\n\n"
        f"🎯 Objetivo · {_objective(view)}\n📍 {view.location or 'Terras do Ocaso'}",
        "s4",
        _keyboard([
            [_button("Deixar de Acompanhar" if view.tracked else "Acompanhar", f"s4:{view.state_version}:track")],
            [_button("Ver Objetivo", "s4:resume")],
            [_button("Abandonar Missão", "s4:abandon")],
            [_button("← Missões", "world:missions")],
        ]),
    )


def render_s4(view: S4View) -> Screen:
    version = view.state_version
    progress = view.progress or {}
    if view.kind == "combat":
        return _combat(view)
    if view.kind == "detail":
        return render_s4_detail(view)
    if view.kind == "offer":
        accept_action = "reaccept" if view.reacceptable else "accept"
        accept_label = "Reaceitar Missão" if view.reacceptable else "Aceitar Missão"
        return Screen(
            f"📜 {S4_TITLE}\nMissão Secundária · Terras do Ocaso\nOren Cal · Refúgio do Ocaso\n\n"
            "Investigue antigos pontos de vigia e compare as marcas deixadas nas Ruínas.",
            "s4", _keyboard([
                [_button(accept_label, f"s4:{version}:{accept_action}")],
                [_button("← Refúgio do Ocaso", "road:local")],
            ]),
        )
    if view.kind == "unavailable":
        rows = []
        rows.append([_button("← Refúgio do Ocaso", "road:local")])
        return Screen(
            f"✒️ Oren Cal\n\n📜 {S4_TITLE} · Indisponível no momento\n"
            "Requer Pedras que Ainda Vigiam concluída e Nv.7.",
            "s4", _keyboard(rows),
        )
    if view.kind == "completed" or view.status == "completed":
        return Screen(
            f"✅ {S4_TITLE} · Concluída\nMissão Secundária · Terras do Ocaso\n\n"
            "✨ XP · 3.990\n🪙 Coroas · 150\n📦 Ferro de Fuligem · 2 · Vinculado\n"
            "📦 Couro Escoriado · 1 · Vinculado\n📦 Resíduo do Ocaso · 1 · Vinculado",
            "s4", _keyboard([[_button("← Refúgio do Ocaso", "road:local")]]),
        )
    if view.kind == "abandon_confirm":
        return Screen(
            f"⚠️ Abandonar Missão\n\n📜 {S4_TITLE}\n\n"
            "O progresso transitório será reiniciado ao reaceitar. Registros permanentes permanecem.",
            "s4_abandon", _keyboard([
                [_button("Confirmar Abandono", f"s4:{version}:abandon:confirm")],
                [_button(f"← {S4_TITLE}", "s4:resume")],
            ]),
        )
    if view.kind == "travel":
        rows = _routes(view)
        rows.append([_button("← Missões", "world:missions")])
        text = f"📜 {S4_TITLE} · Em Andamento\n🎯 {_objective(view)}\n📍 {view.location}"
        if view.location == BOSQUE and view.level < 8:
            text += "\n\n🔒 Ruínas do Vigia · Acesso normal a partir do Nv.8"
        return Screen(text, "s4", _keyboard(rows))
    if view.kind == "watch_points":
        found = set(progress.get("watch_points", ()))
        rows = []
        for index, key in enumerate(S4_WATCH_POINTS, start=1):
            if key not in found:
                rows.append([_button(str(index), f"s4:{version}:watch:{index}")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"🛡️ Ruínas do Vigia\n📜 {S4_TITLE}\n🎯 Antigos Pontos de Vigia · {len(found)}/3\n\n"
            + "\n".join(
                f"{index} {'✅' if key in found else '⚪'} Ponto de vigia"
                for index, key in enumerate(S4_WATCH_POINTS, start=1)
            ),
            "s4", _keyboard(rows),
        )
    if view.kind == "orientation":
        return Screen(
            f"🛡️ Ruínas do Vigia\n📜 {S4_TITLE}\n\n🎯 Registrar a orientação das marcas de patrulha",
            "s4", _keyboard([
                [_button("Registrar orientação", f"s4:{version}:orientation")],
                [_button("← Missões", "world:missions")],
            ]),
        )
    if view.kind == "combat_pending":
        if view.proposal_id is not None:
            return Screen(
                f"📜 {S4_TITLE} · Confirmação de Grupo\n\n"
                "A proposta para enfrentar o Vigia Rachado está ativa. "
                "Confira elegibilidade e confirme a entrada na tela do Grupo.",
                "s4",
                _keyboard([
                    [_button("Abrir Grupo", "group:root")],
                    [_button("Atualizar", "s4:resume")],
                ]),
            )
        rows = []
        if view.group_size > 1:
            rows.append([_button("Propor combate em Grupo", f"s4:{version}:group")])
        rows.append([_button("Enfrentar Solo", f"s4:{version}:solo")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {S4_TITLE} · Em Andamento\n🎯 O Vigia Rachado aguarda nas Ruínas.",
            "s4", _keyboard(rows),
        )
    if view.kind == "recovery":
        rows = []
        if view.location == RUINS:
            rows.append([_button("Tentar novamente", f"s4:{version}:retry")])
            if view.group_size > 1:
                rows.append([_button("Propor tentativa em Grupo", f"s4:{version}:group")])
        else:
            rows.extend(_routes(view))
        rows.append([_button("← Missões", "world:missions")])
        text = (
            "💀 Derrota · Vigia Rachado\n"
            f"🔥 {progress.get('recovery_brazier') or 'Braseiro do Refúgio'}\n"
            f"{progress.get('recovery_location') or view.location} · Terras do Ocaso\n"
            "❤️ HP · Restaurado\nVigor e Consumíveis usados permanecem.\n\n"
            f"📜 {S4_TITLE} · Etapa 3 · Progresso anterior preservado"
        )
        if view.location == BOSQUE and view.level < 8:
            text += "\n🔒 Ruínas do Vigia · Acesso normal a partir do Nv.8"
        return Screen(text, "s4_recovery", _keyboard(rows))
    if view.kind == "turn_point":
        return Screen(
            f"🛡️ Ruínas do Vigia\n📜 {S4_TITLE}\n\n🎯 Localizar o ponto onde a patrulha muda de direção",
            "s4", _keyboard([
                [_button("Localizar mudança da patrulha", f"s4:{version}:turn")],
                [_button("← Missões", "world:missions")],
            ]),
        )
    if view.kind == "examine":
        return Screen(
            f"🛡️ Ruínas do Vigia\n📜 {S4_TITLE}\n\n🎯 Examinar o local sem tirar conclusões além do registro.",
            "s4", _keyboard([
                [_button("Examinar local", f"s4:{version}:examine")],
                [_button("← Missões", "world:missions")],
            ]),
        )
    if view.kind == "return":
        rows = []
        if view.location == RUINS:
            rows.append([_button("Retornar ao Bosque", "road:route:bosque")])
        elif view.location == BOSQUE:
            rows.append([_button("Seguir para a Charneca", "road:route:charneca")])
        elif view.location == CHARNECA:
            rows.append([_button("Retornar ao Refúgio", "road:route:refuge")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {S4_TITLE} · Em Andamento\n🎯 Retornar a Oren Cal\n📍 {view.location}",
            "s4", _keyboard(rows),
        )
    if view.kind == "report":
        return Screen(
            f"✒️ Oren Cal\n\n📜 {S4_TITLE}\n\n"
            "— Eles não patrulham ao acaso. Isso não prova vontade. Prova que houve uma ordem bastante precisa para sobreviver a quem a deu.",
            "s4", _keyboard([
                [_button("Reportar a Oren Cal", f"s4:{version}:report")],
                [_button("← Missões", "world:missions")],
            ]),
        )
    if view.kind == "oren":
        return Screen("✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso", "oren_cal", _keyboard([]))
    return render_s4_detail(view)
