"""Visual/skin catalog (A6): presentation-only art bound to an appearance cosmetic.

A visual never carries game rules and never reads or infers ``weapon_family``
or other mechanical metadata (Weapon Metadata contract v1.0.0). Artwork is not bundled: the image of a visual
comes from configuration under the key ``image_key(visual_id)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VISUAL_KINDS = ("appearance",)
_VISUAL_ID = re.compile(r"^visual\.[a-z0-9_]+(\.[a-z0-9_]+)*$")


def image_key(visual_id: str) -> str:
    """Key of the configured image (``creation_images``) for a visual."""
    return visual_id


@dataclass(frozen=True, slots=True)
class VisualDefinition:
    visual_id: str
    kind: str
    name: str
    # Appearance visuals: the owned cosmetic (type "appearance") that unlocks it.
    cosmetic_id: str | None = None


def validate_visuals(visuals: tuple[VisualDefinition, ...], cosmetic_types: dict[str, str]) -> None:
    """Raise ValueError when the catalog is inconsistent."""
    seen: set[str] = set()
    bound: set[str] = set()
    for visual in visuals:
        if not _VISUAL_ID.match(visual.visual_id):
            raise ValueError(f"invalid visual id: {visual.visual_id!r}")
        if visual.visual_id in seen:
            raise ValueError(f"duplicate visual id: {visual.visual_id}")
        seen.add(visual.visual_id)
        if visual.kind not in VISUAL_KINDS:
            raise ValueError(f"unknown visual kind: {visual.kind}")
        if not visual.name.strip():
            raise ValueError(f"visual without name: {visual.visual_id}")
        if visual.cosmetic_id is None:
            raise ValueError(f"appearance visual needs cosmetic_id: {visual.visual_id}")
        if cosmetic_types.get(visual.cosmetic_id) != "appearance":
            raise ValueError(f"cosmetic is not an appearance: {visual.cosmetic_id}")
        binding = visual.cosmetic_id
        if binding in bound:
            raise ValueError(f"binding already used: {binding}")
        bound.add(binding)


# No artwork or skin is defined by the Source yet: the catalog starts empty.
VISUALS: tuple[VisualDefinition, ...] = ()
VISUALS_BY_ID = {visual.visual_id: visual for visual in VISUALS}
VISUAL_BY_COSMETIC = {v.cosmetic_id: v for v in VISUALS if v.cosmetic_id is not None}
