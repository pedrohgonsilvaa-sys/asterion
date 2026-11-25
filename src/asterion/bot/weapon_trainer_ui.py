"""Telas do Treinador de Armas (Proficiências de Armas, spec v1.0.0)."""

from html import escape

from aiogram.types import InlineKeyboardButton

from asterion.application.weapon_proficiency import (
    TRAINER_LOCATION,
    TrainerView,
    TrainingRejected,
)
from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import (
    back,
    blocks,
    button,
    field,
    keyboard,
    narrative,
    number,
    pairs,
)
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


# Bloco UI 1 §2 · Treinamento de Armas (apresentação de Darian Veyr).
FAMILY_EMOJI = {
    ProficiencyFamily.SWORDS: "🗡️",
    ProficiencyFamily.BLADES: "🔪",
    ProficiencyFamily.BLUNT: "🔨",
    ProficiencyFamily.AXES: "🪓",
    ProficiencyFamily.POLEARMS: "⚔️",
    ProficiencyFamily.BOWS: "🏹",
    ProficiencyFamily.CROSSBOWS: "🏹",
    ProficiencyFamily.ARCANE_FOCI: "🔮",
    ProficiencyFamily.SHIELD: "🛡️",
}
WEAPONS_TEXT = (
    "Treinamento voltado à aquisição de proficiência e ao domínio de diferentes "
    "famílias de armas."
)
SHIELD_TEXT = (
    "Treinamento voltado ao domínio de escudos, aprimorando o controle, a proteção e a "
    "eficiência defensiva durante o combate."
)
# Texto de Espadas e de Escudos: Bloco UI 1. Demais famílias: descrição objetiva no
# mesmo molde, a revisar pelo autor (nenhuma regra nasce daqui).
FAMILY_TEXT = {
    ProficiencyFamily.SWORDS: (
        "Armas equilibradas, voltadas ao controle dos movimentos, precisão e "
        "versatilidade em combate."
    ),
    ProficiencyFamily.BLADES: (
        "Armas curtas e leves, voltadas à rapidez dos golpes, usadas de perto ou "
        "arremessadas."
    ),
    ProficiencyFamily.BLUNT: (
        "Armas de impacto, voltadas à força de cada golpe."
    ),
    ProficiencyFamily.AXES: (
        "Armas pesadas na cabeça, voltadas a golpes amplos e de grande impacto."
    ),
    ProficiencyFamily.POLEARMS: (
        "Armas de cabo longo, voltadas ao alcance e ao controle da distância em combate."
    ),
    ProficiencyFamily.BOWS: (
        "Armas de disparo, voltadas à precisão e ao ataque a partir da distância."
    ),
    ProficiencyFamily.CROSSBOWS: (
        "Armas de disparo mecânico, voltadas a tiros firmes, armados antes de cada "
        "disparo."
    ),
    ProficiencyFamily.ARCANE_FOCI: (
        "Instrumentos de canalização, voltados ao controle e à condução de forças "
        "arcanas."
    ),
    ProficiencyFamily.SHIELD: SHIELD_TEXT,
}
ACQUIRE_LABEL = {ProficiencyFamily.SHIELD: "🛡️ Adquirir Proficiência"}


def _family_label(family: ProficiencyFamily) -> str:
    return f"{FAMILY_EMOJI[family]} {FAMILY_LABELS[family]}"


def _with_notice(text: str, notice: str | None) -> str:
    return f"{text}\n\n{escape(notice)}" if notice else text


def render_weapon_trainer(view: TrainerView, notice: str | None = None) -> Screen:
    """Lista só as famílias de arma que a Classe pode aprender (Escudo tem tela própria)."""
    families = [
        entry.family for entry in view.entries if entry.family != ProficiencyFamily.SHIELD
    ]
    text = blocks("⚔️ <b>Treinamento de Armas</b>", narrative(WEAPONS_TEXT))
    options = [button(_family_label(family), f"wpt:c:{family.value}") for family in families]
    return Screen(
        _with_notice(text, notice),
        "menu",
        keyboard(*pairs(options), back("refuge:darian")),
        "HTML",
    )


def render_weapon_family(
    view: TrainerView, family: ProficiencyFamily, notice: str | None = None
) -> Screen:
    """Família: Nível e Custo da próxima Proficiência (spec v1.0.0) ou ``Adquirida``."""
    owned = any(entry.family == family and entry.owned for entry in view.entries)
    if family == ProficiencyFamily.SHIELD:
        heading, back_to = "🛡️ <b>Treinamento de Escudos</b>", "refuge:darian"
    else:
        heading, back_to = f"<b>{_family_label(family)}</b>", "wpt:root"
    if owned:
        details = field("📜", "Proficiência", "Adquirida")
        rows = []
    else:
        terms = view.next_terms
        details = "\n".join(
            (
                field("⭐", "Nível", str(terms.min_level)),
                field("💰", "Custo", f"{number(terms.cost_crowns)} Coroas"),
            )
        )
        rows = (
            [[button(ACQUIRE_LABEL.get(family, "⚔️ Adquirir Proficiência"),
                     f"wpt:ok:{family.value}")]]
            if view.at_trainer
            else []
        )
    text = blocks(heading, narrative(FAMILY_TEXT[family]), details)
    return Screen(_with_notice(text, notice), "menu", keyboard(*rows, back(back_to)), "HTML")
