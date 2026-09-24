"""Combat HUD reconstructed exclusively from a persisted backend view."""

import base64
from decimal import Decimal, localcontext
from html import escape
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.bot.creation_ui import COPY, Screen
from asterion.domain.combat import Combat, CombatConsumableOption, CombatEvent, allowed_actions
from asterion.domain.consumables import definition


class CombatCallback(CallbackData, prefix="fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class P1CombatCallback(CallbackData, prefix="p1fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


_CONSUMABLE_CALLBACK_KEYS = {
    "consumable.heal": "H",
    "consumable.purification": "P",
    "consumable.antidote.tdo.i": "A",
    "consumable.vigor.tdo.i": "V",
    "consumable.heal.vde.ii": "h",
    "consumable.purification.vde.ii": "p",
    "consumable.antidote.vde.ii": "a",
    "consumable.vigor.vde.ii": "v",
    "consumable.protection.vde.ii": "B",
    "consumable.dispeller.iii": "D",
    "consumable.warding.iv": "R",
}
_CONSUMABLE_CALLBACK_IDS = {key: item_id for item_id, key in _CONSUMABLE_CALLBACK_KEYS.items()}


def _base36(value: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = digits[remainder] + result
    return result


def _from_base36(value: str) -> int:
    return int(value, 36)


def _uuid_token(value: UUID) -> str:
    return base64.urlsafe_b64encode(value.bytes).decode("ascii").rstrip("=")


def _uuid_from_token(value: str) -> UUID:
    return UUID(bytes=base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))


def _text_token(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _text_from_token(value: str) -> str:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("utf-8")


class CombatConsumableCallback(CallbackData, prefix="cu"):
    activity: str
    version: str
    item: str
    target: str
    effect: str

    @classmethod
    def for_option(cls, activity_id: UUID, version: int, option: CombatConsumableOption):
        item = _CONSUMABLE_CALLBACK_KEYS[option.item_id]
        return cls(
            activity=_uuid_token(activity_id),
            version=_base36(version),
            item=item,
            target=_text_token(option.target_id),
            effect=option.effect_id or "-",
        )

    @property
    def activity_id(self) -> UUID:
        return _uuid_from_token(self.activity)

    @property
    def state_version(self) -> int:
        return _from_base36(self.version)

    @property
    def item_id(self) -> str:
        return _CONSUMABLE_CALLBACK_IDS[self.item]

    @property
    def target_id(self) -> str:
        return _text_from_token(self.target)

    @property
    def effect_id(self) -> str | None:
        return None if self.effect == "-" else self.effect


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
    if event.action.startswith("prepare:"):
        action_id = event.action.split(":", 1)[1]
        action = state.enemy_actions.get(action_id)
        label = escape(action.name if action else action_id)
        return f"⚠️ <b>{actor_name}</b> prepara <b>{label}</b>."
    if event.action == "defend":
        return f"🛡️ <b>{actor_name}</b> usa Defender."
    if event.action == "resguardo:block":
        effect = _effect_label(state, event.effect_id)
        target = escape(state.fighters[event.target].name)
        return f"🛡️ Resguardo bloqueia <b>{effect}</b> em <b>{target}</b>."
    if event.action.startswith("consumable:"):
        return _consumable_event_line(state, event, actor_name)
    actions = state.player_actions if event.actor == "player" else state.enemy_actions
    action = actions[event.action]
    label = action.name.split(" ", 1)[-1] if event.actor == "player" else action.name
    target = state.fighters["enemy" if event.actor == "player" else "player"]
    emoji = (
        "⚔️"
        if event.actor == "player" and event.action == "attack"
        else "🎴"
        if event.actor == "player"
        else "🐺"
    )
    if event.actor == "player" and event.action == "attack":
        line = (
            f"{emoji} <b>{actor_name}</b> ataca <b>{escape(target.name)}</b> "
            f"e causa <code>{number(event.damage)}</code> de dano."
        )
    else:
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
    if event.barrier_absorbed:
        line += f" Barreira absorve <code>{number(event.barrier_absorbed)}</code>."
    return line


def _effect_label(state: Combat, effect_id: str) -> str:
    if effect_id.startswith("dot:"):
        return escape(
            {
                "dot:poison": "Veneno",
                "dot:bleed": "Sangramento",
                "dot:burn": "Queimadura",
            }.get(effect_id, "DoT")
        )
    action = state.enemy_actions.get(effect_id) or state.player_actions.get(effect_id)
    return escape(action.name if action is not None else effect_id)


def _consumable_event_line(state: Combat, event: CombatEvent, actor_name: str) -> str:
    item_id = event.action.removeprefix("consumable:")
    item = definition(item_id)
    item_name = escape(item.name if item is not None else item_id)
    target_name = escape(state.fighters[event.target].name)
    family = item.family.value if item is not None else ""
    line = f"🧪 <b>{actor_name}</b> usa <b>{item_name}</b>."
    if family == "healing":
        line += f" Recupera <code>{number(event.healed)}</code> HP."
    elif family == "protection":
        line += (
            f" 🔰 Barreira · <code>{number(event.barrier_value)}</code> · <code>2T</code>."
        )
    elif family == "warding":
        line += " 🛡️ Resguardo · <code>2T</code> · <code>1 Carga</code>."
    elif family == "dispeller":
        line += (
            f" em <b>{target_name}</b>. ✨ "
            f"<b>{_effect_label(state, event.effect_id)}</b> removido."
        )
    elif family == "antidote":
        line += f" ☣️ <b>{_effect_label(state, event.effect_id)}</b> removido."
    elif family == "purification":
        line += f" ✨ <b>{_effect_label(state, event.effect_id)}</b> removido."
    return line


def render_combat(view: CombatView) -> Screen:
    state = view.combat
    player, enemy = state.fighters["player"], state.fighters["enemy"]
    icon = COPY[f"class:{player.character_class}"].split(" ", 1)[0]
    recent = [state.opening_log] + [event_line(state, event) for event in state.events]
    lines = [
        f"Turno {player.opportunity} · <b>{escape(player.name)}</b>",
        "",
        f"<b>🐺 {escape(enemy.name)}</b>",
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
    if player.barrier > 0 and player.barrier_remaining > 0:
        lines.insert(
            11,
            f"🔰 Barreira · <code>{number(player.barrier)}</code> · "
            f"<code>{player.barrier_remaining}T</code>",
        )
    if player.ward_charges > 0 and player.ward_remaining > 0:
        lines.insert(
            11,
            f"🛡️ Resguardo · <code>{player.ward_remaining}T</code> · <code>1 Carga</code>",
        )
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
                lines.extend(
                    [
                        f"🎴 <b>{escape(clean)}</b> · Arte de Classe",
                        f"⚔️ Dano · <code>{number(art.coefficient * 100)}%</code> ATQ",
                        "⏳ Recarga · <code>2</code>",
                    ]
                )
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
                callback_data=(P1CombatCallback if view.context == "p1" else CombatCallback)(
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
    if state.result == "victory" and view.context == "prologue":
        # Mechanical receipt only: no new story scene or Braseiro/Descansar button.
        lines.append("320 XP")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
    if view.consumable_options:
        rows = [buttons] if buttons else []
        rows.extend(
            [
                InlineKeyboardButton(
                    text=f"🧪 {option.label}",
                    callback_data=CombatConsumableCallback.for_option(
                        view.activity_id, state.version, option
                    ).pack(),
                )
            ]
            for option in view.consumable_options
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    return Screen("\n".join(lines).rstrip(), view.context, keyboard, parse_mode="HTML")
