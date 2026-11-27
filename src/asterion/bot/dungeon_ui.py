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
from asterion.bot.ui_format import (
    back,
    blocks,
    button,
    column,
    field,
    narrative,
    pairs,
    reward_html,
    rewards,
)
from asterion.bot.ui_format import (
    keyboard as _kb,
)
from asterion.domain.combat import action_target_ids
from asterion.domain.dungeons import DIFFICULTIES


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


FAMILY_CALLBACKS = {
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
}
FAMILY_KEYS = {
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
}
FAMILY_BY_KEY = {key: family for family, key in FAMILY_KEYS.items()}
FAMILY_EMOJI = {"dungeon.tdo.cripta_ocaso": "🏚️", "dungeon.tdo.galerias_vigia": "🏛️"}
DIFFICULTY_BUTTONS = {
    "s": ("stable", "🟢 Estável"),
    "f": ("fractured", "🟠 Fraturada"),
    "r": ("rupture", "🔴 Ruptura"),
}
# Toda Masmorra tem cinco encontros, o quinto é o Chefe (DungeonService, ordinal 5).
DUNGEON_ENCOUNTERS = 5
RUPTURE_LEVEL = 60
ORDINAL_NAMES = {1: "Primeiro", 2: "Segundo", 3: "Terceiro", 4: "Quarto"}
DUNGEONS_TEXT = (
    "Alguns caminhos não terminam nas estradas abertas. Entre ruínas esquecidas, passagens "
    "ocultas e estruturas consumidas pelo tempo, existem lugares onde os perigos das Terras "
    "do Ocaso se aprofundam."
)
# Nomes curtos só nos botões de seleção; a tela individual usa o nome completo da Masmorra.
SHORT_BUTTON_NAMES = {
    "dungeon.tdo.cripta_ocaso": "Cripta",
    "dungeon.tdo.galerias_vigia": "Galerias",
}
DUNGEON_INTRO_TEXT = (
    "Uma passagem esquecida conduz para além das trilhas conhecidas. O ar muda à medida que "
    "avança. As paredes guardam marcas de quem esteve aqui antes — e nem todas parecem ter "
    "partido."
)
INTRO_FAMILIES = frozenset(SHORT_BUTTON_NAMES)
ENTER_CALLBACK_PREFIX = "dungeon:enter:"


def _emoji(family_id: str) -> str:
    return FAMILY_EMOJI.get(family_id, "🗝️")


def _dungeon_title(view: DungeonView) -> str:
    return f"{_emoji(view.family_id)} <b>{escape(view.dungeon_name)}</b>"


def _gate_reason(view: DungeonView, suffix: str) -> str | None:
    """None when the difficulty is open; otherwise the lock text the service implies."""
    difficulty = DIFFICULTY_BUTTONS[suffix][0]
    gate = dict(view.difficulty_gates).get(
        difficulty, {"stable": "level", "fractured": "first_stable", "rupture": "level"}[
            difficulty
        ]
    )
    if gate == "available":
        return None
    if difficulty == "fractured":
        return f"Requer Nv.{view.minimum_level}" if gate == "level" else "Concluir Estável"
    if difficulty == "rupture":
        return "Concluir Fraturada" if gate == "first_fractured" else f"Nv.{RUPTURE_LEVEL}"
    return f"Requer Nv.{view.minimum_level}"


def _notice(view: DungeonView) -> str | None:
    if view.reason == "vigor":
        return "🔒 Vigor · Insuficiente"
    if view.reason == "foreground":
        return "🔒 Atividade · Conclua o primeiro plano atual"
    return None


def render_dungeon_difficulty(view: DungeonView, suffix: str) -> Screen:
    """Detalhes de uma dificuldade (Bloco UI 1 §5): Nível, Encontros e Vigor canônicos."""
    key = FAMILY_KEYS.get(view.family_id)
    if view.kind != "detail" or key is None or suffix not in DIFFICULTY_BUTTONS:
        return _render_dungeons(view)
    difficulty = DIFFICULTIES[DIFFICULTY_BUTTONS[suffix][0]]
    level = RUPTURE_LEVEL if suffix == "r" else view.minimum_level
    text = blocks(
        _dungeon_title(view),
        narrative(
            f"Uma incursão pela {view.dungeon_name} avança por cinco encontros até "
            "alcançar seu Chefe final."
        ),
        "\n".join(
            (
                field("⭐", "Nível", str(level)),
                field("⚔️", "Encontros", str(DUNGEON_ENCOUNTERS)),
                field("⚡", "Vigor", str(difficulty.vigor)),
            )
        ),
        _notice(view),
    )
    locked = _gate_reason(view, suffix)
    if locked is None:
        rows = [
            [button("🗝️ Iniciar Masmorra", f"dungeon:start:{key}:{suffix}")],
            [
                button("👥 Grupo", f"dungeon:group:{key}:{suffix}"),
                button("🔎 Pareamento", f"dungeon:queue:{key}:{suffix}"),
            ],
        ]
    else:
        rows = [[button(f"🔒 {locked}", "dungeon:noop")]]
    back_to = FAMILY_CALLBACKS.get(view.family_id, "dungeon:known")
    return Screen(text, "dungeon_crypt", _kb(*rows, back(back_to)), "HTML")


def _render_dungeons(view: DungeonView, *, difficulties: bool = False) -> Screen:
    if view.kind == "known":
        options = [
            button(
                f"{_emoji(family_id)} {SHORT_BUTTON_NAMES.get(family_id, name)}",
                FAMILY_CALLBACKS.get(family_id, "dungeon:known"),
            )
            for family_id, name, *_ in view.known_dungeons
        ]
        text = blocks("🗝️ <b>Masmorras</b>", narrative(DUNGEONS_TEXT))
        return Screen(
            text, "dungeon_crypt", _kb(*pairs(options), back("adv:hub")), "HTML"
        )
    if view.kind in {"empty", "hidden"}:
        return Screen(
            blocks("🗝️ <b>Masmorras</b>", "Nenhuma Masmorra conhecida."),
            "dungeon_crypt",
            _kb(back("menu:back")),
            "HTML",
        )
    if view.kind == "detail":
        key = FAMILY_KEYS.get(view.family_id)
        if key is None:
            return Screen(
                "⛓️ Masmorra indisponível\n\nEsta Masmorra não está disponível.",
                "dungeon_crypt",
                InlineKeyboardMarkup(
                    inline_keyboard=[[_button("↩️ Retornar", "dungeon:known")]]
                ),
            )
        if view.family_id in INTRO_FAMILIES and not difficulties:
            # Tela individual aprovada (§1.8/§1.9): nome completo e emoji próprios, resolvidos
            # da Masmorra selecionada; ⚔️ Entrar abre a escolha de dificuldade.
            return Screen(
                blocks(_dungeon_title(view), narrative(DUNGEON_INTRO_TEXT), _notice(view)),
                "dungeon_crypt",
                _kb([button("⚔️ Entrar", f"{ENTER_CALLBACK_PREFIX}{key}")], back("dungeon:known")),
                "HTML",
            )
        text = blocks(
            _dungeon_title(view),
            narrative(
                f"Uma incursão pela {view.dungeon_name} avança por cinco encontros até "
                "alcançar o confronto final. A dificuldade escolhida determina os perigos, o "
                "custo de Vigor e as condições da incursão."
            ),
            _notice(view),
        )
        options = [
            button(label, f"dungeon:d:{key}:{suffix}")
            for suffix, (_, label) in DIFFICULTY_BUTTONS.items()
        ]
        return Screen(
            text,
            "dungeon_crypt",
            _kb(
                *column(*options),
                back(
                    FAMILY_CALLBACKS[view.family_id]
                    if view.family_id in INTRO_FAMILIES
                    else "dungeon:known"
                ),
            ),
            "HTML",
        )
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
    run = f"{view.run_id.hex}:{view.state_version}" if view.run_id is not None else ""
    abandon = [_button("Abandonar Masmorra", f"dungeon:confirm:{run}")]
    if view.kind == "brazier":
        text = blocks(
            "🔥 <b>Braseiro da Masmorra</b>",
            narrative(
                "O fogo permanece aceso entre as pedras e oferece um ponto seguro dentro da "
                "incursão."
            ),
        )
        return Screen(
            text,
            "dungeon_crypt",
            _kb([button("🔥 Descansar", f"dungeon:b:{run}")], back("dungeon:known")),
            "HTML",
        )
    if view.kind == "retry":
        # Derrota com Braseiro ativo: a incursão continua no mesmo run_id.
        text = blocks(
            "💀 <b>Derrota</b>",
            narrative(
                "O personagem cai durante o confronto e deixa de participar dos combates "
                "seguintes até alcançar uma condição válida de recuperação."
            ),
            narrative(
                f"O grupo retorna ao último Braseiro ativo, no Encontro {view.ordinal}. Os "
                "personagens derrotados são recuperados e a incursão continua."
            ),
        )
        return Screen(
            text,
            "dungeon_crypt",
            _kb([button("🔄 Retornar ao Braseiro", f"dungeon:r:{run}")], abandon),
            "HTML",
        )
    if view.kind == "ready":
        enter = f"dungeon:e:{run}"
        counter = f"⚔️ <b>Encontro {view.ordinal} / {DUNGEON_ENCOUNTERS}</b>"
        if view.ordinal >= DUNGEON_ENCOUNTERS:
            parts = (
                "👑 <b>Chefe</b>",
                narrative(
                    "O último confronto da incursão aguarda adiante. A derrota do Chefe "
                    "encerra a masmorra e consolida a conclusão válida da run."
                ),
                counter,
            )
            label = "⚔️ Enfrentar"
        elif view.ordinal <= 1:
            parts = (
                _dungeon_title(view),
                narrative(
                    "As portas se fecham atrás do grupo. O primeiro encontro aguarda adiante "
                    "e a incursão começa."
                ),
                counter,
            )
            label = "⚔️ Avançar"
        else:
            # Molde "Encontro": a mesma tela abre depois de um retorno ao Braseiro, e
            # o serviço não entrega recompensa por encontro (só na conclusão).
            parts = (
                f"⚔️ <b>{ORDINAL_NAMES.get(view.ordinal, str(view.ordinal))} Encontro</b>",
                narrative(
                    "O caminho termina diante da próxima ameaça da incursão. O confronto "
                    "começa enquanto o restante da masmorra permanece adiante."
                ),
                counter,
            )
            label = "⚔️ Combater"
        return Screen(
            blocks(*parts), "dungeon_crypt", _kb([button(label, enter)], abandon), "HTML"
        )
    if view.kind == "failed":
        text = blocks(
            "💀 <b>Masmorra Falhada</b>",
            narrative(
                "Todos os participantes foram derrotados antes que um Braseiro válido "
                "estivesse disponível. A incursão chega ao fim."
            ),
            narrative(
                "O Vigor reservado é liberado integralmente. Recompensas econômicas "
                "provisórias vinculadas à conclusão são descartadas, enquanto conhecimentos "
                "persistentes permanecem registrados."
            ),
        )
        return Screen(text, "dungeon_crypt", _kb(back("dungeon:known")), "HTML")
    if view.kind == "expired":
        text = blocks(
            "⌛ <b>Masmorra Expirada</b>",
            narrative(f"A incursão pela {view.dungeon_name} expirou."),
            "O Vigor reservado foi devolvido.",
        )
        return Screen(text, "dungeon_crypt", _kb(back("dungeon:known")), "HTML")
    if view.kind == "completed":
        text = blocks(
            "🏆 <b>Masmorra concluída</b>",
            narrative(
                "O Chefe foi derrotado e a incursão chega ao fim. O progresso e as "
                "recompensas válidas da run são consolidados."
            ),
            rewards(reward_html(line) for line in view.reward_lines),
            "✨ <b>Primeira Conclusão</b>" if view.first_clear else None,
        )
        return Screen(text, "dungeon_crypt", _kb(back("dungeon:known")), "HTML")
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


def render_dungeons(view: DungeonView, *, difficulties: bool = False) -> Screen:
    """Dungeon screen with the art of its family (see asset_catalog)."""
    return with_dungeon_art(_render_dungeons(view, difficulties=difficulties), view.family_id)
