"""Lossless JSON snapshots. Decimal values never pass through binary floats."""

from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Action, Combat, CombatEvent, DotState, Effect, Fighter, Tutorial
from asterion.domain.combat_math import CombatStats


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def encode(state: Combat) -> dict:
    value = asdict(state)
    for key in ("id", "ruleset", "version"):
        del value[key]
    return _json_value(value)


def decode(payload: dict, combat_id: UUID, ruleset: str, version: int) -> Combat:
    payload = dict(payload)
    payload.pop("dots", None)  # legacy snapshots used a non-authoritative label list
    def action(value):
        return Action(
            **(
                value
                | {
                    "coefficient": Decimal(value["coefficient"]),
                    "attack_debuff": Decimal(value["attack_debuff"]),
                    "per_bonus_if_target_poisoned": Decimal(
                        value.get("per_bonus_if_target_poisoned", "0")
                    ),
                    "self_barrier_coefficient": Decimal(
                        value.get("self_barrier_coefficient", "0")
                    ),
                }
            )
        )

    fighters = {}
    for key, value in payload["fighters"].items():
        fighters[key] = Fighter(
            **(
                value
                | {
                    "hp": Decimal(value["hp"]),
                    "barrier": Decimal(value.get("barrier", "0")),
                    "stats": CombatStats(
                        **{stat: Decimal(number) for stat, number in value["stats"].items()}
                    ),
                    "effects": [
                        Effect(**(effect | {"magnitude": Decimal(effect["magnitude"])}))
                        for effect in value["effects"]
                    ],
                    "damage_taken_modifiers": {
                        kind: Decimal(modifier)
                        for kind, modifier in value.get(
                            "damage_taken_modifiers", {}
                        ).items()
                    },
                }
            )
        )
    tutorial = payload["tutorial"]
    if tutorial:
        tutorial = Tutorial(**(tutorial | {"required_basics": tuple(tutorial["required_basics"])}))
    return Combat(
        **(
            payload
            | {
                "id": combat_id,
                "ruleset": ruleset,
                "version": version,
                "fighters": fighters,
                "player_actions": {
                    key: action(value) for key, value in payload["player_actions"].items()
                },
                "enemy_actions": {
                    key: action(value) for key, value in payload["enemy_actions"].items()
                },
                "ai_cycle": tuple(payload["ai_cycle"]),
                "ai_priority": tuple(payload.get("ai_priority", ())),
                "order": tuple(payload["order"]),
                "tutorial": tutorial,
                "events": [
                    CombatEvent(
                        **(
                            event
                            | {
                                "healed": Decimal(event["healed"]),
                                "barrier_absorbed": Decimal(
                                    event.get("barrier_absorbed", "0")
                                ),
                                "barrier_value": Decimal(event.get("barrier_value", "0")),
                            }
                        )
                    )
                    for event in payload["events"]
                ],
                "dot_states": {
                    target: [
                        DotState(
                            **(
                                dot
                                | {
                                    "snapshot_attack": Decimal(dot["snapshot_attack"]),
                                    "stack_snapshots": [
                                        Decimal(value)
                                        for value in dot.get("stack_snapshots", [])
                                    ],
                                }
                            )
                        )
                        for dot in dots
                    ]
                    for target, dots in payload.get("dot_states", {}).items()
                },
            }
        )
    )
