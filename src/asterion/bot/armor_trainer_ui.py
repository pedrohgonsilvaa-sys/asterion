"""Aba "Armaduras" do Treinador (Proficiências de Armadura, spec Classes de Armadura v1.0.0)."""

from html import escape

from aiogram.types import InlineKeyboardButton

from asterion.application.armor_proficiency import ArmorTrainerView, ArmorTrainingRejected
from asterion.application.weapon_proficiency import TRAINER_LOCATION
from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import back, blocks, button, column, field, keyboard, narrative, number
from asterion.domain.armor_proficiency import ARMOR_TERMS
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


# Bloco UI 1 §2 · Treinamento de Armaduras (apresentação de Darian Veyr).
ARMOR_BUTTONS = {
    "veste": "👘 Vestes",
    "leve": "🥋 Leves",
    "media": "🦺 Médias",
    "pesada": "⛑️ Pesadas",
}
ARMOR_TEXT = (
    "Treinamento voltado ao domínio de diferentes categorias de armaduras, preparando o "
    "combatente para escolher a proteção adequada ao seu estilo de combate."
)


def render_armor_trainer(view: ArmorTrainerView, notice: str | None = None) -> Screen:
    text = blocks("🥋 <b>Treinamento de Armaduras</b>", narrative(ARMOR_TEXT))
    if notice:
        text += f"\n\n{escape(notice)}"
    options = [
        button(ARMOR_BUTTONS[entry.terms.armor_class], f"apt:c:{entry.terms.armor_class}")
        for entry in view.entries
    ]
    return Screen(text, "menu", keyboard(*column(*options), back("refuge:darian")), "HTML")


def render_armor_class(
    view: ArmorTrainerView, armor_class: str, notice: str | None = None
) -> Screen:
    """Categoria: Nível e Custo canônicos (Classes de Armadura v1.0.0) ou ``Adquirida``."""
    terms = ARMOR_TERMS[armor_class]
    owned = any(e.owned and e.terms.armor_class == armor_class for e in view.entries)
    if owned:
        details = field("📜", "Proficiência", "Adquirida")
        rows = []
    else:
        details = "\n".join(
            (
                field("⭐", "Nível", str(terms.min_level)),
                field("💰", "Custo", f"{number(terms.cost_crowns)} Coroas"),
            )
        )
        rows = (
            [[button("🥋 Adquirir Proficiência", f"apt:ok:{armor_class}")]]
            if view.at_trainer
            else []
        )
    text = blocks(f"<b>{ARMOR_BUTTONS[armor_class]}</b>", details)
    if notice:
        text += f"\n\n{escape(notice)}"
    return Screen(text, "menu", keyboard(*rows, back("apt:root")), "HTML")
