"""Altos Cinéreos' Pedreira do Contrapeso on the shared dungeon engine."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import ActionEffect, Combat, CombatPhaseTrigger, CombatStatAura
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    ALTOS_ESCARAVELHO_BASALTO,
    ALTOS_PEDREIRA_OPERARIO,
    ALTOS_PEDREIRA_PESO_SEM_FIM,
    ALTOS_PEDREIRA_PRENSOR,
    Creature,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    creature_for,
)

D = Decimal

ALTOS_PEDREIRA_FAMILY_ID = "dungeon.altos.pedreira_contrapeso"
ALTOS_PEDREIRA_CONTENT_VERSION = "altos-1.0.1"
ALTOS_PEDREIRA_RULESET_VERSION = "dungeon-1.0"
ALTOS_PEDREIRA_DISCOVERY_UNLOCK = "unlock.dungeon.altos.pedreira_contrapeso"
ALTOS_PEDREIRA_KNOWN_PATH_UNLOCK = ALTOS_PEDREIRA_FAMILY_ID
ALTOS_PEDREIRA_FIRST_CLEAR_PREFIX = f"{ALTOS_PEDREIRA_FAMILY_ID}.first_clear."
ALTOS_PEDREIRA_REWARD_PREFIX = f"{ALTOS_PEDREIRA_FAMILY_ID}.run."
ALTOS_PEDREIRA_CORE_ID = "material.special.altos.core.pedreira_contrapeso"
ALTOS_PEDREIRA_CORE_NAME = "Núcleo da Pedreira do Contrapeso"
ALTOS_PEDREIRA_RECIPE_UNLOCK = "recipe.altos.pedreira.relicario_peso_suspenso"
ALTOS_PEDREIRA_RECIPE_NAME = "Relicário do Peso Suspenso"
ALTOS_PEDREIRA_BRAZIER_LABEL = "Braseiro do Trilho Baixo"
ALTOS_PEDREIRA_CODEX_ENTRY = "codex.altos.dungeon.pedreira_contrapeso"
ALTOS_PEDREIRA_CYCLE_CODEX_ENTRY = "codex.altos.dungeon.ciclo_contrapeso"
ALTOS_PEDREIRA_BOSS_CODEX_ENTRY = "codex.altos.dungeon.peso_sem_fim"
ALTOS_PEDREIRA_ENVIRONMENTS = {
    1: "Rampa de Arrasto",
    2: "Plataforma de Transferência",
    3: "Prensor Antigo",
    4: "Pátio de Contrapeso",
    5: "Peso sem Fim",
}
ALTOS_PEDREIRA_BASIC_MATERIAL_WEIGHTS = (
    ("material.altos.ferro_contrapeso", 4500),
    ("material.altos.cinza_basalto", 3500),
    ("material.altos.couro_escarpa", 1000),
    ("material.altos.liquen_pedreira", 1000),
)

_TRAVA_CARGA = Creature(
    "encounter_element.altos.pedreira.trava_carga",
    "Trava de Carga",
    "common",
    "balanced",
    46,
    46,
    0,
    (),
    (),
)


def altos_pedreira_encounter_specs(
    ordinal: int, difficulty: str, initial_group_size: int
) -> tuple[CreatureCombatantSpec, ...]:
    if ordinal == 1:
        return (CreatureCombatantSpec(creature_for(ALTOS_PEDREIRA_OPERARIO), 45, "operario"),)
    if ordinal == 2:
        return (
            CreatureCombatantSpec(creature_for(ALTOS_PEDREIRA_OPERARIO), 45, "operario"),
            CreatureCombatantSpec(creature_for(ALTOS_ESCARAVELHO_BASALTO), 45, "escaravelho"),
        )
    if ordinal == 3:
        return (CreatureCombatantSpec(creature_for(ALTOS_PEDREIRA_PRENSOR), 46, "prensor"),)
    if ordinal == 4:
        return (
            CreatureCombatantSpec(creature_for(ALTOS_PEDREIRA_OPERARIO), 46, "operario"),
            *(
                CreatureCombatantSpec(
                    _TRAVA_CARGA,
                    46,
                    f"trava_{index}",
                    stat_multipliers=StatMultipliers(D("0.20"), D(1), D("0.80"), D(1)),
                    passive=True,
                    required_for_victory=False,
                    defeat_on_zero=False,
                )
                for index in range(1, 4)
            ),
        )
    if ordinal == 5:
        return (
            CreatureCombatantSpec(
                creature_for(ALTOS_PEDREIRA_PESO_SEM_FIM),
                47,
                "peso_sem_fim",
                stat_multipliers=_dungeon_boss_scale(difficulty, initial_group_size),
            ),
        )
    raise ValueError("Altos dungeon encounter ordinal must be between 1 and 5.")


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


def altos_pedreira_enemy_rewards(ordinal: int) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (spec.creature.creature_id, spec.level, spec.creature.category)
        for spec in altos_pedreira_encounter_specs(ordinal, "stable", 1)
        if spec.required_for_victory
    )


def create_altos_pedreira_combat(
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
    enemies = altos_pedreira_encounter_specs(ordinal, difficulty, initial_group_size)

    def configure(state: Combat) -> None:
        state.configuration_snapshot = (state.configuration_snapshot or {}) | {
            "dungeon": {
                "family_id": ALTOS_PEDREIRA_FAMILY_ID,
                "difficulty": difficulty,
                "ordinal": ordinal,
                "seed": run_seed,
                "initial_group_size": initial_group_size,
            }
        }
        if ordinal == 4:
            state.stat_auras = (
                CombatStatAura(
                    "altos.pedreira.trava_carga.defense",
                    "defense",
                    ("trava_1", "trava_2", "trava_3"),
                    ("operario",),
                    D("0.04"),
                ),
            )
        if ordinal != 5:
            return

        elevated = state.enemy_actions["contrapeso_elevado"]
        low = state.enemy_actions["contrapeso_baixo"]
        state.enemy_actions["contrapeso_elevado"] = replace(
            elevated,
            self_effects=(
                ActionEffect(
                    "altos.pedreira.contrapeso_elevado.attack",
                    "attack",
                    D("0.08"),
                    2,
                    "buff",
                ),
                ActionEffect(
                    "altos.pedreira.contrapeso_elevado.defense",
                    "defense",
                    D("0.08"),
                    2,
                    "debuff",
                ),
            ),
            skip_if_any_self_effect_active=(
                "altos.pedreira.contrapeso_elevado.attack",
                "altos.pedreira.contrapeso_baixo.attack",
            ),
            ai_priority_after=(
                "contrapeso_baixo",
                "contrapeso_elevado",
                "queda_massa",
                "cabo_tensao",
                "impacto_carro",
            ),
            phase_ids=("I", "II", "III"),
        )
        state.enemy_actions["contrapeso_baixo"] = replace(
            low,
            self_barrier_hp_fraction=D("0.08"),
            self_barrier_duration=2,
            self_effects=(
                ActionEffect(
                    "altos.pedreira.contrapeso_baixo.attack",
                    "attack",
                    D("0.08"),
                    2,
                    "debuff",
                ),
            ),
            barrier_bound_effect_ids=("altos.pedreira.contrapeso_baixo.attack",),
            skip_if_barrier_active=True,
            skip_if_self_effect_active="altos.pedreira.contrapeso_elevado.attack",
            ai_priority_after=(
                "contrapeso_elevado",
                "contrapeso_baixo",
                "queda_massa",
                "cabo_tensao",
                "impacto_carro",
            ),
            phase_ids=("I", "II"),
        )
        state.enemy_actions["queda_massa"] = replace(
            state.enemy_actions["queda_massa"],
            skip_if_actor_last_action=("queda_massa",),
            phase_ids=("I", "II", "III"),
        )
        for action_id in ("impacto_carro", "cabo_tensao"):
            state.enemy_actions[action_id] = replace(
                state.enemy_actions[action_id], phase_ids=("I", "II", "III")
            )
        state.phase_id = "I"
        state.ai_priorities["enemy"] = ()
        state.phase_triggers = (
            CombatPhaseTrigger(
                "altos.pedreira.phase.ii",
                "enemy",
                D("0.65"),
                phase_id="II",
                ai_priority=(
                    "contrapeso_elevado",
                    "contrapeso_baixo",
                    "queda_massa",
                    "cabo_tensao",
                    "impacto_carro",
                ),
            ),
            CombatPhaseTrigger(
                "altos.pedreira.phase.iii",
                "enemy",
                D("0.30"),
                phase_id="III",
                ai_priority=(
                    "queda_massa",
                    "contrapeso_elevado",
                    "cabo_tensao",
                    "impacto_carro",
                ),
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
        flavor=ALTOS_PEDREIRA_ENVIRONMENTS[ordinal],
        opening_log=f"⛏️ {ALTOS_PEDREIRA_ENVIRONMENTS[ordinal]}",
        party=party,
        configure_combat=configure,
    )
