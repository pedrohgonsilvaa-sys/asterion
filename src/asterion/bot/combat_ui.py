"""Combat HUD reconstructed exclusively from a persisted backend view."""

from decimal import Decimal, localcontext
from html import escape
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.bot.creation_ui import COPY, Screen
from asterion.domain.combat import Combat, CombatEvent, allowed_actions


class CombatCallback(CallbackData, prefix="fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


def number(value: Decimal | int) -> str:
    return (
        format(value, "f").rstrip("0").rstrip(".")
        if isinstance(value, Decimal) and value % 1
        else str(int(value))
    )


def hp_bar(current: Decimal, maximum: Decimal, *, color: str = "🟩") -> str:
    with localcontext() as ctx:
        ctx.prec = 50
        filled = min(10, max(0, int(current * 10 / maximum))) if maximum else 0
        return color * filled + "⬜" * (10 - filled)


def event_line(state: Combat, event: CombatEvent) -> str:
    actor = state.fighters[event.actor]
    actor_name = escape(actor.name)
    if event.action == "defend":
        return f"🛡️ <b>{actor_name}</b> usa Defender."
    actions = state.player_actions if event.actor == "player" else state.enemy_actions
    action = actions[event.action]
    label = action.name.split(" ", 1)[-1]
    target = state.fighters["enemy" if event.actor == "player" else "player"]
    emoji = (
        "⚔️" if event.actor == "player" and event.action == "attack"
        else "🎴" if event.actor == "player" else "🐺"
    )
    verb = "ataca" if event.action == "attack" else "usa"
    line = (
        f"{emoji} <b>{actor_name}</b> {verb} <b>{escape(target.name)}</b> "
        f"e causa <code>{number(event.damage)}</code> de dano."
    )
    if event.action != "attack" and event.actor == "player":
        line = (
            f"{emoji} <b>{actor_name}</b> usa <b>{escape(label)}</b> em "
            f"<b>{escape(target.name)}</b> e causa <code>{number(event.damage)}</code> de dano."
        )
    if event.critical:
        line += " Crítico."
    if event.healed:
        line += f" Cura <code>{number(event.healed)}</code>."
    if event.effect_id:
        effect = actions[event.action]
        line += (
            f" Reduz ATQ em <code>{number(effect.attack_debuff * 100)}%</code> por "
            f"<code>{effect.duration}T</code>."
        )
    return line


def render_combat(view: CombatView) -> Screen:
    state = view.combat
    player, enemy = state.fighters["player"], state.fighters["enemy"]
    icon = COPY[f"class:{player.character_class}"].split(" ", 1)[0]
    recent = [state.opening_log] + [event_line(state, event) for event in state.events]
    lines = [
        f"Turno {player.opportunity} · <b>{escape(player.name)}</b>",
        "",
        f"<b>{escape(enemy.name)}</b>",
        f"❤️ <code>{number(enemy.hp)} / {number(enemy.stats.hp)}</code>",
        hp_bar(enemy.hp, enemy.stats.hp),
        "",
        state.flavor,
        "",
        f"👉 {icon} <b>{escape(player.name)}</b>",
        f"❤️ <code>{number(player.hp)} / {number(player.stats.hp)}</code>",
        hp_bar(player.hp, player.stats.hp),
        "",
        "📜 Registro de Combate · Recentes",
        "",
        "\n".join(recent[-4:]),
        "",
    ]
    available = allowed_actions(state)
    buttons = []
    for action in available:
        if action == "attack":
            label, hint = "Atacar", "⚔️ Atacar · Causa Dano"
        elif action == "defend":
            label, hint = "Defender", "🛡️ Defender · Reduz Dano até seu próximo Turno"
        else:
            art = state.player_actions[action]
            clean = art.name.split(" ", 1)[-1]
            label = clean
            hint = clean
            if state.tutorial_stage == "art":
                lines.extend([
                    f"🎴 <b>{escape(clean)}</b> · Arte de Classe",
                    f"⚔️ Dano · <code>{number(art.coefficient * 100)}%</code> ATQ",
                    "⏳ Recarga · <code>2</code>",
                ])
                if art.attack_debuff:
                    lines.insert(
                        -1,
                        f"🌀 Efeito · −<code>{number(art.attack_debuff * 100)}%</code> ATQ "
                        f"por <code>{art.duration}T</code>",
                    )
        lines.append(hint)
        buttons.append(
            InlineKeyboardButton(
                text=label,
                callback_data=CombatCallback(
                    activity=view.activity_id.hex,
                    version=state.version,
                    action=action,
                ).pack(),
            )
        )
    if state.tutorial_stage == "normal" and not state.result:
        remaining = max(0, player.cooldowns.get("art", 0) - player.opportunity)
        if remaining:
            lines.append(f"{state.player_actions['art'].name} · CD{remaining}")
    if state.result == "victory":
        # Mechanical receipt only: no new story scene or Braseiro/Descansar button.
        lines.append("320 XP")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
    return Screen("\n".join(lines).rstrip(), "prologue_first_combat", keyboard, parse_mode="HTML")
