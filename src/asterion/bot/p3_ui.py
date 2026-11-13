"""Telegram presentation for P3; all progress comes from P3Service views."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p3 import P3_FRAGMENTS, P3_REWARD_CHOICES, P3View
from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, CHARNECA, REFUGE
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


_FRAGMENT_NAMES = ("Viga Calcinada", "Tábua Rachada", "Pedra Enegrecida")


def _keyboard(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def _combat(view: P3View) -> Screen:
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen(
            "🌿 Sob Galhos Calcinados · Em Andamento\n\n"
            "O encontro está sendo reconstruído a partir do estado registrado.",
            "p3",
            _keyboard([_button("Atualizar", "p3:resume")]),
        )
    combat_view = CombatView(
        activity_id=view.activity_id,
        encounter_id=view.encounter_id,
        character_id=view.character_id,
        combat=view.combat,
        stage="p3",
        xp=view.xp,
        context="p3",
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
    hud = render_combat(combat_view)
    return Screen(
        "🌿 Sob Galhos Calcinados · Combate de Missão\n\n" + hud.text,
        "p3",
        hud.keyboard,
        parse_mode=hud.parse_mode,
    )


def _objective(view: P3View) -> str:
    progress = view.progress or {}
    if view.step == 1:
        return "Entrar no Bosque Calcinado"
    if view.step == 2:
        return f"Localizar fragmentos de construção · {len(set(progress.get('fragments', [])))}/3"
    if view.step == 3:
        return "Vencer o Cervo Escoriado"
    if view.step == 4:
        return "Examinar o Fragmento Entalhado"
    if view.step == 5:
        return "Retornar a Oren Cal no Refúgio do Ocaso"
    return "Escolher um Equipamento Raro de Campanha"


def render_p3_detail(view: P3View) -> Screen:
    return Screen(
        "🌿 Sob Galhos Calcinados · Em Andamento\n"
        "Missão Principal · Terras do Ocaso\n\n"
        f"🎯 Objetivo · {_objective(view)}\n"
        f"📍 {view.location or 'Terras do Ocaso'}",
        "p3",
        _keyboard(
            [_button("Ver Objetivo", "p3:resume")],
            [_button("← Missões", "world:missions")],
        ),
    )


def render_p3(view: P3View) -> Screen:
    version = view.state_version
    progress = view.progress or {}

    if view.kind == "combat":
        return _combat(view)
    if view.kind == "offer":
        return Screen(
            "🌿 Sob Galhos Calcinados\n"
            "Missão Principal · Terras do Ocaso\n"
            "Oren Cal · Refúgio do Ocaso\n\n"
            "🎯 Investigar os fragmentos de construção sob as raízes do Bosque Calcinado.\n\n"
            "<i>— Pedra trabalhada debaixo de árvores queimadas. Isto estava aqui antes "
            "do Bosque ser como o conhecemos.</i>",
            "p3",
            _keyboard(
                [_button("Aceitar Missão", f"p3:{version}:accept")],
                [_button("← Refúgio do Ocaso", "road:local")],
            ),
            parse_mode="HTML",
        )
    if view.kind == "unavailable":
        return Screen(
            "✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso\n\n"
            "🌿 Sob Galhos Calcinados · Indisponível no momento",
            "oren_cal",
            _keyboard([_button("← Refúgio do Ocaso", "road:local")]),
        )
    if view.kind == "completed" or view.status == "completed":
        name = P3_REWARD_CHOICES.get(
            progress.get("selected_reward", ""), ("Equipamento Raro", "")
        )[0]
        return Screen(
            "✅ Sob Galhos Calcinados · Concluída\n"
            "Missão Principal · Terras do Ocaso\n\n"
            "✨ XP · 4.400\n🪙 Coroas · 180\n"
            f"🎁 {name} · Raro · Nv.5 · +0 · Vinculado ao Adquirir\n"
            "📖 Códice · Antigos Asterianos atualizado",
            "p3",
            _keyboard([_button("← Refúgio do Ocaso", "road:local")]),
        )
    if view.kind == "oren":
        rows: list[list[InlineKeyboardButton]] = []
        if view.status == "active" and view.step == 5:
            text = (
                "✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso\n\n"
                "<i>— Pedra trabalhada debaixo de árvores queimadas. Isto estava aqui antes "
                "do Bosque ser como o conhecemos.</i>\n\n"
                "🎯 Entregar o registro e escolher um Equipamento de Campanha."
            )
            rows.append([_button("Falar com Oren Cal", f"p3:{version}:oren")])
        elif view.status == "active" and view.step == 6:
            return render_p3(
                P3View(**{**view.__dict__, "kind": "choice"})
            )
        elif view.status == "active":
            text = (
                "✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso\n\n"
                "📜 Sob Galhos Calcinados · Em Andamento"
            )
            rows.append([_button("Ver Objetivo", "p3:resume")])
        elif view.status == "completed":
            return render_p3(P3View(**{**view.__dict__, "kind": "completed"}))
        elif view.available:
            text = "✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso"
            rows.append([_button("Sob Galhos Calcinados", "p3:offer")])
        else:
            text = "✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso"
        rows.append([_button("← Refúgio do Ocaso", "road:local")])
        return Screen(text, "oren_cal", InlineKeyboardMarkup(inline_keyboard=rows))
    if view.kind == "travel":
        if view.location == REFUGE:
            label, callback = "Seguir para a Charneca", f"p3:{version}:route:charneca"
            objective = "Viajar até a Charneca da Fuligem"
        elif view.location == CHARNECA:
            label, callback = "Seguir para o Bosque", f"p3:{version}:enter"
            objective = "Entrar no Bosque Calcinado"
        else:
            label, callback = "Atualizar", "p3:resume"
            objective = "Entrar no Bosque Calcinado"
        return Screen(
            "🌿 Sob Galhos Calcinados · Em Andamento\n"
            f"🎯 Objetivo · {objective}\n📍 {view.location} · Terras do Ocaso",
            "p3",
            _keyboard(
                [_button(label, callback)],
                [_button("← Missões", "world:missions")],
            ),
        )
    if view.kind == "fragments":
        found = set(progress.get("fragments", ()))
        lines = [
            "🌲 Bosque Calcinado · Terras do Ocaso",
            "🌿 Sob Galhos Calcinados · Em Andamento",
            f"🎯 Fragmentos de Construção · {len(found)}/3",
            "",
        ]
        pending = []
        for index, (name, fragment_id) in enumerate(
            zip(_FRAGMENT_NAMES, P3_FRAGMENTS, strict=True), start=1
        ):
            if fragment_id in found:
                lines.append(f"✅ {name}")
            else:
                lines.append(f"⚪ {name}")
                pending.append([_button(name, f"p3:{version}:fragment:{index}")])
        return Screen(
            "\n".join(lines),
            "p3",
            _keyboard(*pending, [_button("← Missões", "world:missions")]),
        )
    if view.kind == "recovery":
        brazier = progress.get("recovery_brazier") or "Braseiro do Refúgio"
        location = progress.get("recovery_location") or view.location
        rows = []
        if view.location == REFUGE:
            rows.append([_button("Seguir para a Charneca", f"p3:{version}:route:charneca")])
        elif view.location == CHARNECA:
            rows.append([_button("Retornar ao Bosque", f"p3:{version}:enter")])
        elif view.location == BOSQUE:
            rows.append([_button("Nova tentativa", f"p3:{version}:retry")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "💀 Derrota · Cervo Escoriado\n"
            f"🔥 {brazier}\n{location} · Terras do Ocaso\n"
            "❤️ HP · Restaurado\nVigor e Consumíveis usados são preservados.\n\n"
            "🌿 Sob Galhos Calcinados · Em Andamento\n"
            "🎯 Retornar ao encontro pela rota disponível.",
            "p3_recovery",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.kind == "combat_pending":
        if view.proposal_id is not None:
            return Screen(
                "🌿 Sob Galhos Calcinados · Confirmação de Grupo\n\n"
                "A proposta de combate está ativa. Confira a entrada e a elegibilidade "
                "na tela do Grupo.",
                "p3",
                _keyboard(
                    [_button("Abrir Grupo", "group:root")],
                    [_button("Atualizar", "p3:resume")],
                ),
            )
        rows = []
        if view.group_size > 1:
            rows.append([_button("Propor combate em Grupo", f"p3:{version}:group")])
        rows.append([_button("Enfrentar Solo", f"p3:{version}:solo")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "🌿 Sob Galhos Calcinados · Em Andamento\n"
            "O caminho está livre para iniciar o encontro com o Cervo Escoriado.",
            "p3",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    if view.kind == "carved":
        return Screen(
            "🏆 Cervo Escoriado derrotado\n"
            "🌲 Bosque Calcinado · Terras do Ocaso\n"
            "🌿 Sob Galhos Calcinados · Em Andamento\n\n"
            "🎯 Examinar o Fragmento Entalhado",
            "p3",
            _keyboard(
                [_button("Examinar Fragmento Entalhado", f"p3:{version}:carved")],
                [_button("← Missões", "world:missions")],
            ),
        )
    if view.kind == "return":
        if view.location == BOSQUE:
            label, callback = "Retornar à Charneca", f"p3:{version}:route:charneca"
        elif view.location == CHARNECA:
            label, callback = "Retornar ao Refúgio", f"p3:{version}:route:refuge"
        else:
            label, callback = "Falar com Oren Cal", "p3:oren"
        return Screen(
            "🌿 Sob Galhos Calcinados · Em Andamento\n"
            f"📍 {view.location} · Terras do Ocaso\n\n"
            "🎯 Retornar a Oren Cal no Refúgio do Ocaso.",
            "p3",
            _keyboard(
                [_button(label, callback)],
                [_button("← Missões", "world:missions")],
            ),
        )
    if view.kind == "choice":
        rows = []
        for choice, (name, slot) in P3_REWARD_CHOICES.items():
            rows.append(
                [_button(f"{name} · {slot} · Raro Nv.5", f"p3:{version}:choose:{choice}")]
            )
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "✒️ Oren Cal · Refúgio do Ocaso\n"
            "🌿 Sob Galhos Calcinados\n\n"
            "🎯 Escolher exatamente um Equipamento Raro de Campanha.\n"
            "A escolha conclui a missão e não pode ser trocada.",
            "p3_choice",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    return render_p3_detail(view)
