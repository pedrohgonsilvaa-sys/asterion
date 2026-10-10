"""Player-facing screens for S3, reconstructed from S3Service views."""
# ruff: noqa: E501

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, REFUGE
from asterion.application.s3 import S3_TRACKS, S3View
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(label: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=data)


def _keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _combat(view: S3View) -> Screen:
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen(
            "📜 Rastros sob os Galhos · Em Andamento\nO encontro está sendo reconstruído.",
            "s3",
            _keyboard([[_button("Atualizar", "s3:resume")]]),
        )
    hud = render_combat(
        CombatView(
            view.activity_id,
            view.encounter_id,
            view.character_id,
            view.combat,
            "s3",
            view.xp,
            context="s3",
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
    return Screen("📜 Rastros sob os Galhos · Encontro de Missão\n" + hud.text, "s3", hud.keyboard, parse_mode=hud.parse_mode)


def _objective(view: S3View) -> str:
    if view.step == 1:
        return "Examinar a rota de suprimentos interrompida no Bosque"
    if view.step == 2:
        return f"Seguir os rastros entre os galhos · {len(set(view.progress.get('tracks', [])))}/3"
    if view.step == 3:
        return "Derrotar o Cervo Escoriado"
    if view.step == 4:
        return "Verificar a carga abandonada"
    return "Reportar a Alda Veyr no Refúgio do Ocaso"


def render_s3_detail(view: S3View) -> Screen:
    track = _button(
        "Deixar de Acompanhar" if view.tracked else "Acompanhar",
        f"s3:{view.state_version}:track",
    )
    return Screen(
        "📜 Rastros sob os Galhos · Em Andamento\nMissão Curta · Terras do Ocaso\n\n"
        f"🎯 Objetivo · {_objective(view)}\n📍 {view.location or 'Terras do Ocaso'}",
        "s3",
        _keyboard([
            [track],
            [_button("Ver Objetivo", "s3:resume")],
            [_button("Abandonar Missão", "s3:abandon")],
            [_button("← Missões", "world:missions")],
        ]),
    )


def render_s3(view: S3View) -> Screen:
    version = view.state_version
    progress = view.progress or {}
    if view.kind == "combat":
        return _combat(view)
    if view.kind == "detail":
        return render_s3_detail(view)
    if view.kind == "offer":
        accept_label = "Reaceitar Missão" if view.reacceptable else "Aceitar Missão"
        accept_action = "reaccept" if view.reacceptable else "accept"
        return Screen(
            "📜 Rastros sob os Galhos\nMissão Curta · Terras do Ocaso\nAlda Veyr · Refúgio do Ocaso\n\n"
            "🎯 Investigar os rastros no Bosque Calcinado e relatar o que foi encontrado.",
            "s3",
            _keyboard([
                [_button(accept_label, f"s3:{version}:{accept_action}")],
                [_button("← Refúgio do Ocaso", "road:local")],
            ]),
        )
    if view.kind == "unavailable":
        rows = []
        if view.reacceptable:
            rows.append([_button("Reaceitar Missão", f"s3:{version}:reaccept")])
        rows.append([_button("← Refúgio do Ocaso", "road:local")])
        return Screen("🪖 Alda Veyr\n\n📜 Rastros sob os Galhos · Indisponível no momento", "s3", _keyboard(rows))
    if view.kind == "completed" or view.status == "completed":
        return Screen(
            "✅ Rastros sob os Galhos · Concluída\nMissão Curta · Terras do Ocaso\n\n"
            "✨ XP · 1.760\n🪙 Coroas · 90\n📦 Couro Escoriado · 2 · Vinculado",
            "s3",
            _keyboard([[_button("← Refúgio do Ocaso", "road:local")]]),
        )
    if view.kind == "abandon_confirm":
        return Screen(
            "⚠️ Abandonar Missão\n\n📜 Rastros sob os Galhos\n\n"
            "Etapa e progresso transitório serão reiniciados ao reaceitar.\n"
            "Registros permanentes já obtidos permanecem preservados.",
            "s1_abandon",
            _keyboard([
                [_button("Confirmar Abandono", f"s3:{version}:abandon:confirm")],
                [_button("← Rastros sob os Galhos", "s3:resume")],
            ]),
        )
    if view.kind == "alda":
        rows = []
        if view.status == "active":
            if view.step == 5:
                rows.append([_button("Reportar a Alda Veyr", f"s3:{version}:report")])
            else:
                rows.append([_button("Ver Rastros sob os Galhos", "s3:resume")])
        elif view.available or view.reacceptable:
            rows.append([_button("Rastros sob os Galhos", "s3:offer")])
        rows.append([_button("← Refúgio do Ocaso", "road:local")])
        return Screen("🪖 Alda Veyr\nRefúgio do Ocaso · Terras do Ocaso", "s3", _keyboard(rows))
    if view.kind == "route":
        if view.location == BOSQUE:
            rows = [[_button("Examinar rota de suprimentos", f"s3:{version}:route")]]
        elif view.campaign_active and view.location == "Refúgio do Ocaso":
            rows = [[_button("Seguir para a Charneca", f"p3:s3route:{version}:charneca")]]
        elif view.campaign_active and view.location == "Charneca da Fuligem":
            rows = [[_button("Seguir para o Bosque", f"p3:s3route:{version}:bosque")]]
        elif view.location == "Refúgio do Ocaso":
            rows = [[_button("Seguir para a Charneca", "road:route:charneca")]]
        elif view.location == "Charneca da Fuligem":
            rows = [[_button("Seguir para o Bosque", "road:route:bosque")]]
        else:
            rows = [[_button("Ver campanha ativa", "p3:resume")]]
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "📜 Rastros sob os Galhos · Em Andamento\n🎯 Examinar a rota de suprimentos interrompida\n"
            f"📍 {view.location}\n\nA investigação da missão ocorre no Bosque Calcinado.",
            "s3",
            _keyboard(rows),
        )
    if view.kind == "tracks":
        found = set(progress.get("tracks", ()))
        lines = ["🌲 Bosque Calcinado · Terras do Ocaso", "📜 Rastros sob os Galhos", "🎯 Rastros entre os galhos", ""]
        buttons = []
        for index, track in enumerate(S3_TRACKS, start=1):
            if track in found:
                lines.append(f"{index} ✅ Rastro {index}")
            else:
                lines.append(f"{index} ⚪ Rastro {index}")
                buttons.append(_button(str(index), f"s3:{version}:track:{index}"))
        return Screen("\n".join(lines), "s3", _keyboard([buttons, [_button("← Missões", "world:missions")]]))
    if view.kind == "recovery":
        rows = []
        if view.location == BOSQUE:
            rows.append([_button("Nova tentativa", f"s3:{version}:retry")])
            if view.group_size > 1:
                rows.append(
                    [_button("Propor tentativa em Grupo", f"s3:{version}:group")]
                )
        elif view.location == REFUGE:
            rows.append([_button(
                "Seguir para a Charneca",
                f"p3:s3route:{version}:charneca" if view.campaign_active else "road:route:charneca",
            )])
        elif view.location == "Charneca da Fuligem":
            rows.append([
                _button(
                    "Seguir para o Bosque",
                    f"p3:s3route:{version}:bosque" if view.campaign_active else "road:route:bosque",
                )
            ])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "💀 Derrota · Cervo Escoriado\n"
            f"🔥 {progress.get('recovery_brazier') or 'Braseiro do Refúgio'}\n"
            f"{progress.get('recovery_location') or view.location} · Terras do Ocaso\n"
            "❤️ HP · Restaurado\nVigor e Consumíveis usados permanecem como estavam.\n\n"
            "📜 Rastros sob os Galhos · Em Andamento\n🎯 Retornar ao Bosque para uma nova tentativa.",
            "s3_recovery",
            _keyboard(rows),
        )
    if view.kind == "combat_pending":
        if view.proposal_id is not None:
            return Screen(
                "📜 Rastros sob os Galhos · Confirmação de Grupo\n\n"
                "A proposta para enfrentar o Cervo Escoriado está ativa. "
                "Confira elegibilidade e confirme a entrada na tela do Grupo.",
                "s3_objective",
                _keyboard(
                    [
                        [_button("Abrir Grupo", "group:root")],
                        [_button("Atualizar", "s3:resume")],
                    ]
                ),
            )
        rows = []
        if view.group_size > 1:
            rows.append([_button("Propor combate em Grupo", f"s3:{version}:group")])
        rows.append([_button("Enfrentar Solo", f"s3:{version}:solo")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "📜 Rastros sob os Galhos · Em Andamento\n\n"
            "O Cervo Escoriado aguarda entre os galhos.",
            "s3_objective",
            _keyboard(rows),
        )
    if view.kind == "cargo":
        return Screen(
            "🏆 Cervo Escoriado derrotado\n📜 Rastros sob os Galhos · Em Andamento\n\n"
            "🎯 Verificar a carga abandonada",
            "s3",
            _keyboard([[_button("Verificar carga abandonada", f"s3:{version}:cargo")], [_button("← Missões", "world:missions")]]),
        )
    if view.kind == "report":
        rows = []
        if view.location == BOSQUE:
            rows.append([_button(
                "Seguir para a Charneca",
                f"p3:s3route:{version}:charneca" if view.campaign_active else "road:route:charneca",
            )])
        elif view.location == "Charneca da Fuligem":
            rows.append([_button(
                "Retornar ao Refúgio",
                f"p3:s3route:{version}:refuge" if view.campaign_active else "road:route:refuge",
            )])
        elif view.location == REFUGE:
            rows.append([_button("Reportar a Alda Veyr", f"s3:{version}:report")])
        rows.append([_button("← Missões", "world:missions")])
        return Screen(
            "📜 Rastros sob os Galhos · Em Andamento\n🎯 Reportar a Alda Veyr\n"
            f"📍 {view.location or 'Refúgio do Ocaso'}",
            "s3",
            _keyboard(rows),
        )
    return render_s3_detail(view)
