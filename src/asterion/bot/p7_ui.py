"""Telegram presentation for P7: A Estrada Estrangulada."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.p7 import P7_TITLE, P7View
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


def _b(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _kb(rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _combat(view: P7View) -> Screen:
    if view.combat is None or view.activity_id is None or view.encounter_id is None:
        return Screen(
            f"📜 {P7_TITLE} · O encontro está sendo reconstruído.",
            "p7",
            _kb([[_b("Atualizar", "p7:resume")]]),
        )
    hud = render_combat(
        CombatView(
            view.activity_id,
            view.encounter_id,
            view.character_id,
            view.combat,
            "p7",
            view.xp,
            context="p7",
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
        f"📜 {P7_TITLE} · Garganta dos Laços\n"
        "⚔️ Encontro Roteirizado · Fauna Regional · Nv.11\n\n"
        + hud.text,
        "p7",
        hud.keyboard,
        parse_mode=hud.parse_mode,
    )


def render_p7(view: P7View) -> Screen:
    version = view.state_version
    progress = view.progress or {}

    if view.kind == "combat":
        return _combat(view)
    if view.kind == "unavailable":
        requirement = (
            "P6 concluída + Nv.11."
            if view.level < 11
            else "Conclua P6 e entre nos Vales pela rota de Campanha."
        )
        return Screen(
            f"📜 {P7_TITLE} · Indisponível\n\nRequer {requirement}",
            "p7",
            _kb([[_b("← Missões", "world:missions")]]),
        )
    if view.kind == "completed" or view.status == "completed":
        return Screen(
            f"✅ {P7_TITLE} · Concluída\n"
            "Missão Principal · Vales dos Enforcados\n\n"
            "✨ XP · 8.750\n"
            "🪙 Coroas · 270\n"
            "📦 Ferro Enredado · 1 · Vinculado\n"
            "📦 Couro Musgoso · 1 · Vinculado\n"
            "🏅 Feito · Estrada Estrangulada\n\n"
            "📍 Vigília do Vale · Braseiro ativo\n"
            "🦌 Caçada Manual · Garganta dos Laços desbloqueada",
            "p7",
            _kb([[_b("← Missões", "world:missions")], [_b("Grupo", "group:root")]]),
        )
    if view.kind == "road_points":
        points = set(progress.get("road_points", ()))
        rows = []
        if "a" not in points:
            rows.append([_b("Examinar trecho soterrado", f"p7:{version}:road:a")])
        if "b" not in points:
            rows.append([_b("Examinar marco quebrado", f"p7:{version}:road:b")])
        rows.append([_b("← Missões", "world:missions")])
        return Screen(
            f"📜 {P7_TITLE} · Garganta dos Laços\n\n"
            "🎯 Examinar dois pontos da antiga estrada.\n"
            f"Progresso · {len(points)}/2\n\n"
            "Raízes atravessam a pedra e sustentam restos de estruturas sobre o caminho.",
            "p7",
            _kb(rows),
        )
    if view.kind == "recent_passage":
        return Screen(
            f"📜 {P7_TITLE} · Garganta dos Laços\n\n"
            "🎯 Procurar sinais de passagem recente entre as raízes.\n\n"
            "A névoa baixa esconde marcas novas entre raízes antigas.",
            "p7",
            _kb(
                [
                    [_b("Seguir os sinais", f"p7:{version}:passage")],
                    [_b("← Missões", "world:missions")],
                ]
            ),
        )
    if view.kind == "start_fauna":
        rows = [
            [_b("Enfrentar Solo", f"p7:{version}:solo")],
            [_b("Formar/Usar Grupo", f"p7:{version}:group")],
            [_b("Grupo", "group:root")],
            [_b("← Missões", "world:missions")],
        ]
        return Screen(
            f"📜 {P7_TITLE} · Garganta dos Laços\n\n"
            "🎯 Sobreviver ao encontro na antiga estrada.\n\n"
            "Movimento repentino corta a névoa. O encontro pertence à fauna regional, "
            "mas a missão não identifica uma espécie específica.",
            "p7",
            _kb(rows),
        )
    if view.kind == "retry":
        return Screen(
            "❌ Encontro encerrado\n"
            "✅ Etapas anteriores preservadas\n"
            "📍 Garganta dos Laços\n"
            "❤️ HP restaurado\n\n"
            "Você pode tentar novamente Solo ou com o Grupo.",
            "p7_recovery",
            _kb(
                [
                    [_b("Tentar Solo", f"p7:{version}:retry")],
                    [_b("Formar/Usar Grupo", f"p7:{version}:group")],
                    [_b("← Missões", "world:missions")],
                ]
            ),
        )
    if view.kind == "worked_stone":
        return Screen(
            f"📜 {P7_TITLE} · Garganta dos Laços\n\n"
            "🎯 Examinar a pedra trabalhada parcialmente exposta.\n\n"
            "Sob terra e raízes, a geometria antiga ainda é legível.",
            "p7",
            _kb(
                [
                    [_b("Examinar estrutura", f"p7:{version}:stone")],
                    [_b("← Missões", "world:missions")],
                ]
            ),
        )
    if view.kind == "proceed_vigilia":
        return Screen(
            f"📜 {P7_TITLE} · Garganta dos Laços\n\n"
            "As raízes parecem ter crescido seguindo estruturas enterradas. "
            "A causa permanece desconhecida.\n\n"
            "🎯 Prosseguir até a Vigília do Vale.",
            "p7",
            _kb(
                [
                    [_b("Prosseguir à Vigília", f"p7:{version}:vigilia")],
                    [_b("← Missões", "world:missions")],
                ]
            ),
        )
    if view.kind == "activate_brazier":
        return Screen(
            f"📜 {P7_TITLE} · Vigília do Vale\n\n"
            "🏘️ Hub seguro regional\n"
            "🎯 Ativar o Braseiro da Vigília antes do relato a Dara Venn.",
            "p7",
            _kb(
                [
                    [_b("Ativar Braseiro", f"p7:{version}:brazier")],
                    [_b("← Missões", "world:missions")],
                ]
            ),
        )
    if view.kind == "report_dara":
        return Screen(
            f"📜 {P7_TITLE} · Vigília do Vale\n\n"
            "🎯 Relatar o estado da rota a Dara Venn.\n\n"
            "O fato confirmado é limitado: as raízes acompanham estruturas enterradas. "
            "A missão não transforma essa correlação em explicação.",
            "p7",
            _kb(
                [
                    [_b("Relatar a Dara Venn", f"p7:{version}:report")],
                    [_b("← Missões", "world:missions")],
                ]
            ),
        )
    return Screen(
        f"📜 {P7_TITLE} · Em Andamento",
        "p7",
        _kb([[_b("Atualizar", "p7:resume")], [_b("← Missões", "world:missions")]]),
    )
