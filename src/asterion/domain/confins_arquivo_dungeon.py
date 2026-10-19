"""Arquivo do Retorno content on the shared persistent dungeon engine."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Combat, CombatPhaseTrigger
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    CONFINS_ARQUIVO_ECO,
    CONFINS_ARQUIVO_GUARDIAN,
    CONFINS_ARQUIVO_O_QUE_CHEGA_ANTES,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    creature_for,
)

D = Decimal

CONFINS_ARQUIVO_FAMILY_ID = "dungeon.confins.arquivo_retorno"
CONFINS_ARQUIVO_CONTENT_VERSION = "confins-1.0.0"
CONFINS_ARQUIVO_RULESET_VERSION = "dungeon-1.0"
CONFINS_ARQUIVO_DISCOVERY_UNLOCK = "unlock.dungeon.confins.arquivo_retorno"
CONFINS_ARQUIVO_KNOWN_PATH_UNLOCK = CONFINS_ARQUIVO_FAMILY_ID
CONFINS_ARQUIVO_FIRST_CLEAR_PREFIX = f"{CONFINS_ARQUIVO_FAMILY_ID}.first_clear."
CONFINS_ARQUIVO_REWARD_PREFIX = f"{CONFINS_ARQUIVO_FAMILY_ID}.run."
CONFINS_ARQUIVO_CORE_ID = "material.special.confins.core.arquivo_retorno"
CONFINS_ARQUIVO_CORE_NAME = "Núcleo do Arquivo do Retorno"
CONFINS_ARQUIVO_RECIPE_UNLOCK = "recipe.confins.arquivo.relicario_entrada_duplicada"
CONFINS_ARQUIVO_RECIPE_NAME = "Relicário da Entrada Duplicada"
CONFINS_ARQUIVO_BRAZIER_LABEL = "Braseiro da Ala de Retorno"
CONFINS_ARQUIVO_CODEX_ENTRY = "codex.confins.dungeon.arquivo_retorno"
CONFINS_ARQUIVO_RECORD_CODEX_ENTRY = "codex.confins.dungeon.registro_repetido"
CONFINS_ARQUIVO_BOSS_CODEX_ENTRY = "codex.confins.dungeon.chegada_antes"
CONFINS_ARQUIVO_BOSS = CONFINS_ARQUIVO_O_QUE_CHEGA_ANTES
CONFINS_ARQUIVO_PHASE_II = "confins.arquivo.phase.ii"
CONFINS_ARQUIVO_PHASE_III = "confins.arquivo.phase.iii"
CONFINS_ARQUIVO_ENVIRONMENTS = {
    1: "Mesa de Entrada",
    2: "Ala de Registros",
    3: "Corredor de Volta",
    4: "Livro Fechado · Placa de Registro de Entrada e Placa de Registro de Saída",
    5: "Sala do Retorno",
}
CONFINS_ARQUIVO_BASIC_MATERIAL_WEIGHTS = (
    ("material.confins.ferro_baliza", 3_000),
    ("material.confins.couro_marcha", 1_500),
    ("material.confins.musgo_limiar", 2_000),
    ("material.confins.po_referencia", 3_500),
)


def confins_arquivo_encounter_specs(
    ordinal: int, difficulty: str, initial_group_size: int
) -> tuple[CreatureCombatantSpec, ...]:
    if ordinal == 1:
        return (CreatureCombatantSpec(creature_for(CONFINS_ARQUIVO_ECO), 54, "enemy"),)
    if ordinal == 2:
        return (
            CreatureCombatantSpec(creature_for(CONFINS_ARQUIVO_ECO), 55, "eco_1"),
            CreatureCombatantSpec(creature_for(CONFINS_ARQUIVO_ECO), 55, "eco_2"),
        )
    if ordinal == 3:
        return (CreatureCombatantSpec(creature_for(CONFINS_ARQUIVO_GUARDIAN), 56, "enemy"),)
    if ordinal == 4:
        return (CreatureCombatantSpec(creature_for(CONFINS_ARQUIVO_ECO), 57, "enemy"),)
    if ordinal == 5:
        return (
            CreatureCombatantSpec(
                creature_for(CONFINS_ARQUIVO_BOSS),
                57,
                "enemy",
                stat_multipliers=_dungeon_boss_scale(difficulty, initial_group_size),
            ),
        )
    raise ValueError("Arquivo do Retorno encounter ordinal must be between 1 and 5.")


def _dungeon_boss_scale(difficulty: str, group_size: int) -> StatMultipliers:
    profile = DIFFICULTIES[difficulty]
    group_hp = D(1) + D("0.78") * (group_size - 1)
    group_attack = D(1) + D("0.07") * (group_size - 1)
    return StatMultipliers(
        D(3) / D("2.20") * profile.boss_hp_multiplier * group_hp,
        profile.boss_attack_multiplier * group_attack,
        D(1),
        D(1),
    )


def confins_arquivo_enemy_rewards(ordinal: int) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (spec.creature.creature_id, spec.level, spec.creature.category)
        for spec in confins_arquivo_encounter_specs(ordinal, "stable", 1)
        if spec.required_for_victory
    )


def create_confins_arquivo_combat(
    combat_id: UUID,
    *,
    name: str,
    character_class: str,
    race: str,
    hp: Decimal,
    level: int,
    difficulty: str,
    equipment: EquipmentConfigurationSnapshot,
    active_art_ids: tuple[str, ...],
    ordinal: int,
    run_seed: str,
    initial_group_size: int = 1,
    party: tuple[PlayerCombatantSpec, ...] | None = None,
) -> Combat:
    combat = create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        confins_arquivo_encounter_specs(ordinal, difficulty, initial_group_size),
        player_level=level,
        equipment_configuration=equipment,
        active_art_ids=active_art_ids,
        flavor=CONFINS_ARQUIVO_ENVIRONMENTS[ordinal],
        opening_log=f"📖 {CONFINS_ARQUIVO_ENVIRONMENTS[ordinal]}",
        party=party,
    )
    combat.configuration_snapshot = (combat.configuration_snapshot or {}) | {
        "dungeon": {
            "family_id": CONFINS_ARQUIVO_FAMILY_ID,
            "difficulty": difficulty,
            "ordinal": ordinal,
            "seed": run_seed,
            "initial_group_size": initial_group_size,
        }
    }
    if ordinal == 4:
        combat.configuration_snapshot["dungeon"]["contextual_evidence"] = [
            "codex.fragment.confins.arquivo.placa_entrada",
            "codex.fragment.confins.arquivo.placa_saida",
        ]
    for key, action in tuple(combat.enemy_actions.items()):
        if key.endswith("rasura_registro") or key.endswith("revisao_retorno"):
            combat.enemy_actions[key] = replace(
                action,
                effect_id=key,
                skip_if_target_effect_active=key,
            )
    if ordinal != 5:
        return combat

    actions = combat.enemy_actions
    actions["registro_antecipado"] = replace(
        actions["registro_antecipado"],
        cooldown=3,
        effect_stat="agility",
        effect_id="registro_antecipado",
        skip_if_target_effect_active="registro_antecipado",
        phase_ids=("I", "II", "III"),
    )
    actions["marca_chegada"] = replace(
        actions["marca_chegada"], phase_ids=("I", "II", "III")
    )
    actions["cobertura_anterior"] = replace(
        actions["cobertura_anterior"],
        cooldown=4,
        max_uses_per_combat=2,
        self_barrier_hp_fraction=D("0.08"),
        self_barrier_duration=2,
        skip_if_barrier_active=True,
        target_mode="self",
        phase_ids=("II", "III"),
    )
    actions["queda_retorno"] = replace(
        actions["queda_retorno"],
        cooldown=3,
        target_mode="all_opponents",
        phase_ids=("II", "III"),
    )
    actions["retorno_sem_ida"] = replace(
        actions["retorno_sem_ida"],
        prepared=True,
        cooldown=5,
        phase_ids=("III",),
    )
    combat.phase_id = "I"
    combat.phase_triggers = (
        CombatPhaseTrigger(
            CONFINS_ARQUIVO_PHASE_II,
            "enemy",
            D("0.70"),
            phase_id="II",
        ),
        CombatPhaseTrigger(
            CONFINS_ARQUIVO_PHASE_III,
            "enemy",
            D("0.35"),
            phase_id="III",
        ),
    )
    return combat
