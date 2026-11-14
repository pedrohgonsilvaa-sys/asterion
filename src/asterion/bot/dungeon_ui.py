"""Player-facing navigation for known dungeons and the Cripta solo run."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.dungeons import DungeonView
from asterion.bot.asset_catalog import with_dungeon_art
from asterion.bot.combat_ui import (
    DungeonCombatCallback,
    class_trial_action_ids,
    render_combat,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.combat import action_target_ids


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _render_dungeons(view: DungeonView) -> Screen:
    if view.kind == "known":
        rows = []
        details = []
        for family_id, name, level_range, location, region in view.known_dungeons:
            callback = {
                "dungeon.tdo.cripta_ocaso": "dungeon:crypt",
                "dungeon.tdo.galerias_vigia": "dungeon:galleries",
                "dungeon.vde.fosso_raizes": "dungeon:fosso",
                "dungeon.vde.santuario_no_antigo": "dungeon:sanctuary",
                "dungeon.nareth.galerias_meridiano": "dungeon:nareth-galleries",
                "dungeon.nareth.observatorio_afundado": "dungeon:nareth-observatory",
                "dungeon.varzeas.enfermaria_afundada": "dungeon:varzeas-infirmary",
                "dungeon.varzeas.cisterna_transferencia": "dungeon:varzeas-cistern",
                "dungeon.altos.pedreira_contrapeso": "dungeon:altos-pedreira",
                "dungeon.altos.bastilha_profunda": "dungeon:altos-bastilha",
                "dungeon.confins.arquivo_retorno": "dungeon:confins-arquivo",
                "dungeon.confins.camara_contradicoes": "dungeon:confins-contradicoes",
            }.get(family_id, "dungeon:known")
            rows.append([_button(f"{name} · {level_range}", callback)])
            details.append(f"{name} · {level_range}\n{region} · {location}")
        text = "⛓️ Masmorras Conhecidas\n\n" + "\n\n".join(details)
        rows.append([_button("← Aventura", "adv:hub")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
        return Screen(text, "dungeon_crypt", keyboard)
    if view.kind in {"empty", "hidden"}:
        return Screen(
            "⛓️ Masmorras Conhecidas\n\nNenhuma Masmorra conhecida.",
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Aventura", "adv:hub")]]),
        )
    if view.kind == "detail":
        text = (
            f"⛓️ {view.dungeon_name} · {view.range_label}\n"
            f"{view.region_display} · {view.entry_display}\n\n"
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
        family_key = {
            "dungeon.tdo.cripta_ocaso": "c",
            "dungeon.tdo.galerias_vigia": "g",
            "dungeon.vde.fosso_raizes": "f",
            "dungeon.vde.santuario_no_antigo": "s",
            "dungeon.nareth.galerias_meridiano": "n",
            "dungeon.nareth.observatorio_afundado": "o",
            "dungeon.varzeas.enfermaria_afundada": "i",
            "dungeon.varzeas.cisterna_transferencia": "t",
            "dungeon.altos.pedreira_contrapeso": "p",
            "dungeon.altos.bastilha_profunda": "b",
            "dungeon.confins.arquivo_retorno": "a",
            "dungeon.confins.camara_contradicoes": "v",
        }.get(view.family_id)
        if family_key is None:
            return Screen(
                "⛓️ Masmorra indisponível\n\nEsta Masmorra não está disponível.",
                "dungeon_crypt",
                InlineKeyboardMarkup(
                    inline_keyboard=[[_button("← Masmorras", "dungeon:known")]]
                ),
            )
        if stable_gate == "available":
            rows.append(
                [
                    _button("🟢 Estável · Solo", f"dungeon:start:{family_key}:s"),
                    _button("👥 Grupo", f"dungeon:group:{family_key}:s"),
                    _button("🔎 Pareamento", f"dungeon:queue:{family_key}:s"),
                ]
            )
        else:
            rows.append(
                [
                    _button(
                        f"🔒 Estável · Requer Nv.{view.minimum_level}", "dungeon:noop"
                    )
                ]
            )
        if fractured_gate == "available":
            rows.append(
                [
                    _button("🟠 Fraturada · Solo", f"dungeon:start:{family_key}:f"),
                    _button("👥 Grupo", f"dungeon:group:{family_key}:f"),
                    _button("🔎 Pareamento", f"dungeon:queue:{family_key}:f"),
                ]
            )
        else:
            reason = (
                f"Requer Nv.{view.minimum_level}"
                if fractured_gate == "level"
                else "Concluir Estável"
            )
            rows.append([_button(f"🔒 Fraturada · {reason}", "dungeon:noop")])
        if rupture_gate == "available":
            rows.append(
                [
                    _button("🔴 Ruptura · Solo", f"dungeon:start:{family_key}:r"),
                    _button("👥 Grupo", f"dungeon:group:{family_key}:r"),
                    _button("🔎 Pareamento", f"dungeon:queue:{family_key}:r"),
                ]
            )
        elif rupture_gate == "first_fractured":
            rows.append([_button("🔒 Ruptura · Concluir Fraturada", "dungeon:noop")])
        else:
            rows.append([_button("🔒 Ruptura · Nv.60", "dungeon:noop")])
        rows.append([_button("← Masmorras", "dungeon:known")])
        return Screen(text, "dungeon_crypt", InlineKeyboardMarkup(inline_keyboard=rows))
    if view.kind == "invite":
        text = (
            f"👥 Convite de Masmorra\n{escape(view.dungeon_name)} · "
            f"{escape(view.difficulty_label or '')}\n\n"
            "Aceitar este convite entra no grupo; o Vigor só será reservado "
            "depois da confirmação de entrada de todos."
        )
        callback_id = view.invite_id.hex if view.invite_id else ""
        rows = [
            [
                _button("Aceitar", f"dungeon:inv:{callback_id}:y"),
                _button("Recusar", f"dungeon:inv:{callback_id}:n"),
            ]
        ]
        return Screen(text, "dungeon_lobby", InlineKeyboardMarkup(inline_keyboard=rows))
    if view.kind in {"lobby", "queue", "confirming", "invite_declined", "cancelled"}:
        state_lines = [
            f"{index}. {escape(name)} · Nv.{level} · ❤️ {hp}/{max_hp} · "
            f"⚡ {vigor} · {escape(status_label)}"
            for index, (name, level, hp, max_hp, vigor, status) in enumerate(
                view.party_members, start=1
            )
            for status_label in ({
                "joined": "No grupo",
                "queued": "Na fila",
                "matched": "Aguardando",
                "confirmed": "Confirmado",
                "invited": "Convidado",
                "left": "Saiu",
            }.get(status, status),)
        ]
        head = (
            "🔎 Pareamento · Procurando · Grupo 2–4"
            if view.kind == "queue"
            else "👥 Confirmação de Entrada"
            if view.kind == "confirming"
            else "👥 Grupo"
        )
        text = (
            f"{head}\n{escape(view.dungeon_name)} · "
            f"{escape(view.difficulty_label or '')}\n\n"
            f"Grupo · {len(view.party_members)}/4\n"
            + "\n".join(state_lines)
        )
        if view.reason and view.reason.startswith("invited:"):
            text += f"\n\n✅ Convite enviado para {escape(view.reason.removeprefix('invited:'))}."
        elif view.reason == "use_command":
            text += "\n\nConvide por nome exato enviando:\n/dungeon_invite Nome do Personagem"
        rows = []
        if view.kind == "confirming" and view.lobby_id:
            rows.append(
                [
                    _button(
                        "Confirmar Entrada",
                        f"dungeon:conf:{view.lobby_id.hex}:{view.lobby_version}:y",
                    ),
                    _button(
                        "Recusar",
                        f"dungeon:conf:{view.lobby_id.hex}:{view.lobby_version}:n",
                    ),
                ]
            )
        elif view.kind == "lobby" and view.lobby_id:
            if view.lobby_leader:
                text += "\n\nConvide por nome exato:\n/dungeon_invite Nome do Personagem"
                if 2 <= len(view.party_members) <= 4:
                    rows.append(
                        [
                            _button(
                                "Confirmar Grupo",
                                f"dungeon:ready:{view.lobby_id.hex}:{view.lobby_version}",
                            )
                        ]
                    )
            rows.append(
                [
                    _button(
                        "Sair do Grupo",
                        f"dungeon:cancel:{view.lobby_id.hex}:{view.lobby_version}",
                    )
                ]
            )
        elif view.kind == "queue" and view.lobby_id:
            if view.lobby_leader and 2 <= len(view.party_members) <= 4:
                rows.append(
                    [
                        _button(
                            "Confirmar Grupo",
                            f"dungeon:ready:{view.lobby_id.hex}:{view.lobby_version}",
                        )
                    ]
                )
            rows.append(
                [
                    _button(
                        "Cancelar Pareamento",
                        f"dungeon:cancel:{view.lobby_id.hex}:{view.lobby_version}",
                    )
                ]
            )
        if view.kind in {"invite_declined", "cancelled"}:
            text += "\n\nA formação foi encerrada. Nenhum Vigor foi reservado."
        rows.append([_button("← Masmorras", "dungeon:known")])
        return Screen(text, "dungeon_lobby", InlineKeyboardMarkup(inline_keyboard=rows))
    if view.kind == "abandon_pending":
        text = (
            f"⛓️ {escape(view.dungeon_name)} · {escape(view.difficulty_label or '')}\n\n"
            "Desistência registrada. A run será encerrada quando todos os membros "
            "ativos confirmarem pelo próprio menu."
        )
        return Screen(
            text,
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Masmorras", "dungeon:known")]]),
        )
    if view.kind == "spectating":
        text = (
            f"⛓️ {escape(view.dungeon_name)} · {escape(view.difficulty_label or '')}\n\n"
            f"{escape(view.environment)}\n"
            "💀 Você foi derrotado neste trecho e permanece fora dos encontros "
            "seguintes até o Braseiro do grupo. Você ainda pode acompanhar a expedição."
        )
        return Screen(
            text,
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Masmorras", "dungeon:known")]]),
        )
    if view.kind == "combat" and view.combat is not None:
        return render_combat(view)
    title = f"⛓️ {escape(view.dungeon_name)} · {escape(view.difficulty_label or '')}"
    brazier_label = view.brazier_label
    if view.kind == "brazier":
        text = (
            f"{title}\n\n🔥 {brazier_label}\n"
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
            f"🔥 {brazier_label} · Checkpoint no Encontro {view.ordinal}"
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
            f"⛓️ {escape(view.dungeon_name)} · {escape(view.difficulty_label or '')}\n\n"
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
            f"💀 Masmorra · Falhada\n{escape(view.dungeon_name)}\n\n"
            "O Vigor reservado foi devolvido. Consumíveis usados permanecem consumidos."
        )
        return Screen(
            text,
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Masmorras", "dungeon:known")]]),
        )
    if view.kind == "expired":
        text = (
            f"⌛ Masmorra · Expirada\n{escape(view.dungeon_name)}\n\n"
            "O Vigor reservado foi devolvido."
        )
        return Screen(
            text,
            "dungeon_crypt",
            InlineKeyboardMarkup(inline_keyboard=[[_button("← Masmorras", "dungeon:known")]]),
        )
    if view.kind == "completed":
        rewards = "\n".join(escape(line) for line in view.reward_lines)
        text = (
            f"🏆 Masmorra · Concluída\n{escape(view.dungeon_name)} · "
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
            f"⛓️ {escape(view.dungeon_name)} · {escape(view.difficulty_label or '')}\n\n"
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
    text = f"⛓️ {escape(view.dungeon_name)}\n\nA execução atual não está disponível."
    return Screen(
        text,
        "dungeon_crypt",
        InlineKeyboardMarkup(inline_keyboard=[[_button("← Aventura", "adv:hub")]]),
    )


def render_dungeon_targets(view: DungeonView, action_index: int) -> Screen:
    state = view.combat
    actor_key = view.combat_actor_key
    actions = class_trial_action_ids(state, actor_key=actor_key)
    if not 0 <= action_index < len(actions):
        return render_combat(view)
    action_id = actions[action_index]
    targets = action_target_ids(state, action_id, actor_key=actor_key or "player")
    if not targets:
        return render_combat(view)
    # action_target_ids returns canonical entity IDs (fighter.id), while
    # Combat.fighters is keyed by internal resolver keys such as "spider".
    # Keep those identities distinct: multiple instances of one creature must
    # remain individually selectable by the callback's versioned target index.
    fighters_by_id = {fighter.id: fighter for fighter in state.fighters.values()}
    target_fighters = [fighters_by_id.get(target_id) for target_id in targets]
    if (
        len(fighters_by_id) != len(state.fighters)
        or len(set(targets)) != len(targets)
        or any(fighter is None or fighter.hp <= 0 for fighter in target_fighters)
    ):
        return Screen(
            "🎯 A lista de alvos ficou indisponível. Atualize o combate antes de escolher.",
            "dungeon",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        _button(
                            "← Combate",
                            DungeonCombatCallback.for_intent(
                                view.run_id,
                                view.activity_id,
                                state.version,
                                action_index,
                                "b",
                            ).pack(),
                        )
                    ]
                ]
            ),
        )
    rows = []
    for index, fighter in enumerate(target_fighters):
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
        f"{index + 1} · {fighter.name}"
        for index, fighter in enumerate(target_fighters)
    )
    return Screen(
        text,
        "dungeon",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


def render_dungeons(view: DungeonView) -> Screen:
    """Dungeon screen with the art of its family (see asset_catalog)."""
    return with_dungeon_art(_render_dungeons(view), view.family_id)
