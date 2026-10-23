"""Runtime actions for Path Arts implemented by the shared combat engine.

The Action value is the shared combat contract, so a Path Art can declare the
same direct, area, multi-hit, healing, barrier, resource and target behaviors
as any other active Art. This registry intentionally contains only shipped
actions; canonical-but-unimplemented Path Arts are not equipable.
"""

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from asterion.domain.arts import (
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    DEVASTADOR_ART_IDS,
    SABOTADOR_ART_IDS,
)
from asterion.domain.combat import (
    Action,
    ActionCondition,
    ActionConditionalModifier,
)


@dataclass(frozen=True, slots=True)
class PathArtActionDefinition:
    art_id: str
    character_class: str
    path_id: str
    action: Action


ARIETE_ART_ID = DEVASTADOR_ART_IDS["ariete"]
ESCUDO_DE_CINZAS_ART_ID = BASTIAO_ART_IDS["escudo_de_cinzas"]
CORTE_DE_EXECUCAO_ART_ID = CARRASCO_ART_IDS["corte_de_execucao"]
VENENO_VELADO_ART_ID = SABOTADOR_ART_IDS["veneno_velado"]

PATH_ART_ACTIONS = MappingProxyType(
    {
        ESCUDO_DE_CINZAS_ART_ID: PathArtActionDefinition(
            art_id=ESCUDO_DE_CINZAS_ART_ID,
            character_class="sentinela",
            path_id="bastiao",
            action=Action(
                ESCUDO_DE_CINZAS_ART_ID,
                "Escudo de Cinzas",
                Decimal(0),
                cooldown=3,
                target_mode="self",
                self_barrier_coefficient=Decimal("0.95"),
                self_barrier_duration=2,
            ),
        ),
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
        ),
        CORTE_DE_EXECUCAO_ART_ID: PathArtActionDefinition(
            art_id=CORTE_DE_EXECUCAO_ART_ID,
            character_class="errante",
            path_id="carrasco",
            action=Action(
                CORTE_DE_EXECUCAO_ART_ID,
                "Corte de Execução",
                Decimal("1.35"),
                cooldown=3,
                conditional_modifiers=(
                    ActionConditionalModifier(
                        "errante.corte_de_execucao.low_hp_power",
                        ActionCondition(
                            "target_hp_fraction_at_most", threshold=Decimal("0.35")
                        ),
                        "damage_power",
                        Decimal("0.15"),
                        operation="multiply",
                    ),
                ),
            ),
        ),
        VENENO_VELADO_ART_ID: PathArtActionDefinition(
            art_id=VENENO_VELADO_ART_ID,
            character_class="errante",
            path_id="sabotador",
            action=Action(
                VENENO_VELADO_ART_ID,
                "Veneno Velado",
                Decimal("0.85"),
                cooldown=2,
                native_dot_kind="poison",
                native_dot_stacks=1,
            ),
        ),
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
