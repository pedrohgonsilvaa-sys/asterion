"""Runtime actions for Path Arts implemented by the shared combat engine.

The Action value is the shared combat contract, so a Path Art can declare the
same direct, area, multi-hit, healing, barrier, resource and target behaviors
as any other active Art. This registry intentionally contains only shipped
actions; canonical-but-unimplemented Path Arts are not equipable.
"""

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from asterion.domain.arts import DEVASTADOR_ART_IDS
from asterion.domain.combat import Action


@dataclass(frozen=True, slots=True)
class PathArtActionDefinition:
    art_id: str
    character_class: str
    path_id: str
    action: Action


ARIETE_ART_ID = DEVASTADOR_ART_IDS["ariete"]

PATH_ART_ACTIONS = MappingProxyType(
    {
        ARIETE_ART_ID: PathArtActionDefinition(
            art_id=ARIETE_ART_ID,
            character_class="sentinela",
            path_id="devastador",
            action=Action(
                ARIETE_ART_ID,
                "Aríete",
                Decimal("1.35"),
                cooldown=2,
                actor_per_bonus=Decimal(10),
            ),
        )
    }
)


def path_player_actions(
    character_class: str,
    selected_path: str | None,
    art_ids: tuple[str, ...],
) -> dict[str, Action]:
    """Resolve only equipped, implemented Path Arts for the frozen Path."""
    if len(art_ids) > 3 or len(set(art_ids)) != len(art_ids):
        raise ValueError("Path Art configuration accepts at most three unique Arts.")
    actions: dict[str, Action] = {}
    for art_id in art_ids:
        definition = PATH_ART_ACTIONS.get(art_id)
        if (
            definition is None
            or definition.character_class != character_class
            or definition.path_id != selected_path
        ):
            raise ValueError("Unknown or ineligible Path Art in combat configuration.")
        actions[art_id] = definition.action
    return actions
