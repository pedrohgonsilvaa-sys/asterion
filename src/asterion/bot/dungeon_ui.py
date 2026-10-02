"""Player-facing navigation for known dungeons and the Cripta solo run."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.dungeons import DungeonView
from asterion.bot.combat_ui import (
    DungeonCombatCallback,
    class_trial_action_ids,
    render_combat,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.combat import action_target_ids


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def render_dungeons(view: DungeonView) -> Screen:
    if view.kind == "known":
        text = (
            "⛓️ Masmorras Conhecidas\n\nCripta do Ocaso · Nv.4–7\n"
            "Terras do Ocaso · Charneca da Fuligem"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [_button("Cripta do Ocaso", "dungeon:crypt")],
                [_button("← Aventura", "world:adventure")],
            ]
        )
        return Screen(text, "dungeon_crypt", keyboard)
    if view.kind in {"empty", "hidden"}:
        return Screen(
            "⛓️ Masmorras Conhecidas\n\nNenhuma Masmorra conhecida.",
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Aventura", "world:adventure")]]),
        )
    if view.kind == "detail":
        text = (
            "⛓️ Cripta do Ocaso · Nv.4–7\n"
            "Terras do Ocaso · Charneca da Fuligem\n\n"
            f"{escape(view.character_name)} · Nv.{view.level}\n"
            f"❤️ HP · {view.hp} / {view.max_hp}\n"
            f"⚡ Vigor · {view.vigor} / {view.max_vigor}"
        )
        if view.reason == "vigor":
            text += "\n\n🔒 Vigor · Insuficiente"
        elif view.reason == "foreground":
            text += "\n\n🔒 Atividade · Conclua o primeiro plano atual"
        stable_gate = dict(view.difficulty_gates).get("stable", "level")
        fractured_gate = dict(view.difficulty_gates).get("fractured", "first_stable")
        rupture_gate = dict(view.difficulty_gates).get("rupture", "level")
        rows = []
        if stable_gate == "available":
            rows.append([_button("🟢 Estável · Solo", "dungeon:start:s")])
        else:
            rows.append([_button("🔒 Estável · Requer Nv.4", "dungeon:noop")])
        if fractured_gate == "available":
            rows.append([_button("🟠 Fraturada · Solo", "dungeon:start:f")])
        else:
            reason = "Requer Nv.4" if fractured_gate == "level" else "Concluir Estável"
            rows.append([_button(f"🔒 Fraturada · {reason}", "dungeon:noop")])
        if rupture_gate == "available":
            rows.append([_button("🔒 Ruptura · Indisponível nesta etapa", "dungeon:noop")])
        elif rupture_gate == "first_fractured":
            rows.append([_button("🔒 Ruptura · Concluir Fraturada", "dungeon:noop")])
        else:
            rows.append([_button("🔒 Ruptura · Nv.60", "dungeon:noop")])
        rows.append([_button("← Masmorras", "dungeon:known")])
        return Screen(text, "dungeon_crypt", InlineKeyboardMarkup(inline_keyboard=rows))
    if view.kind == "combat" and view.combat is not None:
        return render_combat(view)
    title = f"⛓️ Cripta do Ocaso · {escape(view.difficulty_label or '')}"
    if view.kind == "brazier":
        text = (
            f"{title}\n\n🔥 Braseiro do Silêncio\n"
            "Uma pausa segura marca o início do próximo trecho."
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    _button(
                        "🔥 Ativar Braseiro", f"dungeon:b:{view.run_id.hex}:{view.state_version}"
                    )
                ],
                [_button("← Masmorras", "dungeon:known")],
            ]
        )
        return Screen(text, "dungeon_crypt", keyboard)
    if view.kind == "retry":
        text = (
            f"{title}\n\n💀 Encontro · Tentativa Encerrada\n"
            f"🔥 Braseiro do Silêncio · Checkpoint no Encontro {view.ordinal}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    _button(
                        "↻ Tentar Novamente", f"dungeon:r:{view.run_id.hex}:{view.state_version}"
                    )
                ],
                [
                    _button(
                        "Abandonar Masmorra",
                        f"dungeon:confirm:{view.run_id.hex}:{view.state_version}",
                    )
                ],
            ]
        )
        return Screen(text, "dungeon_crypt", keyboard)
    if view.kind == "ready":
        text = (
            f"⛓️ Cripta do Ocaso · {escape(view.difficulty_label or '')}\n\n"
            f"{escape(view.character_name)} · Nv.{view.level}\n"
            f"❤️ HP · {view.hp} / {view.max_hp}\n"
            f"⚡ Vigor · {view.vigor} / {view.max_vigor}\n\n"
            f"{escape(view.environment)}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    _button(
                        "⚔️ Entrar no Encontro", f"dungeon:e:{view.run_id.hex}:{view.state_version}"
                    )
                ],
                [
                    _button(
                        "Abandonar Masmorra",
                        f"dungeon:confirm:{view.run_id.hex}:{view.state_version}",
                    )
                ],
            ]
        )
        return Screen(text, "dungeon_crypt", keyboard)
    if view.kind == "failed":
        text = (
            "💀 Masmorra · Falhada\nCripta do Ocaso\n\n"
            "O Vigor reservado foi devolvido. Consumíveis usados permanecem consumidos."
        )
        return Screen(
            text,
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Masmorras", "dungeon:known")]]),
        )
    if view.kind == "expired":
        text = "⌛ Masmorra · Expirada\nCripta do Ocaso\n\nO Vigor reservado foi devolvido."
        return Screen(
            text,
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Masmorras", "dungeon:known")]]),
        )
    if view.kind == "completed":
        rewards = "\n".join(escape(line) for line in view.reward_lines)
        text = (
            f"🏆 Masmorra · Concluída\nCripta do Ocaso · "
            f"{escape(view.difficulty_label or '')}\n\n{rewards}"
        )
        if view.first_clear:
            text += "\n\n✨ Primeira Conclusão"
        return Screen(
            text,
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Masmorras", "dungeon:known")]]),
        )
    if view.kind == "confirm_abandon":
        text = (
            f"⛓️ Cripta do Ocaso · {escape(view.difficulty_label or '')}\n\n"
            "Abandonar esta Masmorra? O Vigor reservado será devolvido; "
            "consumíveis usados não voltam."
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [_button("Abandonar", f"dungeon:a:{view.run_id.hex}:{view.state_version}")],
                [_button("← Continuar", f"dungeon:back:{view.run_id.hex}:{view.state_version}")],
            ]
        )
        return Screen(text, "dungeon_crypt", keyboard)
    text = "⛓️ Cripta do Ocaso\n\nA execução atual não está disponível."
    return Screen(
        text,
        "dungeon_crypt",
        InlineKeyboardMarkup(inline_keyboard=[[_button("← Aventura", "world:adventure")]]),
    )


def render_dungeon_targets(view: DungeonView, action_index: int) -> Screen:
    state = view.combat
    actions = class_trial_action_ids(state)
    if not 0 <= action_index < len(actions):
        return render_combat(view)
    action_id = actions[action_index]
    targets = action_target_ids(state, action_id)
    if not targets:
        return render_combat(view)
    rows = []
    for index, key in enumerate(targets):
        fighter = state.fighters[key]
        callback = DungeonCombatCallback.for_intent(
            view.run_id, view.activity_id, state.version, action_index, f"d{index:x}"
        ).pack()
        rows.append([_button(f"{index + 1} · {fighter.name}", callback)])
    rows.append(
        [
            _button(
                "← Combate",
                DungeonCombatCallback.for_intent(
                    view.run_id, view.activity_id, state.version, action_index, "b"
                ).pack(),
            )
        ]
    )
    text = "🎯 Escolha o Alvo\n\n" + "\n".join(
        f"{index + 1} · {state.fighters[key].name}" for index, key in enumerate(targets)
    )
    return Screen(
        text,
        "dungeon",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
