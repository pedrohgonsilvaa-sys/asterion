"""Combat HUD reconstructed exclusively from a persisted backend view."""

from decimal import Decimal, localcontext
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


def hp_bar(current: Decimal, maximum: Decimal) -> str:
    with localcontext() as ctx:
        ctx.prec = 50
        filled = min(10, max(0, int(current * 10 / maximum)))
        return "▰" * filled + "▱" * (10 - filled)


def event_line(state: Combat, event: CombatEvent) -> str:
    actor = state.fighters[event.actor]
    if event.action == "defend":
        return f"{actor.name} · 🛡️ Defender"
    actions = state.player_actions if event.actor == "player" else state.enemy_actions
    label = actions[event.action].name
    line = f"{actor.name} · {label} · −{event.damage} HP"
    if event.critical:
        line += " · Crítico"
    if event.healed:
        line += f" · +{number(event.healed)} HP"
    if event.effect_id:
        effect = actions[event.action]
        line += f" · −{number(effect.attack_debuff * 100)}% ATQ · {effect.duration}T"
    return line


def render_combat(view: CombatView) -> Screen:
    state = view.combat
    player, enemy = state.fighters["player"], state.fighters["enemy"]
    icon = COPY[f"class:{player.character_class}"].split(" ", 1)[0]
    recent = [state.opening_log] + [event_line(state, event) for event in state.events]
    lines = [
        f"Turno {player.opportunity} · {player.name}",
        "",
        enemy.name,
        f"❤️ {number(enemy.hp)} / {number(enemy.stats.hp)}",
        hp_bar(enemy.hp, enemy.stats.hp),
        "",
        state.flavor,
        "",
        f"👉 {icon} {player.name}",
        f"❤️ {number(player.hp)} / {number(player.stats.hp)}",
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
            label = state.player_actions[action].name
            hint = label
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
    return Screen("\n".join(lines).rstrip(), "prologue_first_combat", keyboard)
