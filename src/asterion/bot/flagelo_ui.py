"""Telegram: telas de O Despertar dos Flagelos (especificação V1.0.0 §17 e §18).

Mesmo padrão visual do HUD de combate compartilhado do Véu (``world_event_veu_ui``): barra
``hp_bar`` do combate, números com ponto de milhar, ``<code>`` para valores. Sem arte própria
ainda (imagens pendentes): usa a arte genérica de Eventos.
"""

from __future__ import annotations

from decimal import Decimal
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.flagelos import CombatScreen, HubView
from asterion.bot.combat_ui import hp_bar
from asterion.bot.creation_ui import Screen
from asterion.domain import flagelos as fl

IMAGE = "world_events"
TITLE = "🔥 Despertar dos Flagelos"
FACE = "Enfrentar o Flagelo"
ACTION_REGISTERED = "✅ Ação registrada."
_CATEGORY = {"offensive": "🗡️ Ofensivo", "defensive": "🛡️ Defensivo", "support": "✨ Suporte"}

_ERRORS = {
    "no_character": "Crie um personagem antes de participar.",
    "no_flagelo": "Nenhum Flagelo desperto agora.",
    "reentry_wait": "Sua reentrada ainda não abriu.",
    "full": "O combate contra o Flagelo está cheio. Tente novamente em instantes.",
    "window_closed": "A janela desta oportunidade já fechou.",
    "waiting_next_round": "Você poderá agir na próxima oportunidade.",
    "not_in_combat": "Você não está em combate contra o Flagelo.",
    "already_registered": "Sua ação desta oportunidade já foi registrada.",
    "invalid_action": "Ação inválida.",
    "busy": "Conclua sua atividade atual antes de enfrentar o Flagelo.",
}


def error_text(code: str, seconds: int = 0) -> str:
    text = _ERRORS.get(code, "Não foi possível concluir essa ação.")
    if code == "reentry_wait" and seconds:
        text += f" Faltam {seconds} s."
    return text


def _fmt(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _elapsed(seconds: int) -> str:
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h {minutes % 60:02d}m"


def _scaling_line(steps: int, paused: bool) -> str:
    """Escala por abandono (espec. final §4): +8% HP Máx. e +3% ATQ por passo, com teto."""
    scaling = fl.scaling_for_steps(steps)
    hp = int(scaling.hp_bonus * 100)
    atq = int(scaling.atq_bonus * 100)
    state = " · pausada (há combatentes)" if paused else ""
    return f"📈 Escala · <code>+{hp}% HP · +{atq}% ATQ</code>{state}"


def _metric_lines(metrics: fl.ParticipationMetrics) -> list[str]:
    defensive = metrics.defender_prevented_damage + metrics.barrier_absorbed
    return [
        f"🗡️ Dano efetivo · <code>{_fmt(metrics.effective_damage)}</code>",
        f"🛡️ Defesa · <code>{_fmt(defensive)}</code>",
        f"✨ Cura efetiva · <code>{_fmt(metrics.effective_healing)}</code>",
    ]


def _reward_lines(reward: dict) -> list[str]:
    lines = []
    if reward.get("xp"):
        lines.append(f"✨ <code>{_fmt(int(reward['xp']))}</code> XP")
    if reward.get("crowns"):
        lines.append(f"💰 <code>{_fmt(int(reward['crowns']))}</code> Coroas")
    totals: dict[str, int] = {}
    for item in reward.get("items", ()):
        totals[item["name"]] = totals.get(item["name"], 0) + int(item["quantity"])
    lines.extend(f"🧱 {escape(name)} × {quantity}" for name, quantity in totals.items())
    equipment = reward.get("equipment")
    if isinstance(equipment, dict):
        lines.append(f"🎁 {escape(equipment['name'])} · {escape(equipment['rarity'])}")
    if reward.get("recipe_name"):
        lines.append(f"📜 Receita descoberta · {escape(reward['recipe_name'])}")
    return lines


# Decisão do autor 2026-11-26 §33.2: emoji de cada Região na tela do Despertar.
REGION_EMOJI = {
    "tdo": "🌘",
    "vde": "🌊",
    "nareth": "🌾",
    "varzeas": "🌹",
    "altos": "🏔️",
    "confins_do_veu": "⬜",
}
NONE_AWAKE = (
    "Nenhum Flagelo despertou. A progressão de cada Região aumenta conforme os jogadores "
    "realizam atividades nela."
)


def awakening_bar(points: int, threshold: int) -> str:
    """🟥 enquanto progride; em 100%, a barra inteira fica 🟪 (decisão 2026-11-26 §33.2)."""
    if threshold and points >= threshold:
        return "🟪" * 10
    filled = min(10, points * 10 // threshold) if threshold else 0
    if points > 0:
        filled = max(1, filled)
    return "🟥" * filled + "⬜" * (10 - filled)


def render_hub(view: HubView) -> Screen:
    lines = ["🔥 <b>Despertar dos Flagelos</b>", ""]
    for bar in view.bars:
        emoji = REGION_EMOJI.get(bar.region_id, bar.emoji)
        lines.extend(
            [
                f"{emoji} <b>{escape(bar.label)}</b> · <code>{bar.points}/{bar.threshold}</code>",
                f"{awakening_bar(bar.points, bar.threshold)} <code>{bar.percent}%</code>",
                "",
            ]
        )
    if lines[-1] == "":
        lines.pop()
    rows: list[list[InlineKeyboardButton]] = []
    active = view.active
    if active is not None:
        lines.extend(
            [
                "",
                f"⚔️ <b>{escape(active.name)}</b>",
                f"🗺️ {escape(active.region)}",
                "",
                f"❤️ <code>{_fmt(active.hp)}/{_fmt(active.max_hp)}</code>",
                hp_bar(Decimal(active.hp), Decimal(active.max_hp), color="🟥"),
                "",
                f"⏱️ Ativo há {_elapsed(active.active_seconds)}",
                f"👥 <code>{active.combatants}/{active.capacity}</code> em combate",
                _scaling_line(active.scaling_steps, active.scaling_paused),
            ]
        )
        me = view.me
        if me is not None:
            lines.append(
                f"🎖️ Participação · <code>{me.participation_points}/{fl.PARTICIPATION_MIN}</code>"
            )
            if me.metrics is not None:
                lines.extend(_metric_lines(me.metrics))
        if me is not None and me.in_combat:
            rows.append([_button("⚔️ Voltar ao combate", "flg:fight")])
        elif me is not None and me.reentry_seconds > 0:
            lines.append(f"⏳ Reentrada em <code>{me.reentry_seconds} s</code>")
            rows.append([_button("🔄 Atualizar", "flg:hub")])
        else:
            rows.append([_button(f"[ {FACE} ]", "flg:enter")])
    else:
        lines.extend(["", f"<i>{escape(NONE_AWAKE)}</i>"])
    if view.last_rankings:
        lines.extend(["", f"🏆 <b>Último Flagelo · {escape(view.last_name or '')}</b>"])
        for category in fl.RANKING_CATEGORIES:
            entries = [line for line in view.last_rankings if line.category == category]
            if not entries:
                continue
            lines.append(_CATEGORY[category])
            for line in entries:
                lines.append(
                    f"{line.position}º {escape(line.name)} · <code>{_fmt(line.value)}</code>"
                )
    if view.last_reward:
        reward_lines = _reward_lines(view.last_reward)
        if reward_lines:
            lines.extend(["", "🎁 <b>Sua recompensa</b>", *reward_lines])
    rows.append([_button("↩️ Retornar", "wev:hub")])
    return Screen("\n".join(lines), IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")


def _history_line(item: dict, names: dict[str, str]) -> str | None:
    kind = item.get("kind")
    amount = _fmt(int(item.get("amount", 0)))
    if kind == "enemy_damaged":
        return f"⚔️ O Flagelo sofreu <b>{amount} de dano</b>."
    if kind == "boss_dot":
        return f"🔥 O Flagelo sofreu <b>{amount} de dano contínuo</b>."
    if kind == "enemy_healed":
        return f"🩸 O Flagelo recuperou <b>{amount} de vida</b>."
    if kind in {"player_damaged", "player_dot"}:
        name = names.get(item.get("character", ""), "Um combatente")
        return f"💥 {escape(name)} sofreu <b>{amount} de dano</b>."
    if kind == "player_dodged":
        name = names.get(item.get("character", ""), "Um combatente")
        return f"💨 {escape(name)} <b>esquivou</b> o golpe."
    return None


def render_combat(view: CombatScreen, names: dict[str, str] | None = None) -> Screen:
    lines = [
        f"⚔️ <b>{escape(view.name)}</b>",
        "",
        f"🌐 <code>Oportunidade {view.round_number}</code> · ⏱️ <code>{view.seconds_left} s</code>",
        "",
        f"❤️ <code>{_fmt(view.boss_hp)}/{_fmt(view.boss_max_hp)}</code>",
        hp_bar(Decimal(view.boss_hp), Decimal(view.boss_max_hp), color="🟥"),
        "",
        f"🧙 <b>{escape(view.self_name)}</b>",
        f"❤️ <code>{_fmt(view.self_hp)}/{_fmt(view.self_max_hp)}</code>",
        hp_bar(Decimal(view.self_hp), Decimal(view.self_max_hp), color="🟥"),
        f"🎖️ Participação · <code>{view.participation_points}/{fl.PARTICIPATION_MIN}</code>",
    ]
    if view.metrics is not None:
        lines.extend(_metric_lines(view.metrics))
    lines.append(_scaling_line(view.scaling_steps, True))
    if view.telegraph:
        lines.extend(["", f"⚠️ <i>O Flagelo prepara {escape(view.telegraph)}.</i>"])
    history = [line for item in view.history if (line := _history_line(item, names or {}))]
    if history:
        lines.extend(["", "📜 <b>Histórico:</b>", *history[:8]])
    if view.waiting:
        lines.extend(["", "⏳ Você age a partir da próxima oportunidade."])
    elif view.acted:
        lines.extend(["", ACTION_REGISTERED])
    rows: list[list[InlineKeyboardButton]] = []
    if view.seconds_left > 0 and not view.waiting and not view.acted:
        number = view.round_number
        rows.append([_button("⚔️ Atacar", f"flg:a:atk:{number}")])
        rows.append([_button("🛡️ Defender", f"flg:a:def:{number}")])
        for slot in view.art_slots:
            rows.append([_button(f"Arte {slot}", f"flg:a:art{slot}:{number}")])
    rows.append([_button("🔄 Atualizar", "flg:fight")])
    rows.append([_button("🚪 Sair do combate", "flg:leave")])
    return Screen("\n".join(lines), IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")


def render_ally_targets(rows_data, kind: str, number: int) -> Screen:
    rows = [
        [_button(name, f"flg:t:{kind}:{number}:c{character_id.hex}")]
        for character_id, name in rows_data
    ]
    rows.append([_button("↩️ Retornar", "flg:fight")])
    return Screen(
        "🎯 <b>Escolha o aliado</b>", IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML"
    )


# Contração gramatical da Região ("nas Terras do Ocaso", "nos Vales dos Enforcados").
_IN_REGION = {
    "Terras do Ocaso": "nas",
    "Vales dos Enforcados": "nos",
    "Planícies de Nareth": "nas",
    "Várzeas Carmesins": "nas",
    "Altos Cinéreos": "nos",
    "Confins do Véu": "nos",
}


def render_notice(kind: str, name: str, short_name: str, region: str) -> str:
    """Os dois únicos avisos da comunidade (§18), texto da especificação."""
    if kind == "spawn":
        return f"⚠️ O Despertar começou.\n\n{name}, despertou {_IN_REGION[region]} {region}."
    return f"🏆 O Flagelo foi derrotado.\n\n{short_name} caiu. O ciclo do Despertar recomeçou."
