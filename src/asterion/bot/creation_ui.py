"""Reusable, data-driven presentation for the initial character creation flow."""

import json
import re
from dataclasses import dataclass
from html import escape
from importlib.resources import files
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.domain.creation import CLASSES, PROLOGUE, RACES, Creation

CATALOG = json.loads(
    files("asterion.bot").joinpath("creation_catalog.json").read_text(encoding="utf-8")
)
SCREENS = CATALOG["screens"]
RACE_CONTENT = CATALOG["races"]
CLASS_CONTENT = CATALOG["classes"]
GENDER_LABELS = ("🚹 Masculino", "🚺 Feminino")
# Sent as a separate message after a rejected name. Generic on purpose: it
# never repeats the rejected name nor exposes the internal reason.
UNAVAILABLE_NAME_WARNING = "⚠️ Nome indisponível. Tente outro nome novamente."


# Kept as a small compatibility surface for callers/tests that need the
# player-facing copy without knowing the catalog shape.
COPY = dict(SCREENS)
for _key, _data in RACE_CONTENT.items():
    COPY[f"race:{_key}"] = _data["detail"]
for _key, _data in CLASS_CONTENT.items():
    COPY[f"class:{_key}"] = _data["detail"]
PROLOGUE_TEXT = (
    "🔥 Cinzas na Estrada\nPrólogo · Terras do Ocaso\n\n"
    "O mundo desperta sob um céu sem cor. Cinzas atravessam a estrada como neve morta, "
    "cobrindo pedras, árvores retorcidas e os restos de algo que um dia talvez tenha sido "
    "um caminho seguro. À frente, entre a névoa e o silêncio, formas quebradas marcam "
    "a direção de sua primeira jornada."
)


def _entity(kind: str, key: str) -> dict:
    return (RACE_CONTENT if kind == "race" else CLASS_CONTENT)[key]


def _label(kind: str, key: str) -> str:
    entity = _entity(kind, key)
    return f"{entity['emoji']} {entity['name']}"


def _pairs(buttons: list) -> list[list]:
    return [buttons[i : i + 2] for i in range(0, len(buttons), 2)]


def _format_markup(text: str) -> str:
    """Convert the catalog's readable Markdown into Telegram-safe HTML."""
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"_(.+?)_", r"<i>\1</i>", text)


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
    # Stable seed for art that belongs to one encounter/activity. Screens
    # without a seed keep the normal random variant behavior.
    media_seed: str | None = None


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
    # Race/class detail steps ("race:<key>", "class:<key>") are built below
    # from the catalog, so they have no entry in SCREENS.
    text = SCREENS.get(step, "")
    if step == "name":
        # Unavailable names keep the name prompt; the warning is a separate
        # message sent by the handler. Format errors keep inline feedback.
        if state.error == "format":
            text = SCREENS["format"]
        else:
            text = SCREENS["name"]
    elif step == "gender":
        rows = [
            [button(label, f"g{i}") for i, label in enumerate(GENDER_LABELS)],
            [button("↩️ Voltar", "backname")],
        ]
    elif step == "race":
        rows = _pairs([button(_label("race", race), f"r{i}") for i, race in enumerate(RACES)])
        rows.append([button("↩️ Voltar", "backgender")])
    elif step == "class":
        rows = _pairs([button(_label("class", cls), f"c{i}") for i, cls in enumerate(CLASSES)])
        rows.append([button("↩️ Voltar", "races")])
    elif step.startswith(("race:", "class:")):
        race_page = step.startswith("race:")
        kind = "race" if race_page else "class"
        key = step.split(":", 1)[1]
        data = _entity(kind, key)
        text = data["detail"]
        rows = [
            [button(f"{data['emoji']} Escolher {data['name']}", "choose")],
            [button("↩️ Voltar", "races" if race_page else "classes")],
        ]
    elif step == "confirm":
        race = _entity("race", state.race or RACES[0])
        klass = _entity("class", state.character_class or CLASSES[0])
        text = (
            f"{text}\n\n"
            f"👤 **Nome** · `{state.name or ''}`\n"
            f"🎭 **Gênero** · `{(state.gender or '').capitalize()}`\n"
            f"{race['emoji']} **Raça** · `{race['name']}`\n"
            f"⚜️ **Classe** · `{klass['name']}`\n\n"
            f"{SCREENS['confirm_warning']}"
        )
        rows = [
            [button("✅ Confirmar Personagem", "confirm")],
            [button("👤 Nome", "name"), button("🎭 Gênero", "gender")],
            [button("🧿 Raça", "race"), button("⚜️ Classe", "class")],
            [button("↩️ Voltar", "classes")],
        ]
    image_key = step
    if state.gender and step.startswith("race:"):
        image_key = f"char.{step.split(':')[1]}.{state.gender}"
    elif state.gender and state.race and step.startswith("class:"):
        image_key = f"char.{state.race}.{state.gender}.{step.split(':')[1]}"
    return Screen(
        _format_markup(text),
        image_key,
        InlineKeyboardMarkup(inline_keyboard=rows) if rows else None,
        "HTML",
    )
