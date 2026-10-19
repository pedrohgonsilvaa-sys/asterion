"""P36 encounter phases and the Regente's two non-economic record anchors."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from asterion.domain.combat import Combat, CombatDamageAura, CombatPhaseTrigger, Fighter
from asterion.domain.combat_math import CombatStats, enemy_stats
from asterion.domain.road import ARCHETYPE, CATEGORY

D = Decimal

REGENT_ID = "boss.confins.regente_fraturado"
ANCHOR_KEYS = ("record_anchor_a", "record_anchor_b")
ANCHOR_IDS = (
    "encounter_element.confins.regente.ancora_registro_a",
    "encounter_element.confins.regente.ancora_registro_b",
)


def configure_regent_encounter(combat: Combat) -> Combat:
    """Attach the source-defined phases and passive, non-rewarding objects."""
    reference = enemy_stats(60, CATEGORY["common"], ARCHETYPE["balanced"])
    for key, element_id, label in zip(
        ANCHOR_KEYS, ANCHOR_IDS, ("A", "B"), strict=True
    ):
        combat.fighters[key] = Fighter(
            id=element_id,
            name=f"Âncora de Registro {label}",
            level=60,
            stats=CombatStats(
                hp=reference.hp * D("0.25"),
                attack=D(0),
                defense=reference.defense,
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

    actions = combat.enemy_actions
    actions["selo_continuidade"] = replace(
        actions["selo_continuidade"],
        cooldown=4,
        max_uses_per_combat=2,
        self_barrier_hp_fraction=D("0.08"),
        self_barrier_duration=-1,
        skip_if_barrier_active=True,
        target_mode="self",
        phase_ids=("I", "II", "III"),
    )
    actions["marca_divergencia"] = replace(
        actions["marca_divergencia"],
        cooldown=3,
        attack_debuff=D("0.12"),
        duration=2,
        effect_stat="defense",
        effect_id="marca_divergencia",
        skip_if_target_effect_active="marca_divergencia",
        phase_ids=("I", "II", "III"),
    )
    actions["leitura_duas_ordens"] = replace(
        actions["leitura_duas_ordens"],
        cooldown=3,
        target_mode="all_opponents",
        phase_ids=("II", "III"),
    )
    actions["ancoragem_conflito"] = replace(
        actions["ancoragem_conflito"],
        cooldown=3,
        phase_ids=("I", "II", "III"),
    )
    actions["desfecho_ultima_ordem"] = replace(
        actions["desfecho_ultima_ordem"],
        cooldown=5,
        prepared=True,
        phase_ids=("III",),
    )
    actions["ordem_sobreposta"] = replace(
        actions["ordem_sobreposta"], phase_ids=("I", "II", "III")
    )

    combat.damage_auras = (
        *combat.damage_auras,
        CombatDamageAura(
            aura_id="confins.regent.record_anchors",
            source_fighter_keys=ANCHOR_KEYS,
            target_fighter_keys=("enemy",),
            reduction_per_source=D("0.05"),
        ),
    )
    combat.phase_id = "I"
    combat.phase_triggers = (
        *combat.phase_triggers,
        CombatPhaseTrigger(
            trigger_id="confins.regent.phase.ii",
            source_fighter_key="enemy",
            hp_fraction_at_most=D("0.70"),
            activate_fighter_keys=ANCHOR_KEYS,
            phase_id="II",
            resolution_id="referencias_incompativeis",
        ),
        CombatPhaseTrigger(
            trigger_id="confins.regent.phase.iii",
            source_fighter_key="enemy",
            hp_fraction_at_most=D("0.35"),
            phase_id="III",
            resolution_id="protocolo_que_nao_pode_concluir",
            consume_active_fighter_keys=ANCHOR_KEYS,
            barrier_source_per_active_fighter_fraction=D("0.05"),
        ),
    )
    combat.ai_priorities["enemy"] = (
        "selo_continuidade",
        "marca_divergencia",
        "desfecho_ultima_ordem",
        "leitura_duas_ordens",
        "ancoragem_conflito",
        "ordem_sobreposta",
    )
    combat.ai_priority = combat.ai_priorities["enemy"]
    combat.party_mode = True
    combat.manual_sides = ("player",)
    return combat
