"""Câmara das Contradições content on the shared persistent dungeon engine."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Combat, CombatDamageAura, CombatPhaseTrigger
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.confins_arquivo_dungeon import _dungeon_boss_scale
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    CONFINS_CONTRADICOES_BOSS,
    CONFINS_CONTRADICOES_CUSTODIO,
    CONFINS_CONTRADICOES_PRECEPTOR,
    CONFINS_VIGIA_DESFASADO,
    Creature,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    creature_for,
)

D = Decimal

CONFINS_CONTRADICOES_FAMILY_ID = "dungeon.confins.camara_contradicoes"
CONFINS_CONTRADICOES_CONTENT_VERSION = "confins-1.0.0"
CONFINS_CONTRADICOES_RULESET_VERSION = "dungeon-1.0"
CONFINS_CONTRADICOES_DISCOVERY_UNLOCK = "unlock.dungeon.confins.camara_contradicoes"
CONFINS_CONTRADICOES_KNOWN_PATH_UNLOCK = CONFINS_CONTRADICOES_FAMILY_ID
CONFINS_CONTRADICOES_FIRST_CLEAR_PREFIX = (
    f"{CONFINS_CONTRADICOES_FAMILY_ID}.first_clear."
)
CONFINS_CONTRADICOES_REWARD_PREFIX = f"{CONFINS_CONTRADICOES_FAMILY_ID}.run."
CONFINS_CONTRADICOES_CORE_ID = "material.special.confins.core.camara_contradicoes"
CONFINS_CONTRADICOES_CORE_NAME = "Núcleo da Câmara das Contradições"
CONFINS_CONTRADICOES_RECIPE_UNLOCK = "recipe.confins.contradicoes.guarda_duas_versoes"
CONFINS_CONTRADICOES_RECIPE_NAME = "Guarda das Duas Versões"
CONFINS_CONTRADICOES_BRAZIER_ID = "dungeon_bonfire.confins.contradicoes.patio_referencia"
CONFINS_CONTRADICOES_BRAZIER_LABEL = "Braseiro do Pátio de Referência"
CONFINS_CONTRADICOES_CODEX_ENTRY = "codex.confins.dungeon.camara_contradicoes"
CONFINS_CONTRADICOES_RECORD_CODEX_ENTRY = "codex.confins.dungeon.ordens_irreconciliaveis"
CONFINS_CONTRADICOES_BOSS_CODEX_ENTRY = "codex.confins.dungeon.testemunha_impossivel"
CONFINS_CONTRADICOES_PHASE_II = "confins.contradicoes.phase.ii"
CONFINS_CONTRADICOES_PHASE_III = "confins.contradicoes.phase.iii"
CONFINS_CONTRADICOES_PLATE_KEYS = ("placa_afirmacao_a", "placa_afirmacao_b")
CONFINS_CONTRADICOES_PLATE_IDS = (
    "encounter_element.confins.contradicoes.placa_afirmacao_a",
    "encounter_element.confins.contradicoes.placa_afirmacao_b",
)
CONFINS_CONTRADICOES_BASIC_MATERIAL_WEIGHTS = (
    ("material.confins.ferro_baliza", 4_000),
    ("material.confins.couro_marcha", 1_000),
    ("material.confins.musgo_limiar", 1_500),
    ("material.confins.po_referencia", 3_500),
)

CONFINS_CONTRADICOES_ENVIRONMENTS = {
    1: "Corredor da Referência · Placa documental A",
    2: "Ponto de Controle · Placa documental B",
    3: "Mesa das Ordens · Pátio de Referência",
    4: "Duas Ordens · Registro físico",
    5: "Sala da Testemunha · placas documentais inertes",
}

_AFFIRMATION_PLATE = Creature(
    "encounter_element.confins.contradicoes.placa_afirmacao",
    "Placa de Afirmação",
    "common",
    "balanced",
    60,
    60,
    0,
    (),
    (),
)


def confins_contradicoes_encounter_specs(
    ordinal: int, difficulty: str, initial_group_size: int
) -> tuple[CreatureCombatantSpec, ...]:
    if ordinal == 1:
        return (CreatureCombatantSpec(creature_for(CONFINS_VIGIA_DESFASADO), 58, "vigia"),)
    if ordinal == 2:
        return (
            CreatureCombatantSpec(
                creature_for(CONFINS_CONTRADICOES_CUSTODIO), 59, "custodio"
            ),
        )
    if ordinal == 3:
        return (
            CreatureCombatantSpec(
                creature_for(CONFINS_CONTRADICOES_PRECEPTOR), 60, "preceptor"
            ),
        )
    if ordinal == 4:
        return (
            CreatureCombatantSpec(
                creature_for(CONFINS_CONTRADICOES_CUSTODIO), 60, "custodio"
            ),
            CreatureCombatantSpec(
                creature_for(CONFINS_CONTRADICOES_PRECEPTOR), 60, "preceptor"
            ),
        )
    if ordinal == 5:
        boss = CreatureCombatantSpec(
            creature_for(CONFINS_CONTRADICOES_BOSS),
            60,
            "testemunha",
            stat_multipliers=_dungeon_boss_scale(difficulty, initial_group_size),
        )
        plates = tuple(
            CreatureCombatantSpec(
                replace(
                    _AFFIRMATION_PLATE,
                    creature_id=element_id,
                    name=f"Placa de Afirmação {label}",
                ),
                60,
                key,
                stat_multipliers=StatMultipliers(D("0.25"), D(1), D(1), D(1)),
                passive=True,
                required_for_victory=False,
                initially_inactive=True,
            )
            for key, element_id, label in zip(
                CONFINS_CONTRADICOES_PLATE_KEYS,
                CONFINS_CONTRADICOES_PLATE_IDS,
                ("A", "B"),
                strict=True,
            )
        )
        return (boss, *plates)
    raise ValueError("Câmara das Contradições encounter ordinal must be between 1 and 5.")


def confins_contradicoes_enemy_rewards(
    ordinal: int,
) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (spec.creature.creature_id, spec.level, spec.creature.category)
        for spec in confins_contradicoes_encounter_specs(ordinal, "stable", 1)
        if spec.required_for_victory
    )


def create_confins_contradicoes_combat(
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
    enemies = confins_contradicoes_encounter_specs(ordinal, difficulty, initial_group_size)

    def configure(state: Combat) -> None:
        dungeon_data = {
            "family_id": CONFINS_CONTRADICOES_FAMILY_ID,
            "difficulty": difficulty,
            "ordinal": ordinal,
            "seed": run_seed,
            "initial_group_size": initial_group_size,
            "brazier_id": CONFINS_CONTRADICOES_BRAZIER_ID,
        }
        state.configuration_snapshot = (state.configuration_snapshot or {}) | {
            "dungeon": dungeon_data
        }
        for key in CONFINS_CONTRADICOES_PLATE_KEYS:
            if key in state.fighters:
                state.fighters[key].encounter_hidden = True
        if ordinal != 5:
            for action_key, action in tuple(state.enemy_actions.items()):
                if action.effect_stat in {"defense", "attack", "agility"} and action.duration:
                    state.enemy_actions[action_key] = replace(
                        action,
                        effect_id=action_key,
                        skip_if_target_effect_active=action_key,
                    )
                if action.self_barrier_coefficient > 0 or action.self_barrier_hp_fraction > 0:
                    state.enemy_actions[action_key] = replace(
                        state.enemy_actions[action_key],
                        target_mode="self",
                        skip_if_barrier_active=True,
                    )
            if ordinal == 4:
                state.configuration_snapshot["dungeon"]["contextual_evidence"] = [
                    "codex.fragment.confins.contradicoes.ordem_a",
                    "codex.fragment.confins.contradicoes.ordem_b",
                ]
            return

        boss_key = "testemunha"
        action_prefix = "e0_"
        for action_id in (
            "referencia_incompativel",
            "revisao_contraditoria",
            "placa_evidencia",
            "leitura_sobreposta",
            "afirmacao_final",
        ):
            key = f"{action_prefix}{action_id}"
            action = state.enemy_actions[key]
            phases = ("I", "II", "III")
            if action_id == "leitura_sobreposta":
                action = replace(action, target_mode="all_opponents", phase_ids=("II", "III"))
            elif action_id == "afirmacao_final":
                action = replace(action, prepared=True, phase_ids=("III",))
            elif action_id == "placa_evidencia":
                action = replace(
                    action,
                    cooldown=4,
                    max_uses_per_combat=2,
                    self_barrier_hp_fraction=D("0.08"),
                    self_barrier_duration=2,
                    target_mode="self",
                    skip_if_barrier_active=True,
                    phase_ids=phases,
                )
            elif action_id == "revisao_contraditoria":
                action = replace(
                    action,
                    cooldown=3,
                    effect_stat="defense",
                    effect_id=action_id,
                    skip_if_target_effect_active=action_id,
                    phase_ids=phases,
                )
            else:
                action = replace(action, phase_ids=phases)
            state.enemy_actions[key] = action

        state.damage_auras = (
            *state.damage_auras,
            CombatDamageAura(
                "confins.contradicoes.affirmation_plates",
                CONFINS_CONTRADICOES_PLATE_KEYS,
                (boss_key,),
                D("0.05"),
                "per_source",
            ),
        )
        state.phase_id = "I"
        state.phase_triggers = (
            CombatPhaseTrigger(
                CONFINS_CONTRADICOES_PHASE_II,
                boss_key,
                D("0.70"),
                activate_fighter_keys=CONFINS_CONTRADICOES_PLATE_KEYS,
                phase_id="II",
                resolution_id="affirmation_plates_observed",
            ),
            CombatPhaseTrigger(
                CONFINS_CONTRADICOES_PHASE_III,
                boss_key,
                D("0.35"),
                phase_id="III",
                resolution_id="affirmation_phase_final",
                consume_active_fighter_keys=CONFINS_CONTRADICOES_PLATE_KEYS,
                barrier_source_per_active_fighter_fraction=D("0.05"),
            ),
        )
        state.ai_priorities[boss_key] = (
            f"{action_prefix}placa_evidencia",
            f"{action_prefix}revisao_contraditoria",
            f"{action_prefix}afirmacao_final",
            f"{action_prefix}leitura_sobreposta",
            f"{action_prefix}referencia_incompativel",
        )
        state.ai_priority = state.ai_priorities[boss_key]
        profile = DIFFICULTIES[difficulty]
        state.pressure_start_opportunity = profile.pressure_start
        state.pressure_cap = 5
        state.configuration_snapshot["dungeon"]["affirmation_plate_ids"] = list(
            CONFINS_CONTRADICOES_PLATE_IDS
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
        flavor=CONFINS_CONTRADICOES_ENVIRONMENTS[ordinal],
        opening_log=f"🌫️ {CONFINS_CONTRADICOES_ENVIRONMENTS[ordinal]}",
        pressure_start_opportunity=(
            DIFFICULTIES[difficulty].pressure_start if ordinal == 5 else 0
        ),
        pressure_cap=5 if ordinal == 5 else 0,
        party=party,
        configure_combat=configure,
    )
