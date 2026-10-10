"""Player-facing screens for the Estrada loop."""
# ruff: noqa: E501

from datetime import UTC, datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.road import (
    BOSQUE,
    CHARNECA,
    REFUGE,
    ROAD,
    RUINS,
    VDE_GARGANTA,
    VDE_MATA,
    VDE_REGION,
    VDE_VIGILIA,
    RoadView,
)
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen
from asterion.domain.road import LOCATION_LEVEL_BANDS


def _round_token(view) -> str:
    round_id = getattr(view, "round_id", None)
    return round_id.hex if round_id is not None else ""


def _round_consumable_state(view) -> str:
    active = []
    if view.prepared_heal:
        active.append("Cura")
    if view.prepared_purify:
        active.append("Purificação")
    return " + ".join(active) if active else "Nenhum"


def _round_timer(view) -> str:
    if view.next_resolution_at is None:
        return "00:00"
    remaining = max(0, int((view.next_resolution_at - datetime.now(UTC)).total_seconds()))
    minutes, seconds = divmod(remaining, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _reward_block(view) -> str:
    if not view.reward_lines:
        return ""
    return "\n\n🎁 Recompensas\n\n" + "\n".join(view.reward_lines)


def _location_copy(location: str) -> tuple[str, str]:
    icon = (
        "🌑" if location == CHARNECA else
        "🌲" if location == BOSQUE else
        "🪨" if location == RUINS else
        "🪢" if location == VDE_GARGANTA else
        "🌫️" if location == VDE_VIGILIA else
        "🌿" if location == VDE_MATA else "🔥"
    )
    low, high = LOCATION_LEVEL_BANDS.get(location, (1, 10))
    region = VDE_REGION if location in {VDE_GARGANTA, VDE_VIGILIA, VDE_MATA} else "Terras do Ocaso"
    return f"{icon} {location}", f"{region} · Nv. {low}–{high}"


def _recovery_route(view) -> InlineKeyboardButton | None:
    attempt_suffix = (
        f":{view.attempt_id.hex}"
        if view.kind == "exploration" and view.attempt_id is not None
        else ""
    )
    if not view.route_available:
        return None
    if view.location == CHARNECA and view.recovery_location == REFUGE:
        return InlineKeyboardButton(
            text="Retornar à Charneca",
            callback_data=f"road:route:charneca{attempt_suffix}",
        )
    if view.location == BOSQUE and view.recovery_location == CHARNECA:
        return InlineKeyboardButton(
            text="Retornar ao Bosque",
            callback_data=f"road:route:bosque{attempt_suffix}",
        )
    if view.location == RUINS and view.recovery_location in {BOSQUE, CHARNECA, REFUGE}:
        next_location = {
            BOSQUE: RUINS,
            CHARNECA: BOSQUE,
            REFUGE: CHARNECA,
        }[view.recovery_location]
        label = {
            RUINS: "Retornar às Ruínas",
            BOSQUE: "Retornar ao Bosque",
            CHARNECA: "Seguir para a Charneca",
        }[next_location]
        return InlineKeyboardButton(
            text=label,
            callback_data=f"road:route:{_route_key(next_location)}{attempt_suffix}",
        )
    return None


def _route_key(location: str) -> str:
    return {
        REFUGE: "refuge",
        CHARNECA: "charneca",
        BOSQUE: "bosque",
        RUINS: "ruinas",
    }[location]


def _local_return(location: str, attempt_id=None) -> InlineKeyboardButton:
    callback_data = (
        f"road:local:{attempt_id.hex}"
        if attempt_id is not None
        else "road:local"
    )
    return InlineKeyboardButton(
        text=f"← {location}", callback_data=callback_data
    )


def _round_screen(view) -> Screen | None:
    if not getattr(view, "kind", "").startswith("round_"):
        return None
    if view.kind == "round_select":
        return render_round_selection(view)
    token = _round_token(view)
    if view.location == VDE_GARGANTA:
        place = "Garganta dos Laços\nVales dos Enforcados · Nv. 11–14"
        local_line = "Garganta dos Laços · Vales dos Enforcados"
    elif view.location == VDE_MATA:
        place = "Mata Suspensa\nVales dos Enforcados · Nv. 13–17"
        local_line = "Mata Suspensa · Vales dos Enforcados"
    elif view.location == CHARNECA:
        place = "🌑 Charneca da Fuligem\nTerras do Ocaso · Nv. 3–5"
        local_line = "Charneca da Fuligem · Terras do Ocaso"
    elif view.location == BOSQUE:
        place = "🌲 Bosque Calcinado\nTerras do Ocaso · Nv. 5–8"
        local_line = "Bosque Calcinado · Terras do Ocaso"
    elif view.location == RUINS:
        place = "🪨 Ruínas do Vigia\nTerras do Ocaso · Nv. 8–10"
        local_line = "Ruínas do Vigia · Terras do Ocaso"
    else:
        # Preserve the established Estrada copy while using the Round snapshot.
        place = "Estrada das Cinzas\nTerras do Ocaso · Nv. 1–10"
        local_line = "Estrada das Cinzas · Terras do Ocaso"
    if view.kind == "round_prepare":
        text = (
            "🏕️ Ronda de Caça\n"
            f"{place}\n\n"
            f"❤️ HP · <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ Vigor · <code>{view.vigor} / {view.max_vigor}</code>\n\n"
            f"🎯 Ronda · {view.batch_size} Encontros\n"
            "⏱️ Cadência · 3 min por Encontro\n"
            f"🧪 Consumíveis · {_round_consumable_state(view)}"
        )
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Consumíveis",
                    callback_data=f"road:round:cons:{token}:{view.state_version}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Iniciar Ronda",
                    callback_data=f"road:round:start:{token}:{view.state_version}",
                )
            ],
            [InlineKeyboardButton(text=f"← {view.location}", callback_data=f"road:round:back:{token}")],
        ]
        return Screen(
            text,
            "road_round_prepare",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML",
        )
    if view.kind == "round_consumables":
        lines = [
            "🧪 Consumíveis da Ronda",
            f"{view.location} · Terras do Ocaso",
            "",
        ]
        buttons = []
        if view.heal_quantity > 0 or view.purify_quantity > 0:
            lines.append("🎒 Consumíveis Elegíveis")
            lines.append("")
            if view.heal_quantity > 0:
                lines.extend(
                    [
                        f"1 🧪 Poção de Cura · {view.heal_quantity}",
                        (
                            "🟢 Uso Automático · Ativo"
                            if view.prepared_heal
                            else "⚪ Uso Automático · Inativo"
                        ),
                        "",
                    ]
                )
                buttons.append(
                    InlineKeyboardButton(
                        text="1",
                        callback_data=(
                            f"road:round:toggle:h:{token}:{view.state_version}"
                        ),
                    )
                )
            if view.purify_quantity > 0:
                lines.extend(
                    [
                        f"2 🧪 Preparado de Purificação · {view.purify_quantity}",
                        (
                            "🟢 Uso Automático · Ativo"
                            if view.prepared_purify
                            else "⚪ Uso Automático · Inativo"
                        ),
                        "",
                    ]
                )
                buttons.append(
                    InlineKeyboardButton(
                        text="2",
                        callback_data=(
                            f"road:round:toggle:p:{token}:{view.state_version}"
                        ),
                    )
                )
            lines.append(
                "⚠️ Somente Consumíveis com Uso Automático ativo poderão ser utilizados durante este lote."
            )
        else:
            lines.append(
                "⚠️ Nenhum Consumível elegível está disponível no Inventário para esta Ronda."
            )
        keyboard = []
        if buttons:
            keyboard.append(buttons)
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="← Ronda",
                    callback_data=f"road:round:prepare:view:{token}:{view.state_version}",
                )
            ]
        )
        return Screen(
            "\n".join(lines),
            "road_round_consumables",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    if view.kind == "round_active":
        text = (
            "🏕️ Ronda de Caça · Andamento\n"
            f"{local_line}\n\n"
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}\n\n"
            f"❤️ HP · {view.hp}\n"
            f"⚡ Vigor · {view.vigor}\n\n"
            f"⏱️ Próximo Encontro · {_round_timer(view)}"
        )
        if view.cancel_requested:
            text += "\n\n⏳ Cancelamento · Após o Encontro Atual"
            keyboard = []
        else:
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="Cancelar Ronda",
                        callback_data=f"road:round:cancel:{token}:{view.state_version}",
                    )
                ]
            ]
        return Screen(
            text,
            "road_round_active",
            InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None,
        )
    if view.kind == "round_interrupted":
        creature = escape(view.creature or "Elite")
        flavor = f"\n\n{escape(view.result_text)}" if view.result_text else ""
        text = (
            "🏕️ Ronda de Caça · Interrompida\n"
            f"{local_line}\n\n"
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}\n"
            "⚠️ Motivo · Elite Encontrado\n\n"
            f"🐺 {creature} · Nv. {view.enemy_level}"
            f"{flavor}"
        )
        keyboard = [[
            InlineKeyboardButton(
                text="Enfrentar Elite",
                callback_data=f"road:round:elite:{token}:{view.state_version}",
            )
        ]]
        return Screen(
            text,
            "road_round_elite",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML",
        )
    if view.kind == "round_completed":
        text = (
            "🏆 Ronda de Caça · Concluída\n"
            f"{view.location} · Terras do Ocaso\n\n"
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}"
            f"{_reward_block(view)}"
        )
        return Screen(
            text,
            "road_round_result",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text=f"← {view.location}", callback_data=f"road:round:back:{token}")
                    ]
                ]
            ),
        )
    if view.kind == "round_cancelled":
        text = (
            "🏕️ Ronda de Caça · Cancelada\n"
            f"{view.location} · Terras do Ocaso\n\n"
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}\n\n"
            "✅ A Ronda foi encerrada. Os encontros já concluídos permanecem registrados."
            f"{_reward_block(view)}"
        )
        return Screen(
            text,
            "road_round_result",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text=f"← {view.location}", callback_data=f"road:round:back:{token}")
                    ]
                ]
            ),
        )
    if view.kind == "round_defeated":
        recovery = (
            f"🔥 {view.recovery_brazier}\n"
            f"{view.recovery_location} · Terras do Ocaso\n\n"
            if view.recovery_brazier and view.recovery_location
            else "🔥 Braseiro da Estrada\nEstrada das Cinzas · Terras do Ocaso\n\n"
        )
        text = (
            "💀 Ronda de Caça · Derrota\n\n"
            f"{recovery}"
            f"{'⚔️ PvPvE · Derrota\n' if view.end_reason == 'pvpve_defeat' else ''}"
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}\n"
            "❤️ HP · Restaurado"
            f"{_reward_block(view)}"
        )
        keyboard = []
        route_button = _recovery_route(view)
        if route_button is not None:
            keyboard.append([route_button])
        keyboard.append([InlineKeyboardButton(text=f"← {view.recovery_location or view.location}", callback_data=f"road:round:back:{token}")])
        return Screen(
            text,
            "brazier_estrada" if view.recovery_location in {None, ROAD} else "road_defeat",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    if view.kind == "round_ended":
        reason = ""
        if view.end_reason == "hp":
            reason = "❤️ HP · Abaixo do Limite Seguro"
        elif view.end_reason == "vigor":
            reason = "⚡ Vigor · Insuficiente"
        elif view.end_reason == "pvpve_context_changed":
            reason = "⚠️ Contexto da busca por rival indisponível"
        elif view.end_reason in {"inventory", "pending", "inventory_pending"}:
            parts = []
            if view.inventory_blocked:
                parts.append("🎒 Inventário · Espaço Insuficiente")
            if view.pending_blocked:
                parts.append("📦 Entregas Pendentes · Limite Atingido")
            reason = "\n".join(parts)
        text = (
            "🏕️ Ronda de Caça · Encerrada\n"
            f"{view.location} · Terras do Ocaso\n\n"
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}\n\n"
            f"{reason}"
            f"{_reward_block(view)}"
        )
        keyboard = []
        corrective = []
        if view.inventory_blocked:
            corrective.append(
                InlineKeyboardButton(text="Inventário", callback_data="inventory:root")
            )
        if view.pending_blocked:
            corrective.append(
                InlineKeyboardButton(
                    text="Entregas Pendentes", callback_data="pending:root"
                )
            )
        if corrective:
            keyboard.append(corrective)
        keyboard.append(
            [InlineKeyboardButton(text=f"← {view.location}", callback_data=f"road:round:back:{token}")]
        )
        return Screen(
            text,
            "road_round_result",
            InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    return None


def render_road(view: RoadView) -> Screen:
    round_screen = _round_screen(view)
    if round_screen is not None:
        return round_screen
    if view.kind == "hunt_queue":
        heading = (
            "🛡️ Ronda · Exposta ao PvPvE"
            if view.pvpve_round_queue
            else "🦌 Caçada · Exposta ao PvPvE"
        )
        text = (
            f"{heading}\n\n"
            f"{_location_copy(view.location)[0]} · Terras do Ocaso\n\n"
            f"{escape(view.result_text or 'Procurando um grupo compatível…')}\n\n"
            "Sem rival compatível, a jornada segue para a presa PvE.\n"
            "⚡ Vigor · Será verificado ao formar o encontro"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Buscar Rival",
                        callback_data=f"road:pvpve:refresh:q:{view.pvpve_queue_id.hex}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Continuar sem Rival",
                        callback_data=f"road:pvpve:continue:q:{view.pvpve_queue_id.hex}",
                    )
                ],
                *(
                    []
                    if view.pvpve_round_queue
                    else [[
                        InlineKeyboardButton(
                            text="Cancelar Caçada",
                            callback_data=f"road:pvpve:cancel:q:{view.pvpve_queue_id.hex}",
                        )
                    ]]
                ),
            ]
        )
        return Screen(text, "hunt_queue", keyboard, parse_mode="HTML")
    if view.kind == "combat" and view.combat is not None:
        screen = render_combat(
            CombatView(
                view.activity_id,
                view.encounter_id,
                view.character_id,
                view.combat,
                "road",
                0,
                context=view.combat_context,
                combat_actor_key=view.combat_actor_key,
                consumable_options=view.consumable_options,
                consumable_screen=view.consumable_screen,
                selected_consumable_id=view.selected_consumable_id,
                selected_target_id=view.selected_target_id,
                selection_parent=view.selection_parent,
                consumable_notice=view.consumable_notice,
                consumable_quantities=view.consumable_quantities,
                consumable_budget_limit=view.consumable_budget_limit,
                ready_consumable_option=view.ready_consumable_option,
            )
        )
        if view.pvpve_round_ai:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Assumir Combate",
                            callback_data=f"road:pvpve:takeover:{view.activity_id.hex}",
                        )
                    ]
                ]
            )
            return Screen(
                f"{screen.text}\n\n🤖 A Ronda está sob controle automático.",
                screen.image_key,
                keyboard,
                screen.parse_mode,
            )
        if view.pvpve_round_takeover:
            return Screen(
                f"{screen.text}\n\n✅ Controle assumido · você agirá na próxima oportunidade.",
                screen.image_key,
                screen.keyboard,
                screen.parse_mode,
            )
        return screen
    if view.kind == "hunt_defeat":
        heading = (
            "💀 PvPvE · Derrota"
            if view.combat_context == "pvpve"
            else "💀 Caçada · Derrota"
        )
        result_line = f"\n\n{escape(view.result_text)}" if view.result_text else ""
        if view.recovery_brazier and view.recovery_location:
            text = (
                f"{heading}\n\n"
                f"🔥 {view.recovery_brazier}\n"
                f"{view.recovery_location} · Terras do Ocaso\n\n"
                f"❤️ HP · Restaurado{result_line}"
            )
            keyboard = []
            route_button = _recovery_route(view)
            if route_button is not None:
                keyboard.append([route_button])
            keyboard.append([InlineKeyboardButton(text=f"← {view.recovery_location}", callback_data="road:local")])
        else:
            text = (
                f"{heading}\n\n🔥 Braseiro da Estrada\nEstrada das Cinzas · Terras do Ocaso\n\n"
                f"❤️ HP · Restaurado{result_line}"
            )
            keyboard = [[_local_return(ROAD)]]
        return Screen(text, "road_defeat", InlineKeyboardMarkup(inline_keyboard=keyboard))
    if view.kind == "hunt_prepare":
        title, subtitle = _location_copy(view.location)
        local_block = f"{title} · Local Atual\n{subtitle}"
        text = (
            "🦌 Caçada\n\n"
            f"{local_block}\n\n"
            f"👤 {escape(view.name or 'Personagem')}\n❤️ <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ Vigor · <code>{view.vigor} / {view.max_vigor}</code>"
        )
        keyboard = [
            [InlineKeyboardButton(text="Caçar", callback_data="road:hunt")],
            [InlineKeyboardButton(text="Grupo", callback_data="group:root")],
            [_local_return(view.location)],
        ]
        return Screen(text, "hunt_prepare", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "hunt_victory":
        text = "🏆 Vitória\n\n🦌 Caçada concluída"
        if view.location in {CHARNECA, BOSQUE, RUINS}:
            text += f"\n\n{_location_copy(view.location)[0]}"
        if view.creature:
            text += f"\n🐾 {escape(view.creature)}"
        if view.variant:
            text += f"\n🧬 Variante · {escape(view.variant)}"
        if view.reward_lines:
            text += "\n\n" + "\n".join(view.reward_lines)
        keyboard = [
            *(
                [[InlineKeyboardButton(text="Caçar Novamente", callback_data=f"road:repeat:{view.activity_id.hex}")]]
                if view.activity_id is not None and view.combat_context != "group_hunt"
                else []
            ),
            [_local_return(view.location)],
        ]
        return Screen(text, "road_victory", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "exploration":
        title, subtitle = _location_copy(view.location)
        if view.recovery_brazier and view.recovery_location:
            text = (
                "💀 Desbravar · Derrota\n\n"
                f"🔥 {view.recovery_brazier}\n"
                f"{view.recovery_location} · Terras do Ocaso\n"
                "❤️ HP · Restaurado\n\n"
                f"{escape(view.result_text or 'A exploração foi interrompida.')}"
            )
        else:
            text = f"🧭 Desbravar\n\n{title}\n{subtitle}\n\n{escape(view.result_text or '')}"
            if view.result_id == "explore.tdo.charneca.braseiro":
                text += "\n\n🔥 Braseiro do Vento Morto · Descoberto"
            elif view.result_id == "explore.tdo.charneca.cripta":
                text += "\n\n🏰 Cripta do Ocaso · Descoberta\n🧭 Caminho Conhecido"
            elif view.result_id == "explore.tdo.bosque.braseiro":
                text += "\n\n🔥 Braseiro dos Galhos Mortos · Descoberto"
            elif view.result_id == "explore.tdo.bosque.estrutura_enterrada":
                text += "\n\n📖 Códice · Antigos Asterianos atualizado"
        buttons = []
        route_button = _recovery_route(view)
        if route_button is not None:
            buttons.append([route_button])
        buttons.append(
            [
                _local_return(
                    view.recovery_location or view.location, view.attempt_id
                )
            ]
        )
        return Screen(
            text, "exploration", InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML"
        )
    if view.kind == "explore_prepare":
        title, subtitle = _location_copy(view.location)
        text = (
            "🧭 Desbravar\n\n"
            f"{title} · Local Atual\n{subtitle}\n\n👤 Solo\n"
            f"❤️ <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ Vigor · <code>{view.vigor} / {view.max_vigor}</code>"
        )
        keyboard = [
            [InlineKeyboardButton(text="Desbravar", callback_data="road:explore:start")],
            [_local_return(view.location)],
        ]
        return Screen(text, "explore_prepare", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "explore_cooldown":
        location_line = f"{_location_copy(view.location)[0]}\n\n" if view.location != ROAD else ""
        text = (
            f"🧭 Desbravar\n\n{location_line}"
            "⏳ Desbravar · Disponível em "
            f"<code>{escape(view.result_text or '00:00')}</code>"
        )
        return Screen(
            text,
            "explore_cooldown",
            InlineKeyboardMarkup(inline_keyboard=[[_local_return(view.location)]]),
            parse_mode="HTML",
        )
    if view.kind == "explore_limit":
        location_line = f"{_location_copy(view.location)[0]}\n\n" if view.location != ROAD else ""
        text = (
            f"🧭 Desbravar\n\n{location_line}"
            "🔒 Desbravar · Limite recente atingido\n"
            f"⏳ Disponível em · <code>{escape(view.result_text or '00:00')}</code>"
        )
        return Screen(
            text,
            "explore_limit",
            InlineKeyboardMarkup(inline_keyboard=[[_local_return(view.location)]]),
            parse_mode="HTML",
        )
    if view.kind in {
        "road", "refuge", "charneca", "bosque", "ruinas",
        "vde_garganta", "vde_vigilia", "vde_mata",
    }:
        return render_current_local(
            view,
            explore_state="available" if view.explore_available else None,
        )
    return Screen(
        "Local indisponível.",
        "road",
        InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="← Menu", callback_data="menu:back")]]
        ),
    )

def render_current_local(
    view: RoadView,
    *,
    explore_state: str | None = None,
    explore_message: str | None = None,
    dungeon: tuple[str, str] | None = None,
    mission_available: bool = False,
) -> Screen:
    """Render the current Local as the sole entry point for local activities."""
    title, subtitle = _location_copy(view.location)
    def bar(current, maximum, fill: str) -> str:
        value = min(10, max(0, int(current * 10 / maximum))) if maximum else 0
        return fill * value + "⬜" * (10 - value)

    lines = [
        "📍 Local Atual",
        title,
        subtitle,
        "",
        f"👤 {escape(view.name or 'Personagem')}",
        f"❤️ HP · {view.hp} / {view.max_hp}",
        bar(view.hp, view.max_hp, "🟩"),
        f"⚡ Vigor · {view.vigor} / {view.max_vigor}",
        bar(view.vigor, view.max_vigor, "🟨"),
    ]
    keyboard: list[list[InlineKeyboardButton]] = []
    if view.location in {ROAD, CHARNECA, BOSQUE, RUINS, VDE_GARGANTA, VDE_MATA}:
        lines.append("")
        if view.hunt_enabled:
            lines.append("🦌 Caçada · Disponível")
            keyboard.append([InlineKeyboardButton(text="Caçar", callback_data="road:hunt")])
            keyboard.append([InlineKeyboardButton(text="Grupo", callback_data="group:root")])
        else:
            lines.append("🔒 Caçada · Indisponível no momento")
        if view.familiar and view.hunt_enabled:
            lines.append("🏕️ Ronda de Caça · Disponível")
            keyboard.append([InlineKeyboardButton(text="Ronda", callback_data="world:round")])
        elif view.hunt_enabled:
            lines.append("🔒 Ronda de Caça · Vença uma Caçada neste Local")
        if not view.explore_enabled:
            lines.append("🔒 Desbravar · Indisponível no momento")
        elif explore_state == "available":
            lines.append("🧭 Desbravar · Disponível")
            keyboard.append(
                [InlineKeyboardButton(text="Desbravar", callback_data="road:explore:start")]
            )
        elif explore_state == "cooldown":
            lines.append(
                "⏳ Desbravar · Em recarga"
                + (f" · {escape(explore_message)}" if explore_message else "")
            )
        elif explore_state == "limit":
            lines.append(
                "🔒 Desbravar · Limite recente atingido"
                + (f" · {escape(explore_message)}" if explore_message else "")
            )
        else:
            lines.append("🚫 Desbravar · Indisponível neste Local")
    if view.location in {VDE_GARGANTA, VDE_MATA}:
        for destination in view.route_destinations:
            route_key, label = {
                (VDE_GARGANTA, VDE_VIGILIA): ("vde_vigilia", "Seguir para a Vigília do Vale"),
                (VDE_VIGILIA, VDE_GARGANTA): ("vde_garganta", "Retornar à Garganta dos Laços"),
                (VDE_VIGILIA, VDE_MATA): ("vde_mata", "Seguir para a Mata Suspensa"),
                (VDE_MATA, VDE_VIGILIA): ("vde_vigilia", "Retornar à Vigília do Vale"),
            }.get((view.location, destination), (None, None))
            if route_key is not None:
                keyboard.append([InlineKeyboardButton(text=label, callback_data=f"road:route:{route_key}")])
        if view.brazier_label:
            lines.append(f"🔥 {escape(view.brazier_label)} · Descoberto")
        elif view.location != ROAD:
            lines.append("🔥 Braseiro · Não descoberto")
        if dungeon is not None:
            dungeon_name, dungeon_callback = dungeon
            lines.append(f"⛓️ {escape(dungeon_name)} · Conhecida")
            keyboard.append(
                [InlineKeyboardButton(text=dungeon_name, callback_data=dungeon_callback)]
            )
        if mission_available:
            lines.append("📜 Missões · Acompanhar objetivos")
            keyboard.append(
                [InlineKeyboardButton(text="Missões", callback_data="world:missions")]
            )
    elif view.location == VDE_VIGILIA:
        lines.extend(["", "🏘️ Hub seguro", "🚫 Caçadas · Indisponíveis neste Local"])
        for destination in view.route_destinations:
            route_key, label = {
                (VDE_VIGILIA, VDE_GARGANTA): ("vde_garganta", "Retornar à Garganta dos Laços"),
                (VDE_VIGILIA, VDE_MATA): ("vde_mata", "Seguir para a Mata Suspensa"),
            }.get((view.location, destination), (None, None))
            if route_key is not None:
                keyboard.append([InlineKeyboardButton(text=label, callback_data=f"road:route:{route_key}")])
        if view.brazier_label:
            lines.append(f"🔥 {escape(view.brazier_label)} · Descoberto")
        if mission_available:
            keyboard.append([InlineKeyboardButton(text="Missões", callback_data="world:missions")])
    else:
        lines.extend(["", "Local narrativo seguro."])
        if view.brazier_label:
            lines.append(f"🔥 {escape(view.brazier_label)} · Descoberto")
        if view.location == REFUGE:
            if mission_available:
                keyboard.append(
                    [InlineKeyboardButton(text="Missões", callback_data="world:missions")]
                )
            keyboard.extend(
                [
                    [InlineKeyboardButton(text="Alda Veyr", callback_data="p2:alda")],
                    [InlineKeyboardButton(text="Oren Cal", callback_data="world:oren")],
                ]
            )
        elif mission_available:
            keyboard.append(
                [InlineKeyboardButton(text="Missão Atual", callback_data="world:missions")]
            )
    keyboard.extend(
        [
            [InlineKeyboardButton(text="Viajar", callback_data="world:map:fromlocal")],
            [InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")],
        ]
    )
    return Screen(
        "\n".join(lines),
        "local_current",
        InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )


def render_round_selection(view: RoadView) -> Screen:
    if not view.familiar:
        text = (
            "🏕️ Ronda de Caça\n\n"
            f"{escape(view.location)}\n\n"
            "🔒 Vença uma Caçada manual neste Local para liberar a Ronda."
        )
        keyboard = [[InlineKeyboardButton(text=f"← {view.location}", callback_data="world:local")]]
    else:
        text = (
            f"🏕️ Ronda de Caça\n{escape(view.location)} · Terras do Ocaso\n\n"
            "Escolha o tamanho do lote.\n\n"
            "1 · 5 Encontros\n2 · 10 Encontros\n3 · 20 Encontros"
        )
        keyboard = [
            [
                InlineKeyboardButton(text="1", callback_data="road:round:new:5"),
                InlineKeyboardButton(text="2", callback_data="road:round:new:10"),
                InlineKeyboardButton(text="3", callback_data="road:round:new:20"),
            ],
            [InlineKeyboardButton(text=f"← {view.location}", callback_data="world:local")],
        ]
    return Screen(
        text,
        "round_selection",
        InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
