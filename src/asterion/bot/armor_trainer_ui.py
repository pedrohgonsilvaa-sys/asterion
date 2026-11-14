"""Aba "Armaduras" do Treinador (Proficiências de Armadura, spec Classes de Armadura v1.0.0)."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.armor_proficiency import ArmorTrainerView, ArmorTrainingRejected
from asterion.application.weapon_proficiency import TRAINER_LOCATION
from asterion.bot.creation_ui import Screen
from asterion.domain.armor_proficiency import ARMOR_CLASS_LABELS, ARMOR_TERMS
from asterion.domain.regional_equipment import ARMOR_CLASS_BONUS

REJECTION_TEXT = {
    ArmorTrainingRejected.UNKNOWN_CLASS: "Essa Proficiência de Armadura não existe.",
    ArmorTrainingRejected.LOCATION_REQUIRED: f"O Treinador fica no {TRAINER_LOCATION}.",
    ArmorTrainingRejected.LEVEL_REQUIRED: "Nível insuficiente para essa Proficiência de Armadura.",
    ArmorTrainingRejected.NOT_ENOUGH_CROWNS: "Coroas insuficientes.",
}


def _number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _bonus(armor_class: str) -> str:
    evasion, block = ARMOR_CLASS_BONUS[armor_class]
    parts = []
    if float(evasion):
        parts.append(f"Esquiva +{evasion.replace('.', ',')}")
    if float(block):
        parts.append(f"Bloqueio +{block.replace('.', ',')}")
    return " · ".join(parts)


def render_armor_trainer(view: ArmorTrainerView, notice: str | None = None) -> Screen:
    lines = [
        "🛡️ Treinador · Armaduras",
        f"{TRAINER_LOCATION} · Terras do Ocaso",
        "",
        "Cada Proficiência de Armadura autoriza, para sempre, equipar peças daquela "
        "classe. O bônus de Esquiva e Bloqueio vem da peça equipada, por peça.",
        f"Suas Coroas: {_number(view.crowns)}",
        "",
    ]
    for entry in view.entries:
        terms = entry.terms
        label = ARMOR_CLASS_LABELS[terms.armor_class]
        mark = "✅" if entry.owned else "◻️"
        price = "grátis (inicial)" if terms.cost_crowns == 0 else (
            f"Nível {terms.min_level} · {_number(terms.cost_crowns)} Coroas"
        )
        lines.append(f"{mark} {label} — {_bonus(terms.armor_class)} — {price}")
    if not view.at_trainer:
        lines.extend(["", REJECTION_TEXT[ArmorTrainingRejected.LOCATION_REQUIRED]])
    if notice:
        lines.extend(["", notice])
    rows = []
    if view.at_trainer:
        rows.extend(
            [
                _button(
                    f"Aprender {ARMOR_CLASS_LABELS[e.terms.armor_class]}",
                    f"apt:c:{e.terms.armor_class}",
                )
            ]
            for e in view.entries
            if not e.owned
        )
    rows.append([_button("⚔️ Armas", "wpt:root")])
    rows.append([_button("← Refúgio do Ocaso", "road:local")])
    return Screen("\n".join(lines), "menu", InlineKeyboardMarkup(inline_keyboard=rows))


def render_armor_trainer_confirm(armor_class: str) -> Screen:
    terms = ARMOR_TERMS[armor_class]
    text = (
        f"🛡️ Aprender Armadura {ARMOR_CLASS_LABELS[armor_class]}\n\n"
        f"Cada peça equipada dá {_bonus(armor_class)}.\n\n"
        f"Custo: {_number(terms.cost_crowns)} Coroas · Nível mínimo {terms.min_level}.\n"
        "A Proficiência é permanente: não pode ser trocada nem desfeita."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [_button("Confirmar", f"apt:ok:{armor_class}")],
            [_button("Cancelar", "apt:root")],
        ]
    )
    return Screen(text, "menu", keyboard)
