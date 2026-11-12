"""Pure rules for public Crafting Services offered through a Personal Shop.

Sources: GDD Estrutural v1.6.0 §27.3, §28.16, §49.10 and §49.11.

Author decisions (2026-11-11, delegated) for points the GDD leaves open:
- the Tesouraria Obra of the artisan's Guilda lowers the Service fee too, fixed
  on the offer when it is created, as it does for item listings;
- the client pays the Recipe's Crafting fee on top of the Service price; the
  Arquivo do Véu discount comes from the artisan's Guilda;
- the artisan earns PXP exactly as in a normal Craft;
- the client must stand at a safe crafting location, outside any foreground
  activity; the artisan may be offline, fighting or anywhere else.
"""

from __future__ import annotations

from datetime import timedelta
from hashlib import sha256

from asterion.domain.professions import RecipeDefinition
from asterion.domain.road import RARITY_SECONDARIES

SERVICE_SLOTS = 3
SERVICE_DURATION = timedelta(days=7)
# Same window as an item purchase preview (domain/market.py); not a game value.
SERVICE_PREVIEW_TTL = timedelta(minutes=5)

# Outputs a Service can deliver. Enchantments apply to an existing equipment and
# are out of scope until that flow exists for a third party.
SERVICE_OUTPUT_KINDS = frozenset(("equipment", "consumable", "rune"))


def recipe_offerable(recipe: RecipeDefinition) -> bool:
    return recipe.output_kind in SERVICE_OUTPUT_KINDS and recipe.creation_enabled


def recipe_signature(recipe: RecipeDefinition) -> str:
    """Changes when a patch changes the Recipe materially (§27.3 suspension)."""
    return sha256(repr(recipe).encode()).hexdigest()


def service_title(recipe: RecipeDefinition) -> str:
    return recipe.output_name or recipe.name


def guaranteed_secondaries(recipe: RecipeDefinition) -> int | None:
    """§27.2/§27.3 preview: how many secondaries are rolled at commit, if any."""
    if recipe.output_kind != "equipment":
        return None
    return RARITY_SECONDARIES.get(recipe.rarity or "Comum", 0)
