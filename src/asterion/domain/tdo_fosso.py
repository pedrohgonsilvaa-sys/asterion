"""Canonical Fosso das Raízes encounters on the shared dungeon engine."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Combat, CombatDamageAura, CombatPhaseTrigger
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    VDE_HANGING_ROOT,
    VDE_PIT_HANGER,
    VDE_PIT_WEAVER,
    VDE_PULSING_NODE,
    VDE_TANGLED_PILGRIM,
    VDE_VINE_SPIDER,
    VDE_WANDERING_BARK,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)

D = Decimal

FOSSO_FAMILY_ID = "dungeon.vde.fosso_raizes"
FOSSO_CONTENT_VERSION = "vde-1.0.4"
FOSSO_RULESET_VERSION = "dungeon-1.0"
FOSSO_LOCATION = "Fosso das Raízes"
FOSSO_ENTRY_LOCATION = "Mata Suspensa"
FOSSO_DISCOVERY_UNLOCK = FOSSO_FAMILY_ID
# This family has one canonical discoverable unlock, not a second parallel path key.
FOSSO_KNOWN_PATH_UNLOCK = FOSSO_DISCOVERY_UNLOCK
FOSSO_FIRST_CLEAR_PREFIX = f"{FOSSO_FAMILY_ID}.first_clear."
FOSSO_REWARD_PREFIX = f"{FOSSO_FAMILY_ID}.run."
FOSSO_CORE_ID = "material.vde.nucleo_fosso_raizes"
FOSSO_CORE_NAME = "Núcleo do Fosso das Raízes"
FOSSO_RECIPE_UNLOCK = "recipe.vde.fosso.relicario_cordas_mortas"
FOSSO_BRAZIER_LABEL = "Braseiro das Cordas Mortas"
FOSSO_CODEX_ENTRY = "codex.location.fosso_das_raizes"
FOSSO_BASIC_MATERIALS = (
    "material.vde.ferro_enredado",
    "material.vde.couro_musgoso",
    "material.vde.erva_de_turfa",
    "material.vde.resina_enredada",
)
FOSSO_CATALYST = "material.vde.catalisador_elite_ii"
FOSSO_FRAGMENT = "material.vde.fragmento_aprimoramento_ii"

FOSSO_ENVIRONMENTS = {
    1: "Passagem Pendente",
    2: "Emaranhado Inferior",
    3: "Tecelã do Fosso",
    4: "Coração do Emaranhado",
    5: "O Que Pende",
}


def fosso_encounter_specs(
    ordinal: int,
    difficulty: str,
    initial_group_size: int,
    reference_level: int,
) -> tuple[CreatureCombatantSpec, ...]:
    if ordinal == 1:
        return (CreatureCombatantSpec(VDE_VINE_SPIDER, 14, "enemy"),)
    if ordinal == 2:
        return (
            CreatureCombatantSpec(VDE_VINE_SPIDER, 15, "spider"),
            CreatureCombatantSpec(VDE_TANGLED_PILGRIM, 15, "pilgrim"),
        )
    if ordinal == 3:
        return (CreatureCombatantSpec(VDE_PIT_WEAVER, 16, "enemy"),)
    if ordinal == 4:
        # The source percentages are relative to the already resolved Comum Nv.16.
        node_scale = StatMultipliers(D("0.20"), D(0), D("0.80") / D("0.90"), D(0))
        return (
            CreatureCombatantSpec(VDE_WANDERING_BARK, 16, "bark"),
            *(
                CreatureCombatantSpec(
                    VDE_PULSING_NODE,
                    16,
                    f"node_{index}",
                    stat_multipliers=node_scale,
                    passive=True,
                    required_for_victory=False,
                    defeat_on_zero=False,
                )
                for index in range(1, 4)
            ),
        )
    if ordinal == 5:
        profile = DIFFICULTIES[difficulty]
        group_hp = D(1) + D("0.78") * (initial_group_size - 1)
        group_attack = D(1) + D("0.07") * (initial_group_size - 1)
        boss_scale = StatMultipliers(
            D(3) / D("2.20") * profile.boss_hp_multiplier * group_hp,
            profile.boss_attack_multiplier * group_attack,
            D(1),
            D(1),
        )
        root_scale = StatMultipliers(D("0.25"), D(0), D(1), D(0))
        return (
            CreatureCombatantSpec(VDE_PIT_HANGER, 17, "enemy", stat_multipliers=boss_scale),
            CreatureCombatantSpec(
                VDE_HANGING_ROOT,
                17,
                "root_1",
                stat_multipliers=root_scale,
                passive=True,
                required_for_victory=False,
                defeat_on_zero=False,
                initially_inactive=True,
            ),
            CreatureCombatantSpec(
                VDE_HANGING_ROOT,
                17,
                "root_2",
                stat_multipliers=root_scale,
                passive=True,
                required_for_victory=False,
                defeat_on_zero=False,
                initially_inactive=True,
            ),
        )
    raise ValueError("Fosso encounter ordinal must be between 1 and 5.")


def create_fosso_combat(
    combat_id: UUID,
    *,
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
    environment = FOSSO_ENVIRONMENTS[ordinal]
    specs = fosso_encounter_specs(ordinal, difficulty, initial_group_size, reference_level)
    combat = create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        specs,
        player_level=level,
        equipment_configuration=equipment,
        active_art_ids=active_art_ids,
        flavor=environment,
        opening_log=f"🪢 {environment}",
        pressure_start_opportunity=(
            {"stable": 12, "fractured": 10, "rupture": 8}[difficulty]
            if ordinal == 5
            else 0
        ),
        pressure_cap=5 if ordinal == 5 else 0,
        party=party,
    )
    combat.configuration_snapshot = (combat.configuration_snapshot or {}) | {
        "active_arts": [
            {"slot": index + 1, "art_id": art_id}
            for index, art_id in enumerate(active_art_ids)
        ],
        "dungeon": {
            "family_id": FOSSO_FAMILY_ID,
            "difficulty": difficulty,
            "ordinal": ordinal,
            "seed": run_seed,
            "initial_group_size": initial_group_size,
        },
    }
    if ordinal == 4:
        combat.damage_auras = (
            CombatDamageAura(
                "fosso.nodes.barrier_received",
                ("node_1", "node_2", "node_3"),
                ("bark",),
                D(0),
                barrier_received_per_source=D("0.10"),
            ),
        )
    elif ordinal == 5:
        action_prefix = "e0_"  # boss is the first of the boss-plus-support roster.
        despencar_key = f"{action_prefix}despencar"
        combat.enemy_actions[despencar_key] = replace(
            combat.enemy_actions[despencar_key], phase_ids=("III",)
        )
        combat.damage_auras = (
            CombatDamageAura(
                "fosso.roots.boss_damage_reduction",
                ("root_1", "root_2"),
                ("enemy",),
                D("0.05"),
                reduction_mode="any_source",
            ),
        )
        combat.phase_id = "I"
        combat.phase_triggers = (
            CombatPhaseTrigger(
                "fosso.phase.ii",
                "enemy",
                D("0.70"),
                activate_fighter_keys=("root_1", "root_2"),
                phase_id="II",
            ),
            CombatPhaseTrigger(
                "fosso.phase.iii",
                "enemy",
                D("0.35"),
                phase_id="III",
            ),
        )
    return combat


def fosso_enemy_rewards(ordinal: int) -> tuple[tuple[str, int, str], ...]:
    rewards = {
        1: (("aranha_cipo", 14, "common"),),
        2: (("aranha_cipo", 15, "common"), ("peregrino_enredado", 15, "uncommon")),
        3: (("tecela_fosso", 16, "elite"),),
        4: (("casca_errante", 16, "uncommon"),),
        5: (("o_que_pende", 17, "boss"),),
    }
    try:
        return rewards[ordinal]
    except KeyError as exc:
        raise ValueError("Fosso encounter ordinal must be between 1 and 5.") from exc
