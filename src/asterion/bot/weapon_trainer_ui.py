"""Telas do Treinador de Armas (Proficiências de Armas, spec v1.0.0)."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.weapon_proficiency import (
    TRAINER_LOCATION,
    TrainerView,
    TrainingRejected,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.weapon_proficiency import (
    FAMILY_LABELS,
    WEAPON_IDENTITIES,
    ProficiencyFamily,
    usable_identities,
)

REJECTION_TEXT = {
    TrainingRejected.UNKNOWN_FAMILY: "Essa Proficiência não existe.",
    TrainingRejected.NOT_LEARNABLE: "Sua Classe não pode aprender essa Proficiência.",
    TrainingRejected.LOCATION_REQUIRED: f"O Treinador de Armas fica no {TRAINER_LOCATION}.",
    TrainingRejected.LEVEL_REQUIRED: "Nível insuficiente para a próxima Proficiência.",
    TrainingRejected.NOT_ENOUGH_CROWNS: "Coroas insuficientes.",
}


def _number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _weapons(view: TrainerView, family: ProficiencyFamily) -> str:
    return ", ".join(
        WEAPON_IDENTITIES[identity].label
        for identity in usable_identities(view.character_class, family)
    )


def render_weapon_trainer(view: TrainerView, notice: str | None = None) -> Screen:
    terms = view.next_terms
    lines = [
        "⚔️ Treinador de Armas",
        f"{TRAINER_LOCATION} · Terras do Ocaso",
        "",
        "Uma Proficiência autoriza, para sempre, equipar as armas daquela família "
        "que sua Classe pode usar. Ela não concede atributos nem bônus de combate.",
        "",
        f"Próxima Proficiência ({terms.ordinal}ª): Nível {terms.min_level} · "
        f"{_number(terms.cost_crowns)} Coroas",
        f"Suas Coroas: {_number(view.crowns)}",
        "",
    ]
    for entry in view.entries:
        mark = "✅" if entry.owned else "◻️"
        lines.append(
            f"{mark} {FAMILY_LABELS[entry.family]} — {_weapons(view, entry.family)}"
        )
    if not view.at_trainer:
        lines.extend(["", REJECTION_TEXT[TrainingRejected.LOCATION_REQUIRED]])
    if notice:
        lines.extend(["", notice])
    rows = []
    if view.at_trainer:
        rows.extend(
            [_button(f"Aprender {FAMILY_LABELS[entry.family]}", f"wpt:c:{entry.family.value}")]
            for entry in view.entries
            if not entry.owned
        )
    rows.append([_button("← Refúgio do Ocaso", "road:local")])
    return Screen("\n".join(lines), "menu", InlineKeyboardMarkup(inline_keyboard=rows))


def render_weapon_trainer_confirm(view: TrainerView, family: ProficiencyFamily) -> Screen:
    terms = view.next_terms
    text = (
        f"⚔️ Aprender {FAMILY_LABELS[family]}\n\n"
        f"Armas liberadas para sua Classe: {_weapons(view, family)}.\n\n"
        f"Custo: {_number(terms.cost_crowns)} Coroas · Nível mínimo {terms.min_level}.\n"
        "A Proficiência é permanente: não pode ser trocada nem desfeita."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [_button("Confirmar", f"wpt:ok:{family.value}")],
            [_button("Cancelar", "wpt:root")],
        ]
    )
    return Screen(text, "menu", keyboard)
