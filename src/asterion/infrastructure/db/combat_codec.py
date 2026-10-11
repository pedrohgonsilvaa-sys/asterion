"""Lossless JSON snapshots. Decimal values never pass through binary floats."""

from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import (
    Action,
    ActionEffect,
    Combat,
    CombatDamageAura,
    CombatEvent,
    CombatPhaseTrigger,
    CombatStatAura,
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
    if isinstance(value, (tuple, list, set, frozenset)):
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
                    "vampirism_fraction": Decimal(value.get("vampirism_fraction", "0")),
                    "actor_per_bonus": Decimal(value.get("actor_per_bonus", "0")),
                    "actor_per_bonus_if_target_bleeding": Decimal(
                        value.get("actor_per_bonus_if_target_bleeding", "0")
                    ),
                    "actor_per_bonus_if_target_hp_fraction_at_most": Decimal(
                        value.get("actor_per_bonus_if_target_hp_fraction_at_most", "0")
                    ),
                    "actor_per_bonus_hp_fraction_threshold": Decimal(
                        value.get("actor_per_bonus_hp_fraction_threshold", "0.40")
                    ),
                    "self_barrier_coefficient": Decimal(
                        value.get("self_barrier_coefficient", "0")
                    ),
                    "self_barrier_hp_fraction": Decimal(
                        value.get("self_barrier_hp_fraction", "0")
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
                    "enemy_hp_fraction_below": (
                        Decimal(value["enemy_hp_fraction_below"])
                        if value.get("enemy_hp_fraction_below") is not None
                        else None
                    ),
                    "enemy_hp_fraction_at_most": (
                        Decimal(value["enemy_hp_fraction_at_most"])
                        if value.get("enemy_hp_fraction_at_most") is not None
                        else None
                    ),
                    "phase_ids": tuple(value.get("phase_ids", ())),
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
                    "revive_fighter_keys": tuple(value.get("revive_fighter_keys", ())),
                    "requires_defeated_fighter_keys": tuple(
                        value.get("requires_defeated_fighter_keys", ())
                    ),
                    "revive_hp_fraction": Decimal(
                        value.get("revive_hp_fraction", "0.50")
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
                    "talent_ids": tuple(value.get("talent_ids", ())),
                    "tagged_direct_damage_reductions": {
                        tag: Decimal(reduction)
                        for tag, reduction in value.get(
                            "tagged_direct_damage_reductions", {}
                        ).items()
                    },
                    "action_chains": value.get("action_chains", {}),
                    "action_use_counts": {
                        key: int(count)
                        for key, count in value.get("action_use_counts", {}).items()
                    },
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
                    "path_power_multiplier": Decimal(
                        event.get("path_power_multiplier", "1")
                    ),
                    "path_final_damage_bonus": Decimal(
                        event.get("path_final_damage_bonus", "0")
                    ),
                    "path_per_bonus": Decimal(event.get("path_per_bonus", "0")),
                    "path_crit_bonus": Decimal(event.get("path_crit_bonus", "0")),
                    "pressure_stacks": int(event.get("pressure_stacks", 0)),
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
                    "path_triggers": tuple(event.get("path_triggers", ())),
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
                "player_actions_by_fighter": {
                    str(fighter_key): {
                        key: action(value) for key, value in actions.items()
                    }
                    for fighter_key, actions in payload.get(
                        "player_actions_by_fighter", {}
                    ).items()
                },
                "enemy_actions": {
                    key: action(value) for key, value in payload["enemy_actions"].items()
                },
                "ai_cycle": tuple(payload["ai_cycle"]),
                "ai_priority": tuple(payload.get("ai_priority", ())),
                "ai_target_cycle": tuple(payload.get("ai_target_cycle", ())),
                "ai_cycles": {
                    str(key): tuple(value)
                    for key, value in payload.get("ai_cycles", {}).items()
                },
                "ai_positions": {
                    str(key): int(value)
                    for key, value in payload.get("ai_positions", {}).items()
                },
                "ai_priorities": {
                    str(key): tuple(value)
                    for key, value in payload.get("ai_priorities", {}).items()
                },
                "pressure_start_opportunity": int(
                    payload.get("pressure_start_opportunity", 0)
                ),
                "pressure_cap": int(payload.get("pressure_cap", 0)),
                "pressure_step": Decimal(payload.get("pressure_step", "0.03")),
                "pressure_stacks": int(payload.get("pressure_stacks", 0)),
                "stat_auras": tuple(
                    CombatStatAura(
                        **(
                            aura
                            | {
                                "source_fighter_keys": tuple(
                                    aura.get("source_fighter_keys", ())
                                ),
                                "target_fighter_keys": tuple(
                                    aura.get("target_fighter_keys", ())
                                ),
                                "multiplier_per_source": Decimal(
                                    aura.get("multiplier_per_source", "0")
                                ),
                            }
                        )
                    )
                    for aura in payload.get("stat_auras", ())
                ),
                "damage_auras": tuple(
                    CombatDamageAura(
                        **(
                            aura
                            | {
                                "source_fighter_keys": tuple(
                                    aura.get("source_fighter_keys", ())
                                ),
                                "target_fighter_keys": tuple(
                                    aura.get("target_fighter_keys", ())
                                ),
                                "reduction_per_source": Decimal(
                                    aura.get("reduction_per_source", "0")
                                ),
                                "reduction_mode": aura.get(
                                    "reduction_mode", "per_source"
                                ),
                                "barrier_received_per_source": Decimal(
                                    aura.get("barrier_received_per_source", "0")
                                ),
                            }
                        )
                    )
                    for aura in payload.get("damage_auras", ())
                ),
                "phase_triggers": tuple(
                    CombatPhaseTrigger(
                        **(
                            trigger
                            | {
                                "hp_fraction_at_most": Decimal(
                                    trigger["hp_fraction_at_most"]
                                ),
                                "activate_fighter_keys": tuple(
                                    trigger.get("activate_fighter_keys", ())
                                ),
                                "revive_fighter_keys": tuple(
                                    trigger.get("revive_fighter_keys", ())
                                ),
                                "revive_hp_fraction": Decimal(
                                    trigger.get("revive_hp_fraction", "0.50")
                                ),
                                "phase_id": trigger.get("phase_id"),
                            }
                        )
                    )
                    for trigger in payload.get("phase_triggers", ())
                ),
                "phase_triggered_ids": set(payload.get("phase_triggered_ids", ())),
                "phase_id": payload.get("phase_id", "default"),
                "party_mode": bool(payload.get("party_mode", False)),
                "manual_sides": tuple(payload.get("manual_sides", ())),
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
