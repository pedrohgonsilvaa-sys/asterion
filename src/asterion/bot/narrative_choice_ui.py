"""Buttons and approved copy for narrative choice nodes.

Only option labels from the v1.0.0 contract are shown. NPC reactions and
future lines are editorial content: until the author approves them, the
dictionaries below stay empty and the screen keeps its canonical text. Never
print tags, rapport or any number from the narrative state.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton

from asterion.application.narrative_choices import NarrativeNodeView

# (choice_id, option_id) -> immediate reaction after committing.
IMMEDIATE_REACTIONS: dict[tuple[str, str], str] = {}
# (hook_id, option_id) -> line a later scene adds when the hook resolves.
FUTURE_REACTIONS: dict[tuple[str, str], str] = {}


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


def future_reaction(hook_id: str, option_id: str | None) -> str | None:
    if option_id is None:
        return None
    return FUTURE_REACTIONS.get((hook_id, option_id))
