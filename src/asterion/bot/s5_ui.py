"""Telegram screens for S5, reconstructed from its persistent service view."""
# ruff: noqa: E501

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, RUINS
from asterion.application.s5 import S5_LIGHT_POINTS, S5_TITLE, S5View
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(label: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=data)


def _keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _combat(view: S5View) -> Screen:
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen(
            f"📜 {S5_TITLE} · O encontro está sendo reconstruído.", "s5",
            _keyboard([[_button("Atualizar", "s5:resume")]]),
        )
    hud = render_combat(
        CombatView(
            view.activity_id, view.encounter_id, view.character_id, view.combat,
            "s5", view.xp, context="s5", consumable_options=view.consumable_options,
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
        f"📜 {S5_TITLE} · Encontro de Missão\n" + hud.text,
        "s5", hud.keyboard, parse_mode=hud.parse_mode,
    )


def _routes(view: S5View):
    if view.location == REFUGE:
        return [[_button("Seguir para a Charneca", "road:route:charneca")]]
    if view.location == CHARNECA:
        return [[_button("Seguir para o Bosque", "road:route:bosque")]]
    if view.location == BOSQUE:
        return [[_button("Seguir para as Ruínas", "road:route:ruinas")]]
    if view.location == RUINS:
        return []
    return []


def _objective(view: S5View) -> str:
    if view.step == 1:
        return "Investigar um relato de luz nas Ruínas"
    if view.step == 2:
        return f"Examinar os pontos de luz · {len(set(view.progress.get('light_points', ())) )}/2"
    if view.step == 3:
        return "Vencer o encontro nas Ruínas"
    if view.step == 4:
        return "Registrar a direção e a duração observadas"
    return "Retornar a Oren Cal no Refúgio do Ocaso"


def render_s5_detail(view: S5View) -> Screen:
    return Screen(
        f"📜 {S5_TITLE} · Em Andamento\nMissão Secundária · Terras do Ocaso\n\n"
        f"🎯 Objetivo · {_objective(view)}\n📍 {view.location or 'Terras do Ocaso'}",
        "s5",
        _keyboard([
            [_button("Deixar de Acompanhar" if view.tracked else "Acompanhar", f"s5:{view.state_version}:track")],
            [_button("Ver Objetivo", "s5:resume")],
            [_button("Abandonar Missão", "s5:abandon")],
            [_button("← Missões", "world:missions")],
        ]),
    )


def render_s5(view: S5View) -> Screen:
    version = view.state_version
    progress = view.progress or {}
    if view.kind == "combat":
        return _combat(view)
    if view.kind == "detail":
        return render_s5_detail(view)
    if view.kind == "offer":
        accept_action = "reaccept" if view.reacceptable else "accept"
        accept_label = "Reaceitar Missão" if view.reacceptable else "Aceitar Missão"
        return Screen(
            f"📜 {S5_TITLE}\nMissão Secundária · Terras do Ocaso\nOren Cal · Refúgio do Ocaso\n\n"
            "Investigue relatos repetidos de luminosidade nas Ruínas, sem uma explicação conhecida.",
            "s5", _keyboard([
                [_button(accept_label, f"s5:{version}:{accept_action}")],
                [_button("← Refúgio do Ocaso", "road:local")],
            ]),
        )
    if view.kind == "unavailable":
        rows = []
        rows.append([_button("← Refúgio do Ocaso", "road:local")])
        return Screen(
            f"✒️ Oren Cal\n\n📜 {S5_TITLE} · Indisponível no momento\n"
            "Requer Pedras que Ainda Vigiam concluída e Nv.8.",
            "s5", _keyboard(rows),
        )
    if view.kind == "completed" or view.status == "completed":
        return Screen(
            f"✅ {S5_TITLE} · Concluída\nMissão Secundária · Terras do Ocaso\n\n"
            "✨ XP · 4.480\n🪙 Coroas · 160\n📦 Ferro de Fuligem · 1 · Vinculado\n"
            "📦 Erva Cinzenta · 1 · Vinculado\n📦 Resíduo do Ocaso · 2 · Vinculado\n"
            "📖 Luzes do Ocaso · Descoberto",
            "s5", _keyboard([[_button("← Refúgio do Ocaso", "road:local")]]),
        )
    if view.kind == "abandon_confirm":
        return Screen(
            f"⚠️ Abandonar Missão\n\n📜 {S5_TITLE}\n\n"
            "O progresso transitório será reiniciado ao reaceitar. Registros permanentes permanecem.",
            "s5_abandon", _keyboard([
                [_button("Confirmar Abandono", f"s5:{version}:abandon:confirm")],
                [_button(f"← {S5_TITLE}", "s5:resume")],
            ]),
        )
    if view.kind == "travel":
        rows = _routes(view)
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {S5_TITLE} · Em Andamento\n🎯 {_objective(view)}\n📍 {view.location}",
            "s5", _keyboard(rows),
        )
    if view.kind == "investigate":
        return Screen(
            f"✨ Ruínas do Vigia\n📜 {S5_TITLE}\n\n🎯 Investigar um relato de luz",
            "s5", _keyboard([
                [_button("Investigar relato de luz", f"s5:{version}:investigate")],
                [_button("← Missões", "world:missions")],
            ]),
        )
    if view.kind == "light_points":
        found = set(progress.get("light_points", ()))
        rows = []
        for index, key in enumerate(S5_LIGHT_POINTS, start=1):
            if key not in found:
                rows.append([_button(str(index), f"s5:{version}:light:{index}")])
        rows.append([_button("← Missões", "world:missions")])
        text = (
            f"✨ Ruínas do Vigia\n📜 {S5_TITLE}\n🎯 Pontos de Luz · {len(found)}/2\n\n"
            + "\n".join(
                f"{index} {'✅' if key in found else '⚪'} Ponto de Luz"
                for index, key in enumerate(S5_LIGHT_POINTS, start=1)
            )
        )
        return Screen(text, "s5", _keyboard(rows))
    if view.kind == "combat_pending":
        if view.proposal_id is not None:
            return Screen(
                f"📜 {S5_TITLE} · Confirmação de Grupo\n\n"
                "A proposta para investigar o fenômeno está ativa. "
                "Confira elegibilidade e confirme a entrada na tela do Grupo.",
                "s5",
                _keyboard([
                    [_button("Abrir Grupo", "group:root")],
                    [_button("Atualizar", "s5:resume")],
                ]),
            )
        rows = []
        if view.group_size > 1:
            rows.append([_button("Propor encontro em Grupo", f"s5:{version}:group")])
        rows.append([_button("Investigar Solo", f"s5:{version}:solo")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            f"📜 {S5_TITLE} · Em Andamento\n🎯 O fenômeno aguarda nas Ruínas.",
            "s5", _keyboard(rows),
        )
    if view.kind == "recovery":
        rows = []
        if view.location == RUINS:
            rows.append([_button("Tentar novamente", f"s5:{version}:retry")])
            if view.group_size > 1:
                rows.append([_button("Propor tentativa em Grupo", f"s5:{version}:group")])
        else:
            rows.extend(_routes(view))
        rows.append([_button("← Missões", "world:missions")])
        text = (
            "💀 Derrota · Encontro das Ruínas\n"
            f"🔥 {progress.get('recovery_brazier') or 'Braseiro do Refúgio'}\n"
            f"{progress.get('recovery_location') or view.location} · Terras do Ocaso\n"
            "❤️ HP · Restaurado\nVigor e Consumíveis usados permanecem.\n\n"
            f"📜 {S5_TITLE} · Etapa 3 · Encontro preservado"
        )
        return Screen(text, "s5_recovery", _keyboard(rows))
    if view.kind == "record":
        return Screen(
            f"✨ Ruínas do Vigia\n📜 {S5_TITLE}\n\n🎯 Registrar direção e duração do fenômeno observado",
            "s5", _keyboard([
                [_button("Registrar fenômeno", f"s5:{version}:record")],
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
            f"📜 {S5_TITLE} · Em Andamento\n🎯 Retornar a Oren Cal\n📍 {view.location}",
            "s5", _keyboard(rows),
        )
    if view.kind == "report":
        return Screen(
            "✒️ Oren Cal\n\n📜 A Luz que Não Aquece\n\n"
            "— A primeira vez podia ser engano. A segunda, coincidência. Agora temos um padrão — e ainda não temos uma explicação.",
            "s5", _keyboard([
                [_button("Reportar a Oren Cal", f"s5:{version}:report")],
                [_button("← Missões", "world:missions")],
            ]),
        )
    return render_s5_detail(view)
