"""Telegram screens for the Altos Cinéreos opening mission."""

# ruff: noqa: E501

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.altos_missions import P25_TITLE, AltosMissionView
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def render_altos_mission(view: AltosMissionView) -> Screen:
    title = escape(view.title or P25_TITLE)
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
                context="altos",
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
            f"📜 {title} · Altos Cinéreos\n⚔️ Encontro roteirizado · Escarpa da Cinza\n\n{hud.text}",
            "missions",
            hud.keyboard,
            parse_mode=hud.parse_mode,
        )

    if view.status == "completed":
        text = (
            f"📜 {title} · Concluída\n\n"
            "✨ 53.500 XP · 720 Coroas\n"
            "📦 1 Ferro de Contrapeso · 1 Líquen de Pedreira"
        )
        rows.append([_button("← Missões", "world:missions")])
        return Screen(text, "missions", InlineKeyboardMarkup(inline_keyboard=rows))

    step_text = {
        2: "Examine os três pontos de sustentação visíveis: contraforte, cabo e escora.",
        3: "Vença o encontro roteirizado contra o Lobo de Escarpa (Nv. 41).",
        4: "Alcance e registre o Braseiro da Escarpa.",
        5: "Acompanhe Hesa Tor e confirme a dependência da rota em reparos redundantes.",
        6: "Chegue ao Abrigo do Peso.",
        7: "Registre o Braseiro do Abrigo.",
        8: "Fale pessoalmente com Rava Kern e Doren Vask.",
        9: "Registre no Códice o trecho Carga Observável.",
    }.get(view.step, "Retome a etapa atual da missão.")
    lines = [f"📜 {title} · Em Andamento", "Altos Cinéreos · Escarpa da Cinza", "", step_text]

    if view.step == 2:
        support_points = set(view.progress.get("support_points", ()))
        options = (
            ("inspect_contraforte", "Examinar o contraforte"),
            ("inspect_cabo", "Examinar o cabo"),
            ("inspect_escora", "Examinar a escora"),
        )
        for action, label in options:
            if action not in support_points:
                rows.append(
                    [_button(label, f"altos:action:{view.state_version}:{action}")]
                )
    elif view.step == 3:
        if view.progress.get("awaiting_retry"):
            rows.append([_button("Tentar novamente", f"altos:retry:{view.state_version}")])
        else:
            rows.extend(
                (
                    [_button("Iniciar encontro Solo", f"altos:combat:{view.state_version}:solo")],
                    [_button("Solicitar encontro em Grupo", f"altos:combat:{view.state_version}:group")],
                )
            )
    elif view.step == 4:
        rows.append(
            [_button("Registrar Braseiro da Escarpa", f"altos:action:{view.state_version}:register_escarpa_brazier")]
        )
    elif view.step == 5:
        rows.append(
            [_button("Confirmar reparos redundantes", f"altos:action:{view.state_version}:confirm_redundant_repairs")]
        )
    elif view.step == 6:
        rows.append([_button("Seguir para o Abrigo do Peso", "road:route:altos_abrigo")])
    elif view.step == 7:
        rows.append(
            [_button("Registrar Braseiro do Abrigo", f"altos:action:{view.state_version}:register_abrigo_brazier")]
        )
    elif view.step == 8:
        if not view.progress.get("spoke_rava"):
            rows.append([_button("Falar com Rava Kern", f"altos:action:{view.state_version}:speak_rava")])
        if not view.progress.get("spoke_doren"):
            rows.append([_button("Falar com Doren Vask", f"altos:action:{view.state_version}:speak_doren")])
    elif view.step == 9:
        if not view.progress.get("codex_recorded"):
            rows.append([_button("Registrar Carga Observável", f"altos:action:{view.state_version}:record_codex")])
        else:
            rows.append([_button("Concluir com Rava Kern", f"altos:action:{view.state_version}:conclude_with_rava")])

    rows.append([_button("← Missões", "world:missions")])
    return Screen("\n".join(lines), "missions", InlineKeyboardMarkup(inline_keyboard=rows))
