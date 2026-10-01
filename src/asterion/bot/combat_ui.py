"""Combat HUD reconstructed exclusively from a persisted backend view."""

import base64
from decimal import Decimal, localcontext
from html import escape
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.bot.creation_ui import COPY, Screen
from asterion.domain.combat import (
    Combat,
    CombatConsumableOption,
    CombatEvent,
    action_target_ids,
    allowed_actions,
    consumable_effect_options,
)
from asterion.domain.consumables import (
    CONSUMABLE_CATALOG,
    ConsumableFamily,
    definition,
)


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


class P2CombatCallback(CallbackData, prefix="p2fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class S2CombatCallback(CallbackData, prefix="s2fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class P3CombatCallback(CallbackData, prefix="p3fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class S3CombatCallback(CallbackData, prefix="s3fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class P4CombatCallback(CallbackData, prefix="p4fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class ClassTrialActionCallback(CallbackData, prefix="trialact"):
    attempt: str
    version: str
    action: str
    target: str

    @classmethod
    def for_intent(
        cls, attempt_id: UUID, version: int, action_index: int, target: str
    ):
        # Action/target indexes decode only against this persisted attempt/version.
        return cls(
            attempt=_uuid_token(attempt_id),
            version=_base36(version),
            action=_base36(action_index),
            target=target,
        )

    @property
    def attempt_id(self) -> UUID:
        return _uuid_from_token(self.attempt)

    @property
    def combat_version(self) -> int:
        return _from_base36(self.version)

    @property
    def action_index(self) -> int:
        return _from_base36(self.action)

    @property
    def target_index(self) -> int | None:
        if self.target in {"x", "s", "b"}:
            return None
        token = self.target[1:] if self.target.startswith("d") else self.target
        return _from_base36(token)

    @property
    def direct_target(self) -> bool:
        return self.target.startswith("d")


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


def class_trial_target_ids(state: Combat, action_id: str) -> tuple[str, ...]:
    action = state.player_actions.get(action_id)
    if action is None or action.target_mode in {"self", "all_opponents", "all_allies"}:
        return ()
    return action_target_ids(state, action_id)


def class_trial_action_ids(state: Combat) -> tuple[str, ...]:
    available = []
    for action_id in allowed_actions(state):
        if action_id == "defend":
            available.append(action_id)
            continue
        action = state.player_actions.get(action_id)
        if action is None:
            continue
        all_targets = action_target_ids(state, action_id)
        if all_targets:
            available.append(action_id)
    return tuple(available)


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


class CombatConsumableFlowCallback(CallbackData, prefix="cf"):
    activity: str
    version: str
    step: str
    item: str
    target: str
    effect: str
    parent: str

    @classmethod
    def for_step(
        cls,
        activity_id: UUID,
        version: int,
        step: str,
        *,
        item_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
        parent: str | None = None,
    ):
        return cls(
            activity=_uuid_token(activity_id),
            version=_base36(version),
            step=step,
            item=_CONSUMABLE_CALLBACK_KEYS[item_id] if item_id is not None else "-",
            target=_text_token(target_id) if target_id is not None else "-",
            effect=_text_token(effect_id) if effect_id is not None else "-",
            parent={"combat": "c", "items": "i", "targets": "t"}.get(parent, "-"),
        )

    @property
    def activity_id(self) -> UUID:
        return _uuid_from_token(self.activity)

    @property
    def state_version(self) -> int:
        return _from_base36(self.version)

    @property
    def item_id(self) -> str | None:
        return _CONSUMABLE_CALLBACK_IDS.get(self.item)

    @property
    def target_id(self) -> str | None:
        return None if self.target == "-" else _text_from_token(self.target)

    @property
    def effect_id(self) -> str | None:
        return None if self.effect == "-" else _text_from_token(self.effect)

    @property
    def parent_screen(self) -> str | None:
        return {"c": "combat", "i": "items", "t": "targets"}.get(self.parent)


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


def _consumable_item_ids(view: CombatView) -> tuple[str, ...]:
    available = {option.item_id for option in view.consumable_options}
    return tuple(item_id for item_id in CONSUMABLE_CATALOG if item_id in available)


def _consumable_summary(item_id: str) -> str:
    item = definition(item_id)
    if item is None:
        return ""
    return {
        ConsumableFamily.HEALING: "❤️ Cura · 22% HP Máximo",
        ConsumableFamily.PURIFICATION: "✨ Purificação · 1 Efeito Negativo",
        ConsumableFamily.ANTIDOTE: "☣️ Antídoto · 1 DoT",
        ConsumableFamily.PROTECTION: "🔰 Barreira · 12% HP Máximo · 2T",
        ConsumableFamily.DISPELLER: "✨ Dissipação · 1 Efeito Positivo",
        ConsumableFamily.WARDING: "🛡️ Resguardo · 2T · 1 Carga",
    }.get(item.family, "")


def _numeric_rows(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    return [buttons[index : index + 5] for index in range(0, len(buttons), 5)]


def _choice_name_and_state(
    state: Combat, item_id: str, target_id: str, effect_id: str
) -> tuple[str, str]:
    selections = dict(
        consumable_effect_options(state, item_id, target_id=target_id)
    )
    selection = selections.get(effect_id, "")
    name = _effect_display_name(state, target_id, selection)
    if selection.startswith("dot:"):
        dots = state.dot_states.get(target_id, ())
        selected = next(
            (
                dot
                for index, dot in enumerate(dots)
                if (dot.instance_id or f"d{index + 1:x}") == effect_id
            ),
            None,
        )
        if selected is not None and selected.stacks > 1:
            return name, f"{selected.stacks} Acúmulos · {selected.remaining}T"
        return name, f"{selected.remaining}T" if selected is not None else ""
    fighter = state.fighters.get(target_id)
    effects = fighter.effects if fighter is not None else ()
    selected = next(
        (
            effect
            for index, effect in enumerate(effects)
            if (effect.instance_id or f"e{index + 1:x}") == effect_id
        ),
        None,
    )
    if selected is None:
        return name, ""
    if selected.stackable and selected.stacks > 1:
        return name, f"{selected.stacks} Acúmulos · {selected.remaining}T"
    return name, f"{selected.remaining}T"


def _effect_display_name(state: Combat, target_id: str, selection: str) -> str:
    if selection.startswith("dot:"):
        return escape(
            {
                "dot:poison": "Veneno",
                "dot:bleed": "Sangramento",
                "dot:burn": "Queimadura",
            }.get(selection, "Dano ao Longo do Tempo")
        )
    effect_id = selection.removeprefix("effect:")
    actions = state.enemy_actions if target_id != "player" else state.player_actions
    action = actions.get(effect_id)
    return escape(action.name if action is not None else "Efeito")


def _render_consumable_selection(view: CombatView) -> Screen:
    state = view.combat
    player = state.fighters["player"]
    screen = view.consumable_screen
    rows: list[list[InlineKeyboardButton]] = []
    lines: list[str] = []

    if screen == "items":
        lines = ["🧪 Consumíveis", f"Turno {player.opportunity} · <b>{escape(player.name)}</b>", ""]
        if view.consumable_notice:
            lines.extend([escape(view.consumable_notice), ""])
        item_ids = _consumable_item_ids(view)
        quantities = dict(view.consumable_quantities)
        item_buttons = []
        for index, item_id in enumerate(item_ids, start=1):
            item = definition(item_id)
            assert item is not None
            lines.extend(
                [
                    f"{index} 🧪 {escape(item.name)} · {quantities.get(item_id, 0)}",
                    _consumable_summary(item_id),
                    "",
                ]
            )
            item_buttons.append(
                InlineKeyboardButton(
                    text=str(index),
                    callback_data=CombatConsumableFlowCallback.for_step(
                        view.activity_id,
                        state.version,
                        "i",
                        item_id=item_id,
                    ).pack(),
                )
            )
        rows.extend(_numeric_rows(item_buttons))
        rows.append(
            [
                InlineKeyboardButton(
                    text="← Combate",
                    callback_data=CombatConsumableFlowCallback.for_step(
                        view.activity_id, state.version, "b", parent="combat"
                    ).pack(),
                )
            ]
        )
    elif screen == "targets":
        item_id = view.selected_consumable_id or ""
        item = definition(item_id)
        item_name = escape(item.name if item is not None else "Dissipador")
        lines = [f"✨ {item_name} · Escolha o Alvo", ""]
        target_counts: dict[str, int] = {}
        for option in view.consumable_options:
            if option.item_id == item_id:
                target_counts[option.target_id] = target_counts.get(option.target_id, 0) + 1
        target_buttons = []
        for index, (target_id, count) in enumerate(target_counts.items(), start=1):
            target = state.fighters.get(target_id)
            if target is None:
                continue
            lines.extend(
                [
                    f"{index} 🐺 {escape(target.name)}",
                    f"Efeitos Removíveis · {count}",
                    "",
                ]
            )
            target_buttons.append(
                InlineKeyboardButton(
                    text=str(index),
                    callback_data=CombatConsumableFlowCallback.for_step(
                        view.activity_id,
                        state.version,
                        "t",
                        item_id=item_id,
                        target_id=target_id,
                    ).pack(),
                )
            )
        rows.extend(_numeric_rows(target_buttons))
        rows.append(
            [
                InlineKeyboardButton(
                    text="← Consumíveis",
                    callback_data=CombatConsumableFlowCallback.for_step(
                        view.activity_id,
                        state.version,
                        "b",
                        item_id=item_id,
                        parent="items",
                    ).pack(),
                )
            ]
        )
    else:
        item_id = view.selected_consumable_id or ""
        target_id = view.selected_target_id or "player"
        item = definition(item_id)
        family = item.family if item is not None else None
        title = (
            "✨ Dissipador · Escolha o Efeito"
            if family == ConsumableFamily.DISPELLER
            else "☣️ Antídoto · Escolha o DoT"
            if family == ConsumableFamily.ANTIDOTE
            else "✨ Purificação · Escolha o Efeito Negativo"
        )
        lines = [title, ""]
        target = state.fighters.get(target_id)
        if family == ConsumableFamily.DISPELLER and target is not None:
            lines.extend([f"🐺 {escape(target.name)}", ""])
        choices = []
        for option in view.consumable_options:
            if (
                option.item_id == item_id
                and option.target_id == target_id
                and option.effect_id is not None
            ):
                if all(existing.effect_id != option.effect_id for existing in choices):
                    choices.append(option)
        effect_buttons = []
        for index, option in enumerate(choices, start=1):
            effect_name, state_label = _choice_name_and_state(
                state, item_id, target_id, option.effect_id or ""
            )
            icon = "🟢" if family == ConsumableFamily.DISPELLER else "🔻"
            detail = f" · {state_label}" if state_label else ""
            lines.extend([f"{index} {icon} {effect_name}{detail}", ""])
            effect_buttons.append(
                InlineKeyboardButton(
                    text=str(index),
                    callback_data=CombatConsumableFlowCallback.for_step(
                        view.activity_id,
                        state.version,
                        "e",
                        item_id=item_id,
                        target_id=target_id,
                        effect_id=option.effect_id,
                        parent=view.selection_parent,
                    ).pack(),
                )
            )
        rows.extend(_numeric_rows(effect_buttons))
        back_to_targets = view.selection_parent == "targets"
        rows.append(
            [
                InlineKeyboardButton(
                    text="← Alvos" if back_to_targets else "← Consumíveis",
                    callback_data=CombatConsumableFlowCallback.for_step(
                        view.activity_id,
                        state.version,
                        "b",
                        item_id=item_id,
                        target_id=target_id if back_to_targets else None,
                        parent="targets" if back_to_targets else "items",
                    ).pack(),
                )
            ]
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    return Screen("\n".join(lines).rstrip(), view.context, keyboard, "HTML")


def _fighter_for_event(state: Combat, identifier: str | None):
    if not identifier:
        return None
    if identifier in state.fighters:
        return state.fighters[identifier]
    return next(
        (fighter for fighter in state.fighters.values() if fighter.id == identifier),
        None,
    )


def event_line(state: Combat, event: CombatEvent) -> str:
    actor = _fighter_for_event(
        state, event.actor_entity_id or event.actor
    )
    if actor is None:
        return "O combate continua."
    actor_name = escape(actor.name)
    if event.action.startswith("prepare:"):
        action_id = event.action.split(":", 1)[1]
        action = state.enemy_actions.get(action_id)
        label = escape(action.name if action else "ataque")
        return f"☄️ <b>{actor_name}</b> prepara <b>{label}</b>."
    if event.action == "defend":
        return f"🛡️ <b>{actor_name}</b> usa Defender."
    if event.action == "hold":
        return f"✨ <b>{actor_name}</b> aguarda."
    if event.action == "resguardo:block":
        effect = _effect_label(state, event.effect_id, target_id=event.target)
        target = _fighter_for_event(state, event.target)
        target_name = escape(target.name if target else actor.name)
        return f"🛡️ Resguardo bloqueia <b>{effect}</b> em <b>{target_name}</b>."
    if event.action.startswith("consumable:"):
        return _consumable_event_line(state, event, actor_name)
    actions = state.player_actions if event.actor == "player" else state.enemy_actions
    action = actions.get(event.action)
    if action is None:
        if event.action.startswith("dot:"):
            dot = {
                "dot:poison": "Veneno",
                "dot:bleed": "Sangramento",
                "dot:burn": "Queimadura",
            }.get(event.action, "Dano contínuo")
            return f"☣️ <b>{actor_name}</b> sofre <b>{dot}</b>."
        return f"✨ <b>{actor_name}</b> age no combate."
    target = _fighter_for_event(state, event.target) or actor
    target_name = escape(target.name)
    if event.barrier_value:
        duration = (
            action.target_barrier_duration
            if target.id != actor.id and action.target_barrier_duration
            else action.self_barrier_duration
        )
        return (
            f"🛡️ <b>{actor_name}</b> ergue <b>{escape(action.name)}</b> "
            f"em <b>{target_name}</b>. Barreira · "
            f"<code>{number(event.barrier_value)}</code> · <code>{duration}T</code>."
        )
    label = action.name.split(" ", 1)[-1] if event.actor == "player" else action.name
    emoji = (
        "⚔️"
        if event.actor == "player" and event.action == "attack"
        else "🎴"
        if event.actor == "player"
        else "🐺"
    )
    if event.actor == "player" and event.action == "attack":
        line = (
            f"{emoji} <b>{actor_name}</b> ataca <b>{target_name}</b> "
            f"e causa <code>{number(event.damage)}</code> de dano."
        )
    elif action.heal_coefficient and event.healed:
        line = (
            f"❤️ <b>{actor_name}</b> usa <b>{escape(label)}</b> em "
            f"<b>{target_name}</b> e recupera <code>{number(event.healed)}</code> HP."
        )
    else:
        line = (
            f"{emoji} <b>{actor_name}</b> usa <b>{escape(label)}</b> em "
            f"<b>{target_name}</b> e causa <code>{number(event.damage)}</code> de dano."
        )
    if event.critical:
        line += " Crítico."
    if event.healed and not action.heal_coefficient:
        line += f" Cura <code>{number(event.healed)}</code>."
    if event.effect_id:
        stat_label = {"attack": "ATQ", "defense": "DEF", "agility": "AGI"}.get(
            action.effect_stat or "attack", action.effect_stat or "ATQ"
        )
        line += (
            f" Reduz {stat_label} em <code>{number(action.attack_debuff * 100)}%</code> por "
            f"<code>{action.duration}T</code>."
        )
    if event.actor_effect_id:
        stat_label = {"attack": "ATQ", "defense": "DEF", "agility": "AGI"}.get(
            action.self_effect_stat or "attack",
            action.self_effect_stat or "ATQ",
        )
        line += (
            f" <b>{actor_name}</b> reduz a própria {stat_label} em "
            f"<code>{number(action.self_effect_magnitude * 100)}%</code> por "
            f"<code>{action.self_effect_duration}T</code>."
        )
    if event.barrier_absorbed:
        line += f" Barreira absorve <code>{number(event.barrier_absorbed)}</code>."
    return line

def _effect_label(state: Combat, effect_id: str, *, target_id: str) -> str:
    if effect_id.startswith("dot:"):
        return escape(
            {
                "dot:poison": "Veneno",
                "dot:bleed": "Sangramento",
                "dot:burn": "Queimadura",
            }.get(effect_id, "DoT")
        )
    action = state.enemy_actions.get(effect_id) or state.player_actions.get(effect_id)
    if action is not None:
        return escape(action.name)
    fallback = "Efeito Negativo" if target_id == "player" else "Efeito Positivo"
    return escape(fallback)


def _consumable_event_line(state: Combat, event: CombatEvent, actor_name: str) -> str:
    item_id = event.action.removeprefix("consumable:")
    item = definition(item_id)
    item_name = escape(item.name if item is not None else item_id)
    target_name = escape(state.fighters[event.target].name)
    family = item.family if item is not None else None
    line = f"🧪 <b>{actor_name}</b> usa <b>{item_name}</b>."
    if family == ConsumableFamily.HEALING:
        return f"{line}\n❤️ <b>{target_name}</b> recupera <code>{number(event.healed)}</code> HP."
    if family == ConsumableFamily.PROTECTION:
        return f"{line}\n🔰 Barreira · <code>{number(event.barrier_value)}</code> · <code>2T</code>"
    if family == ConsumableFamily.WARDING:
        return f"{line}\n🛡️ Resguardo · <code>2T</code> · <code>1 Carga</code>"
    if family == ConsumableFamily.DISPELLER:
        removed = _removed_effect_summary(event)
        return (
            f"🧪 <b>{actor_name}</b> usa <b>{item_name}</b> em <b>{target_name}</b>.\n"
            f"✨ <b>{_effect_label(state, event.effect_id, target_id=event.target)}</b> · {removed}"
        )
    if family == ConsumableFamily.ANTIDOTE:
        effect = _effect_label(state, event.effect_id, target_id=event.target)
        return f"{line}\n☣️ <b>{effect}</b> · Removido"
    if family == ConsumableFamily.PURIFICATION:
        effect = _effect_label(state, event.effect_id, target_id=event.target)
        return f"{line}\n✨ <b>{effect}</b> · Removido"
    return line


def _removed_effect_summary(event: CombatEvent) -> str:
    if event.effect_removal_kind == "stack":
        return "1 Acúmulo Removido"
    # Legacy snapshots have no removal metadata. Use the existing neutral
    # player-facing wording without consulting the target's current effects.
    return "Removido"


def _fighter_side(state: Combat, key: str) -> str:
    fighter = state.fighters[key]
    return fighter.side or ("player" if key == "player" else "enemy")


def _status_lines(state: Combat, fighter, *, player: bool = False) -> list[str]:
    name = escape(fighter.name)
    lines: list[str] = []
    if fighter.barrier > 0 and fighter.barrier_remaining > 0:
        icon = "🔰" if player else "🛡️"
        lines.append(
            f"{icon} Barreira de {name} · <code>{number(fighter.barrier)}</code> · "
            f"<code>{fighter.barrier_remaining}T</code>"
        )
    for effect in fighter.effects:
        stat = {
            "attack": "ATQ",
            "defense": "DEF",
            "agility": "AGI",
            "perception": "PER",
            "precision": "PRE",
        }.get(effect.stat, effect.stat.upper())
        sign = "−" if effect.kind == "debuff" else "+"
        lines.append(
            f"{'🔻' if effect.kind == 'debuff' else '✨'} {name} · {stat} "
            f"{sign}<code>{number(abs(effect.magnitude) * 100)}%</code> · "
            f"<code>{effect.remaining}T</code>"
        )
    dots = state.dot_states.get(fighter.id, ())
    for dot in dots:
        label = {
            "poison": "Veneno",
            "bleed": "Sangramento",
            "burn": "Queimadura",
        }.get(dot.kind, "Efeito contínuo")
        lines.append(
            f"☣️ {name} · {label} · {dot.stacks} · <code>{dot.remaining}T</code>"
        )
    if player and fighter.ward_charges > 0 and fighter.ward_remaining > 0:
        lines.append(
            f"🛡️ Resguardo · <code>{fighter.ward_remaining}T</code> · "
            f"<code>{fighter.ward_charges} Carga(s)</code>"
        )
    return lines


def _trial_fighter_card(state: Combat, key: str, *, icon: str) -> list[str]:
    fighter = state.fighters[key]
    name = escape(fighter.name)
    lines = [
        f"{icon} <b>{name}</b>",
        f"❤️ <code>{number(fighter.hp)} / {number(fighter.stats.hp)}</code>",
        hp_bar(fighter.hp, fighter.stats.hp),
    ]
    lines.extend(_status_lines(state, fighter, player=(key == "player")))
    lines.append("")
    return lines


def render_combat(view: CombatView) -> Screen:
    state = view.combat
    is_trial = view.context == "class_trial"
    if not is_trial and view.consumable_screen is not None:
        return _render_consumable_selection(view)
    player = state.fighters["player"]
    icon = COPY[f"class:{player.character_class}"].split(" ", 1)[0]
    recent = [state.opening_log] + [event_line(state, event) for event in state.events]
    if is_trial:
        lines = []
        if view.trial_stage_caption:
            lines.extend([f"⚔️ Provação · {escape(view.trial_stage_caption)}", ""])
        lines.extend(
            [
                f"Turno {player.opportunity} · <b>{escape(player.name)}</b>",
                "",
            ]
        )
        enemies = sorted(
            (
                key for key in state.fighters
                if key != "player" and _fighter_side(state, key) == "enemy"
            ),
            key=lambda key: (state.fighters[key].id, key),
        )
        allies = sorted(
            (
                key for key in state.fighters
                if key != "player" and _fighter_side(state, key) == "player"
            ),
            key=lambda key: (state.fighters[key].id, key),
        )
        for key in enemies:
            prepared_source = _fighter_for_event(state, state.prepared_source)
            marker = "☄️" if prepared_source is state.fighters[key] else (
                "🐺" if state.fighters[key].takes_turn else "✦"
            )
            lines.extend(_trial_fighter_card(state, key, icon=marker))
        if state.prepared_action:
            prepared = state.enemy_actions.get(state.prepared_action)
            source = _fighter_for_event(state, state.prepared_source)
            if prepared is not None and source is not None:
                lines.extend(
                    [
                        f"☄️ <b>{escape(source.name)}</b> prepara "
                        f"<b>{escape(prepared.name)}</b>.",
                        "",
                    ]
                )
        if state.flavor:
            lines.extend([escape(state.flavor), ""])
        for key in allies:
            lines.extend(_trial_fighter_card(state, key, icon="✨"))
        lines.extend(_trial_fighter_card(state, "player", icon=f"👉 {icon}"))
        lines.extend(["📜 Registro de Combate · Recentes", "", "\n".join(recent[-4:]), ""])
    else:
        enemy = state.fighters["enemy"]
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
        status_lines = []
        if enemy.barrier > 0 and enemy.barrier_remaining > 0:
            status_lines.append(
                f"🛡️ Barreira de {escape(enemy.name)} · "
                f"<code>{number(enemy.barrier)}</code> · <code>{enemy.barrier_remaining}T</code>"
            )
        if player.barrier > 0 and player.barrier_remaining > 0:
            status_lines.append(
                f"🔰 Barreira · <code>{number(player.barrier)}</code> · "
                f"<code>{player.barrier_remaining}T</code>"
            )
        if player.ward_charges > 0 and player.ward_remaining > 0:
            status_lines.append(
                f"🛡️ Resguardo · <code>{player.ward_remaining}T</code> · <code>1 Carga</code>"
            )
        if status_lines:
            lines[11:11] = status_lines
        if view.consumable_notice:
            lines[8:8] = [escape(view.consumable_notice), ""]

    available = (
        class_trial_action_ids(state)
        if is_trial
        else allowed_actions(state)
    )
    buttons = []
    for action in available:
        if action == "attack":
            label, hint = "Atacar", "⚔️ Atacar · Causa Dano"
        elif action == "defend":
            label, hint = "Defender", "🛡️ Defender · Reduz Dano até seu próximo Turno"
        else:
            art = state.player_actions[action]
            clean = art.name.removeprefix("🎴 ").strip().removeprefix("🗡️ ")
            label = clean
            hint = clean
            if not is_trial and state.tutorial_stage == "art":
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
        if not is_trial:
            lines.append(hint)
        if is_trial:
            action_ids = class_trial_action_ids(state)
            action_index = action_ids.index(action)
            targets = class_trial_target_ids(state, action)
            if action in {"attack", "defend"}:
                targets = class_trial_target_ids(state, action)
            target_code = (
                "s" if len(targets) > 1
                else "d0" if len(targets) == 1
                else "x"
            )
            callback = ClassTrialActionCallback.for_intent(
                view.activity_id, state.version, action_index, target_code
            ).pack()
        else:
            callback_action = action
            if action.startswith("class_art.") and isinstance(state.configuration_snapshot, dict):
                active = state.configuration_snapshot.get("active_arts", ())
                slot = next(
                    (
                        entry.get("slot")
                        for entry in active
                        if isinstance(entry, dict) and entry.get("art_id") == action
                    ),
                    None,
                )
                if slot in {1, 2, 3}:
                    callback_action = f"a{slot}"
            callback = (
                P1CombatCallback
                if view.context == "p1"
                else P2CombatCallback
                if view.context == "p2"
                else S2CombatCallback
                if view.context == "s2"
                else P3CombatCallback
                if view.context == "p3"
                else S3CombatCallback
                if view.context == "s3"
                else P4CombatCallback
                if view.context == "p4"
                else CombatCallback
            )(
                activity=view.activity_id.hex,
                version=state.version,
                action=callback_action,
            ).pack()
        buttons.append(InlineKeyboardButton(text=label, callback_data=callback))

    if not is_trial and state.tutorial_stage == "normal" and not state.result:
        remaining = max(0, player.cooldowns.get("art", 0) - player.opportunity)
        if remaining:
            lines.append(f"{state.player_actions['art'].name} · CD{remaining}")
    if state.result == "victory" and view.context == "prologue":
        lines.append("320 XP")
    keyboard_rows = [buttons] if buttons else []
    if not is_trial and view.consumable_options:
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="Consumível",
                    callback_data=CombatConsumableFlowCallback.for_step(
                        view.activity_id, state.version, "o"
                    ).pack(),
                )
            ]
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows) if keyboard_rows else None
    return Screen("\n".join(lines).rstrip(), view.context, keyboard, parse_mode="HTML")
