"""Player-facing screens for the Estrada loop."""
# ruff: noqa: E501

from datetime import UTC, datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.road import BOSQUE, CHARNECA, REFUGE, ROAD, RoadView
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
    icon = "🌑" if location == CHARNECA else "🌲" if location == BOSQUE else "🔥"
    low, high = LOCATION_LEVEL_BANDS.get(location, (1, 10))
    return f"{icon} {location}", f"Terras do Ocaso · Nv. {low}–{high}"


def _recovery_route(view) -> InlineKeyboardButton | None:
    if not view.route_available:
        return None
    if view.location == CHARNECA and view.recovery_location == REFUGE:
        return InlineKeyboardButton(
            text="Retornar à Charneca", callback_data="road:route:charneca"
        )
    if view.location == BOSQUE and view.recovery_location == CHARNECA:
        return InlineKeyboardButton(
            text="Retornar ao Bosque", callback_data="road:route:bosque"
        )
    return None


def _local_return(location: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"← {location}", callback_data="road:local"
    )


def _route_button(destination: str, current: str) -> InlineKeyboardButton:
    labels = {
        (REFUGE, CHARNECA): ("Seguir para a Charneca", "road:route:charneca"),
        (CHARNECA, REFUGE): ("Retornar ao Refúgio", "road:route:refuge"),
        (CHARNECA, BOSQUE): ("Seguir para o Bosque", "road:route:bosque"),
        (BOSQUE, CHARNECA): ("Retornar à Charneca", "road:route:charneca"),
    }
    label, callback = labels[(current, destination)]
    return InlineKeyboardButton(text=label, callback_data=callback)


def _route_destinations(view: RoadView) -> tuple[str, ...]:
    if view.route_destinations:
        return view.route_destinations
    # Preserve legacy RoadView fixtures/callsites that only supplied the old bool.
    if not view.route_available:
        return ()
    if view.location == REFUGE:
        return (CHARNECA,)
    if view.location == CHARNECA:
        return (REFUGE,)
    if view.location == BOSQUE:
        return (CHARNECA,)
    return ()


def _round_screen(view) -> Screen | None:
    if not getattr(view, "kind", "").startswith("round_"):
        return None
    token = _round_token(view)
    if view.location == CHARNECA:
        place = "🌑 Charneca da Fuligem\nTerras do Ocaso · Nv. 3–5"
        local_line = "Charneca da Fuligem · Terras do Ocaso"
    elif view.location == BOSQUE:
        place = "🌲 Bosque Calcinado\nTerras do Ocaso · Nv. 5–8"
        local_line = "Bosque Calcinado · Terras do Ocaso"
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
            [InlineKeyboardButton(text="← Caçada", callback_data=f"road:round:back:{token}")],
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
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Enfrentar Elite",
                    callback_data=f"road:round:elite:{token}:{view.state_version}",
                )
            ],
            [InlineKeyboardButton(text="← Caçada", callback_data=f"road:round:back:{token}")],
        ]
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
                        InlineKeyboardButton(text="← Caçada", callback_data=f"road:round:back:{token}")
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
                        InlineKeyboardButton(text="← Caçada", callback_data=f"road:round:back:{token}")
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
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}\n"
            "❤️ HP · Restaurado"
            f"{_reward_block(view)}"
        )
        keyboard = []
        route_button = _recovery_route(view)
        if route_button is not None:
            keyboard.append([route_button])
        keyboard.append([InlineKeyboardButton(text="← Caçada", callback_data=f"road:round:back:{token}")])
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
            [InlineKeyboardButton(text="← Caçada", callback_data=f"road:round:back:{token}")]
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
    route_destinations = _route_destinations(view)
    if view.kind == "combat" and view.combat is not None:
        return render_combat(
            CombatView(
                view.activity_id,
                view.encounter_id,
                view.character_id,
                view.combat,
                "road",
                0,
                context="road",
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
    if view.kind == "hunt_defeat":
        if view.recovery_brazier and view.recovery_location:
            text = (
                "💀 Caçada · Derrota\n\n"
                f"🔥 {view.recovery_brazier}\n"
                f"{view.recovery_location} · Terras do Ocaso\n\n"
                "❤️ HP · Restaurado\n\n🦌 Caçada · Encerrada"
            )
            keyboard = []
            route_button = _recovery_route(view)
            if route_button is not None:
                keyboard.append([route_button])
            keyboard.append([InlineKeyboardButton(text=f"← {view.recovery_location}", callback_data="road:local")])
        else:
            text = (
                "💀 Derrota\n\n🔥 Braseiro da Estrada\nEstrada das Cinzas · Terras do Ocaso\n\n"
                "❤️ HP · Restaurado\n\n🦌 Caçada · Encerrada"
            )
            keyboard = [
                [InlineKeyboardButton(text="Caçar Novamente", callback_data="road:prepare")],
                [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
            ]
        return Screen(text, "road_defeat", InlineKeyboardMarkup(inline_keyboard=keyboard))
    if view.kind == "hunt_prepare":
        title, subtitle = _location_copy(view.location)
        local_block = f"{title} · Local Atual\n{subtitle}"
        text = (
            "🦌 Caçada\n\n"
            f"{local_block}\n\n"
            f"👤 {escape(view.name or 'Personagem')}\n❤️ <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ Vigor · <code>{view.vigor} / {view.max_vigor}</code>\n\n👤 Grupo\n⚔️ Escolha o formato da Caçada."
        )
        keyboard = [
            [InlineKeyboardButton(text="[1] Solo", callback_data="road:hunt")],
            [InlineKeyboardButton(text="[2] Grupo", callback_data="road:unavailable:group")],
            [_local_return(view.location)],
        ]
        return Screen(text, "hunt_prepare", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "hunt_victory":
        text = "🏆 Vitória\n\n🦌 Caçada concluída"
        if view.location in {CHARNECA, BOSQUE}:
            text += f"\n\n{_location_copy(view.location)[0]}"
        if view.creature:
            text += f"\n🐾 {escape(view.creature)}"
        if view.variant:
            text += f"\n🧬 Variante · {escape(view.variant)}"
        if view.reward_lines:
            text += "\n\n" + "\n".join(view.reward_lines)
        keyboard = [
            [InlineKeyboardButton(text="Caçar Novamente", callback_data="road:prepare")],
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
        elif view.retry_available and view.recovery_brazier is None:
            buttons.append([InlineKeyboardButton(text="Desbravar Novamente", callback_data="road:explore")])
        buttons.append([_local_return(view.recovery_location or view.location)])
        return Screen(
            text, "exploration", InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML"
        )
    if view.kind == "explore_prepare":
        title, subtitle = _location_copy(view.location)
        text = (
            "🧭 Desbravar\n\n"
            f"{title} · Local Atual\n{subtitle}\n\n👤 Solo\n"
            f"❤️ <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ 4 Vigor quando a economia for concedida · <code>{view.vigor} / {view.max_vigor}</code>"
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
    if view.location == ROAD:
        round_line = (
            "1 🏕️ Ronda · 5 Encontros\n"
            "2 🏕️ Ronda · 10 Encontros\n"
            "3 🏕️ Ronda · 20 Encontros"
            if view.familiar
            else "🔒 Ronda de Caça · Vença uma Caçada neste Local"
        )
        text = (
            "🔥 Estrada das Cinzas · Local Atual\nTerras do Ocaso · Nv. 1–10\n\n"
            "🔥 Braseiro · Descoberto\n"
            + (
                "🧭 Desbravar · Disponível\n"
                if view.explore_available
                else "⏳ Desbravar · Em recarga\n"
            )
            + "🦌 Caçada · Disponível\n\n"
            + round_line
        )
        keyboard = [
            [InlineKeyboardButton(text="Caçar", callback_data="road:prepare")],
            *(
                [[InlineKeyboardButton(text="Desbravar", callback_data="road:explore")]]
                if view.explore_available
                else []
            ),
            *(
                [[
                    InlineKeyboardButton(text="1", callback_data="road:round:new:5"),
                    InlineKeyboardButton(text="2", callback_data="road:round:new:10"),
                    InlineKeyboardButton(text="3", callback_data="road:round:new:20"),
                ]]
                if view.familiar
                else []
            ),
            *(
                [[InlineKeyboardButton(text="Travessia dos Braseiros", callback_data="world:travel")]]
                if view.brazier_id and view.brazier_destinations
                else []
            ),
            [InlineKeyboardButton(text="← Terras do Ocaso", callback_data="menu:back")],
        ]
    elif view.location in {CHARNECA, BOSQUE}:
        round_line = (
            "1 🏕️ Ronda · 5 Encontros\n"
            "2 🏕️ Ronda · 10 Encontros\n"
            "3 🏕️ Ronda · 20 Encontros"
            if view.familiar
            else "🔒 Ronda de Caça · Vença uma Caçada neste Local"
        )
        brazier_line = (
            "🔥 Braseiro · Descoberto"
            if view.brazier_id is not None
            else "🔥 Braseiro · Não descoberto"
        )
        title, subtitle = _location_copy(view.location)
        text = (
            f"{title} · Local Atual\n{subtitle}\n\n"
            f"{brazier_line}\n"
            + (
                "🧭 Desbravar · Disponível\n"
                if view.explore_available
                else "⏳ Desbravar · Em recarga\n"
            )
            + "🦌 Caçada · Disponível\n\n"
            + round_line
        )
        keyboard = [
            [InlineKeyboardButton(text="Caçar", callback_data="road:prepare")],
            *(
                [[InlineKeyboardButton(text="Desbravar", callback_data="road:explore")]]
                if view.explore_available
                else []
            ),
            *(
                [[
                    InlineKeyboardButton(text="1", callback_data="road:round:new:5"),
                    InlineKeyboardButton(text="2", callback_data="road:round:new:10"),
                    InlineKeyboardButton(text="3", callback_data="road:round:new:20"),
                ]]
                if view.familiar
                else []
            ),
            *([[_route_button(destination, view.location) for destination in route_destinations]]
              if route_destinations else []),
            *(
                [[InlineKeyboardButton(text="Travessia dos Braseiros", callback_data="world:travel")]]
                if view.brazier_id and view.brazier_destinations
                else []
            ),
            [InlineKeyboardButton(text="← Terras do Ocaso", callback_data="menu:back")],
        ]
    elif view.location == REFUGE:
        text = "🔥 Braseiro do Refúgio\nRefúgio do Ocaso · Terras do Ocaso"
        keyboard = [
            [InlineKeyboardButton(text="Alda Veyr", callback_data="p2:alda")],
            [InlineKeyboardButton(text="Oren Cal", callback_data="world:oren")],
            *([[_route_button(destination, view.location) for destination in route_destinations]]
              if route_destinations else []),
            *(
                [[InlineKeyboardButton(text="Travessia dos Braseiros", callback_data="world:travel")]]
                if view.brazier_id and view.brazier_destinations
                else []
            ),
            [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
        ]
    else:
        text = "Local indisponível."
        keyboard = [[InlineKeyboardButton(text="← Menu", callback_data="menu:back")]]
    return Screen(text, "road", InlineKeyboardMarkup(inline_keyboard=keyboard))
