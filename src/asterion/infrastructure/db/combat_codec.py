"""Lossless JSON snapshots. Decimal values never pass through binary floats."""

from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Action, Combat, CombatEvent, Effect, Fighter, Tutorial
from asterion.domain.combat_math import Stats


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
    def action(value):
        return Action(
            **(
                value
                | {
                    "coefficient": Decimal(value["coefficient"]),
                    "attack_debuff": Decimal(value["attack_debuff"]),
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
                    "stats": Stats(
                        **{stat: Decimal(number) for stat, number in value["stats"].items()}
                    ),
                    "effects": [
                        Effect(**(effect | {"magnitude": Decimal(effect["magnitude"])}))
                        for effect in value["effects"]
                    ],
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
                "order": tuple(payload["order"]),
                "tutorial": tutorial,
                "events": [
                    CombatEvent(**(event | {"healed": Decimal(event["healed"])}))
                    for event in payload["events"]
                ],
            }
        )
    )
