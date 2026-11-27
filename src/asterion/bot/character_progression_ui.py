"""Player-facing Talents and Active Arts screens."""

import re
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.active_arts import ActiveArtCharacterView
from asterion.application.talents import TalentView
from asterion.bot.creation_ui import Screen
from asterion.bot.flavor_ui import with_flavor
from asterion.domain.arts import (
    ACTIVE_ART_IDS_BY_CLASS,
    ORACULO_ART_IDS,
    TECELAO_ART_IDS,
    active_art_definition,
    weapon_requirement_label,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.path_arts import (
    AGOUREIRO_CONDENACAO_CHAIN,
    CARRASCO_MARCA_DA_MORTE_CHAIN,
)
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.talents import IMPLEMENTED_TALENT_LEVELS, TalentDefinition


def _base36(value: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = digits[remainder] + result
    return result


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _character_lines(name: str, character_class: str, selected_path: str | None) -> list[str]:
    class_label = _class_label(character_class)
    path_name = PATH_DEFINITIONS[selected_path].name if selected_path in PATH_DEFINITIONS else None
    return [
        escape(name),
        class_label + (f" · {escape(path_name)}" if path_name else ""),
    ]


def _class_label(character_class: str) -> str:
    return {
        "sentinela": "Sentinela",
        "errante": "Errante",
        "vigia": "Vigia",
        "tecelao": "Tecelão",
        "oraculo": "Oráculo",
        "luminar": "Luminar",
    }.get(character_class, character_class.title())


def render_talent_root(view: TalentView) -> Screen:
    lines = [
        "🌿 Talentos",
        "",
        *_character_lines(view.character_name, view.character_class, view.selected_path),
        "",
    ]
    lines.extend(["🌿 Pontos de Talento", f"Disponíveis · {view.available_points}"])
    rows = [[_button("Ver Talentos", f"tal:list:{_base36(view.combat_configuration_version)}")]]
    if view.choices and not view.foreground:
        rows.append(
            [
                _button(
                    "Redistribuir Talentos",
                    f"tal:respec:{_base36(view.combat_configuration_version)}",
                )
            ]
        )
    if view.foreground:
        lines.extend(["", "🔒 Configuração · Bloqueada durante a atividade"])
    rows.append([_button("← Personagem", "character:root")])
    return with_flavor(Screen("\n".join(lines), "character", _keyboard(rows)), "talentos")


def _talent_state(view: TalentView, talent: TalentDefinition) -> tuple[str, str]:
    choice = next((item for item in view.choices if item.talent_id == talent.talent_id), None)
    if choice is not None and choice.active:
        return "✅", "Adquirido"
    if choice is not None:
        if talent.level > view.level:
            return "🕰️", f"Adquirido · Retorna no Nv.{talent.level}"
        return "🕰️", "Adquirido · Ponto ainda inativo"
    if talent.level not in IMPLEMENTED_TALENT_LEVELS:
        return "🔒", f"Requer Nv.{talent.level}"
    if view.level < talent.level:
        return "🔒", f"Requer Nv.{talent.level}"
    if view.available_points > 0:
        return "✨", "Disponível"
    return "🔒", "Sem Ponto disponível"


def render_talent_list(view: TalentView) -> Screen:
    rows: list[list[InlineKeyboardButton]] = []
    lines = [
        "🌿 Talentos",
        "",
        *_character_lines(view.character_name, view.character_class, view.selected_path),
        "",
    ]
    for level in (5, 15, 25, 35, 45, 55):
        lines.append(f"Nv.{level}")
        tier = [talent for talent in view.talents if talent.level == level]
        buttons = []
        for talent in tier:
            icon, state = _talent_state(view, talent)
            lines.append(f"{icon} {escape(talent.name)} · {state}")
            index = next(
                i for i, item in enumerate(view.talents) if item.talent_id == talent.talent_id
            )
            buttons.append(
                _button(
                    str(index + 1),
                    f"tal:d:{_base36(index)}:{_base36(view.combat_configuration_version)}",
                )
            )
        rows.append(buttons)
        lines.append("")
    if view.foreground:
        lines.extend(["🔒 Configuração · Bloqueada durante a atividade", ""])
    rows.append([_button("← Talentos", "tal:root")])
    return Screen("\n".join(lines).rstrip(), "character", _keyboard(rows))


def render_talent_detail(view: TalentView, talent: TalentDefinition) -> Screen:
    icon, state = _talent_state(view, talent)
    lines = [
        f"🌿 {escape(talent.name)}",
        f"{escape(talent.category)} · Nv.{talent.level}",
        "",
        escape(talent.description),
        "",
        f"{icon} {state}",
    ]
    rows = []
    if state == "Disponível" and not view.foreground:
        index = next(i for i, item in enumerate(view.talents) if item.talent_id == talent.talent_id)
        rows.append(
            [
                _button(
                    "Adquirir Talento",
                    f"tal:a:{_base36(index)}:{_base36(view.combat_configuration_version)}",
                )
            ]
        )
    rows.append([_button("← Talentos", f"tal:list:{_base36(view.combat_configuration_version)}")])
    return Screen("\n".join(lines), "character", _keyboard(rows))


def render_talent_respec(view: TalentView) -> Screen:
    cost = view.respec_cost
    safe = view.location == "Refúgio do Ocaso"
    can_confirm = bool(view.choices) and safe and not view.foreground and view.crowns >= cost
    lines = [
        "🌿 Redistribuir Talentos",
        "",
        f"Pontos Recuperados · {len(view.choices)}",
        f"🪙 Custo · {cost:,} Coroas".replace(",", "."),
        "📍 Local · Refúgio do Ocaso",
    ]
    if view.foreground:
        lines.append("🔒 Configuração · Bloqueada durante a atividade")
    elif not safe:
        lines.append("🔒 Local · Local Inapropriado")
    elif view.crowns < cost:
        lines.append("🔒 Coroas · Insuficientes")
    rows = []
    if can_confirm:
        rows.append(
            [
                _button(
                    "Confirmar Redistribuição",
                    f"tal:rc:{_base36(view.combat_configuration_version)}",
                )
            ]
        )
    rows.append([_button("← Talentos", "tal:root")])
    return Screen("\n".join(lines), "character", _keyboard(rows))


def _actions_for_view(view: ActiveArtCharacterView) -> dict:
    actions = {}
    for art_id in ACTIVE_ART_IDS_BY_CLASS[view.character_class]:
        try:
            definition = active_art_definition(art_id)
            actions.update(
                class_player_actions(
                    view.character_class,
                    (art_id,),
                    selected_path=(
                        definition.path_id
                        if definition is not None and definition.path_id is not None
                        else view.selected_path
                    ),
                )
            )
        except ValueError:
            # Arts owned by another Path remain outside this character's catalog.
            continue
    return actions


def _art_ids(view: ActiveArtCharacterView) -> tuple[str, ...]:
    all_arts = ACTIVE_ART_IDS_BY_CLASS[view.character_class]
    return tuple(art_id for art_id in all_arts if art_id in view.available_art_ids)


def _art_index(view: ActiveArtCharacterView, art_id: str) -> int:
    return ACTIVE_ART_IDS_BY_CLASS[view.character_class].index(art_id)


def _weapon_requirement_notice(view: ActiveArtCharacterView, art_id: str) -> str | None:
    if art_id not in view.weapon_incompatible_art_ids:
        return None
    definition = active_art_definition(art_id)
    if definition is None or not definition.weapon_requirement:
        return "🔒 Requisito de arma não atendido."
    return f"🔒 Requer {weapon_requirement_label(definition)} equipada."


def _eligibility_notice(view: ActiveArtCharacterView, art_id: str) -> str | None:
    if art_id not in view.ineligible_art_ids:
        return None
    definition = active_art_definition(art_id)
    if definition is None:
        return "🔒 Arte indisponível nesta configuração."
    if view.level < definition.min_level:
        return f"🔒 Requer Nv.{definition.min_level}; remova a Arte antes de combater."
    if definition.path_id is not None and definition.path_id != view.selected_path:
        path_name = PATH_DEFINITIONS.get(definition.path_id)
        label = path_name.name if path_name is not None else definition.path_id
        return f"🔒 Requer Caminho {escape(label)}; remova a Arte antes de combater."
    return "🔒 Arte indisponível nesta configuração."


def _art_category(action) -> str:
    if action.manifestation_kind == "triade_encarnada":
        return "Manifestação"
    if any(effect.stat == "interpor_next_direct" for effect in action.target_effects):
        return "Suporte"
    if (
        action.heal_coefficient
        or action.self_barrier_coefficient
        or action.target_barrier_coefficient
    ):
        return "Suporte"
    if action.target_mode == "self":
        return "Preparação"
    if (
        action.native_dot_kind
        or action.attack_debuff
        or action.effect_stat
        or action.target_effects
    ):
        return "Efeito"
    return "Ataque"


def _percent(value) -> str:
    return format((value * 100).normalize(), "f")


def _effect_lines(effects) -> list[str]:
    labels = {
        "attack": "ATQ",
        "defense": "DEF",
        "agility": "AGI",
        "per": "PER",
        "crit": "CRIT",
        "evasion": "Esquiva",
        "block": "Bloqueio",
        "healing_received": "Cura recebida",
    }
    lines = []
    for effect in effects:
        if effect.stat == "interpor_next_direct":
            lines.append(
                f"🛡️ Próximo Dano Direto recebido · −{abs(effect.magnitude) * 100:g}% "
                f"· {effect.duration}T"
            )
            continue
        sign = "−" if effect.magnitude < 0 else "+"
        if effect.stat_modifier_mode == "percentage_points":
            amount = f"{abs(effect.magnitude):g} p.p."
        else:
            amount = f"{abs(effect.magnitude) * 100:g}%"
        lines.append(
            f"✨ {labels.get(effect.stat, effect.stat)} · {sign}{amount} · {effect.duration}T"
        )
    return lines


def _art_mechanics_lines(action) -> list[str]:
    lines = []
    if action.coefficient:
        per_hit = " por golpe" if action.hit_count > 1 else ""
        lines.append(f"⚔️ Dano · {_percent(action.coefficient)}% ATQ{per_hit}")
    if action.hit_count > 1:
        lines.append(f"💥 Atinge · {action.hit_count} vezes")
    if action.heal_coefficient:
        lines.append(f"❤️ Cura · {_percent(action.heal_coefficient)}% ATQ")
    if action.self_barrier_coefficient:
        lines.append(
            f"🛡️ Barreira · {_percent(action.self_barrier_coefficient)}% ATQ "
            f"· {action.self_barrier_duration}T"
        )
    if action.target_barrier_coefficient:
        lines.append(
            f"🛡️ Barreira · {_percent(action.target_barrier_coefficient)}% ATQ "
            f"· {action.target_barrier_duration}T"
        )
    if action.attack_debuff:
        stat = {
            "attack": "ATQ",
            "defense": "DEF",
            "agility": "AGI",
            "healing_received": "Cura recebida",
        }.get(action.effect_stat or "attack", "ATQ")
        lines.append(
            f"🌀 Efeito · −{_percent(action.attack_debuff)}% {stat} · {action.duration}T"
        )
    if action.native_dot_kind:
        lines.append(f"☣️ Aplica · {action.native_dot_kind.title()}")
    if action.self_effect_id and action.self_effect_stat:
        stat = {
            "attack": "ATQ",
            "defense": "DEF",
            "agility": "AGI",
            "healing_received": "Cura recebida",
        }.get(action.self_effect_stat, action.self_effect_stat.upper())
        sign = "−" if action.self_effect_kind == "debuff" else "+"
        lines.append(
            f"✨ Em si · {sign}{_percent(action.self_effect_magnitude)}% {stat} "
            f"· {action.self_effect_duration}T"
        )
    lines.extend(_effect_lines(action.self_effects))
    lines.extend(_effect_lines(action.target_effects))
    if action.next_direct_crit_bonus:
        lines.append(
            f"🎯 Próximo Dano Direto · +{action.next_direct_crit_bonus:g} p.p. CRIT "
            f"· {action.next_direct_crit_duration}T"
        )
    if action.crit_bonus_if_target_debuffed:
        lines.append(
            f"💥 Contra alvo com Debuff · +{action.crit_bonus_if_target_debuffed:g} p.p. CRIT"
        )
    distinct_negative_power_modifiers = [
        modifier
        for modifier in action.conditional_modifiers
        if modifier.condition.kind == "target_distinct_normal_negative_effects_at_least"
        and modifier.component == "damage_power"
        and modifier.operation == "add"
    ]
    for modifier in action.conditional_modifiers:
        if (
            modifier.condition.kind == "class_resource_at_least"
            and modifier.condition.resource == "aim"
            and modifier.component == "crit_bonus"
        ):
            lines.append(
                f"🎯 Com {modifier.condition.minimum}+ Miras no alvo no início da ação · "
                f"+{modifier.magnitude:g} p.p. CRIT"
            )
        elif (
            modifier.condition.kind == "class_resource_at_least"
            and modifier.condition.resource == "retaliation"
            and modifier.component == "precision_bonus"
        ):
            lines.append(
                "🛡️ Com Retaliação ativa no início da ação · "
                f"+{modifier.magnitude:g} p.p. PER"
            )
        elif (
            modifier.condition.kind == "class_resource_at_least"
            and modifier.condition.resource == "retaliation"
            and modifier.component == "attack_debuff"
        ):
            lines.append(
                "🛡️ Com Retaliação ativa no início da ação · "
                f"aplica −{modifier.magnitude * 100:g}% ATQ por {action.duration}T"
            )
        elif (
            modifier.condition.kind == "target_has_normal_negative_effect"
            and modifier.component == "precision_bonus"
        ):
            lines.append(
                "🎯 Contra alvo com DoT ou Debuff normal válido no início da ação · "
                f"+{modifier.magnitude:g} p.p. PER"
            )
        elif (
            modifier.condition.kind == "target_has_normal_debuff"
            and modifier.component == "crit_bonus"
        ):
            lines.append(
                "💥 Contra alvo com Debuff normal válido no início da ação · "
                f"+{modifier.magnitude:g} p.p. CRIT"
            )
        elif (
            modifier.condition.kind == "class_resource_at_least"
            and modifier.condition.resource == "omen_offensive"
            and modifier.component == "attack_debuff"
        ):
            lines.append(
                "🔮 Ao consumir Presságio Ofensivo do alvo · "
                f"−{_percent(modifier.magnitude)}% Cura recebida · {action.duration}T"
            )
        elif (
            modifier.condition.kind == "actor_hp_fraction_below"
            and modifier.component == "damage_power"
        ):
            lines.append(
                f"⚔️ Com HP próprio <{_percent(modifier.condition.threshold)}% · "
                f"+{_percent(modifier.magnitude)}% potência"
            )
        elif (
            modifier.condition.kind == "target_hp_fraction_at_most"
            and modifier.component == "crit_bonus"
        ):
            lines.append(
                f"💥 Contra alvo com HP ≤{_percent(modifier.condition.threshold)}% · "
                f"+{modifier.magnitude:g} p.p. CRIT"
            )
    if distinct_negative_power_modifiers:
        per_effect = distinct_negative_power_modifiers[0].magnitude
        maximum = sum(
            (modifier.magnitude for modifier in distinct_negative_power_modifiers),
            start=0,
        )
        lines.append(
            "⚔️ Por tipo distinto de DoT/Debuff normal válido no início · "
            f"+{_percent(per_effect)}% potência · máximo +{_percent(maximum)}%"
        )
    for resource_use in action.resource_uses:
        if resource_use.resource == "aim" and resource_use.consume > 0:
            timing = (
                "após a resolução"
                if resource_use.consume_at == "after_resolution"
                else "no commit"
            )
            lines.append(f"🎯 Consome {resource_use.consume} Miras do alvo {timing}")
    if action.per_bonus_if_target_poisoned:
        lines.append(
            f"🎯 Contra alvo Envenenado · +{action.per_bonus_if_target_poisoned:g} p.p. PER"
        )
    if action.actor_per_bonus:
        lines.append(f"🎯 PER na ação · +{action.actor_per_bonus:g} p.p.")
    if action.self_barrier_debuff_magnitude_reduction:
        lines.append(
            "🛡️ Barreira reduz em "
            f"{action.self_barrier_debuff_magnitude_reduction * 100:g}% "
            "a magnitude de Debuffs recebidos."
        )
    chain_key = action.consumes_chain or action.prepares_chain
    if chain_key == "trama_encadeada" or action.id in TECELAO_ART_IDS.values():
        lines.append("✨ Trama Encadeada · prepara ou consome a janela")
    elif chain_key == CARRASCO_MARCA_DA_MORTE_CHAIN:
        lines.append(
            "☠️ Marca da Morte · próxima Arte direta do Carrasco recebe +12% em 2T"
        )
    elif chain_key == AGOUREIRO_CONDENACAO_CHAIN:
        lines.append(
            "🔮 Condenação · próxima Arte do Agoureiro recebe +20% em 2T"
        )

    if action.manifestation_kind == "triade_encarnada":
        lines.extend(
            (
                "🐺 Último Lobo · Dano Direto 155% ATQ",
                "🦉 Última Coruja · Dano Direto 95% ATQ e −20% AGI · 2T",
                "🐻 Último Urso · Barreira 120% ATQ · 2T",
                "A própria Tríade não altera a última manifestação.",
            )
        )
        target = "Forma da última manifestação válida"
    elif action.target_mode == "self":
        target = "Você"
    elif action.target_mode in {"ally", "ally_or_self"}:
        target = "Você ou Aliado"
    elif action.target_mode == "all_opponents":
        target = "Todos os Inimigos"
    elif action.target_mode == "all_allies":
        target = "Todos os Aliados"
    else:
        target = "1 Inimigo"
    lines.extend(
        [
            f"🎯 Alvo · {target}",
            f"⏳ Recarga · {action.cooldown or action.blocked_opportunities} Rodadas",
        ]
    )
    return lines


# Especificação consolidada 2026-11-26, Parte I §7–§9.
ARTS_TITLE = "🧿 Artes"
ARTS_TEXT = (
    "Artes são técnicas especiais que permitem canalizar habilidades únicas durante os "
    "confrontos de Asterion."
)
ARTS_PER_PAGE = 4
# Descrições de Arte definidas pela Fonte; sem descrição, a linha não aparece.
ART_DESCRIPTIONS = {
    "sentinela.golpe_de_guarda": (
        "O golpe usa o peso da lâmina e a firmeza da guarda para atingir o inimigo em um "
        "movimento direto."
    ),
}
ART_CATEGORY_EMOJI = {
    "Ataque": "⚔️",
    "Efeito": "🌀",
    "Suporte": "✨",
    "Preparação": "🛡️",
    "Manifestação": "🔮",
}
_KEYCAPS = ("1️⃣", "2️⃣", "3️⃣")
# Regras de Presságio das Artes do Oráculo, mostradas junto da mecânica da Arte.
ART_OMEN_LINES = {
    ORACULO_ART_IDS["augurio_favoravel"]: (
        "🔮 Buff positivo bem-sucedido · gera Presságio Defensivo no alvo.",
    ),
    ORACULO_ART_IDS["selo_da_queda"]: (
        "🔮 Debuff normal aplicado com sucesso · gera Presságio Ofensivo no alvo.",
        "🔮 Presságio Ofensivo preexistente no alvo · fortalece o Dano Direto.",
    ),
}
_FIELD_LINE = re.compile(r"^(\S+) ([^·]+?) · (.+)$")


def _art_emoji(action) -> str:
    return ART_CATEGORY_EMOJI.get(_art_category(action), "⚔️")


def _art_description(art_id: str) -> str | None:
    return next(
        (text for key, text in ART_DESCRIPTIONS.items() if art_id.endswith(key)), None
    )


def _field_html(line: str) -> str:
    """``⚔️ Dano · 110% ATQ`` → ``⚔️ <b>Dano</b> · <code>110% ATQ</code>``."""
    match = _FIELD_LINE.match(line)
    if match is None:
        return escape(line)
    emoji, label, value = match.groups()
    return f"{emoji} <b>{escape(label)}</b> · <code>{escape(value)}</code>"


def render_art_root(view: ActiveArtCharacterView, page: int = 0) -> Screen:
    actions = _actions_for_view(view)
    version = _base36(view.combat_configuration_version)
    equipped_lines = []
    for slot in (1, 2, 3):
        art_id = next((entry.art_id for entry in view.slots if entry.slot == slot), None)
        name = actions[art_id].name if art_id in actions else "Vazio"
        equipped_lines.append(f"{_KEYCAPS[slot - 1]} <code>{escape(name)}</code>")
    known = list(_art_ids(view))
    pages = max(1, -(-len(known) // ARTS_PER_PAGE))
    page = min(max(page, 0), pages - 1)
    shown = known[page * ARTS_PER_PAGE : (page + 1) * ARTS_PER_PAGE]
    known_lines = [
        f"{_art_emoji(actions[art_id])} <code>{escape(actions[art_id].name)}</code>"
        for art_id in shown
    ]
    buttons = [
        _button(
            f"{_art_emoji(actions[art_id])} {actions[art_id].name.split()[0]}",
            f"art:d:{_base36(_art_index(view, art_id))}:{version}",
        )
        for art_id in shown
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    navigation = []
    if page > 0:
        navigation.append(_button("◀️ Anterior", f"art:p:{page - 1}"))
    if page < pages - 1:
        navigation.append(_button("▶️ Próxima", f"art:p:{page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append([_button("↩️ Retornar", "character:root")])
    parts = [
        f"<b>{escape(ARTS_TITLE)}</b>",
        f"<i>{escape(ARTS_TEXT)}</i>",
        "✨ <b>Artes Equipadas</b>\n\n" + "\n".join(equipped_lines),
        "📚 <b>Artes Conhecidas</b>\n\n" + "\n".join(known_lines)
        if known_lines
        else "📚 <b>Artes Conhecidas</b>",
    ]
    return Screen("\n\n".join(parts), "character", _keyboard(rows), parse_mode="HTML")


def render_art_detail(view: ActiveArtCharacterView, art_id: str) -> Screen:
    """Detalhe da Arte: a escolha da posição acontece aqui mesmo (§8–§9).

    Não há campo separado de Requisito de Arma: a compatibilidade continua como regra
    do sistema e é verificada ao equipar.
    """
    action = _actions_for_view(view)[art_id]
    definition = active_art_definition(art_id)
    art_index = _art_index(view, art_id)
    version = _base36(view.combat_configuration_version)
    equipped_slot = next((entry.slot for entry in view.slots if entry.art_id == art_id), None)
    parts = [f"{_art_emoji(action)} <b>{escape(action.name)}</b>"]
    if description := _art_description(art_id):
        parts.append(f"<i>{escape(description)}</i>")
    parts.append("\n".join(_field_html(line) for line in _art_mechanics_lines(action)))
    if omen := ART_OMEN_LINES.get(art_id):
        parts.append("\n".join(escape(line) for line in omen))
    origin = _class_label(view.character_class) + (
        f" · {PATH_DEFINITIONS[definition.path_id].name}"
        if definition is not None and definition.path_id in PATH_DEFINITIONS
        else ""
    )
    about = []
    if definition is not None:
        about.append(_field_html(f"🔓 Desbloqueio · Nv. {definition.min_level}"))
    about.append(_field_html(f"🛡️ Arte Ativa · {origin}"))
    parts.append("\n".join(about))
    rows = [
        [
            _button(
                f"{_KEYCAPS[slot - 1]} Equipar Arte [Slot {slot}]",
                f"art:s:{_base36(art_index)}:{slot}:{version}",
            )
        ]
        for slot in (1, 2, 3)
    ]
    if equipped_slot is not None:
        rows.append(
            [_button("❌ Desequipar", f"art:u:{_base36(equipped_slot)}:{version}")]
        )
    rows.append([_button("↩️ Retornar", "art:r")])
    return Screen("\n\n".join(parts), "character", _keyboard(rows), parse_mode="HTML")
