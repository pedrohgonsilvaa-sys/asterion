"""Altos Cinéreos' Bastilha Profunda on the shared dungeon engine."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Combat, CombatDamageAura, CombatPhaseTrigger
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    ALTOS_BASTILHA_COORDENADOR_CARGA,
    ALTOS_BASTILHA_CUSTODIO_PONTE,
    ALTOS_BASTILHA_GUARDIAO_CONTRAPESO,
    ALTOS_QUEBRA_CABOS,
    ALTOS_VIGIA_CARGA,
    Creature,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    creature_for,
)

D = Decimal

ALTOS_BASTILHA_FAMILY_ID = "dungeon.altos.bastilha_profunda"
ALTOS_BASTILHA_CONTENT_VERSION = "altos-1.0.1"
ALTOS_BASTILHA_RULESET_VERSION = "dungeon-1.0"
ALTOS_BASTILHA_DISCOVERY_UNLOCK = "unlock.dungeon.altos.bastilha_profunda"
ALTOS_BASTILHA_KNOWN_PATH_UNLOCK = ALTOS_BASTILHA_FAMILY_ID
ALTOS_BASTILHA_FIRST_CLEAR_PREFIX = f"{ALTOS_BASTILHA_FAMILY_ID}.first_clear."
ALTOS_BASTILHA_REWARD_PREFIX = f"{ALTOS_BASTILHA_FAMILY_ID}.run."
ALTOS_BASTILHA_CORE_ID = "material.special.altos.core.bastilha_profunda"
ALTOS_BASTILHA_CORE_NAME = "Núcleo da Bastilha Profunda"
ALTOS_BASTILHA_RECIPE_UNLOCK = "recipe.altos.bastilha.guarda_ordem_profunda"
ALTOS_BASTILHA_RECIPE_NAME = "Guarda da Ordem Profunda"
ALTOS_BASTILHA_BRAZIER_LABEL = "Braseiro da Câmara de Ordem"
ALTOS_BASTILHA_CODEX_ENTRY = "codex.altos.dungeon.bastilha_profunda"
ALTOS_BASTILHA_PROTOCOLS_CODEX_ENTRY = "codex.altos.dungeon.protocolos_prioridade"
ALTOS_BASTILHA_BOSS_CODEX_ENTRY = "codex.altos.dungeon.guardiao_contrapeso"
ALTOS_BASTILHA_GUARDIAN = "boss.altos.bastilha.guardiao_contrapeso"
ALTOS_BASTILHA_ANCHOR_ELEMENT = "encounter_element.altos.bastilha.ponto_ancoragem"
ALTOS_BASTILHA_PHASE_II = "altos.bastilha.phase.ii"
ALTOS_BASTILHA_PHASE_III = "altos.bastilha.phase.iii"
ALTOS_BASTILHA_ENVIRONMENTS = {
    1: "Arquivo de Trânsito",
    2: "Passagem de Serviço",
    3: "Custódio de Ponte",
    4: "Coordenador de Carga",
    5: "Guardião do Contrapeso",
}
ALTOS_BASTILHA_BASIC_MATERIAL_WEIGHTS = (
    ("material.altos.ferro_contrapeso", 5_000),
    ("material.altos.cinza_basalto", 3_500),
    ("material.altos.liquen_pedreira", 1_000),
    ("material.altos.couro_escarpa", 500),
)

_ANCHOR = Creature(
    ALTOS_BASTILHA_ANCHOR_ELEMENT,
    "Ponto de Ancoragem",
    "common",
    "balanced",
    50,
    50,
    0,
    (),
    (),
)


def altos_bastilha_encounter_specs(
    ordinal: int, difficulty: str, initial_group_size: int
) -> tuple[CreatureCombatantSpec, ...]:
    if ordinal == 1:
        return (CreatureCombatantSpec(creature_for(ALTOS_VIGIA_CARGA), 48, "vigia"),)
    if ordinal == 2:
        return (
            CreatureCombatantSpec(creature_for(ALTOS_VIGIA_CARGA), 48, "vigia"),
            CreatureCombatantSpec(creature_for(ALTOS_QUEBRA_CABOS), 48, "quebra_cabos"),
        )
    if ordinal == 3:
        return (
            CreatureCombatantSpec(
                creature_for(ALTOS_BASTILHA_CUSTODIO_PONTE), 49, "custodio_ponte"
            ),
        )
    if ordinal == 4:
        return (
            CreatureCombatantSpec(
                creature_for(ALTOS_BASTILHA_COORDENADOR_CARGA), 49, "coordenador_carga"
            ),
        )
    if ordinal == 5:
        guardian = CreatureCombatantSpec(
            creature_for(ALTOS_BASTILHA_GUARDIAO_CONTRAPESO),
            50,
            "guardiao_contrapeso",
            stat_multipliers=_dungeon_boss_scale(difficulty, initial_group_size),
        )
        anchors = tuple(
            CreatureCombatantSpec(
                _ANCHOR,
                50,
                f"ponto_ancoragem_{index}",
                stat_multipliers=StatMultipliers(D("0.20"), D(1), D("0.80"), D(1)),
                passive=True,
                required_for_victory=False,
                initially_inactive=True,
            )
            for index in (1, 2)
        )
        return (guardian, *anchors)
    raise ValueError("Bastilha Profunda encounter ordinal must be between 1 and 5.")


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


def altos_bastilha_enemy_rewards(ordinal: int) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (spec.creature.creature_id, spec.level, spec.creature.category)
        for spec in altos_bastilha_encounter_specs(ordinal, "stable", 1)
        if spec.required_for_victory
    )


def create_altos_bastilha_combat(
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
    enemies = altos_bastilha_encounter_specs(ordinal, difficulty, initial_group_size)

    def configure(state: Combat) -> None:
        state.configuration_snapshot = (state.configuration_snapshot or {}) | {
            "dungeon": {
                "family_id": ALTOS_BASTILHA_FAMILY_ID,
                "difficulty": difficulty,
                "ordinal": ordinal,
                "seed": run_seed,
                "initial_group_size": initial_group_size,
            }
        }
        if ordinal != 5:
            return

        guardian_key = "guardiao_contrapeso"
        anchor_keys = ("ponto_ancoragem_1", "ponto_ancoragem_2")
        action_prefix = "e0_"
        for key in anchor_keys:
            if key in state.fighters:
                state.fighters[key].encounter_hidden = True
        guardian_action_key = f"{action_prefix}ancora_postura"
        guardian = state.enemy_actions[guardian_action_key]
        state.enemy_actions[guardian_action_key] = replace(
            guardian,
            target_mode="self",
            self_barrier_hp_fraction=D("0.08"),
            max_uses_per_combat=2,
            phase_ids=("I", "II"),
        )
        forced_action_key = f"{action_prefix}redistribuicao_forcada"
        state.enemy_actions[forced_action_key] = replace(
            state.enemy_actions[forced_action_key],
            phase_ids=("III",),
        )
        sweep_action_key = f"{action_prefix}varredura_ponte"
        state.enemy_actions[sweep_action_key] = replace(
            state.enemy_actions[sweep_action_key],
            target_mode="all_opponents",
            phase_ids=("I", "II", "III"),
        )
        for action_id in ("impacto_sustentacao", "linha_carga"):
            action_key = f"{action_prefix}{action_id}"
            state.enemy_actions[action_key] = replace(
                state.enemy_actions[action_key], phase_ids=("I", "II", "III")
            )

        state.phase_id = "I"
        state.damage_auras = (
            *state.damage_auras,
            CombatDamageAura(
                "altos.bastilha.anchor.final_damage_reduction",
                anchor_keys,
                (guardian_key,),
                D("0.05"),
                "per_source",
            ),
        )
        state.phase_triggers = (
            CombatPhaseTrigger(
                ALTOS_BASTILHA_PHASE_II,
                guardian_key,
                D("0.70"),
                activate_fighter_keys=anchor_keys,
                phase_id="II",
            ),
            CombatPhaseTrigger(
                ALTOS_BASTILHA_PHASE_III,
                guardian_key,
                D("0.35"),
                phase_id="III",
            ),
        )

    return create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        enemies,
        player_level=level,
        equipment_configuration=equipment,
        active_art_ids=active_art_ids,
        flavor=ALTOS_BASTILHA_ENVIRONMENTS[ordinal],
        opening_log=f"⛓️ {ALTOS_BASTILHA_ENVIRONMENTS[ordinal]}",
        party=party,
        configure_combat=configure,
    )
