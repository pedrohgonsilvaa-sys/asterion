"""Safe resolution of configured image references (Telegram file_id or file:)."""

from __future__ import annotations

import os
from pathlib import Path

from asterion.domain.visuals import VISUAL_BY_COSMETIC, image_key


def assets_root() -> Path:
    return Path(os.environ.get("ASTERION_ASSETS_DIR", "assets")).resolve()


def resolve_asset_file(ref: str, root: Path | None = None) -> Path | None:
    """Return the file for a ``file:`` ref only if it stays inside the assets root.

    Absolute paths, ``..`` escapes and symlinks leaving the root are refused.
    Both ``file:assets/x.png`` and ``file:x.png`` (relative to the root) work.
    """
    base = (root or assets_root()).resolve()
    raw = ref.removeprefix("file:").strip()
    if not raw or "\0" in raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute() or candidate.drive:
        return None
    options = [Path.cwd() / candidate, base / candidate]
    for option in options:
        try:
            resolved = option.resolve()
            resolved.relative_to(base)
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            return resolved
    return None


def visual_image_key(images: dict[str, str], *, cosmetic_id: str) -> str | None:
    """Image key of the visual bound to a cosmetic, only if art is configured."""
    visual = VISUAL_BY_COSMETIC.get(cosmetic_id)
    if visual is None:
        return None
    key = image_key(visual.visual_id)
    return key if images.get(key) else None
