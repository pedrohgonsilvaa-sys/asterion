"""Player-facing Talents and Active Arts screens."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.active_arts import ActiveArtCharacterView
from asterion.application.talents import TalentView
from asterion.bot.creation_ui import Screen
from asterion.domain.arts import (
    ACTIVE_ART_IDS_BY_CLASS,
    LUMINAR_ART_IDS,
    ORACULO_ART_IDS,
    TECELAO_ART_IDS,
    active_art_definition,
    weapon_requirement_label,
)
from asterion.domain.class_trials import class_player_actions
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
    return Screen("\n".join(lines), "character", _keyboard(rows))


def _talent_state(view: TalentView, talent: TalentDefinition) -> tuple[str, str]:
    acquired = {
        choice.talent_id for choice in view.choices if choice.point_slot <= view.total_points
    }
    if talent.talent_id in acquired:
        return "✅", "Adquirido"
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
    if (
        action.prepares_chain
        or action.consumes_chain
        or action.id in TECELAO_ART_IDS.values()
    ):
        lines.append("✨ Trama Encadeada · prepara ou consome a janela")

    if action.target_mode == "self":
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


def render_art_root(view: ActiveArtCharacterView) -> Screen:
    actions = _actions_for_view(view)
    art_ids = _art_ids(view)
    equipped = {slot.art_id: slot.slot for slot in view.slots}
    lines = [
        "🎴 Artes",
        "",
        *_character_lines(view.character_name, view.character_class, view.selected_path),
        "",
        "🎴 Artes Equipadas",
    ]
    rows = []
    for slot in (1, 2, 3):
        art_id = next((entry.art_id for entry in view.slots if entry.slot == slot), None)
        if art_id is None:
            lines.append(f"{slot} · Vazio")
            continue
        action = actions[art_id]
        index = _art_index(view, art_id)
        lines.append(f"{slot} {escape(action.name)} · {_art_category(action)}")
        if notice := _eligibility_notice(view, art_id):
            lines.append(notice)
        if notice := _weapon_requirement_notice(view, art_id):
            lines.append(notice)
        rows.append(
            [
                _button(
                    str(slot),
                    f"art:d:{_base36(index)}:{_base36(view.combat_configuration_version)}",
                )
            ]
        )
    lines.extend(["", "📚 Outras Artes"])
    other_buttons = []
    for art_id in art_ids:
        if art_id in equipped:
            continue
        action = actions[art_id]
        index = _art_index(view, art_id)
        lines.append(f"{index + 1} {escape(action.name)} · {_art_category(action)}")
        if notice := _weapon_requirement_notice(view, art_id):
            lines.append(notice)
        other_buttons.append(
            _button(
                str(index + 1),
                f"art:d:{_base36(index)}:{_base36(view.combat_configuration_version)}",
            )
        )
    rows.extend([other_buttons[i : i + 3] for i in range(0, len(other_buttons), 3)])
    if view.foreground:
        lines.extend(["", "🔒 Configuração · Bloqueada durante a atividade"])
    rows.append([_button("← Personagem", "character:root")])
    return Screen("\n".join(lines), "character", _keyboard(rows))


def render_art_detail(view: ActiveArtCharacterView, art_id: str) -> Screen:
    action = _actions_for_view(view)[art_id]
    definition = active_art_definition(art_id)
    art_index = _art_index(view, art_id)
    equipped_slot = next((entry.slot for entry in view.slots if entry.art_id == art_id), None)
    incompatible = art_id in view.weapon_incompatible_art_ids
    lines = [
        f"🎴 {escape(action.name)}",
        f"Arte Ativa · {_class_label(view.character_class)}"
        + (
            f" · {escape(PATH_DEFINITIONS[definition.path_id].name)}"
            if definition is not None and definition.path_id in PATH_DEFINITIONS
            else ""
        ),
        "",
    ]
    if definition is not None:
        lines.insert(2, f"🔓 Desbloqueio · Nv.{definition.min_level}")
    lines.extend(_art_mechanics_lines(action))
    if definition is not None and definition.weapon_requirement:
        lines.extend(
            [
                "",
                "🗡️ Requisito de arma · "
                + escape(weapon_requirement_label(definition)),
            ]
        )
    elif art_id == TECELAO_ART_IDS["geada_tecida"]:
        lines.extend(["", "🗡️ Requisito de arma · Nenhum"])
    elif art_id == ORACULO_ART_IDS["augurio_favoravel"]:
        lines.extend(
            [
                "",
                "🗡️ Requisito de arma · Nenhum",
                "🔮 Buff positivo bem-sucedido · gera Presságio Defensivo no alvo.",
            ]
        )
    elif art_id == LUMINAR_ART_IDS["luz_restauradora"]:
        lines.extend(["", "🗡️ Requisito de arma · Nenhum"])
    if incompatible:
        lines.append("🔒 Requisito não atendido · equipe uma arma compatível.")
    if notice := _eligibility_notice(view, art_id):
        lines.extend(["", notice])
    if equipped_slot is not None:
        lines.extend(["", f"🧩 Slot · {equipped_slot}"])
    rows = []
    if equipped_slot is not None and not view.foreground:
        rows.append(
            [
                _button(
                    "Desequipar Arte",
                    f"art:u:{_base36(equipped_slot)}:{_base36(view.combat_configuration_version)}",
                )
            ]
        )
    elif (
        equipped_slot is None
        and not incompatible
        and art_id not in view.ineligible_art_ids
        and not view.foreground
    ):
        rows.append(
            [
                _button(
                    "Equipar Arte",
                    f"art:e:{_base36(art_index)}:{_base36(view.combat_configuration_version)}",
                )
            ]
        )
    elif view.foreground:
        lines.extend(["", "🔒 Configuração · Bloqueada durante a atividade"])
    rows.append([_button("← Artes", f"art:r:{_base36(view.combat_configuration_version)}")])
    return Screen("\n".join(lines), "character", _keyboard(rows))


def render_art_slot_choice(view: ActiveArtCharacterView, art_id: str) -> Screen:
    if art_id in view.weapon_incompatible_art_ids:
        return render_art_detail(view, art_id)
    action = _actions_for_view(view)[art_id]
    art_index = _art_index(view, art_id)
    filled = {entry.slot: entry.art_id for entry in view.slots}
    empty_slots = [slot for slot in (1, 2, 3) if slot not in filled]
    replacing = not empty_slots
    target_slots = (1, 2, 3) if replacing else empty_slots
    lines = [
        "🎴 Equipar Arte",
        "",
        f"{escape(action.name)}",
        f"Arte Ativa · "
        f"{_character_lines(view.character_name, view.character_class, view.selected_path)[1]}",
        "",
        *_art_mechanics_lines(action),
        "",
        "🎴 Artes Equipadas",
    ]
    rows = []
    for slot in (1, 2, 3):
        current_id = filled.get(slot)
        if current_id is None:
            lines.append(f"{slot} · Vazio")
        else:
            lines.append(f"{slot} {escape(_actions_for_view(view)[current_id].name)}")
    lines.extend(
        ["", "Escolha um slot vazio." if not replacing else "Escolha qual Arte deseja substituir."]
    )
    if not view.foreground:
        rows.append(
            [
                _button(
                    str(slot),
                    f"art:s:{_base36(art_index)}:{slot}:{_base36(view.combat_configuration_version)}",
                )
                for slot in target_slots
            ]
        )
    rows.append(
        [
            _button(
                "← Arte", f"art:d:{_base36(art_index)}:{_base36(view.combat_configuration_version)}"
            )
        ]
    )
    return Screen("\n".join(lines), "character", _keyboard(rows))
