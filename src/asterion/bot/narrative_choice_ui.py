"""Buttons and approved copy for narrative choice nodes.

Option labels come from the v1.0.0 contract. Future lines come from the
approved Textos de Reação dos NPCs v1.0.0 and reach the screen only after the
application checked that the speaker legitimately knows the choice. Immediate
reactions have no approved copy yet, so that dictionary stays empty. Never
print tags, rapport or any number from the narrative state.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton

from asterion.application.narrative_choices import NarrativeNodeView
from asterion.domain.narrative_choices import ReactionLine

# (choice_id, option_id) -> immediate reaction after committing.
IMMEDIATE_REACTIONS: dict[tuple[str, str], str] = {}



def narrative_option_rows(
    node: NarrativeNodeView | None, callback_prefix: str
) -> list[list[InlineKeyboardButton]]:
    """One row per option; callback ``<prefix>:nc:<option_id>``."""
    if node is None or not node.pending:
        return []
    return [
        [InlineKeyboardButton(text=label, callback_data=f"{callback_prefix}:nc:{option_id}")]
        for option_id, label in node.options
    ]


def immediate_reaction(node: NarrativeNodeView | None) -> str | None:
    if node is None or node.selected_option is None:
        return None
    return IMMEDIATE_REACTIONS.get((node.choice_id, node.selected_option))


def future_reaction(line: ReactionLine) -> str:
    """Speaker and approved line, plain text (callers escape for HTML)."""
    return f"{line.speaker_name}: “{line.text}”"
