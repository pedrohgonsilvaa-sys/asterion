"""Canonical campaign-boss combat rules for the Nareth climax."""

from __future__ import annotations

from decimal import Decimal

from asterion.domain.combat import (
    Action,
    Combat,
    CombatPhaseTrigger,
    CombatStatAura,
    Fighter,
)
from asterion.domain.combat_math import CombatStats
from asterion.domain.road import Creature, road_enemy_stats

D = Decimal

ARCHON_AXES = ("axis_carga", "axis_guarda", "axis_ritmo")
ARCHON_PHASE_II = "nareth.arconte.phase.ii"
ARCHON_PHASE_III = "nareth.arconte.phase.iii"


def configure_nareth_campaign_boss(combat: Combat, creature_id: str, *, shared: bool) -> Combat:
    """Install the source-defined Nareth boss actions and mechanics."""
    combat.party_mode = True
    if not shared:
        combat.manual_sides = ("player",)
    if creature_id == "custodio_sem_norte":
        _configure_custodio(combat)
    elif creature_id == "arconte_invertido":
        _configure_archon(combat)
    else:
        raise ValueError(f"Not a Nareth campaign boss: {creature_id}")
    return combat


def _configure_custodio(combat: Combat) -> None:
    combat.phase_id = "I"
    combat.enemy_actions.update(
        {
            "golpe_marco": Action("golpe_marco", "Golpe de Marco", D("1.00")),
            "rota_negada": Action(
                "rota_negada", "Rota Negada", D("0.90"), cooldown=3,
                attack_debuff=D("0.10"), duration=2, effect_stat="agility",
                effect_id="rota_negada", skip_if_target_effect_active="rota_negada",
            ),
            "correcao_cega": Action(
                "correcao_cega", "Correção Cega", D("1.25"), cooldown=3,
            ),
            "queda_sem_norte": Action(
                "queda_sem_norte", "Queda sem Norte", D("1.70"),
                prepared=True, cooldown=4,
            ),
        }
    )
    combat.ai_cycles["enemy"] = (
        "golpe_marco", "rota_negada", "correcao_cega", "queda_sem_norte",
    )
    combat.ai_priorities["enemy"] = (
        "queda_sem_norte", "rota_negada", "correcao_cega", "golpe_marco",
    )
    combat.ai_cycle = combat.ai_cycles["enemy"]
    combat.ai_priority = combat.ai_priorities["enemy"]


def _configure_archon(combat: Combat) -> None:
    boss = "enemy"
    combat.phase_id = "I"
    combat.enemy_actions.update(
        {
            "golpe_diretiva": Action("golpe_diretiva", "Golpe de Diretiva", D("1.00")),
            "correcao_coordenada": Action(
                "correcao_coordenada", "Correção de Coordenada", D("0.90"),
                cooldown=3, attack_debuff=D("0.10"), duration=2,
                effect_stat="defense", effect_id="correcao_coordenada",
                skip_if_target_effect_active="correcao_coordenada",
            ),
            "deslocamento_medido": Action(
                "deslocamento_medido", "Deslocamento Medido", D("0.85"),
                cooldown=3, attack_debuff=D("0.10"), duration=2,
                effect_stat="agility", effect_id="deslocamento_medido",
                skip_if_target_effect_active="deslocamento_medido",
            ),
            "ordem_invertida": Action(
                "ordem_invertida", "Ordem Invertida", D("1.30"), cooldown=3,
            ),
            "varredura_meridiano": Action(
                "varredura_meridiano", "Varredura do Meridiano", D("0.80"),
                cooldown=3, target_mode="all_opponents", phase_ids=("II", "III"),
            ),
            "protocolo_continuidade": Action(
                "protocolo_continuidade", "Protocolo de Continuidade", D(0),
                cooldown=5, self_barrier_hp_fraction=D("0.08"),
                self_barrier_duration=2, skip_if_barrier_active=True,
                max_uses_per_combat=2, phase_ids=("II",),
            ),
            "retificacao_final": Action(
                "retificacao_final", "Retificação Final", D("1.80"),
                prepared=True, cooldown=5, phase_ids=("III",),
            ),
        }
    )
    combat.ai_cycles[boss] = (
        "golpe_diretiva", "correcao_coordenada", "deslocamento_medido",
        "ordem_invertida", "varredura_meridiano", "protocolo_continuidade",
        "retificacao_final",
    )
    combat.ai_priorities[boss] = (
        "retificacao_final", "protocolo_continuidade", "varredura_meridiano",
        "correcao_coordenada", "deslocamento_medido", "ordem_invertida",
        "golpe_diretiva",
    )
    combat.ai_cycle = combat.ai_cycles[boss]
    combat.ai_priority = combat.ai_priorities[boss]

    common = Creature("nareth_common_30", "Comum", "common", "balanced", 30, 30, 0, (), ())
    common_stats = road_enemy_stats(common, 30)
    for key, label in zip(
        ARCHON_AXES,
        ("Eixo de Carga", "Eixo de Guarda", "Eixo de Ritmo"),
        strict=True,
    ):
        stats = CombatStats(
            common_stats.hp * D("0.30"), D(0), common_stats.defense * D("0.90"), D(0)
        )
        combat.fighters[key] = Fighter(
            id=key, name=label, level=30, stats=stats, hp=D(0), side="enemy",
            takes_turn=False, defeat_on_zero=False, required_for_victory=False,
        )
    combat.stat_auras = (
        CombatStatAura("nareth.arconte.carga", "attack", (ARCHON_AXES[0],), (boss,), D("0.05")),
        CombatStatAura("nareth.arconte.guarda", "defense", (ARCHON_AXES[1],), (boss,), D("0.05")),
        CombatStatAura("nareth.arconte.ritmo", "agility", (ARCHON_AXES[2],), (boss,), D("0.05")),
    )
    combat.phase_triggers = (
        CombatPhaseTrigger(
            ARCHON_PHASE_II, boss, D("0.70"),
            activate_fighter_keys=ARCHON_AXES, phase_id="II",
        ),
        CombatPhaseTrigger(ARCHON_PHASE_III, boss, D("0.35"), phase_id="III"),
    )


def nareth_boss_phase_evidence(combat: Combat) -> tuple[str, ...]:
    evidence: set[str] = set()
    is_archon = "protocolo_continuidade" in combat.enemy_actions
    if is_archon and ARCHON_PHASE_II in combat.phase_triggered_ids:
        evidence.update(
            {
                "phase:corrigir_o_que_permanece",
                "mechanic:eixo_carga_observado",
                "mechanic:eixo_guarda_observado",
                "mechanic:eixo_ritmo_observado",
            }
        )
    if is_archon and ARCHON_PHASE_III in combat.phase_triggered_ids:
        evidence.add("phase:a_medida_impossivel")
    observed = {
        "protocolo_continuidade": "action:protocolo_de_continuidade",
        "retificacao_final": "action:retificacao_final",
    }
    for action_id, evidence_id in observed.items():
        if any(
            event.actor_entity_id == "enemy"
            and event.action.removeprefix("prepare:") == action_id
            for event in combat.events
        ):
            evidence.add(evidence_id)
    if not is_archon and "queda_sem_norte" in combat.enemy_actions:
        if any(
            event.actor_entity_id == "enemy" and event.action == "prepare:queda_sem_norte"
            for event in combat.events
        ):
            evidence.add("mechanic:queda_sem_norte_telegraph")
        if any(
            event.actor_entity_id == "enemy"
            and event.action == "queda_sem_norte"
            and event.prepared_resolution
            for event in combat.events
        ):
            evidence.add("mechanic:queda_sem_norte_resolved")
    if any(
        combat.fighters.get(key) is not None
        and combat.fighters[key].hp > 0
        for key in ARCHON_AXES
    ):
        evidence.add("mechanic:eixos_contraditorios_observados")
    return tuple(sorted(evidence))
