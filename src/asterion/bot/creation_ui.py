"""Presentation-only copy and keyboards, sourced from CHARACTER_CREATION_UI.md."""

import json
from dataclasses import dataclass
from importlib.resources import files
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.domain.creation import CLASSES, GENDERS, PROLOGUE, RACES, Creation

GENDER_LABELS = tuple(gender.capitalize() for gender in GENDERS)

COPY = json.loads(files("asterion.bot").joinpath("creation_copy.json").read_text(encoding="utf-8"))
PROLOGUE_TEXT = (
    "🔥 Cinzas na Estrada\nPrólogo · Terras do Ocaso\n\n"
    "O mundo desperta sob um céu sem cor. Cinzas atravessam a estrada como neve morta, "
    "cobrindo pedras, árvores retorcidas e os restos de algo que um dia talvez tenha sido "
    "um caminho seguro. À frente, entre a névoa e o silêncio, formas quebradas marcam "
    "a direção de sua primeira jornada."
)


class CreationCallback(CallbackData, prefix="cc"):
    draft: str
    version: int
    action: str

    @property
    def draft_id(self) -> UUID:
        return UUID(hex=self.draft)


@dataclass(frozen=True)
class Screen:
    text: str
    image_key: str
    keyboard: InlineKeyboardMarkup | None
    parse_mode: str | None = None


def render(state: Creation) -> Screen:
    def button(label: str, action: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=label,
            callback_data=CreationCallback(
                draft=state.id.hex,
                version=state.version,
                action=action,
            ).pack(),
        )

    rows = []
    step = state.step
    if step == PROLOGUE:
        return Screen(
            PROLOGUE_TEXT,
            PROLOGUE,
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Seguir pela Estrada", callback_data="prologue:continue"
                        ),
                    ]
                ]
            ),
        )
    text = COPY[step]
    if step == "name":
        if state.error:
            text = COPY[state.error].replace("Luiken", state.rejected_name or "")
    elif step == "gender":
        rows = [
            [button(label, f"g{i}") for i, label in enumerate(GENDER_LABELS)],
            [button("← Nome", "backname")],
        ]
    elif step == "race":
        rows = [
            [button(str(i + 1), f"r{i}") for i in range(len(RACES))],
            [button("← Gênero", "backgender")],
        ]
    elif step == "class":
        rows = [
            [button(str(i + 1), f"c{i}") for i in range(3)],
            [button(str(i + 1), f"c{i}") for i in range(3, len(CLASSES))],
            [button("← Raças", "races")],
        ]
    elif step.startswith(("race:", "class:")):
        title = text.splitlines()[0].split(" ", 1)[1]
        race_page = step.startswith("race:")
        rows = [
            [button(f"Escolher {title}", "choose")],
            [button("← Raças" if race_page else "← Classes", "races" if race_page else "classes")],
        ]
    elif step == "confirm":
        race_title = COPY[f"race:{state.race}"].splitlines()[0]
        class_title = COPY[f"class:{state.character_class}"].splitlines()[0]
        passive = next(
            line for line in COPY[f"race:{state.race}"].splitlines() if " · Passiva Racial" in line
        )
        race_icon, race_name = race_title.split(" ", 1)
        class_icon, class_name = class_title.split(" ", 1)
        text = (
            text.replace("Luiken", state.name or "")
            .replace("🎭 Gênero · Masculino", f"🎭 Gênero · {(state.gender or '').capitalize()}")
            .replace("🕯️ Raça · Remanescente", f"{race_icon} Raça · {race_name}")
            .replace("🧩 Adaptabilidade · Passiva Racial", passive)
            .replace("🗡️ Classe · Errante", f"{class_icon} Classe · {class_name}")
        )
        rows = [
            [button("Confirmar Personagem", "confirm")],
            [button("Nome", "name"), button("Gênero", "gender")],
            [button("Raça", "race"), button("Classe", "class")],
            [button("← Classes", "classes")],
        ]
    image_key = step
    if state.gender and step.startswith("race:"):
        image_key = f"char.{step.split(':')[1]}.{state.gender}"
    elif state.gender and state.race and step.startswith("class:"):
        image_key = f"char.{state.race}.{state.gender}.{step.split(':')[1]}"
    return Screen(text, image_key, InlineKeyboardMarkup(inline_keyboard=rows) if rows else None)
