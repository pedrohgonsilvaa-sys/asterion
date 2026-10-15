"""Canonical Várzeas campaign-boss combat rules."""

from __future__ import annotations

from decimal import Decimal

from asterion.domain.combat import Action, Combat, CombatPhaseTrigger

D = Decimal

MATRIX_PHASE_II = "varzeas.matriz.phase.ii"
MATRIX_PHASE_III = "varzeas.matriz.phase.iii"


def configure_varzeas_campaign_boss(
    combat: Combat, creature_id: str, *, shared: bool
) -> Combat:
    """Install only the published phase and action behavior for Várzeas bosses."""
    combat.party_mode = True
    if not shared:
        combat.manual_sides = ("player",)
    if creature_id == "matriz_rubra":
        _configure_matrix(combat)
    elif creature_id == "custodio_quarentena":
        _configure_quarantine_custodian(combat)
    else:
        raise ValueError(f"Not a Várzeas campaign boss: {creature_id}")
    return combat


def _configure_matrix(combat: Combat) -> None:
    boss = combat.fighters["enemy"]
    combat.phase_id = "I"
    heal_coefficient = boss.stats.hp * D("0.04") / boss.stats.attack
    combat.enemy_actions.update(
        {
            "pulso_regulador": Action(
                "pulso_regulador", "Pulso Regulador", D("0.80"),
                cooldown=3, target_mode="all_opponents",
            ),
            "coleta_dirigida": Action(
                "coleta_dirigida", "Coleta Dirigida", D("1.00"),
                cooldown=3, attack_debuff=D("0.10"), duration=2,
                effect_stat="defense", effect_id="coleta_dirigida",
                skip_if_target_effect_active="coleta_dirigida",
            ),
            "membrana_contencao": Action(
                "membrana_contencao", "Membrana de Contenção", D(0),
                cooldown=4, target_mode="self", self_barrier_hp_fraction=D("0.08"),
                self_barrier_duration=2, skip_if_barrier_active=True,
                skip_if_actor_last_action=("sobrecarga_matriz",),
            ),
            "transferencia_externa": Action(
                "transferencia_externa", "Transferência Externa", D("1.65"),
                prepared=True, cooldown=4,
            ),
            "regulacao_emergencia": Action(
                "regulacao_emergencia", "Regulação de Emergência", D(0),
                cooldown=4, phase_ids=("II",), target_mode="self",
                heal_coefficient=heal_coefficient, max_uses_per_combat=3,
                skip_if_barrier_active=True,
            ),
            "sobrecarga_matriz": Action(
                "sobrecarga_matriz", "Sobrecarga da Matriz", D("1.10"),
                prepared=True, cooldown=5, phase_ids=("III",),
                target_mode="all_opponents",
                skip_if_actor_last_action=("membrana_contencao",),
            ),
            "triagem_terminal": Action(
                "triagem_terminal", "Triagem Terminal", D("1.35"),
                cooldown=3, phase_ids=("III",),
                actor_per_bonus_if_target_hp_fraction_at_most=D("0.10"),
                actor_per_bonus_hp_fraction_threshold=D("0.40"),
            ),
        }
    )
    combat.ai_cycles["enemy"] = (
        "pulso_regulador", "coleta_dirigida", "membrana_contencao",
        "transferencia_externa", "regulacao_emergencia", "sobrecarga_matriz",
        "triagem_terminal",
    )
    combat.ai_priorities["enemy"] = (
        "triagem_terminal", "sobrecarga_matriz", "regulacao_emergencia",
        "transferencia_externa", "coleta_dirigida", "pulso_regulador",
        "membrana_contencao",
    )
    combat.ai_cycle = combat.ai_cycles["enemy"]
    combat.ai_priority = combat.ai_priorities["enemy"]
    combat.phase_triggers = (
        CombatPhaseTrigger(
            MATRIX_PHASE_II, "enemy", D("0.70"), phase_id="II"
        ),
        CombatPhaseTrigger(
            MATRIX_PHASE_III, "enemy", D("0.35"), phase_id="III"
        ),
    )


def _configure_quarantine_custodian(combat: Combat) -> None:
    combat.phase_id = "I"
    combat.enemy_actions.update(
        {
            "golpe_isolamento": Action(
                "golpe_isolamento", "Golpe de Isolamento", D("1.00")
            ),
            "rota_selada": Action(
                "rota_selada", "Rota Selada", D("0.90"), cooldown=3,
                attack_debuff=D("0.10"), duration=2, effect_stat="agility",
                effect_id="rota_selada", skip_if_target_effect_active="rota_selada",
            ),
            "correcao_perimetro": Action(
                "correcao_perimetro", "Correção de Perímetro", D("1.25"),
                cooldown=3,
            ),
            "fecho_quarentena": Action(
                "fecho_quarentena", "Fecho de Quarentena", D("1.75"),
                prepared=True, cooldown=4,
            ),
        }
    )
    combat.ai_cycles["enemy"] = (
        "golpe_isolamento", "rota_selada", "correcao_perimetro", "fecho_quarentena"
    )
    combat.ai_priorities["enemy"] = (
        "fecho_quarentena", "rota_selada", "correcao_perimetro", "golpe_isolamento"
    )
    combat.ai_cycle = combat.ai_cycles["enemy"]
    combat.ai_priority = combat.ai_priorities["enemy"]
    combat.phase_triggers = ()


def varzeas_boss_phase_evidence(combat: Combat) -> tuple[str, ...]:
    evidence: set[str] = set()
    if MATRIX_PHASE_II in combat.phase_triggered_ids:
        evidence.add("phase:persistencia")
    if MATRIX_PHASE_III in combat.phase_triggered_ids:
        evidence.add("phase:emergencia")
    for action_id in (
        "transferencia_externa",
        "regulacao_emergencia",
        "sobrecarga_matriz",
    ):
        if any(
            event.actor_entity_id == "enemy"
            and event.action.removeprefix("prepare:") == action_id
            for event in combat.events
        ):
            evidence.add(f"action:{action_id}")
    if any(
        event.actor_entity_id == "enemy"
        and event.action.removeprefix("prepare:") == "rota_selada"
        for event in combat.events
    ):
        evidence.add("action:rota_selada")
    if any(
        event.actor_entity_id == "enemy"
        and event.action.removeprefix("prepare:") == "fecho_quarentena"
        for event in combat.events
    ):
        evidence.add("action:fecho_quarentena")
    return tuple(sorted(evidence))
