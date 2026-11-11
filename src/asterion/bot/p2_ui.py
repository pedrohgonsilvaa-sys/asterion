"""Player-facing screens for P2, derived only from the persisted P2View."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p2 import P2View
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen

_REWARD_LINES = (
    "✨ XP · 3.300",
    "🪙 Coroas · 140",
    "📦 Ferro de Fuligem · 1 · Vinculado",
    "📦 Erva Cinzenta · 2 · Vinculado",
    "📦 Resíduo do Ocaso · 1 · Vinculado",
)
_ASH_POINTS = (
    "p2.ash_point.1",
    "p2.ash_point.2",
    "p2.ash_point.3",
)


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _keyboard(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def _reward_block() -> str:
    return "🎁 Recompensas\n\n" + "\n".join(_REWARD_LINES)


def _combat_screen(view: P2View) -> Screen:
    if (
        view.combat is None
        or view.activity_id is None
        or view.encounter_id is None
    ):
        return Screen(
            "📜 Fuligem sem Fogo · Em Andamento\n\n"
            "O encontro está sendo reconstruído a partir do estado registrado.",
            "p2",
            _keyboard(_button("Atualizar", "p2:resume")),
        )
    combat_view = CombatView(
        activity_id=view.activity_id,
        encounter_id=view.encounter_id,
        character_id=view.character_id,
        combat=view.combat,
        stage="p2",
        xp=0,
        context="p2",
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
    return render_combat(combat_view)


def _mission_objective(view: P2View) -> str:
    progress = view.progress or {}
    if view.step == 1:
        return "Viajar até a Charneca da Fuligem"
    if view.step == 2:
        count = len(set(progress.get("ash_points", [])))
        return f"Examinar Pontos de Fuligem · {count}/3"
    if view.step == 3 and progress.get("awaiting_retry"):
        return "Retornar à Charneca"
    if view.step == 3:
        return "Derrotar a Aranha de Cinza"
    if view.step == 4:
        return (
            "Levar o registro a Oren Cal"
            if progress.get("stone_examined")
            else "Examinar a Pedra Marcada"
        )
    if view.step == 5:
        return "Falar com Oren Cal"
    return "Reportar a situação a Alda Veyr"


def render_p2_mission_detail(view: P2View) -> Screen:
    local = (
        "Destino contextual · Charneca da Fuligem"
        if view.step == 1
        else view.location or "Terras do Ocaso"
    )
    text = (
        "📜 Fuligem sem Fogo · Em Andamento\n"
        "Missão Principal · Terras do Ocaso\n\n"
        f"🎯 Objetivo · {_mission_objective(view)}\n"
        f"📍 {local}\n\n"
        f"{_reward_block()}"
    )
    return Screen(
        text,
        "p2",
        _keyboard(
            [_button("Ver Objetivo", "p2:resume")],
            [_button("← Missões", "world:missions")],
        ),
    )


def render_p2(view: P2View) -> Screen:
    version = view.state_version
    progress = view.progress or {}

    if view.kind == "combat":
        return _combat_screen(view)

    if view.kind == "offer":
        identity = "".join(f"<i>{escape(line)}</i>\n\n" for line in view.identity_lines)
        reply = f"<i>{escape(view.identity_reply)}</i>\n\n" if view.identity_reply else ""
        text = (
            "📜 Fuligem sem Fogo\n"
            "Missão Principal · Terras do Ocaso\n\n"
            "🪖 Alda Veyr\n\n"
            "<i>— Fuligem sem fogo significa que alguém chegou antes de nós — "
            "ou que estamos olhando para o problema errado.</i>\n\n"
            f"{identity}{reply}"
            "🎯 Objetivo · Investigar a fuligem sem queima recente na Charneca da Fuligem.\n\n"
            f"{_reward_block()}"
        )
        option_rows = [
            [_button(label, f"p2:{version}:ask:{option_id}")]
            for option_id, label in view.identity_options
        ]
        return Screen(
            text,
            "p2",
            _keyboard(
                [_button("Aceitar Missão", f"p2:{version}:accept")],
                *option_rows,
                [_button("← Refúgio do Ocaso", "road:local")],
            ),
            parse_mode="HTML",
        )

    if view.kind == "unavailable":
        lines = ["🪖 Alda Veyr", "", "📜 Fuligem sem Fogo · Indisponível no momento"]
        if view.blocked_by_foreground:
            lines.extend(["", "⚠️ Há uma atividade em andamento."])
        return Screen(
            "\n".join(lines),
            "p2",
            _keyboard([_button("← Refúgio do Ocaso", "road:local")]),
        )

    if view.kind == "completed" or view.status == "completed":
        return Screen(
            "✅ Fuligem sem Fogo · Concluída\n"
            "Missão Principal · Terras do Ocaso\n\n"
            f"{_reward_block()}",
            "p2",
            _keyboard([_button("← Refúgio do Ocaso", "road:local")]),
        )

    if view.kind == "travel":
        return Screen(
            "📜 Fuligem sem Fogo · Em Andamento\n\n"
            "🎯 Objetivo · Viajar até a Charneca da Fuligem\n"
            "📍 Destino contextual · Charneca da Fuligem",
            "p2",
            _keyboard(
                [_button("Seguir para a Charneca", f"p2:{version}:travel")],
                [_button("← Missões", "world:missions")],
            ),
        )

    if view.kind == "ash_points":
        points = set(progress.get("ash_points", []))
        lines = [
            "🌫️ Charneca da Fuligem",
            "📜 Fuligem sem Fogo · Em Andamento",
            "",
            f"🎯 Examinar Pontos de Fuligem · {len(points)}/3",
            "",
        ]
        buttons = []
        for index, point_id in enumerate(_ASH_POINTS, start=1):
            if point_id in points:
                lines.append(f"{index} ✅ Ponto de Fuligem · {index}")
            else:
                lines.append(f"{index} ⚪ Ponto de Fuligem · {index}")
                buttons.append(_button(str(index), f"p2:{version}:ash:{point_id}"))
        rows = [buttons[index : index + 3] for index in range(0, len(buttons), 3)]
        rows.append([_button("← Missões", "world:missions")])
        return Screen("\n".join(lines), "p2", InlineKeyboardMarkup(inline_keyboard=rows))

    if view.kind == "recovery":
        return Screen(
            "💀 Derrota\n\n"
            "Refúgio do Ocaso · Terras do Ocaso\n"
            "❤️ HP · Restaurado\n\n"
            "📜 Fuligem sem Fogo · Em Andamento\n\n"
            "🎯 Retornar à Charneca e enfrentar a Aranha de Cinza.",
            "p2",
            _keyboard(
                [_button("Retornar à Charneca", f"p2:{version}:retry")],
                [_button("← Missões", "world:missions")],
            ),
        )

    if view.kind == "combat_pending":
        lines = [
            "📜 Fuligem sem Fogo · Em Andamento",
            "🌫️ Charneca da Fuligem",
            "",
            "🕷️ Aranha de Cinza",
            "O encontro pode ser enfrentado sozinho ou com o Grupo.",
        ]
        if view.proposal_id is not None:
            state = (
                "Confirmação pronta"
                if view.proposal_status == "ready"
                else "Aguardando confirmações"
            )
            lines.extend(["", f"👥 {state} · abra Grupo para iniciar."])
            keyboard = _keyboard(
                [_button("Abrir Grupo", "group:root")],
                [_button("← Missões", "world:missions")],
            )
        else:
            rows = [[_button("Enfrentar Solo", f"p2:{version}:solo")]]
            if view.group_size > 1:
                rows.append([_button("Formar Grupo", f"p2:{version}:group")])
            rows.append([_button("← Missões", "world:missions")])
            keyboard = _keyboard(*rows)
        return Screen("\n".join(lines), "p2", keyboard)

    if view.kind == "stone":
        lines = [
            "📜 Fuligem sem Fogo · Em Andamento",
            "🌫️ Charneca da Fuligem",
            "",
        ]
        if progress.get("combat_result") == "victory":
            lines.extend(["🏆 Aranha de Cinza derrotada.", ""])
        if progress.get("stone_examined"):
            lines.append("🎯 Objetivo · Levar o registro a Oren Cal")
            label, action = "Retornar ao Refúgio", "refuge"
        else:
            lines.append("🎯 Objetivo · Examinar a Pedra Marcada")
            label, action = "Examinar Pedra Marcada", "stone"
        return Screen(
            "\n".join(lines),
            "p2",
            _keyboard(
                [_button(label, f"p2:{version}:{action}")],
                [_button("← Missões", "world:missions")],
            ),
        )

    if view.kind == "oren":
        return Screen(
            "✒️ Oren Cal\nRefúgio do Ocaso · Terras do Ocaso\n\n"
            "🎯 Objetivo · Entregar o registro da Pedra Marcada.",
            "p2",
            _keyboard(
                [_button("Falar com Oren Cal", f"p2:{version}:oren")],
                [_button("← Missões", "world:missions")],
            ),
        )

    if view.kind == "alda":
        return Screen(
            "🪖 Alda Veyr\nRefúgio do Ocaso · Terras do Ocaso\n\n"
            "<i>— Esta marca não é decoração. Também não vou chamá-la de escrita "
            "até termos prova.</i>\n\n"
            "🎯 Objetivo · Reportar a situação a Alda Veyr.",
            "p2",
            _keyboard(
                [_button("Alda Veyr", f"p2:{version}:report")],
                [_button("← Missões", "world:missions")],
            ),
            parse_mode="HTML",
        )

    return Screen(
        "📜 Fuligem sem Fogo · Em Andamento",
        "p2",
        _keyboard([_button("Ver Objetivo", "p2:resume")]),
    )
