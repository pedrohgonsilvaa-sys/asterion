"""Player-facing screens for the Estrada loop."""
# ruff: noqa: E501

from datetime import UTC, datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.road import ROAD, RoadView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen


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


def _round_screen(view) -> Screen | None:
    if not getattr(view, "kind", "").startswith("round_"):
        return None
    token = _round_token(view)
    if view.kind == "round_prepare":
        text = (
            "🏕️ Ronda de Caça\n"
            "Estrada das Cinzas\n"
            "Terras do Ocaso · Nv. 1–10\n\n"
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
            "Estrada das Cinzas · Terras do Ocaso",
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
            "Estrada das Cinzas · Terras do Ocaso\n\n"
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
            "Estrada das Cinzas · Terras do Ocaso\n\n"
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
            "Estrada das Cinzas · Terras do Ocaso\n\n"
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}"
            f"{_reward_block(view)}"
        )
        return Screen(
            text,
            "road_round_result",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="← Caçada", callback_data=f"road:round:back:{token}"
                        )
                    ]
                ]
            ),
        )
    if view.kind == "round_cancelled":
        text = (
            "🏕️ Ronda de Caça · Cancelada\n"
            "Estrada das Cinzas · Terras do Ocaso\n\n"
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
                        InlineKeyboardButton(
                            text="← Caçada", callback_data=f"road:round:back:{token}"
                        )
                    ]
                ]
            ),
        )
    if view.kind == "round_defeated":
        text = (
            "💀 Ronda de Caça · Derrota\n\n"
            "🔥 Braseiro da Estrada\n"
            "Estrada das Cinzas · Terras do Ocaso\n\n"
            f"⚔️ Encontros · {view.completed_encounters}/{view.batch_size}\n"
            "❤️ HP · Restaurado"
            f"{_reward_block(view)}"
        )
        return Screen(
            text,
            "brazier_estrada",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="← Caçada", callback_data=f"road:round:back:{token}"
                        )
                    ]
                ]
            ),
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
            "Estrada das Cinzas · Terras do Ocaso\n\n"
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
    if view.kind == "combat" and view.combat is not None:
        return render_combat(
            CombatView(
                view.activity_id,
                view.encounter_id,
                view.character_id,
                view.combat,
                "road",
                0,
                "road",
            )
        )
    if view.kind == "hunt_defeat":
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
        text = (
            "🦌 Caçada\n\n🔥 Estrada das Cinzas\nTerras do Ocaso · Nv. 1–10\n\n"
            f"👤 {escape(view.name or 'Personagem')}\n❤️ <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ Vigor · <code>{view.vigor} / {view.max_vigor}</code>\n\n👤 Grupo\n⚔️ Escolha o formato da Caçada."
        )
        keyboard = [
            [InlineKeyboardButton(text="[1] Solo", callback_data="road:hunt")],
            [InlineKeyboardButton(text="[2] Grupo", callback_data="road:unavailable:group")],
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        return Screen(text, "hunt_prepare", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "hunt_victory":
        text = "🏆 Vitória\n\n🦌 Caçada concluída"
        if view.creature:
            text += f"\n🐾 {escape(view.creature)}"
        if view.variant:
            text += f"\n🧬 Variante · {escape(view.variant)}"
        if view.reward_lines:
            text += "\n\n" + "\n".join(view.reward_lines)
        keyboard = [
            [InlineKeyboardButton(text="Caçar Novamente", callback_data="road:prepare")],
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        return Screen(text, "road_victory", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "exploration":
        text = f"🧭 Desbravar\n\n🔥 Estrada das Cinzas\nTerras do Ocaso · Nv. 1–10\n\n{escape(view.result_text or '')}"
        buttons = [
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        if view.retry_available:
            buttons.insert(0, [InlineKeyboardButton(text="Desbravar Novamente", callback_data="road:explore")])
        return Screen(
            text, "exploration", InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML"
        )
    if view.kind == "explore_prepare":
        text = (
            "🧭 Desbravar\n\n🔥 Estrada das Cinzas · Local Atual\n"
            "Terras do Ocaso · Nv. 1–10\n\n👤 Solo\n"
            f"❤️ <code>{view.hp} / {view.max_hp}</code>\n"
            f"⚡ 4 Vigor quando a economia for concedida · <code>{view.vigor} / {view.max_vigor}</code>"
        )
        keyboard = [
            [InlineKeyboardButton(text="Desbravar", callback_data="road:explore:start")],
            [InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")],
        ]
        return Screen(text, "explore_prepare", InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    if view.kind == "explore_cooldown":
        text = (
            "🧭 Desbravar\n\n"
            "⏳ Desbravar · Disponível em "
            f"<code>{escape(view.result_text or '00:00')}</code>"
        )
        return Screen(
            text,
            "explore_cooldown",
            InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")]]),
            parse_mode="HTML",
        )
    if view.kind == "explore_limit":
        text = (
            "🧭 Desbravar\n\n"
            "🔒 Desbravar · Limite recente atingido\n"
            f"⏳ Disponível em · <code>{escape(view.result_text or '00:00')}</code>"
        )
        return Screen(
            text,
            "explore_limit",
            InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="← Estrada das Cinzas", callback_data="road:local")]]),
            parse_mode="HTML",
        )
    if view.location == ROAD:
        round_line = "[Ronda ×5] [Ronda ×10] [Ronda ×20]" if view.familiar else "🔒 Ronda de Caça · Vença uma Caçada neste Local"
        text = (
            "🔥 Estrada das Cinzas · Local Atual\nTerras do Ocaso · Nv. 1–10\n\n"
            "🔥 Braseiro · Descoberto\n"
            + ("🧭 Desbravar · Disponível\n" if view.explore_available else "⏳ Desbravar · Em recarga\n")
            + "🦌 Caçada · Disponível\n\n"
            + round_line
        )
        keyboard = [
            [InlineKeyboardButton(text="Caçar", callback_data="road:prepare")],
            *([[InlineKeyboardButton(text="Desbravar", callback_data="road:explore")]] if view.explore_available else []),
            *([[InlineKeyboardButton(text="Ronda ×5", callback_data="road:round:new:5"), InlineKeyboardButton(text="Ronda ×10", callback_data="road:round:new:10"), InlineKeyboardButton(text="Ronda ×20", callback_data="road:round:new:20")]] if view.familiar else []),
            [
                InlineKeyboardButton(
                    text="Travessia dos Braseiros", callback_data="road:travel:refuge"
                )
            ],
            [InlineKeyboardButton(text="← Terras do Ocaso", callback_data="menu:back")],
        ]
    else:
        text = "🔥 Braseiro do Refúgio\nRefúgio do Ocaso · Terras do Ocaso"
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Travessia dos Braseiros", callback_data="road:travel:road"
                )
            ],
            [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
        ]
    return Screen(text, "road", InlineKeyboardMarkup(inline_keyboard=keyboard))
