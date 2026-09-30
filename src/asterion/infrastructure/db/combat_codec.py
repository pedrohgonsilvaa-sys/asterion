"""Lossless JSON snapshots. Decimal values never pass through binary floats."""

from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import (
    Action,
    ActionEffect,
    Combat,
    CombatEvent,
    DotState,
    Effect,
    Fighter,
    Tutorial,
)
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
                    "self_barrier_debuff_magnitude_reduction": Decimal(
                        value.get("self_barrier_debuff_magnitude_reduction", "0")
                    ),
                    "self_effect_magnitude": Decimal(
                        value.get("self_effect_magnitude", "0")
                    ),
                    "heal_coefficient": Decimal(
                        value.get("heal_coefficient", "0")
                    ),
                    "target_barrier_coefficient": Decimal(
                        value.get("target_barrier_coefficient", "0")
                    ),
                    "target_barrier_debuff_magnitude_reduction": Decimal(
                        value.get("target_barrier_debuff_magnitude_reduction", "0")
                    ),
                    "next_direct_crit_bonus": Decimal(
                        value.get("next_direct_crit_bonus", "0")
                    ),
                    "crit_bonus_if_target_debuffed": Decimal(
                        value.get("crit_bonus_if_target_debuffed", "0")
                    ),
                    "self_effects": tuple(
                        ActionEffect(
                            **(effect | {"magnitude": Decimal(effect["magnitude"])})
                        )
                        for effect in value.get("self_effects", ())
                    ),
                    "target_effects": tuple(
                        ActionEffect(
                            **(effect | {"magnitude": Decimal(effect["magnitude"])})
                        )
                        for effect in value.get("target_effects", ())
                    ),
                    "self_state_tags_after": (
                        tuple(value["self_state_tags_after"])
                        if value.get("self_state_tags_after") is not None
                        else None
                    ),
                    "chain_power_bonus": Decimal(value.get("chain_power_bonus", "0")),
                    "chain_power_bonus_damage": (
                        Decimal(value["chain_power_bonus_damage"])
                        if value.get("chain_power_bonus_damage") is not None
                        else None
                    ),
                    "chain_power_bonus_healing": (
                        Decimal(value["chain_power_bonus_healing"])
                        if value.get("chain_power_bonus_healing") is not None
                        else None
                    ),
                    "chain_power_bonus_barrier": (
                        Decimal(value["chain_power_bonus_barrier"])
                        if value.get("chain_power_bonus_barrier") is not None
                        else None
                    ),
                    "prepares_chain_duration": int(
                        value.get("prepares_chain_duration", 2)
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
                    "barrier_debuff_magnitude_reduction": Decimal(
                        value.get("barrier_debuff_magnitude_reduction", "0")
                    ),
                    "protection_reduction_per_layer": Decimal(
                        value.get("protection_reduction_per_layer", "0")
                    ),
                    "protection_layers": int(value.get("protection_layers", 0)),
                    "training_state_tags": tuple(value.get("training_state_tags", ())),
                    "tagged_direct_damage_reductions": {
                        tag: Decimal(reduction)
                        for tag, reduction in value.get(
                            "tagged_direct_damage_reductions", {}
                        ).items()
                    },
                    "action_chains": value.get("action_chains", {}),
                    "next_direct_crit_bonus": Decimal(
                        value.get("next_direct_crit_bonus", "0")
                    ),
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

    def combat_event(event):
        return CombatEvent(
            **(
                event
                | {
                    "healed": Decimal(event["healed"]),
                    "barrier_absorbed": Decimal(event.get("barrier_absorbed", "0")),
                    "barrier_value": Decimal(event.get("barrier_value", "0")),
                    "power_multiplier": Decimal(event.get("power_multiplier", "1")),
                    "damage_power_multiplier": Decimal(
                        event.get("damage_power_multiplier", "1")
                    ),
                    "healing_power_multiplier": Decimal(
                        event.get("healing_power_multiplier", "1")
                    ),
                    "barrier_power_multiplier": Decimal(
                        event.get("barrier_power_multiplier", "1")
                    ),
                    "applied_effect_magnitude": Decimal(
                        event.get("applied_effect_magnitude", "0")
                    ),
                    "actor_applied_effect_magnitude": Decimal(
                        event.get("actor_applied_effect_magnitude", "0")
                    ),
                    "base_healing": Decimal(event.get("base_healing", "0")),
                    "calculated_healing": Decimal(
                        event.get("calculated_healing", "0")
                    ),
                    "effective_healing": Decimal(
                        event.get("effective_healing", event.get("healed", "0"))
                    ),
                    "healing_received_multiplier": Decimal(
                        event.get("healing_received_multiplier", "1")
                    ),
                    "overheal": Decimal(event.get("overheal", "0")),
                    "target_hp_after": (
                        Decimal(event["target_hp_after"])
                        if event.get("target_hp_after") is not None
                        else None
                    ),
                    "actor_effect_facts": tuple(
                        (
                            str(row[0]),
                            str(row[1]),
                            Decimal(row[2]),
                            int(row[3]),
                            str(row[4]),
                        )
                        for row in event.get("actor_effect_facts", ())
                    ),
                    "fighter_hp_after": tuple(
                        (str(row[0]), Decimal(row[1]))
                        for row in event.get("fighter_hp_after", ())
                    ),
                    "calculated_damage": int(event.get("calculated_damage", 0)),
                    "effective_damage": int(event.get("effective_damage", 0)),
                    "target_effect_ids": tuple(event.get("target_effect_ids", ())),
                    "actor_effect_ids": tuple(event.get("actor_effect_ids", ())),
                    "target_state_tags": tuple(event.get("target_state_tags", ())),
                    "target_effect_application_event_ids": tuple(
                        event.get("target_effect_application_event_ids", ())
                    ),
                }
            )
        )

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
                "ai_target_cycle": tuple(payload.get("ai_target_cycle", ())),
                "order": tuple(payload["order"]),
                "tutorial": tutorial,
                "events": [combat_event(event) for event in payload["events"]],
                "mechanic_events": [
                    combat_event(event) for event in payload.get("mechanic_events", ())
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
