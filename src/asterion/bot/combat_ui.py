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
    active_player_key,
    allowed_actions,
    consumable_effect_options,
    player_actions_for,
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


class CampaignCombatCallback(CallbackData, prefix="cc"):
    activity: str
    version: str
    action: str
    target: str

    @classmethod
    def for_intent(cls, activity_id: UUID, version: int, action_index: int, target: str):
        return cls(
            activity=activity_id.hex,
            version=_base36(version),
            action=_base36(action_index),
            target=target,
        )

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)

    @property
    def combat_version(self) -> int:
        return _from_base36(self.version)

    @property
    def action_index(self) -> int:
        return _from_base36(self.action)


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


class P5CombatCallback(CallbackData, prefix="p5fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class S6CombatCallback(CallbackData, prefix="s6fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class P6CombatCallback(CallbackData, prefix="p6fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class S4CombatCallback(CallbackData, prefix="s4fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class S5CombatCallback(CallbackData, prefix="s5fight"):
    activity: str
    version: int
    action: str

    @property
    def activity_id(self) -> UUID:
        return UUID(hex=self.activity)


class DungeonCombatCallback(CallbackData, prefix="df"):
    run: str
    activity: str
    version: str
    action: str
    target: str

    @classmethod
    def for_intent(
        cls, run_id: UUID, activity_id: UUID, version: int, action_index: int, target: str
    ):
        return cls(
            run=run_id.hex[:16],
            activity=_uuid_token(activity_id),
            version=_base36(version),
            action=_base36(action_index),
            target=target,
        )

    @property
    def activity_id(self) -> UUID:
        return _uuid_from_token(self.activity)

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
        return _from_base36(self.target[1:] if self.target.startswith("d") else self.target)


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


def class_trial_target_ids(
    state: Combat, action_id: str, *, actor_key: str | None = None
) -> tuple[str, ...]:
    actor_key = actor_key or active_player_key(state) or "player"
    action = player_actions_for(state, actor_key).get(action_id)
    if action is None or action.target_mode in {"self", "all_opponents", "all_allies"}:
        return ()
    return action_target_ids(state, action_id, actor_key=actor_key)


def class_trial_action_ids(
    state: Combat, *, actor_key: str | None = None
) -> tuple[str, ...]:
    actor_key = actor_key or active_player_key(state) or "player"
    available = []
    for action_id in allowed_actions(state, actor_key):
        if action_id == "defend":
            available.append(action_id)
            continue
        action = player_actions_for(state, actor_key).get(action_id)
        if action is None:
            continue
        all_targets = action_target_ids(state, action_id, actor_key=actor_key)
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


def _class_resource_update_line(
    state: Combat,
    event: CombatEvent,
    viewer_key: str | None,
) -> str:
    if not event.class_resource_changes or viewer_key not in state.fighters:
        return ""
    actor_key = next(
        (
            key
            for key, fighter in state.fighters.items()
            if fighter.id == (event.actor_entity_id or event.actor)
        ),
        event.actor,
    )
    if (
        actor_key not in state.fighters
        or _fighter_side(state, actor_key) != _fighter_side(state, viewer_key)
    ):
        return ""
    labels = {
        "retaliation": "Retaliação",
        "aim": "Mira",
        "trama": "Trama",
        "omen_offensive": "Presságio Ofensivo",
        "omen_defensive": "Presságio Defensivo",
        "luminar_state": "Fulgor/Julgamento",
    }
    updates: list[str] = []
    for resource, target_id, consumed, remaining in event.class_resource_changes:
        target = _fighter_for_event(state, target_id)
        target_suffix = (
            f" em <b>{escape(target.name)}</b>"
            if target is not None and target.id != event.actor_entity_id
            else ""
        )
        noun = "acúmulo(s)" if resource == "aim" else "instância(s)"
        updates.append(
            f"{labels.get(resource, 'Recurso')}:{target_suffix} "
            f"<code>{consumed}</code> {noun} consumida(s) · "
            f"restam <code>{remaining}</code>"
        )
    return "♻️ " + "; ".join(updates) + "."


def event_line(
    state: Combat,
    event: CombatEvent,
    *,
    viewer_key: str | None = None,
) -> str:
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
            line = f"☣️ <b>{actor_name}</b> sofre <b>{dot}</b>."
        else:
            line = f"✨ <b>{actor_name}</b> age no combate."
        removal = _action_effect_removal_line(state, event)
        return f"{line}{' ' + removal if removal else ''}"
    target = _fighter_for_event(state, event.target) or actor
    target_name = escape(target.name)
    if event.barrier_value:
        duration = (
            action.target_barrier_duration
            if target.id != actor.id and action.target_barrier_duration
            else action.self_barrier_duration
        )
        line = (
            f"🛡️ <b>{actor_name}</b> ergue <b>{escape(action.name)}</b> "
            f"em <b>{target_name}</b>. Barreira · "
            f"<code>{number(event.barrier_value)}</code> · <code>{duration}T</code>."
        )
        update = _class_resource_update_line(state, event, viewer_key)
        return f"{line}{' ' + update if update else ''}"
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
    elif action.target_effects and not action.coefficient:
        line = (
            f"✨ <b>{actor_name}</b> usa <b>{escape(action.name)}</b> "
            f"em <b>{target_name}</b>."
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
        effect_stat = event.applied_effect_stat or action.effect_stat or "attack"
        if event.applied_effect_stat:
            stat_label = {"attack": "ATQ", "defense": "DEF", "agility": "AGI"}.get(
                effect_stat, effect_stat.upper()
            )
            magnitude = event.applied_effect_magnitude
            duration = event.applied_effect_duration
            sign = "+" if event.applied_effect_kind == "buff" else "−"
            line += (
                f" {target_name} recebe {sign}<code>{number(magnitude * 100)}% "
                f"{stat_label}</code> por <code>{duration}T</code>."
            )
        elif action.attack_debuff:
            stat_label = {"attack": "ATQ", "defense": "DEF", "agility": "AGI"}.get(
                effect_stat, effect_stat.upper()
            )
            line += (
                f" {target_name} recebe −<code>{number(action.attack_debuff * 100)}% "
                f"{stat_label}</code> por <code>{action.duration}T</code>."
            )
        else:
            line += f" {target_name} recebe o efeito <b>{escape(event.effect_id)}</b>."
    if event.actor_effect_id:
        stat_label = {"attack": "ATQ", "defense": "DEF", "agility": "AGI"}.get(
            action.self_effect_stat or "attack",
            action.self_effect_stat or "ATQ",
        )
        magnitude = number(action.self_effect_magnitude * 100)
        duration = f"<code>{action.self_effect_duration}T</code>"
        if action.self_effect_kind == "buff":
            line = (
                f"✨ <b>{actor_name}</b> usa <b>{escape(action.name)}</b> e eleva a própria "
                f"{stat_label} em <code>{magnitude}%</code> por {duration}."
            )
        else:
            line += (
                f" <b>{actor_name}</b> reduz a própria {stat_label} em "
                f"<code>{magnitude}%</code> por {duration}."
            )
    if event.barrier_absorbed:
        line += f" Barreira absorve <code>{number(event.barrier_absorbed)}</code>."
    removal = _action_effect_removal_line(state, event)
    if removal:
        line += f" {removal}"
    update = _class_resource_update_line(state, event, viewer_key)
    if update:
        line += f" {update}"
    if (
        "oraculo.pressagio_defensive_criado" in event.path_triggers
        and viewer_key in state.fighters
    ):
        owner_key = next(
            (
                key
                for key, fighter in state.fighters.items()
                if fighter.id == (event.actor_entity_id or event.actor)
            ),
            None,
        )
        target = _fighter_for_event(state, event.target)
        if (
            owner_key is not None
            and target is not None
            and _fighter_side(state, owner_key) == _fighter_side(state, viewer_key)
        ):
            marks = state.fighters[owner_key].path_state.get("omen_defensive", {})
            mark = marks.get(target.id) if isinstance(marks, dict) else None
            if isinstance(mark, dict) and int(mark.get("remaining", 0)) > 0:
                line += (
                    f" 🔮 Presságio Defensivo gerado em <b>{escape(target.name)}</b> "
                    f"· <code>{int(mark['remaining'])}T</code>."
                )
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
    if effect_id.startswith("effect:"):
        return escape(effect_id.removeprefix("effect:"))
    if effect_id:
        return escape(effect_id)
    fallback = "Efeito Negativo" if target_id == "player" else "Efeito Positivo"
    return escape(fallback)


def _action_effect_removal_line(state: Combat, event: CombatEvent) -> str:
    component = event.effect_removal_component
    if component is None:
        return ""
    label = "Purificação" if component == "purification" else "Dispel"
    if event.effect_removal_result == "missed":
        return f"✨ {label} não aplicado: o ataque não atingiu o alvo."
    if not event.removed_effect_ids:
        return f"✨ {label}: nenhum efeito elegível foi removido."
    target = _fighter_for_event(state, event.target)
    target_name = escape(target.name if target is not None else event.target)
    removed = []
    for index, effect_id in enumerate(event.removed_effect_ids):
        kind = (
            event.effect_removal_kinds[index]
            if index < len(event.effect_removal_kinds)
            else event.effect_removal_kind
        )
        if kind == "stack":
            remaining = (
                event.remaining_effect_stacks[index]
                if index < len(event.remaining_effect_stacks)
                else 0
            )
            detail = f"1 acúmulo removido · Restam {remaining}"
        else:
            detail = "Removido"
        removed.append(
            f"<b>{_effect_label(state, effect_id, target_id=event.target)}</b> · {detail}"
        )
    return f"✨ {label} em <b>{target_name}</b>: " + ", ".join(removed) + "."


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


def _has_normal_negative_effect(state: Combat, fighter) -> bool:
    return any(
        effect.kind == "debuff"
        and not effect.fixed_mechanic
        and effect.remaining > 0
        and effect.stacks > 0
        for effect in fighter.effects
    ) or any(
        not dot.fixed_mechanic and dot.remaining > 0 and dot.stacks > 0
        for dot in state.dot_states.get(fighter.id, ())
    )


def _class_mechanic_status_lines(
    state: Combat, fighter_key: str, viewer_key: str
) -> list[str]:
    """Show the viewer's team resources and its own target marks."""
    fighter = state.fighters.get(fighter_key)
    viewer = state.fighters.get(viewer_key)
    if fighter is None or viewer is None:
        return []

    viewer_side = _fighter_side(state, viewer_key)
    fighter_side = _fighter_side(state, fighter_key)
    same_side = fighter_side == viewer_side
    lines: list[str] = []

    if same_side:
        if fighter.character_class == "sentinela" and fighter.retaliation_charges > 0:
            lines.append(
                f"🛡️ Retaliação · <code>{fighter.retaliation_remaining}T</code>"
            )
        trama = fighter.path_state.get("trama_state")
        if (
            fighter.character_class == "tecelao"
            and isinstance(trama, dict)
            and int(trama.get("remaining", 0)) > 0
        ):
            lines.append(f"🪄 Trama · <code>{int(trama['remaining'])}T</code>")
        luminar = fighter.path_state.get("luminar_state")
        if (
            fighter.character_class == "luminar"
            and isinstance(luminar, dict)
            and int(luminar.get("remaining", 0)) > 0
        ):
            kind = luminar.get("kind")
            label = "Fulgor" if kind == "fulgor" else "Julgamento" if kind == "julgamento" else None
            if label:
                icon = "☀️" if kind == "fulgor" else "⚖️"
                lines.append(f"{icon} {label} · <code>{int(luminar['remaining'])}T</code>")

        for owner_key, owner in state.fighters.items():
            if (
                fighter.hp <= 0
                or owner.hp <= 0
                or owner.character_class != "oraculo"
                or _fighter_side(state, owner_key) != viewer_side
            ):
                continue
            marks = owner.path_state.get("omen_defensive", {})
            omen = marks.get(fighter.id) if isinstance(marks, dict) else None
            if isinstance(omen, dict) and int(omen.get("remaining", 0)) > 0:
                lines.append(
                    f"🔮 Presságio Defensivo · <code>{int(omen['remaining'])}T</code>"
                )

    # Internal marks are shown only when a living character on the viewer's
    # side applied them. This keeps an opponent's private class state hidden.
    if not same_side:
        for owner_key, owner in state.fighters.items():
            if owner.hp <= 0 or _fighter_side(state, owner_key) != viewer_side:
                continue
            if owner.character_class == "vigia":
                aim_from = fighter.path_state.get("aim_from", {})
                aim = aim_from.get(owner.id) if isinstance(aim_from, dict) else None
                if isinstance(aim, dict) and int(aim.get("remaining", 0)) > 0:
                    maximum = (
                        4
                        if owner.selected_path == "atirador"
                        else 2
                        if owner.selected_path == "rastreador"
                        else 3
                    )
                    lines.append(
                        f"🎯 Mira · {int(aim.get('stacks', 0))}/{maximum} · "
                        f"<code>{int(aim['remaining'])}T</code>"
                    )
            if owner.character_class == "oraculo":
                for key, label in (
                    ("omen_offensive", "Presságio Ofensivo"),
                    ("omen_defensive", "Presságio Defensivo"),
                ):
                    marks = owner.path_state.get(key, {})
                    omen = marks.get(fighter.id) if isinstance(marks, dict) else None
                    if isinstance(omen, dict) and int(omen.get("remaining", 0)) > 0:
                        lines.append(
                            f"🔮 {label} · <code>{int(omen['remaining'])}T</code>"
                        )
        if (
            any(
                owner.hp > 0
                and owner.character_class == "errante"
                and _fighter_side(state, owner_key) == viewer_side
                for owner_key, owner in state.fighters.items()
            )
            and _has_normal_negative_effect(state, fighter)
        ):
            lines.append("🗡️ Oportunismo · elegível")

    return lines


def _class_resource_label(resource: str, state_kind: str | None = None) -> str:
    if resource == "luminar_state":
        return "Fulgor" if state_kind == "fulgor" else "Julgamento"
    return {
        "retaliation": "Retaliação",
        "aim": "Mira",
        "trama": "Trama",
        "omen_offensive": "Presságio Ofensivo",
        "omen_defensive": "Presságio Defensivo",
    }.get(resource, "Recurso de Classe")


def _class_resource_count_for_ui(
    state: Combat,
    actor_key: str,
    resource: str,
    *,
    target_id: str | None = None,
    state_kind: str | None = None,
) -> int:
    actor = state.fighters[actor_key]
    if resource == "retaliation":
        return int(actor.retaliation_charges > 0 and actor.retaliation_remaining > 0)
    if resource == "trama":
        value = actor.path_state.get("trama_state")
        return (
            int(value.get("remaining", 0))
            if isinstance(value, dict) and int(value.get("remaining", 0)) > 0
            else 0
        )
    if resource == "luminar_state":
        value = actor.path_state.get("luminar_state")
        return int(
            isinstance(value, dict)
            and int(value.get("remaining", 0)) > 0
            and value.get("kind") == state_kind
        )
    if target_id is None:
        return 0
    target = next(
        (fighter for fighter in state.fighters.values() if fighter.id == target_id),
        None,
    )
    if target is None:
        return 0
    if resource == "aim":
        entries = target.path_state.get("aim_from", {})
        value = entries.get(actor.id) if isinstance(entries, dict) else None
        return int(value.get("stacks", 0)) if isinstance(value, dict) else 0
    if resource in {"omen_offensive", "omen_defensive"}:
        entries = actor.path_state.get(resource, {})
        value = entries.get(target.id) if isinstance(entries, dict) else None
        return int(value.get("remaining", 0)) if isinstance(value, dict) else 0
    return 0


def _action_resource_hints(
    state: Combat,
    actor_key: str,
    action_id: str,
    action,
) -> list[str]:
    actor = state.fighters.get(actor_key)
    if actor is None:
        return []
    targets = action_target_ids(state, action_id, actor_key=actor_key)
    hints: list[str] = []
    for use in action.resource_uses:
        label = _class_resource_label(use.resource, use.state_kind)
        if use.target_selector == "actor":
            available = _class_resource_count_for_ui(
                state, actor_key, use.resource, state_kind=use.state_kind
            )
            verb = "Exige" if use.required else "Disponível"
            hints.append(
                f"{verb} {label}: <code>{available}/{max(use.minimum, use.consume)}</code>"
            )
            continue
        candidates = targets if use.target_selector == "each_target" else targets[:4]
        if not candidates:
            hints.append(f"{label}: selecione um alvo elegível")
            continue
        values = []
        for target_id in candidates:
            available = _class_resource_count_for_ui(
                state,
                actor_key,
                use.resource,
                target_id=target_id,
                state_kind=use.state_kind,
            )
            target = next(
                (fighter for fighter in state.fighters.values() if fighter.id == target_id),
                None,
            )
            if target is not None:
                values.append(f"{escape(target.name)} {available}")
        requirement = "Exige" if use.required else "Usa"
        count = max(use.minimum, use.consume)
        if use.target_selector == "primary_target":
            hints.append(
                f"{requirement} {label} <code>{count}</code> no alvo principal "
                f"(disponível: {', '.join(values)})"
            )
        else:
            hints.append(f"{label} por alvo (disponível: {', '.join(values)})")
    for modifier in action.conditional_modifiers:
        condition = modifier.condition
        if condition.kind == "actor_hp_fraction_below":
            description = (
                f"HP próprio abaixo de {number(condition.threshold * 100)}%"
            )
        elif condition.kind == "target_hp_fraction_at_most":
            description = (
                f"alvo com HP até {number(condition.threshold * 100)}%"
            )
        elif condition.kind == "target_has_normal_negative_effect":
            description = "alvo com Debuff comum no início da ação"
        elif condition.kind == "class_resource_at_least":
            if (
                condition.resource == "aim"
                and modifier.component == "crit_bonus"
            ):
                description = (
                    f"alvo com {condition.minimum}+ Miras no início da ação · "
                    f"+{number(modifier.magnitude)} p.p. CRIT"
                )
            else:
                description = (
                    f"{_class_resource_label(condition.resource or '', condition.state_kind)} "
                    f"≥ {condition.minimum}"
                )
        else:
            description = "condição da ação"
        hints.append(f"Bônus condicional · {description}")
    return hints


def _status_lines(
    state: Combat,
    fighter,
    *,
    player: bool = False,
    viewer_key: str = "player",
) -> list[str]:
    name = escape(fighter.name)
    lines: list[str] = []
    if fighter.barrier > 0 and fighter.barrier_remaining != 0:
        icon = "🔰" if player else "🛡️"
        duration = _barrier_duration_summary(fighter)
        lines.append(
            f"{icon} Barreira de {name} · <code>{number(fighter.barrier)}</code> · "
            f"{duration}"
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
    class_lines = _class_mechanic_status_lines(state, fighter.id, viewer_key)
    if class_lines:
        if lines:
            lines.append("")
        lines.extend(class_lines)
    return lines


def _barrier_duration_summary(fighter) -> str:
    durations = [
        "até absorvida" if layer.remaining < 0 else f"{layer.remaining}T"
        for layer in fighter.barriers
    ]
    return f"<code>{' + '.join(durations)}</code>"


def _trial_fighter_card(
    state: Combat, key: str, *, icon: str, viewer_key: str
) -> list[str]:
    fighter = state.fighters[key]
    name = escape(fighter.name)
    lines = [
        f"{icon} <b>{name}</b>",
        f"❤️ <code>{number(fighter.hp)} / {number(fighter.stats.hp)}</code>",
        hp_bar(fighter.hp, fighter.stats.hp),
    ]
    lines.extend(
        _status_lines(
            state,
            fighter,
            player=(_fighter_side(state, key) == _fighter_side(state, viewer_key)),
            viewer_key=viewer_key,
        )
    )
    lines.append("")
    return lines


def render_combat(view: CombatView) -> Screen:
    state = view.combat
    is_trial = view.context == "class_trial"
    is_dungeon = view.context == "dungeon"
    is_pvpve = view.context == "pvpve"
    is_party_combat = is_trial or is_dungeon or state.party_mode
    is_campaign_party = state.party_mode and not is_trial and not is_dungeon
    actor_bound_party = is_campaign_party or view.context == "group_hunt"
    if not is_trial and view.consumable_screen is not None:
        return _render_consumable_selection(view)
    active_key = active_player_key(state)
    requested_actor_key = getattr(view, "combat_actor_key", None)
    action_actor_key = (
        requested_actor_key
        if requested_actor_key == active_key
        else active_key
        if not is_dungeon and not actor_bound_party
        else None
    )
    player_key = active_key or requested_actor_key or "player"
    player = state.fighters.get(player_key, state.fighters.get("player"))
    if player is None:
        return Screen("⚔️ Combate indisponível.", view.context)
    player_actions = player_actions_for(state, action_actor_key or player_key)
    icon = COPY[f"class:{player.character_class}"].split(" ", 1)[0]
    recent = [state.opening_log] + [
        event_line(state, event, viewer_key=player_key) for event in state.events
    ]
    if is_party_combat:
        lines = []
        if is_trial and view.trial_stage_caption:
            lines.extend([f"⚔️ Provação · {escape(view.trial_stage_caption)}", ""])
        elif is_pvpve:
            lines.extend(["⚔️ Confronto PvPvE · Disputa pelo Rastro", ""])
        elif is_dungeon:
            lines.extend([f"⛓️ Masmorra · {escape(view.environment)}", ""])
            if getattr(view, "member_status", None) == "defeated":
                lines.extend(
                    [
                        "💀 Você foi derrotado neste encontro. "
                        "A expedição continua em modo de observação.",
                        "",
                    ]
                )
        lines.extend(
            [
                f"Turno {player.opportunity} · <b>{escape(player.name)}</b>",
                "",
            ]
        )
        viewer_side = _fighter_side(state, player_key) if is_pvpve else "player"
        enemies = sorted(
            (
                key
                for key in state.fighters
                if _fighter_side(state, key) != viewer_side
                and (is_pvpve or _fighter_side(state, key) == "enemy")
                and not state.fighters[key].encounter_hidden
                and state.fighters[key].hp > 0
            ),
            key=lambda key: (state.fighters[key].id, key),
        )
        allies = sorted(
            (
                key
                for key in state.fighters
                if _fighter_side(state, key) == viewer_side
                and (is_pvpve or _fighter_side(state, key) == "player")
            ),
            key=lambda key: (state.fighters[key].id, key),
        )
        for key in enemies:
            prepared_source = _fighter_for_event(state, state.prepared_source)
            marker = (
                f"⚔️ {COPY[f'class:{state.fighters[key].character_class}'].split(' ', 1)[0]}"
                if is_pvpve
                else "☄️"
                if prepared_source is state.fighters[key]
                else ("🐺" if state.fighters[key].takes_turn else "✦")
            )
            lines.extend(
                _trial_fighter_card(state, key, icon=marker, viewer_key=player_key)
            )
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
            fighter_icon = (
                f"👉 {COPY[f'class:{state.fighters[key].character_class}'].split(' ', 1)[0]}"
                if key == active_key
                else "✨"
            )
            lines.extend(
                _trial_fighter_card(state, key, icon=fighter_icon, viewer_key=player_key)
            )
        lines.extend(["📜 Registro de Combate · Recentes", "", "\n".join(recent[-4:]), ""])
    else:
        enemy = state.fighters["enemy"]
        lines = [
            f"Turno {player.opportunity} · <b>{escape(player.name)}</b>",
            "",
            f"<b>🐺 {escape(enemy.name)}</b>",
            f"❤️ <code>{number(enemy.hp)} / {number(enemy.stats.hp)}</code>",
            hp_bar(enemy.hp, enemy.stats.hp),
        ]
        enemy_class_lines = _class_mechanic_status_lines(state, "enemy", player_key)
        if enemy_class_lines:
            lines.extend(enemy_class_lines)
        lines.extend(
            [
                "",
                state.flavor,
                "",
                f"👉 {icon} <b>{escape(player.name)}</b>",
                f"❤️ <code>{number(player.hp)} / {number(player.stats.hp)}</code>",
                hp_bar(player.hp, player.stats.hp),
            ]
        )
        lines.extend(["", "📜 Registro de Combate · Recentes", "", "\n".join(recent[-4:]), ""])
        status_lines: list[str] = []
        if enemy.barrier > 0 and enemy.barrier_remaining != 0:
            duration = _barrier_duration_summary(enemy)
            status_lines.append(
                f"🛡️ Barreira de {escape(enemy.name)} · "
                f"<code>{number(enemy.barrier)}</code> · {duration}"
            )
        if player.barrier > 0 and player.barrier_remaining != 0:
            duration = _barrier_duration_summary(player)
            status_lines.append(
                f"🔰 Barreira · <code>{number(player.barrier)}</code> · "
                f"{duration}"
            )
        if player.ward_charges > 0 and player.ward_remaining > 0:
            status_lines.append(
                f"🛡️ Resguardo · <code>{player.ward_remaining}T</code> · <code>1 Carga</code>"
            )
        for effect in player.effects:
            if effect.kind != "buff" or effect.remaining <= 0:
                continue
            stat = {
                "attack": "ATQ",
                "defense": "DEF",
                "agility": "AGI",
                "perception": "PER",
                "precision": "PRE",
            }.get(effect.stat, effect.stat.upper())
            amount = (
                f"{number(effect.magnitude)} p.p."
                if effect.stat_modifier_mode == "percentage_points"
                else f"{number(effect.magnitude * 100)}%"
            )
            effect_name = (
                "Firmeza" if effect.id == "sentinel.firmeza" else escape(effect.id)
            )
            status_lines.append(
                f"✨ {effect_name} · {stat} +<code>{amount}</code> · "
                f"<code>{effect.remaining}T</code>"
            )
        player_class_lines = _class_mechanic_status_lines(state, player_key, player_key)
        if player_class_lines:
            if status_lines:
                status_lines.append("")
            status_lines.extend(player_class_lines)
        active_art_cooldowns = []
        for action_id, action in player_actions.items():
            if not action_id.startswith(("class_art.", "path_art.")):
                continue
            remaining = max(
                0,
                player.cooldowns.get(action_id, 0) - player.opportunity,
            )
            if remaining:
                active_art_cooldowns.append(
                    f"⏳ {escape(action.name)} · CD<code>{remaining}</code>"
                )
        if active_art_cooldowns:
            if status_lines:
                status_lines.append("")
            status_lines.extend(active_art_cooldowns)
        if status_lines:
            insert_at = lines.index("📜 Registro de Combate · Recentes")
            lines[insert_at:insert_at] = status_lines
        if view.consumable_notice:
            lines[8:8] = [escape(view.consumable_notice), ""]

    available = (
        class_trial_action_ids(state, actor_key=action_actor_key)
        if is_party_combat and action_actor_key is not None
        else allowed_actions(state, action_actor_key)
        if action_actor_key is not None
        else ()
    )
    buttons = []
    target_button_rows = []
    for action in available:
        if action == "attack":
            label, hint = "Atacar", "⚔️ Atacar · Causa Dano"
        elif action == "defend":
            label, hint = "Defender", "🛡️ Defender · Reduz Dano até seu próximo Turno"
        else:
            art = player_actions[action]
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
            if action not in {"attack", "defend"}:
                lines.extend(
                    _action_resource_hints(
                        state, player_key, action, player_actions[action]
                    )
                )
        if is_trial:
            action_ids = class_trial_action_ids(state, actor_key=action_actor_key)
            action_index = action_ids.index(action)
            targets = class_trial_target_ids(state, action, actor_key=action_actor_key)
            target_code = "s" if len(targets) > 1 else "d0" if len(targets) == 1 else "x"
            callback = ClassTrialActionCallback.for_intent(
                view.activity_id, state.version, action_index, target_code
            ).pack()
        elif is_dungeon:
            action_ids = class_trial_action_ids(state, actor_key=action_actor_key)
            action_index = action_ids.index(action)
            definition = player_actions.get(action)
            targets = (
                ()
                if definition is None
                or definition.target_mode in {"self", "all_opponents", "all_allies"}
                else action_target_ids(state, action, actor_key=action_actor_key or "player")
            )
            target_code = "s" if len(targets) > 1 else "d0" if targets else "x"
            callback = DungeonCombatCallback.for_intent(
                view.run_id, view.activity_id, state.version, action_index, target_code
            ).pack()
        elif is_campaign_party:
            action_ids = class_trial_action_ids(state, actor_key=action_actor_key)
            action_index = action_ids.index(action)
            definition = player_actions.get(action)
            targets = (
                ()
                if definition is None
                or definition.target_mode in {"self", "all_opponents", "all_allies"}
                else action_target_ids(state, action, actor_key=action_actor_key or "player")
            )
            if len(targets) > 1:
                for target_index, target_id in enumerate(targets):
                    target = next(
                        (
                            fighter
                            for fighter in state.fighters.values()
                            if fighter.id == target_id
                        ),
                        None,
                    )
                    target_name = target.name if target is not None else "Oponente"
                    target_button_rows.append(
                        [
                            InlineKeyboardButton(
                                text=f"{label} · {target_name[:16]}",
                                callback_data=CampaignCombatCallback.for_intent(
                                    view.activity_id,
                                    state.version,
                                    action_index,
                                    f"d{target_index}",
                                ).pack(),
                            )
                        ]
                    )
                continue
            target_code = "s" if len(targets) > 1 else "d0" if targets else "x"
            callback = CampaignCombatCallback.for_intent(
                view.activity_id, state.version, action_index, target_code
            ).pack()
        else:
            callback_action = action
            if action.startswith(("class_art.", "path_art.")) and isinstance(
                state.configuration_snapshot, dict
            ):
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
                else P5CombatCallback
                if view.context == "p5"
                else S6CombatCallback
                if view.context == "s6"
                else P6CombatCallback
                if view.context == "p6"
                else S4CombatCallback
                if view.context == "s4"
                else S5CombatCallback
                if view.context == "s5"
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
            art = player_actions.get("art")
            if art is not None:
                lines.append(f"{art.name} · CD{remaining}")
    if state.result == "victory" and view.context == "prologue":
        lines.append("320 XP")
    keyboard_rows = [buttons] if buttons else []
    keyboard_rows.extend(target_button_rows)
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
