"""Várzeas dungeons on the shared persistent dungeon combat engine."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import ActionEffect, Combat, CombatPhaseTrigger
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    VARZEAS_DUNGEON_CONDUCTOR,
    VARZEAS_DUNGEON_CURATOR,
    VARZEAS_DUNGEON_EXECUTOR,
    VARZEAS_DUNGEON_PERSISTENT,
    VARZEAS_DUNGEON_TRANSFER_HEART,
    VARZEAS_DUNGEON_TRANSFUSED,
    VARZEAS_GARDEN_GRAFT,
    VARZEAS_HEMARIS_WARDEN,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)

D = Decimal

VARZEAS_INFIRMARY_FAMILY_ID = "dungeon.varzeas.enfermaria_afundada"
VARZEAS_INFIRMARY_CONTENT_VERSION = "varzeas-1.0.2"
VARZEAS_INFIRMARY_RULESET_VERSION = "dungeon-1.0"
VARZEAS_INFIRMARY_LOCATION = "Enfermaria Afundada"
VARZEAS_INFIRMARY_ENTRY_LOCATION = "Brejos do Pulso"
VARZEAS_INFIRMARY_DISCOVERY_UNLOCK = f"{VARZEAS_INFIRMARY_FAMILY_ID}.discovered"
VARZEAS_INFIRMARY_KNOWN_PATH_UNLOCK = VARZEAS_INFIRMARY_FAMILY_ID
VARZEAS_INFIRMARY_FIRST_CLEAR_PREFIX = f"{VARZEAS_INFIRMARY_FAMILY_ID}.first_clear."
VARZEAS_INFIRMARY_REWARD_PREFIX = f"{VARZEAS_INFIRMARY_FAMILY_ID}.run."
VARZEAS_INFIRMARY_CORE_ID = "material.varzeas.nucleo_enfermaria_afundada"
VARZEAS_INFIRMARY_CORE_NAME = "Núcleo da Enfermaria Afundada"
VARZEAS_INFIRMARY_RECIPE_UNLOCK = "recipe.varzeas.enfermaria.mascara_triagem_silenciosa"
VARZEAS_INFIRMARY_RECIPE_NAME = "Máscara da Triagem Silenciosa"
VARZEAS_INFIRMARY_BRAZIER_LABEL = "Braseiro da Enfermaria"
VARZEAS_INFIRMARY_CODEX_ENTRY = "codex.location.enfermaria_afundada"

VARZEAS_CISTERN_FAMILY_ID = "dungeon.varzeas.cisterna_transferencia"
VARZEAS_CISTERN_CONTENT_VERSION = "varzeas-1.0.2"
VARZEAS_CISTERN_RULESET_VERSION = "dungeon-1.0"
VARZEAS_CISTERN_LOCATION = "Cisterna de Transferência"
VARZEAS_CISTERN_ENTRY_LOCATION = "Galerias de Transferência"
VARZEAS_CISTERN_DISCOVERY_UNLOCK = f"{VARZEAS_CISTERN_FAMILY_ID}.discovered"
VARZEAS_CISTERN_KNOWN_PATH_UNLOCK = VARZEAS_CISTERN_FAMILY_ID
VARZEAS_CISTERN_FIRST_CLEAR_PREFIX = f"{VARZEAS_CISTERN_FAMILY_ID}.first_clear."
VARZEAS_CISTERN_REWARD_PREFIX = f"{VARZEAS_CISTERN_FAMILY_ID}.run."
VARZEAS_CISTERN_CORE_ID = "material.varzeas.nucleo_cisterna_transferencia"
VARZEAS_CISTERN_CORE_NAME = "Núcleo da Cisterna de Transferência"
VARZEAS_CISTERN_RECIPE_UNLOCK = "recipe.varzeas.cisterna.peitoral_fluxo_contido"
VARZEAS_CISTERN_RECIPE_NAME = "Peitoral do Fluxo Contido"
VARZEAS_CISTERN_BRAZIER_LABEL = "Braseiro da Cisterna"
VARZEAS_CISTERN_CODEX_ENTRY = "codex.location.cisterna_transferencia"

VARZEAS_DUNGEON_BASIC_MATERIALS = (
    "material.varzeas.ferro_de_salmoura",
    "material.varzeas.couro_de_varzea",
    "material.varzeas.junco_ferruginoso",
    "material.varzeas.soro_antigo",
)
VARZEAS_DUNGEON_CATALYST = "material.varzeas.catalisador_elite_iv"
VARZEAS_DUNGEON_FRAGMENT = "material.varzeas.fragmento_aprimoramento_iv"

VARZEAS_INFIRMARY_ENVIRONMENTS = {
    1: "Triagem Submersa",
    2: "Ala de Retenção",
    3: "Curador Vazio",
    4: "Sala de Persistência",
    5: "O Persistente",
}
VARZEAS_CISTERN_ENVIRONMENTS = {
    1: "Linha de Alimentação",
    2: "Condutor Rubro",
    3: "Câmara de Contenção",
    4: "Executor de Hemaris",
    5: "Coração de Transferência",
}

VARZEAS_PERSISTENT_PHASE_II = "varzeas.infirmary.persistence"
VARZEAS_PERSISTENT_PHASE_III = "varzeas.infirmary.no_discharge"
VARZEAS_HEART_PHASE_II = "varzeas.cistern.increasing_pressure"
VARZEAS_HEART_PHASE_III = "varzeas.cistern.final_transfer"


def varzeas_dungeon_encounter_specs(
    family_id: str,
    ordinal: int,
    difficulty: str,
    initial_group_size: int,
    reference_level: int,
) -> tuple[CreatureCombatantSpec, ...]:
    if family_id == VARZEAS_INFIRMARY_FAMILY_ID:
        if ordinal in {1, 2}:
            return (CreatureCombatantSpec(VARZEAS_DUNGEON_TRANSFUSED, reference_level, "enemy"),)
        if ordinal == 3:
            return (CreatureCombatantSpec(VARZEAS_DUNGEON_CURATOR, reference_level, "enemy"),)
        if ordinal == 4:
            return (
                CreatureCombatantSpec(VARZEAS_DUNGEON_TRANSFUSED, reference_level, "transfused"),
                CreatureCombatantSpec(VARZEAS_GARDEN_GRAFT, reference_level, "graft"),
            )
        if ordinal == 5:
            return (
                CreatureCombatantSpec(
                    VARZEAS_DUNGEON_PERSISTENT,
                    reference_level,
                    "enemy",
                    stat_multipliers=_boss_scale(difficulty, initial_group_size),
                ),
            )
    elif family_id == VARZEAS_CISTERN_FAMILY_ID:
        if ordinal in {1, 3}:
            return (CreatureCombatantSpec(VARZEAS_HEMARIS_WARDEN, reference_level, "enemy"),)
        if ordinal == 2:
            return (CreatureCombatantSpec(VARZEAS_DUNGEON_CONDUCTOR, reference_level, "enemy"),)
        if ordinal == 4:
            return (CreatureCombatantSpec(VARZEAS_DUNGEON_EXECUTOR, reference_level, "enemy"),)
        if ordinal == 5:
            return (
                CreatureCombatantSpec(
                    VARZEAS_DUNGEON_TRANSFER_HEART,
                    reference_level,
                    "enemy",
                    stat_multipliers=_boss_scale(difficulty, initial_group_size),
                ),
            )
    raise ValueError("Várzeas dungeon encounter ordinal must be between 1 and 5.")


def _boss_scale(difficulty: str, group_size: int) -> StatMultipliers:
    profile = DIFFICULTIES[difficulty]
    group_hp = D(1) + D("0.78") * (group_size - 1)
    group_attack = D(1) + D("0.07") * (group_size - 1)
    return StatMultipliers(
        D(3) / D("2.20") * profile.boss_hp_multiplier * group_hp,
        profile.boss_attack_multiplier * group_attack,
        D(1),
        D(1),
    )


def create_varzeas_dungeon_combat(
    combat_id: UUID,
    *,
    family_id: str,
    name: str,
    character_class: str,
    race: str,
    hp: Decimal,
    level: int,
    difficulty: str,
    reference_level: int,
    equipment: EquipmentConfigurationSnapshot,
    active_art_ids: tuple[str, ...],
    ordinal: int,
    run_seed: str,
    initial_group_size: int = 1,
    party: tuple[PlayerCombatantSpec, ...] | None = None,
) -> Combat:
    environments = (
        VARZEAS_INFIRMARY_ENVIRONMENTS
        if family_id == VARZEAS_INFIRMARY_FAMILY_ID
        else VARZEAS_CISTERN_ENVIRONMENTS
        if family_id == VARZEAS_CISTERN_FAMILY_ID
        else None
    )
    if environments is None:
        raise ValueError(f"Unknown Várzeas dungeon family: {family_id}")
    state = create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        varzeas_dungeon_encounter_specs(
            family_id, ordinal, difficulty, initial_group_size, reference_level
        ),
        player_level=level,
        equipment_configuration=equipment,
        active_art_ids=active_art_ids,
        flavor=environments[ordinal],
        opening_log=f"🥀 {environments[ordinal]}",
        party=party,
    )
    state.configuration_snapshot = (state.configuration_snapshot or {}) | {
        "dungeon": {
            "family_id": family_id,
            "difficulty": difficulty,
            "ordinal": ordinal,
            "seed": run_seed,
            "initial_group_size": initial_group_size,
        }
    }
    if ordinal == 5 and family_id == VARZEAS_INFIRMARY_FAMILY_ID:
        state.phase_id = "I"
        for action_id in (
            "protocolo_continuidade",
            "manutencao_repetida",
        ):
            state.enemy_actions[action_id] = replace(
                state.enemy_actions[action_id], phase_ids=("II",)
            )
        state.enemy_actions["intervencao_final"] = replace(
            state.enemy_actions["intervencao_final"], phase_ids=("III",)
        )
        state.phase_triggers = (
            CombatPhaseTrigger(
                VARZEAS_PERSISTENT_PHASE_II, "enemy", D("0.70"), phase_id="II"
            ),
            CombatPhaseTrigger(
                VARZEAS_PERSISTENT_PHASE_III, "enemy", D("0.35"), phase_id="III"
            ),
        )
    elif ordinal == 5 and family_id == VARZEAS_CISTERN_FAMILY_ID:
        state.phase_id = "I"
        state.enemy_actions["linha_aberta"] = replace(
            state.enemy_actions["linha_aberta"],
            self_effects=(
                ActionEffect(
                    "varzeas.cistern.line_open.attack", "attack", D("0.08"), 2, "buff"
                ),
                ActionEffect(
                    "varzeas.cistern.line_open.defense", "defense", D("0.08"), 2, "debuff"
                ),
            ),
            skip_if_self_effect_active="varzeas.cistern.line_closed.attack",
        )
        state.enemy_actions["linha_fechada"] = replace(
            state.enemy_actions["linha_fechada"],
            self_effects=(
                ActionEffect(
                    "varzeas.cistern.line_closed.attack", "attack", D("0.08"), 2, "debuff"
                ),
            ),
            skip_if_self_effect_active="varzeas.cistern.line_open.attack",
            phase_ids=("I", "II"),
        )
        state.enemy_actions["transferencia_final"] = replace(
            state.enemy_actions["transferencia_final"], phase_ids=("III",)
        )
        state.phase_triggers = (
            CombatPhaseTrigger(
                VARZEAS_HEART_PHASE_II, "enemy", D("0.65"), phase_id="II"
            ),
            CombatPhaseTrigger(
                VARZEAS_HEART_PHASE_III, "enemy", D("0.30"), phase_id="III"
            ),
        )
    return state


def varzeas_dungeon_enemy_rewards(
    family_id: str, ordinal: int, reference_level: int
) -> tuple[tuple[str, int, str], ...]:
    specs = varzeas_dungeon_encounter_specs(family_id, ordinal, "stable", 1, reference_level)
    return tuple(
        (spec.creature.creature_id, reference_level, spec.creature.category)
        for spec in specs
        if spec.required_for_victory
    )
