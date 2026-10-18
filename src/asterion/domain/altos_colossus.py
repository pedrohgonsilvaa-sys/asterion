"""P30 encounter rules for the Colosso Cinéreo and its structural Escoras."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from asterion.domain.combat import Combat, CombatDamageAura, CombatPhaseTrigger, Fighter
from asterion.domain.combat_math import CombatStats, enemy_stats
from asterion.domain.road import ARCHETYPE, CATEGORY

D = Decimal

COLOSSUS_ID = "boss.altos.colosso_cinereo"
ESCORA_KEYS = ("escora_a", "escora_b", "escora_c")
ESCORA_IDS = tuple(f"encounter_element.altos.colosso.{key}" for key in ESCORA_KEYS)


def configure_colossus_encounter(combat: Combat) -> Combat:
    """Attach the source-defined phase machine and non-economic encounter elements."""
    reference = enemy_stats(50, CATEGORY["common"], ARCHETYPE["balanced"])
    for key, element_id, suffix in zip(ESCORA_KEYS, ESCORA_IDS, ("A", "B", "C"), strict=True):
        combat.fighters[key] = Fighter(
            id=element_id,
            name=f"Escora de Sustentação {suffix}",
            level=50,
            stats=CombatStats(
                hp=reference.hp * D("0.25"),
                attack=D(0),
                defense=reference.defense * D("0.80"),
                agility=D(0),
                per=D(0),
                crit=D(0),
                evasion=D(0),
                block=D(0),
            ),
            hp=D(0),
            side="enemy",
            takes_turn=False,
            defeat_on_zero=False,
            required_for_victory=False,
            encounter_hidden=True,
        )

    combat.damage_auras = (
        CombatDamageAura(
            aura_id="colosso.escoras.sustentacao",
            source_fighter_keys=ESCORA_KEYS,
            target_fighter_keys=("enemy",),
            reduction_per_source=D("0.04"),
        ),
    )
    combat.phase_id = "phase_i"
    combat.phase_triggers = (
        CombatPhaseTrigger(
            trigger_id="colosso.phase_ii",
            source_fighter_key="enemy",
            hp_fraction_at_most=D("0.70"),
            activate_fighter_keys=ESCORA_KEYS,
            phase_id="phase_ii",
        ),
        CombatPhaseTrigger(
            trigger_id="colosso.phase_iii",
            source_fighter_key="enemy",
            hp_fraction_at_most=D("0.35"),
            phase_id="phase_iii",
            consume_active_fighter_keys=ESCORA_KEYS,
            barrier_source_per_active_fighter_fraction=D("0.03"),
        ),
    )

    actions = combat.enemy_actions
    actions["marca_carga"] = replace(
        actions["marca_carga"],
        effect_id="marca_carga",
        skip_if_target_effect_active="marca_carga",
        phase_ids=("phase_i", "phase_ii", "phase_iii"),
    )
    actions["placa_sustentacao"] = replace(
        actions["placa_sustentacao"],
        self_barrier_hp_fraction=D("0.08"),
        self_barrier_duration=-1,
        skip_if_barrier_active=True,
        max_uses_per_combat=2,
        target_mode="self",
        phase_ids=("phase_i", "phase_ii"),
    )
    actions["varredura_contrapeso"] = replace(
        actions["varredura_contrapeso"],
        target_mode="all_opponents",
        phase_ids=("phase_ii", "phase_iii"),
    )
    actions["carga_distribuida"] = replace(
        actions["carga_distribuida"],
        target_mode="all_opponents",
        phase_ids=("phase_iii",),
        skip_if_actor_last_action=("carga_distribuida",),
    )
    combat.party_mode = True
    combat.manual_sides = ("player",)
    return combat
