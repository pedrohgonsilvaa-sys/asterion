"""Canonical P12 Matriarch combat content on the shared combat engine."""

from __future__ import annotations

from decimal import Decimal

from asterion.domain.combat import (
    Action,
    Combat,
    CombatDamageAura,
    CombatPhaseTrigger,
    Fighter,
)
from asterion.domain.combat_math import CombatStats
from asterion.domain.road import Creature, road_enemy_stats

D = Decimal

CONNECTION_KEYS = (
    "connection_a",
    "connection_b",
    "connection_c",
)
CONNECTION_AURA_ID = "matriarca.connections"
PHASE_II_ID = "matriarca.phase.ii"
PHASE_III_ID = "matriarca.phase.iii"


def configure_matriarch_combat(combat: Combat, *, shared: bool) -> Combat:
    """Install phase actions and dormant targetable connections on a boss fight."""
    boss_key = "enemy"
    combat.phase_id = "I"
    combat.party_mode = True
    if not shared:
        combat.manual_sides = ("player",)

    combat.enemy_actions.update(
        {
            "varredura_raizes": Action(
                "varredura_raizes",
                "Varredura das Raízes",
                D("0.80"),
                cooldown=3,
                target_mode="all_opponents",
                phase_ids=("II", "III"),
            ),
            "abraco_berco": Action(
                "abraco_berco",
                "Abraço do Berço",
                D(0),
                cooldown=5,
                self_barrier_hp_fraction=D("0.08"),
                self_barrier_duration=2,
                skip_if_barrier_active=True,
                max_uses_per_combat=2,
                phase_ids=("II",),
            ),
            "estrangulamento_vale": Action(
                "estrangulamento_vale",
                "Estrangulamento do Vale",
                D("1.80"),
                prepared=True,
                cooldown=5,
                phase_ids=("III",),
            ),
        }
    )
    combat.enemy_actions["raiz_constritiva"] = Action(
        "raiz_constritiva",
        "Raiz Constritiva",
        D("0.90"),
        attack_debuff=D("0.10"),
        duration=2,
        cooldown=3,
        effect_stat="agility",
        effect_id="raiz_constritiva",
        skip_if_target_effect_active="raiz_constritiva",
    )
    combat.enemy_actions["seiva_corrompida"] = Action(
        "seiva_corrompida",
        "Seiva Corrompida",
        D("0.80"),
        cooldown=3,
        native_dot_kind="poison",
        native_dot_stacks=1,
        skip_if_target_dot_at_cap="poison",
    )
    combat.enemy_actions["chicote_radicular"] = Action(
        "chicote_radicular",
        "Chicote Radicular",
        D("1.30"),
        cooldown=3,
    )
    combat.ai_cycles[boss_key] = (
        "golpe_matriarca",
        "raiz_constritiva",
        "seiva_corrompida",
        "chicote_radicular",
        "varredura_raizes",
        "abraco_berco",
        "estrangulamento_vale",
    )
    combat.ai_priorities[boss_key] = (
        "estrangulamento_vale",
        "abraco_berco",
        "varredura_raizes",
        "raiz_constritiva",
        "seiva_corrompida",
        "chicote_radicular",
        "golpe_matriarca",
    )
    combat.ai_cycle = combat.ai_cycles[boss_key]
    combat.ai_priority = combat.ai_priorities[boss_key]

    common = Creature("common_reference", "Comum", "common", "balanced", 20, 20, 0, (), ())
    common_stats = road_enemy_stats(common, 20)
    labels = (
        "Conexão Radicular A",
        "Conexão Radicular B",
        "Conexão Radicular C",
    )
    for key, label in zip(CONNECTION_KEYS, labels, strict=True):
        stats = CombatStats(
            common_stats.hp * D("0.30"),
            D(0),
            common_stats.defense * D("0.90"),
            D(0),
        )
        combat.fighters[key] = Fighter(
            id=key,
            name=label,
            level=20,
            stats=stats,
            hp=D(0),
            side="enemy",
            takes_turn=False,
            defeat_on_zero=False,
            required_for_victory=False,
        )
    combat.damage_auras = (
        CombatDamageAura(
            CONNECTION_AURA_ID,
            CONNECTION_KEYS,
            (boss_key,),
            D("0.04"),
        ),
    )
    combat.phase_triggers = (
        CombatPhaseTrigger(
            PHASE_II_ID,
            boss_key,
            D("0.70"),
            activate_fighter_keys=CONNECTION_KEYS,
            phase_id="II",
        ),
        CombatPhaseTrigger(
            PHASE_III_ID,
            boss_key,
            D("0.35"),
            phase_id="III",
        ),
    )
    return combat


def matriarch_phase_evidence(combat: Combat) -> tuple[str, ...]:
    evidence: set[str] = set()
    if PHASE_II_ID in combat.phase_triggered_ids:
        evidence.add("phase:a_rede")
        evidence.add("mechanic:conexoes_radicular_observadas")
    if PHASE_III_ID in combat.phase_triggered_ids:
        evidence.add("phase:aquilo_que_permanece")
    if any(
        event.actor_entity_id == "enemy"
        and event.action.removeprefix("prepare:") == "abraco_berco"
        for event in combat.events
    ):
        evidence.add("action:abraco_do_berco")
    if any(
        event.actor_entity_id == "enemy"
        and event.action.removeprefix("prepare:") == "estrangulamento_vale"
        for event in combat.events
    ):
        evidence.add("action:estrangulamento_do_vale")
    return tuple(sorted(evidence))
